"""
Generischer OpenAI-kompatibler API-Adapter.

Unterstützt alle Provider in etc/providers.yaml die openai_compatible: true setzen.
Ein einziger Client für: Qwen (Singapore), DeepSeek, Mistral, Groq, OpenRouter.

Verwendung:
    adapter = ApiAdapter("qwen-max")
    result  = adapter.ask("Erkläre Quantencomputing in 3 Sätzen.")
    print(result.text, result.cost_usd)
"""

import os
import time
import logging
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

# Kein LangChain — direkt urllib3 oder requests für minimale Abhängigkeiten
try:
    import urllib3
    import urllib3.request
    _HTTP_LIB = "urllib3"
except ImportError:
    import urllib.request as _urllib_req
    _HTTP_LIB = "stdlib"

log = logging.getLogger(__name__)

_BASE = Path("/opt/ai-orchestrator")
_PROVIDERS_CFG = _BASE / "etc" / "providers.yaml"


# ─────────────────────────────────────────────────────────────
# Konfiguration laden (einmal beim Import, dann gecacht)
# ─────────────────────────────────────────────────────────────

def _load_providers() -> dict:
    with open(_PROVIDERS_CFG) as f:
        return yaml.safe_load(f)

_CFG: dict = _load_providers()


# ─────────────────────────────────────────────────────────────
# Datenstrukturen
# ─────────────────────────────────────────────────────────────

@dataclass
class ApiResult:
    """Rückgabe eines API-Calls — Text + Metadaten für Kostenmonitor."""
    text: str                       # generierter Text
    prompt_tokens: int = 0          # Input-Token laut API
    completion_tokens: int = 0      # Output-Token laut API
    total_tokens: int = 0
    cost_usd: float = 0.0           # berechnete Kosten in USD
    provider: str = ""
    model_id: str = ""              # exakter API-Modellname
    alias: str = ""                 # logischer Alias (z.B. "qwen-max")
    latency_s: float = 0.0
    raw_response: Optional[dict] = field(default=None, repr=False)


@dataclass
class Message:
    """Nachricht für den Chat-Verlauf."""
    role: str    # "system" | "user" | "assistant"
    content: str


# ─────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ─────────────────────────────────────────────────────────────

def _resolve_alias(alias: str) -> tuple[str, str, dict, dict]:
    """
    Löst einen logischen Alias in (provider_name, model_key, provider_cfg, model_cfg) auf.
    Wirft KeyError wenn unbekannt.
    """
    aliases = _CFG.get("aliases", {})
    if alias not in aliases:
        raise KeyError(f"Unbekannter Modell-Alias: '{alias}'. "
                       f"Bekannte: {list(aliases.keys())}")
    provider_name, model_key = aliases[alias]
    provider_cfg = _CFG["providers"][provider_name]
    model_cfg    = provider_cfg["models"][model_key]
    return provider_name, model_key, provider_cfg, model_cfg


def _get_api_key(provider_cfg: dict) -> str:
    """Liest API-Key aus Umgebungsvariable (niemals hardcoded)."""
    env_var = provider_cfg["auth_env"]
    key = os.environ.get(env_var, "").strip()
    if not key:
        raise EnvironmentError(
            f"API-Key-Variable '{env_var}' nicht gesetzt. "
            f"Export setzen: export {env_var}=sk-..."
        )
    return key


def _calculate_cost(model_cfg: dict, prompt_tokens: int, completion_tokens: int) -> float:
    """Berechnet Kosten in USD auf Basis der Preise in providers.yaml."""
    p_in  = model_cfg.get("price_input_per_1m", 0.0)
    p_out = model_cfg.get("price_output_per_1m", 0.0)
    cost  = (prompt_tokens / 1_000_000) * p_in + (completion_tokens / 1_000_000) * p_out
    return round(cost, 8)


