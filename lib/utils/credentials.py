"""
Verschlüsselte Credential-Verwaltung via Fernet (AES-128-CBC + HMAC-SHA256).
Key liegt in /root/.config/ai-orchestrator/keyfile — niemals im Projekt-Verzeichnis.
"""
import os
import json
import stat
import logging
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger(__name__)

KEY_DIR  = Path("/root/.config/ai-orchestrator")
KEY_FILE = KEY_DIR / "keyfile"
CRED_FILE = Path("/opt/ai-orchestrator/etc/credentials.enc")


def _ensure_keydir():
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    # Nur root darf lesen/schreiben
    KEY_DIR.chmod(0o700)


def get_or_create_key() -> bytes:
    """Lädt oder erstellt den Verschlüsselungs-Key."""
    _ensure_keydir()
    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes().strip()
        return key
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)  # Nur root, kein group/other
    log.info("Neuer Verschlüsselungs-Key erstellt: %s", KEY_FILE)
    return key


def _fernet() -> Fernet:
    return Fernet(get_or_create_key())


def save_credentials(creds: dict):
    """
    Speichert Credentials verschlüsselt.
    creds = {"claude": {"email": "...", "password": "..."}, ...}
    """
    # Input-Validation: nur Strings, keine verschachtelten Objekte
    for service, data in creds.items():
        if not isinstance(service, str) or not all(c.isalnum() or c == '_' for c in service):
            raise ValueError(f"Ungültiger Service-Name: {service!r}")
        for k, v in data.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise ValueError(f"Credentials müssen Strings sein: {k}={v!r}")

    raw = json.dumps(creds).encode()
    encrypted = _fernet().encrypt(raw)
    CRED_FILE.write_bytes(encrypted)
    CRED_FILE.chmod(0o600)
    log.info("Credentials verschlüsselt gespeichert")


def load_credentials(service: str = None) -> dict:
    """Lädt und entschlüsselt Credentials. Optional für einen Service."""
    if not CRED_FILE.exists():
        return {}
    try:
        encrypted = CRED_FILE.read_bytes()
        raw = _fernet().decrypt(encrypted)
        creds = json.loads(raw)
    except InvalidToken:
        log.error("Credentials-Datei konnte nicht entschlüsselt werden — falscher Key?")
        return {}
    except json.JSONDecodeError:
        log.error("Credentials-Datei ist kein gültiges JSON")
        return {}

    if service:
        return creds.get(service, {})
    return creds


def set_credential(service: str, key: str, value: str):
    """Einzelnen Credential-Eintrag setzen/überschreiben."""
    creds = load_credentials()
    if service not in creds:
        creds[service] = {}
    creds[service][key] = value
    save_credentials(creds)
    log.info("Credential gesetzt: %s/%s", service, key)


# CLI für initiales Einrichten
if __name__ == "__main__":
    import getpass
    print("AI Orchestrator — Credentials einrichten")
    print("(Gespeichert verschlüsselt in", CRED_FILE, ")")
    print()

    for service in ("claude", "gemini", "copilot", "openai"):
        print(f"--- {service.upper()} ---")
        email = input(f"  Email (Enter=überspringen): ").strip()
        if not email:
            continue
        password = getpass.getpass(f"  Passwort: ")
        set_credential(service, "email", email)
        set_credential(service, "password", password)
        print(f"  ✓ {service} gespeichert")

    print("\nFertig. Credentials sind verschlüsselt.")
