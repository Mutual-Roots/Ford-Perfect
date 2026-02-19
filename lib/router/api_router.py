"""
API-Router-Erweiterung für den bestehenden Classifier.

Entscheidet ob ein Task per direkter API (schnell/günstig) oder per
Browser-Web-Session (Claude.ai, Gemini Studio etc.) bearbeitet wird.

Entscheidungslogik:
  1. Ist für den Task-Typ ein API-Modell konfiguriert (api_routing in rules.yaml)?
  2. Sind alle benötigten API-Keys gesetzt?
  3. Ist das Tages-Budget noch nicht überschritten?
  → Wenn alles ja: API-Pfad, sonst: Web-Adapter-Fallback

Verwendung (im Orchestrator-Hauptprozess):
    from lib.router.api_router import ApiRouter
    router = ApiRouter()
    decision = router.decide(prompt, attachments=[], available_web={"claude","gemini"})
    if decision.use_api:
        result = decision.get_adapter().ask(prompt)
    else:
        result = web_adapters[decision.web_service].ask(prompt)
"""

import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)

_BASE        = Path("/opt/ai-orchestrator")
_RULES_CFG   = _BASE / "etc" / "rules.yaml"
_PROV_CFG    = _BASE / "etc" / "providers.yaml"
_API_RULES   = _BASE / "etc" / "api_rules.yaml"


# ─────────────────────────────────────────────────────────────
# Config laden
# ─────────────────────────────────────────────────────────────

def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


# ─────────────────────────────────────────────────────────────
# Entscheidungsobjekt
# ─────────────────────────────────────────────────────────────

@dataclass
class RoutingDecision:
    """Ergebnis der Routing-Entscheidung."""
    use_api: bool                  # True = API, False = Web-Adapter
    task_type: str = ""

    # API-Pfad
    alias: str = ""                # Modell-Alias (z.B. "qwen-max")
    api_fallback_alias: str = ""   # Fallback-Alias wenn Primary fehlschlägt

    # Web-Pfad
    web_service: str = ""          # z.B. "claude", "gemini"

    # Begründung (für Logging)
    reason: str = ""

    def get_adapter(self):
        """Erstellt ApiAdapter für diese Entscheidung (nur wenn use_api=True)."""
        if not self.use_api:
            raise RuntimeError("get_adapter() nur im API-Modus aufrufbar.")
        from lib.adapters.api_adapter import ApiAdapter
        return ApiAdapter(alias=self.alias)

    def get_fallback_adapter(self):
        """Erstellt Fallback-ApiAdapter (falls Primary fehlschlägt)."""
        if not self.api_fallback_alias:
            return None
        from lib.adapters.api_adapter import ApiAdapter
        return ApiAdapter(alias=self.api_fallback_alias)


# ─────────────────────────────────────────────────────────────
# ApiRouter
# ─────────────────────────────────────────────────────────────