def _build_headers(provider_cfg: dict, api_key: str) -> dict:
    """Erstellt HTTP-Header (Authorization + etwaige Extra-Header aus Config)."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    # Optionale Extra-Header (z.B. OpenRouter HTTP-Referer)
    for k, v in provider_cfg.get("extra_headers", {}).items():
        headers[k] = v
    return headers


def _http_post(url: str, headers: dict, payload: dict, timeout_s: int) -> dict:
    """
    HTTP POST mit urllib3 (bevorzugt) oder stdlib als Fallback.
    Gibt geparste JSON-Antwort zurück oder wirft Exception.
    """
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    if _HTTP_LIB == "urllib3":
        http = urllib3.PoolManager(
            timeout=urllib3.Timeout(connect=10, read=timeout_s),
            retries=urllib3.Retry(total=2, backoff_factor=1,
                                  status_forcelist=[429, 500, 502, 503, 504]),
        )
        resp = http.request("POST", url, body=body, headers=headers)
        if resp.status >= 400:
            raise RuntimeError(
                f"API-Fehler {resp.status}: {resp.data.decode('utf-8', errors='replace')[:500]}"
            )
        return json.loads(resp.data.decode("utf-8"))

    else:
        # Stdlib-Fallback (kein Retry-Mechanismus)
        import urllib.request
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)


# ─────────────────────────────────────────────────────────────
# Haupt-Adapter
# ─────────────────────────────────────────────────────────────

class ApiAdapter:
    """
    Generischer OpenAI-kompatibler Client.

    Instanziierung mit logischem Alias aus providers.yaml:
        adapter = ApiAdapter("qwen-max")       # Alibaba Singapore
        adapter = ApiAdapter("deepseek-v3")    # DeepSeek
        adapter = ApiAdapter("mistral-large")  # Mistral EU
        adapter = ApiAdapter("llama-70b")      # Groq (gratis)

    Optional: direkte (provider, model_key)-Angabe:
        adapter = ApiAdapter(provider="groq", model_key="gemma2-9b")
    """

    def __init__(
        self,
        alias: str = "",
        provider: str = "",
        model_key: str = "",
        system_prompt: str = "",
    ):
        if alias:
            self.alias = alias
            (self.provider_name, self.model_key,
             self.provider_cfg, self.model_cfg) = _resolve_alias(alias)
        elif provider and model_key:
            self.alias = f"{provider}/{model_key}"
            self.provider_name = provider
            self.model_key = model_key
            self.provider_cfg = _CFG["providers"][provider]
            self.model_cfg = self.provider_cfg["models"][model_key]
        else:
            raise ValueError("Entweder 'alias' oder 'provider' + 'model_key' angeben.")

        self.system_prompt = system_prompt
        self._api_url = self.provider_cfg["base_url"].rstrip("/") + "/chat/completions"
        self._timeout = self.provider_cfg.get("timeout_s", 60)

        log.debug(
            "ApiAdapter bereit: alias=%s provider=%s model=%s url=%s",
            self.alias, self.provider_name,
            self.model_cfg["model_id"], self._api_url,
        )

    def ask(
        self,
        prompt: str,
        history: list[Message] = None,
        max_tokens: int = None,
        temperature: float = 0.7,
        stream: bool = False,           # Streaming derzeit nicht implementiert
    ) -> ApiResult:
        """
        Sendet einen Prompt und gibt ApiResult zurück.

        history: optionale Vorgeschichte (Liste von Message-Objekten)
        max_tokens: überschreibt den Modell-Default
        """
        if stream:
            raise NotImplementedError("Streaming ist noch nicht implementiert.")

        # ── Nachrichten zusammenstellen ──────────────────────
        messages = []

        # System-Prompt nur einfügen wenn das Modell ihn unterstützt
        if self.system_prompt and self.model_cfg.get("supports_system", True):
            messages.append({"role": "system", "content": self.system_prompt})
        elif self.system_prompt:
            # Modell ohne System-Prompt-Unterstützung (z.B. DeepSeek R1):
            # System-Prompt als erstes User-Message einbetten
            prompt = f"[Systemanweisung: {self.system_prompt}]\n\n{prompt}"
            log.debug("System-Prompt in User-Message eingebettet (Modell unterstützt es nicht nativ)")

        # Verlauf (falls übergeben)
        for msg in (history or []):
            messages.append({"role": msg.role, "content": msg.content})

        # Aktuelle Anfrage
        messages.append({"role": "user", "content": prompt})

        # ── Payload aufbauen ─────────────────────────────────
        max_out = max_tokens or self.model_cfg.get("max_output_tokens", 4096)
        payload = {
            "model":       self.model_cfg["model_id"],
            "messages":    messages,
            "max_tokens":  max_out,
            "temperature": temperature,
        }

        # ── API-Key + Header ─────────────────────────────────
        api_key = _get_api_key(self.provider_cfg)
        headers = _build_headers(self.provider_cfg, api_key)

        # ── Request absetzen ─────────────────────────────────
        log.info(
            "API-Call → %s/%s (%d Zeichen Prompt, %d Token max)",
            self.provider_name, self.model_cfg["model_id"],
            len(prompt), max_out,
        )
        t_start = time.monotonic()

        try:
            resp_json = _http_post(self._api_url, headers, payload, self._timeout)
        except Exception as exc:
            log.error("API-Call fehlgeschlagen (%s/%s): %s",
                      self.provider_name, self.model_cfg["model_id"], exc)
            raise

        latency = time.monotonic() - t_start

        # ── Antwort parsen ───────────────────────────────────
        choice  = resp_json.get("choices", [{}])[0]
        text    = choice.get("message", {}).get("content", "").strip()
        usage   = resp_json.get("usage", {})

        prompt_tokens     = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens      = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost              = _calculate_cost(self.model_cfg, prompt_tokens, completion_tokens)

        result = ApiResult(
            text              = text,
            prompt_tokens     = prompt_tokens,
            completion_tokens = completion_tokens,
            total_tokens      = total_tokens,
            cost_usd          = cost,
            provider          = self.provider_name,
            model_id          = self.model_cfg["model_id"],
            alias             = self.alias,
            latency_s         = round(latency, 3),
            raw_response      = resp_json,
        )

        log.info(
            "API-Antwort erhalten: %d Token (in=%d out=%d) | %.4f USD | %.2f s",
            total_tokens, prompt_tokens, completion_tokens, cost, latency,
        )
        return result

    def chat(
        self,
        messages: list[Message],
        max_tokens: int = None,
        temperature: float = 0.7,
    ) -> ApiResult:
        """
        Low-level Chat-Interface: übergibt beliebige Message-Liste direkt.
        Nützlich für vollständige Konversationssteuerung.
        """
        openai_msgs = [{"role": m.role, "content": m.content} for m in messages]
        api_key     = _get_api_key(self.provider_cfg)
        headers     = _build_headers(self.provider_cfg, api_key)
        max_out     = max_tokens or self.model_cfg.get("max_output_tokens", 4096)

        payload = {
            "model":       self.model_cfg["model_id"],
            "messages":    openai_msgs,
            "max_tokens":  max_out,
            "temperature": temperature,
        }

        t_start  = time.monotonic()
        resp_json = _http_post(self._api_url, headers, payload, self._timeout)
        latency  = time.monotonic() - t_start

        choice  = resp_json.get("choices", [{}])[0]
        text    = choice.get("message", {}).get("content", "").strip()
        usage   = resp_json.get("usage", {})

        prompt_tokens     = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens      = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cost              = _calculate_cost(self.model_cfg, prompt_tokens, completion_tokens)

        return ApiResult(
            text=text, prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens, total_tokens=total_tokens,
            cost_usd=cost, provider=self.provider_name,
            model_id=self.model_cfg["model_id"], alias=self.alias,
            latency_s=round(latency, 3), raw_response=resp_json,
        )


# ─────────────────────────────────────────────────────────────
# Factory-Funktion (bequemer Einstiegspunkt)
# ─────────────────────────────────────────────────────────────

def make_adapter(alias: str, system_prompt: str = "") -> ApiAdapter:
    """Erstellt ApiAdapter anhand logischem Alias. Wirft KeyError bei unbekanntem Alias."""
    return ApiAdapter(alias=alias, system_prompt=system_prompt)


def list_aliases() -> list[str]:
    """Gibt alle konfigurierten Modell-Aliase zurück."""
    return list(_CFG.get("aliases", {}).keys())


def get_model_info(alias: str) -> dict:
    """Gibt Modell-Metadaten zurück (Preise, Limits, etc.)."""
    _, _, provider_cfg, model_cfg = _resolve_alias(alias)
    return {
        "alias": alias,
        "provider": provider_cfg.get("display_name"),
        "base_url": provider_cfg.get("base_url"),
        **model_cfg,
    }


# ─────────────────────────────────────────────────────────────
# Schnelltest (direkt ausführbar)
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    alias   = sys.argv[1] if len(sys.argv) > 1 else "llama-8b"
    prompt  = sys.argv[2] if len(sys.argv) > 2 else "Sag kurz Hallo und nenn dein Modell."

    print(f"\nVerfügbare Aliase: {list_aliases()}\n")
    print(f"Teste Alias: {alias}")
    print(f"Prompt: {prompt}\n")

    try:
        adapter = make_adapter(alias)
        result  = adapter.ask(prompt)
        print(f"─── Antwort ───────────────────────────────────")
        print(result.text)
        print(f"\n─── Metadaten ─────────────────────────────────")
        print(f"  Provider:  {result.provider} / {result.model_id}")
        print(f"  Token:     {result.prompt_tokens} in + {result.completion_tokens} out")
        print(f"  Kosten:    ${result.cost_usd:.6f} USD")
        print(f"  Latenz:    {result.latency_s} s")
    except EnvironmentError as e:
        print(f"FEHLER: {e}")
        print("  Setze den API-Key als Umgebungsvariable und versuche es erneut.")
