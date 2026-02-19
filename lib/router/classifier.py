"""Regel-basierter Task-Classifier und Service-Router."""
import re
import yaml
from pathlib import Path

CONFIG_PATH = Path("/opt/ai-orchestrator/etc/rules.yaml")


class Router:
    def __init__(self):
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f)
        self.routing = cfg["routing"]
        self.patterns = {
            task_type: [re.compile(p, re.I) for p in patterns]
            for task_type, patterns in cfg.get("patterns", {}).items()
        }

    def classify(self, prompt: str, attachments: list = None) -> str:
        """Bestimmt Task-Typ anhand Prompt + Anhänge."""
        attachments = attachments or []

        # 1. Anhang-basiert (zuverlässigster Indikator)
        exts = [a.rsplit(".", 1)[-1].lower() for a in attachments if "." in a]
        if "pdf" in exts:
            return "pdf_analysis"
        if any(e in exts for e in ("png", "jpg", "jpeg", "webp", "gif")):
            return "image_analysis"

        # 1b. PDF/Bild im Prompt-Text erwähnt (ohne Anhang)
        if re.search(r'\bpdf\b', prompt, re.I):
            return "pdf_analysis"

        # 2. Prompt-Länge als Hinweis auf Kontext
        if len(prompt) > 50000:
            return "long_context"

        # 3. Regex-Pattern-Matching
        for task_type, compiled_patterns in self.patterns.items():
            if any(p.search(prompt) for p in compiled_patterns):
                return task_type

        return "general_qa"

    def route(self, task_type: str, available: set = None) -> list[str]:
        """
        Gibt geordnete Liste von Services zurück (primary first, dann fallbacks).
        available: Set aktiver/verfügbarer Services. None = alle.
        """
        rule = self.routing.get(task_type, self.routing["general_qa"])
        candidates = []

        primary = rule.get("primary")
        fallback = rule.get("fallback")
        only = rule.get("only", False)

        if primary:
            candidates.append(primary)
        if fallback and not only:
            candidates.append(fallback)

        # Filter auf verfügbare Services
        if available is not None:
            candidates = [c for c in candidates if c in available]

        return candidates

    def decide(self, prompt: str, attachments: list = None, available: set = None) -> tuple[str, str]:
        """Kompletter Entscheidungsweg: Prompt → (task_type, service)."""
        task_type = self.classify(prompt, attachments)
        services = self.route(task_type, available)
        if not services:
            services = ["claude"]  # letzter Fallback
        return task_type, services[0]


if __name__ == "__main__":
    r = Router()
    tests = [
        "Schreib mir eine Python-Funktion für Fibonacci",
        "Analysiere dieses PDF-Dokument",
        "Was sind die neuesten News über OpenAI?",
        "Erkläre mir Quantencomputing",
    ]
    for t in tests:
        tt, svc = r.decide(t)
        print(f"  [{tt:20s}] → {svc:10s} | {t[:50]}")
