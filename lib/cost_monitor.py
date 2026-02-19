"""
Kostenmonitor für API-Calls.

Speichert jeden API-Call in SQLite (var/api_costs.db) und prüft
das Tages-Budget aus etc/providers.yaml.

Verwendung:
    from lib.cost_monitor import CostMonitor
    monitor = CostMonitor()
    monitor.record(result)                    # ApiResult einbuchen
    monitor.check_budget()                    # Wirft BudgetExceeded wenn Limit erreicht
    stats = monitor.today_stats()             # Tagesübersicht
    monitor.print_report()                    # Health-Check-Ausgabe
"""

import sqlite3
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)

_BASE   = Path("/opt/ai-orchestrator")
_DB     = _BASE / "var" / "api_costs.db"
_CFG    = _BASE / "etc" / "providers.yaml"


# ─────────────────────────────────────────────────────────────
# Schema
# ─────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS api_calls (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                REAL    NOT NULL,          -- Unix-Timestamp (UTC)
    date_utc          TEXT    NOT NULL,          -- YYYY-MM-DD (für Tages-Grouping)
    alias             TEXT    NOT NULL,          -- logischer Alias (z.B. "qwen-max")
    provider          TEXT    NOT NULL,          -- provider-Name
    model_id          TEXT    NOT NULL,          -- exakter API-Modellname
    prompt_tokens     INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens      INTEGER NOT NULL DEFAULT 0,
    cost_usd          REAL    NOT NULL DEFAULT 0.0,
    latency_s         REAL    NOT NULL DEFAULT 0.0,
    task_type         TEXT,                      -- aus dem Router (optional)
    task_id           TEXT,                      -- Queue-Task-ID (optional)
    ok                INTEGER NOT NULL DEFAULT 1 -- 1=Erfolg, 0=Fehler
);

CREATE INDEX IF NOT EXISTS idx_date ON api_calls(date_utc);
CREATE INDEX IF NOT EXISTS idx_alias ON api_calls(alias);

CREATE TABLE IF NOT EXISTS budget_events (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        REAL    NOT NULL,
    date_utc  TEXT    NOT NULL,
    event     TEXT    NOT NULL,   -- "warn" | "exceeded"
    spend_usd REAL    NOT NULL,
    limit_usd REAL    NOT NULL
);
"""


# ─────────────────────────────────────────────────────────────
# Ausnahme
# ─────────────────────────────────────────────────────────────

class BudgetExceeded(Exception):
    """Wird geworfen wenn das Tages-Budget überschritten ist."""
    def __init__(self, spent: float, limit: float):
        self.spent = spent
        self.limit = limit
        super().__init__(
            f"Tages-Budget überschritten: ${spent:.4f} ausgegeben, Limit ${limit:.2f}. "
            f"Keine weiteren API-Calls bis UTC-Mitternacht."
        )


# ─────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────

def _today_utc() -> str:
    """Aktuelles UTC-Datum als YYYY-MM-DD."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_budget_cfg() -> dict:
    with open(_CFG) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("budget", {
        "daily_usd": 5.00,
        "warn_at_usd": 3.00,
    })


# ─────────────────────────────────────────────────────────────
# CostMonitor-Klasse
# ─────────────────────────────────────────────────────────────