class ApiRouter:
    """
    Ergänzt den bestehenden Router/Classifier um API-Modell-Unterstützung.
    Liest api_routing aus etc/api_rules.yaml (nicht api_rules ist in etc/ — neu erstellen).
    """

    def __init__(self):
        self._rules      = _load_yaml(_RULES_CFG)
        self._providers  = _load_yaml(_PROV_CFG)
        self._api_rules  = _load_yaml(_API_RULES) if _API_RULES.exists() else {}
        self._api_routing = self._api_rules.get("api_routing", {})
        self._strategy   = self._api_rules.get("strategy", {})
        self._aliases    = self._providers.get("aliases", {})

        log.debug(
            "ApiRouter geladen: %d API-Routing-Regeln, Strategie=%s",
            len(self._api_routing),
            self._strategy.get("prefer", "web"),
        )

    def _key_available(self, alias: str) -> bool:
        """Prüft ob der API-Key für diesen Alias in der Umgebung gesetzt ist."""
        if alias not in self._aliases:
            return False
        provider_name, _ = self._aliases[alias]
        env_var = self._providers["providers"][provider_name]["auth_env"]
        key = os.environ.get(env_var, "").strip()
        available = bool(key)
        if not available:
            log.debug("API-Key fehlt für Alias '%s' (Env: %s)", alias, env_var)
        return available

    def _budget_ok(self) -> bool:
        """Schnelle Budget-Prüfung — False wenn Limit überschritten."""
        try:
            from lib.cost_monitor import CostMonitor, BudgetExceeded
            CostMonitor().check_budget()
            return True
        except Exception as exc:
            # BudgetExceeded oder Datenbankfehler
            log.warning("Budget-Check: %s", exc)
            return False

    def decide(
        self,
        prompt: str,
        attachments: list = None,
        available_web: set = None,
        force_api: bool = False,
        force_web: bool = False,
    ) -> RoutingDecision:
        """
        Trifft Routing-Entscheidung: API vs. Web-Adapter.

        prompt:        Eingabetext
        attachments:   Liste von Dateipfaden/URLs (für Classifier)
        available_web: Menge verfügbarer Web-Services (aktive Browser-Sessions)
        force_api:     Erzwingt API-Pfad (Budget-Check wird dennoch durchgeführt)
        force_web:     Erzwingt Web-Adapter-Pfad
        """
        attachments   = attachments or []
        available_web = available_web or set()

        # ── 1. Task-Typ klassifizieren (bestehender Classifier) ──
        from lib.router.classifier import Router
        task_type, web_primary = Router().decide(prompt, attachments, available_web or None)

        log.info("Task-Typ: %s | Web-Primary: %s", task_type, web_primary)

        # ── 2. Erzwingung ─────────────────────────────────────
        if force_web:
            return RoutingDecision(
                use_api=False, task_type=task_type,
                web_service=web_primary, reason="force_web",
            )

        # ── 3. Web-Only Tasks: immer Web-Adapter ─────────────
        web_only = self._api_rules.get("web_only", [])
        if task_type in web_only and not force_api:
            return RoutingDecision(
                use_api=False, task_type=task_type,
                web_service=web_primary,
                reason=f"Task-Typ '{task_type}' ist Web-Only (multimodal/kein API-Äquivalent)",
            )

        # ── 4. Prüfen ob es eine API-Routing-Regel gibt ───────
        api_rule = self._api_routing.get(task_type)
        if not api_rule and not force_api:
            return RoutingDecision(
                use_api=False, task_type=task_type,
                web_service=web_primary,
                reason=f"Keine API-Regel für Task-Typ '{task_type}'",
            )

        # ── 5. Strategie: wann API bevorzugen? ───────────────
        strategy = self._strategy.get("prefer", "api")   # "api" | "web" | "cost"

        if strategy == "web" and not force_api:
            # Web bevorzugt, API nur wenn kein Web-Service verfügbar
            if web_primary and web_primary in available_web:
                return RoutingDecision(
                    use_api=False, task_type=task_type,
                    web_service=web_primary,
                    reason="Strategie=web: Web-Service verfügbar",
                )

        # ── 6. API-Kandidaten auflösen ────────────────────────
        primary_alias  = api_rule.get("primary") if api_rule else None
        fallback_alias = api_rule.get("fallback") if api_rule else None

        # Prüfe Primary
        if primary_alias and self._key_available(primary_alias):
            chosen_alias = primary_alias
        elif fallback_alias and self._key_available(fallback_alias):
            chosen_alias  = fallback_alias
            fallback_alias = None     # kein weiterer Fallback
            log.info("API Primary '%s' nicht verfügbar, nutze Fallback '%s'",
                     primary_alias, chosen_alias)
        else:
            # Kein API-Key → Web-Fallback
            return RoutingDecision(
                use_api=False, task_type=task_type,
                web_service=web_primary,
                reason=f"API-Keys fehlen für '{primary_alias}'/'{fallback_alias}'",
            )

        # ── 7. Budget-Check ───────────────────────────────────
        if not self._budget_ok():
            return RoutingDecision(
                use_api=False, task_type=task_type,
                web_service=web_primary,
                reason="Tages-Budget erschöpft — Fallback auf Web-Adapter",
            )

        # ── 8. Entscheidung: API ──────────────────────────────
        return RoutingDecision(
            use_api=True, task_type=task_type,
            alias=chosen_alias,
            api_fallback_alias=fallback_alias or "",
            reason=f"API-Modell '{chosen_alias}' gewählt (Strategie: {strategy})",
        )

    def available_api_aliases(self) -> list[str]:
        """Gibt alle Aliase zurück für die ein API-Key gesetzt ist."""
        return [a for a in self._aliases if self._key_available(a)]

    def status_report(self) -> dict:
        """Gibt Übersicht über verfügbare API-Modelle zurück (für Health-Check)."""
        report = {}
        for alias in self._aliases:
            provider_name, model_key = self._aliases[alias]
            prov  = self._providers["providers"][provider_name]
            model = prov["models"][model_key]
            env   = prov["auth_env"]
            report[alias] = {
                "provider":  provider_name,
                "model_id":  model["model_id"],
                "key_set":   self._key_available(alias),
                "env_var":   env,
                "tier":      model.get("tier", "?"),
                "cost_in":   model.get("price_input_per_1m", 0),
                "cost_out":  model.get("price_output_per_1m", 0),
            }
        return report


# ─────────────────────────────────────────────────────────────
# Schnelltest
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    router = ApiRouter()

    prompts = [
        ("Schreib mir eine Python-Funktion für Fibonacci", []),
        ("Was sind die neuesten News über OpenAI?", []),
        ("Analysiere dieses Dokument", ["report.pdf"]),
        ("Erkläre Quantencomputing in 3 Sätzen", []),
        ("Übersetze diesen Text auf Deutsch", []),
    ]

    print("\n── API-Routing-Entscheidungen ──────────────────────────")
    for prompt, attachments in prompts:
        d = router.decide(prompt, attachments, available_web={"claude", "gemini", "copilot"})
        if d.use_api:
            print(f"  API  [{d.alias:20s}] [{d.task_type:18s}] | {prompt[:45]}")
        else:
            print(f"  WEB  [{d.web_service:20s}] [{d.task_type:18s}] | {prompt[:45]}")
        print(f"         Grund: {d.reason}")

    print("\n── Verfügbare API-Aliase (Keys gesetzt) ────────────────")
    for alias in router.available_api_aliases():
        print(f"  ✓ {alias}")

    available = router.available_api_aliases()
    missing   = [a for a in router._aliases if a not in available]
    if missing:
        print("\n── API-Keys fehlen (Web-Fallback aktiv) ────────────────")
        for alias in missing:
            env = router._providers["providers"][router._aliases[alias][0]]["auth_env"]
            print(f"  ✗ {alias:20s}  → export {env}=...")