class CostMonitor:
    def __init__(self, db_path: Path = _DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._budget = _load_budget_cfg()

    @contextmanager
    def _conn(self):
        con = sqlite3.connect(str(self.db_path), timeout=10)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _init_db(self):
        with self._conn() as con:
            con.executescript(_SCHEMA)
        log.debug("Kosten-DB bereit: %s", self.db_path)

    # ──────────────────────────────────────────────────────────
    # Eintragen
    # ──────────────────────────────────────────────────────────

    def record(
        self,
        result,                         # ApiResult-Objekt aus api_adapter
        task_type: str = None,
        task_id: str = None,
        ok: bool = True,
    ):
        """Bucht einen API-Call in die Datenbank ein."""
        now = time.time()
        date = _today_utc()
        with self._conn() as con:
            con.execute(
                """
                INSERT INTO api_calls
                  (ts, date_utc, alias, provider, model_id,
                   prompt_tokens, completion_tokens, total_tokens,
                   cost_usd, latency_s, task_type, task_id, ok)
                VALUES (?,?,?,?,?, ?,?,?, ?,?,?,?,?)
                """,
                (
                    now, date,
                    result.alias, result.provider, result.model_id,
                    result.prompt_tokens, result.completion_tokens, result.total_tokens,
                    result.cost_usd, result.latency_s,
                    task_type, task_id, int(ok),
                ),
            )
        log.debug("Cost recorded: alias=%s cost=%.6f USD", result.alias, result.cost_usd)

    def record_error(
        self,
        alias: str,
        provider: str,
        model_id: str,
        task_type: str = None,
        task_id: str = None,
    ):
        """Erfasst einen fehlgeschlagenen API-Call (0 Token, 0 Kosten, ok=0)."""
        now  = time.time()
        date = _today_utc()
        with self._conn() as con:
            con.execute(
                """
                INSERT INTO api_calls
                  (ts, date_utc, alias, provider, model_id,
                   prompt_tokens, completion_tokens, total_tokens,
                   cost_usd, latency_s, task_type, task_id, ok)
                VALUES (?,?,?,?,?, 0,0,0, 0.0,0.0,?,?,0)
                """,
                (now, date, alias, provider, model_id, task_type, task_id),
            )

    # ──────────────────────────────────────────────────────────
    # Budget-Prüfung
    # ──────────────────────────────────────────────────────────

    def today_spend(self, date: str = None) -> float:
        """Gibt heutige Gesamtausgaben in USD zurück."""
        date = date or _today_utc()
        with self._conn() as con:
            row = con.execute(
                "SELECT COALESCE(SUM(cost_usd), 0.0) FROM api_calls WHERE date_utc=? AND ok=1",
                (date,),
            ).fetchone()
        return float(row[0])

    def check_budget(self):
        """
        Prüft ob das Tages-Budget noch nicht überschritten wurde.
        Wirft BudgetExceeded wenn Limit erreicht. Loggt Warnung wenn Warnschwelle erreicht.
        """
        limit   = float(self._budget.get("daily_usd", 5.00))
        warn_at = float(self._budget.get("warn_at_usd", 3.00))
        spent   = self.today_spend()

        if spent >= limit:
            self._log_budget_event("exceeded", spent, limit)
            raise BudgetExceeded(spent, limit)

        if spent >= warn_at:
            log.warning(
                "Budget-Warnung: $%.4f von $%.2f verbraucht (%.0f%%)",
                spent, limit, (spent / limit) * 100,
            )
            self._log_budget_event("warn", spent, limit)

    def _log_budget_event(self, event: str, spent: float, limit: float):
        """Schreibt Budget-Ereignis in eigene Tabelle (dedupliziert nach Stunde)."""
        date = _today_utc()
        now  = time.time()
        with self._conn() as con:
            # Nur einmal pro Stunde loggen um Spam zu vermeiden
            one_hour_ago = now - 3600
            exists = con.execute(
                "SELECT 1 FROM budget_events WHERE date_utc=? AND event=? AND ts>?",
                (date, event, one_hour_ago),
            ).fetchone()
            if not exists:
                con.execute(
                    "INSERT INTO budget_events (ts, date_utc, event, spend_usd, limit_usd) VALUES (?,?,?,?,?)",
                    (now, date, event, spent, limit),
                )

    # ──────────────────────────────────────────────────────────
    # Statistiken
    # ──────────────────────────────────────────────────────────

    def today_stats(self, date: str = None) -> dict:
        """Liefert Tages-Statistiken als Dictionary."""
        date = date or _today_utc()
        with self._conn() as con:
            # Gesamt
            total_row = con.execute(
                """SELECT COUNT(*) as calls, COALESCE(SUM(prompt_tokens),0) as pt,
                          COALESCE(SUM(completion_tokens),0) as ct,
                          COALESCE(SUM(total_tokens),0) as tt,
                          COALESCE(SUM(cost_usd),0.0) as cost,
                          COALESCE(AVG(latency_s),0.0) as avg_lat
                   FROM api_calls WHERE date_utc=? AND ok=1""",
                (date,),
            ).fetchone()

            # Pro Provider
            by_provider = con.execute(
                """SELECT provider, COUNT(*) as calls,
                          COALESCE(SUM(total_tokens),0) as tokens,
                          COALESCE(SUM(cost_usd),0.0) as cost
                   FROM api_calls WHERE date_utc=? AND ok=1
                   GROUP BY provider ORDER BY cost DESC""",
                (date,),
            ).fetchall()

            # Pro Alias
            by_alias = con.execute(
                """SELECT alias, COUNT(*) as calls,
                          COALESCE(SUM(total_tokens),0) as tokens,
                          COALESCE(SUM(cost_usd),0.0) as cost
                   FROM api_calls WHERE date_utc=? AND ok=1
                   GROUP BY alias ORDER BY cost DESC""",
                (date,),
            ).fetchall()

            # Fehler
            errors = con.execute(
                "SELECT COUNT(*) FROM api_calls WHERE date_utc=? AND ok=0",
                (date,),
            ).fetchone()[0]

        limit = float(self._budget.get("daily_usd", 5.00))
        spend = float(total_row["cost"])

        return {
            "date":            date,
            "total_calls":     total_row["calls"],
            "total_errors":    errors,
            "prompt_tokens":   total_row["pt"],
            "completion_tokens": total_row["ct"],
            "total_tokens":    total_row["tt"],
            "cost_usd":        spend,
            "budget_usd":      limit,
            "budget_used_pct": round((spend / limit) * 100, 1) if limit else 0,
            "avg_latency_s":   round(total_row["avg_lat"], 3),
            "by_provider":     [dict(r) for r in by_provider],
            "by_alias":        [dict(r) for r in by_alias],
        }

    def recent_calls(self, n: int = 20, date: str = None) -> list[dict]:
        """Gibt die letzten n API-Calls zurück."""
        date = date or _today_utc()
        with self._conn() as con:
            rows = con.execute(
                """SELECT ts, alias, provider, model_id, total_tokens, cost_usd,
                          latency_s, task_type, ok
                   FROM api_calls WHERE date_utc=?
                   ORDER BY ts DESC LIMIT ?""",
                (date, n),
            ).fetchall()
        return [dict(r) for r in rows]

    def last_n_days(self, n: int = 7) -> list[dict]:
        """Aggregiert Ausgaben der letzten n Tage."""
        with self._conn() as con:
            rows = con.execute(
                """SELECT date_utc, COUNT(*) as calls,
                          COALESCE(SUM(total_tokens),0) as tokens,
                          COALESCE(SUM(cost_usd),0.0) as cost
                   FROM api_calls WHERE ok=1
                   GROUP BY date_utc
                   ORDER BY date_utc DESC LIMIT ?""",
                (n,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ──────────────────────────────────────────────────────────
    # Health-Check-Ausgabe (für bin/health-check)
    # ──────────────────────────────────────────────────────────

    def print_report(self):
        """Gibt formatierten Kosten-Report für den Health-Check aus."""
        s = self.today_stats()
        limit = s["budget_usd"]
        spend = s["cost_usd"]
        pct   = s["budget_used_pct"]

        # Budget-Balken (20 Zeichen)
        filled = min(int(pct / 5), 20)
        bar    = "█" * filled + "░" * (20 - filled)
        warn   = " ⚠" if pct >= 60 else ("  🛑" if pct >= 100 else "")

        print("╠══════════════════════════════════════╣")
        print("║         API-Kosten (heute, UTC)      ║")
        print("╠══════════════════════════════════════╣")
        print(f"  Calls:    {s['total_calls']:>4}  (Fehler: {s['total_errors']})")
        print(f"  Token:    {s['total_tokens']:>8,}")
        print(f"  Ausgaben: ${spend:>7.4f} / ${limit:.2f}{warn}")
        print(f"  Budget:   [{bar}] {pct:.0f}%")
        print(f"  Ø Latenz: {s['avg_latency_s']:.2f} s")

        if s["by_provider"]:
            print("  ─── Nach Provider ───────────────────")
            for p in s["by_provider"]:
                print(f"    {p['provider']:12s} {p['calls']:3d} calls  "
                      f"{p['tokens']:>8,} tk  ${p['cost']:.4f}")

        # 7-Tage-Verlauf kompakt
        history = self.last_n_days(7)
        if len(history) > 1:
            print("  ─── 7-Tage-Verlauf ──────────────────")
            for h in history:
                print(f"    {h['date_utc']}  {h['calls']:3d} calls  ${h['cost']:.4f}")


# ─────────────────────────────────────────────────────────────
# Schnelltest
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from lib.adapters.api_adapter import ApiResult

    monitor = CostMonitor()

    # Fake-Ergebnis eintragen (für Test ohne echte API)
    fake = ApiResult(
        text="Testantwort", prompt_tokens=100, completion_tokens=50,
        total_tokens=150, cost_usd=0.000015, provider="groq",
        model_id="llama-3.1-8b-instant", alias="llama-8b", latency_s=0.45,
    )
    monitor.record(fake, task_type="general_qa", task_id="test-001")
    print("Eingebucht.")

    stats = monitor.today_stats()
    print(f"Heutige Ausgaben: ${stats['cost_usd']:.6f} USD über {stats['total_calls']} Calls")
    monitor.print_report()
