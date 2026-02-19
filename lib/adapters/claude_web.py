"""Claude.ai Web-Adapter via Selenium + System-Chromium."""
import pickle
import time
import logging
from pathlib import Path
from typing import Optional

import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from lib.utils.humanizer import think, read_pause, type_text, maybe_scroll, hover_move

log = logging.getLogger(__name__)

with open("/opt/ai-orchestrator/etc/config.yaml") as f:
    CFG = yaml.safe_load(f)

SESSION_FILE = Path("/opt/ai-orchestrator") / CFG["services"]["claude"]["session_file"]
CLAUDE_URL   = CFG["services"]["claude"]["url"]
BR           = CFG["browser"]
HUM          = CFG["humanizer"]
SEL          = CFG.get("selectors", {}).get("claude", {
    "editor": 'div[role="textbox"]',
    "response": '.font-claude-response-body',
    "login_check": '[href="/login"]',
})


PROFILE_DIR = "/opt/ai-orchestrator/var/chromium-profile"

def _clear_singleton_lock():
    """Entfernt Chromium-Lock falls ein früherer Prozess ihn hinterlassen hat."""
    lock = Path(PROFILE_DIR) / "SingletonLock"
    if lock.exists():
        lock.unlink()
        log.debug("SingletonLock entfernt")


def _make_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    # Eigenes Profil — Session bleibt erhalten, kein Keyring-Stress
    opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
    opts.add_argument("--password-store=basic")   # v10 Cookies, kein KWallet
    if headless:
        opts.add_argument("--headless=new")
    else:
        opts.add_argument("--ozone-platform=wayland")
        opts.add_argument("--remote-debugging-port=9222")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument(f"--window-size={BR['window_size'][0]},{BR['window_size'][1]}")
    opts.add_argument(f"--user-agent={BR['user_agent']}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    svc = Service(BR["driver"])
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def _save_session(driver: webdriver.Chrome):
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    cookies = driver.get_cookies()
    with open(SESSION_FILE, "wb") as f:
        pickle.dump(cookies, f)
    log.info("Session gespeichert: %d cookies", len(cookies))


def _load_session(driver: webdriver.Chrome) -> bool:
    if not SESSION_FILE.exists():
        return False
    driver.get(CLAUDE_URL)
    time.sleep(2)
    with open(SESSION_FILE, "rb") as f:
        cookies = pickle.load(f)
    for c in cookies:
        try:
            driver.add_cookie(c)
        except Exception:
            pass
    driver.refresh()
    time.sleep(3)
    return True


def _accept_cookies_if_needed(driver: webdriver.Chrome):
    """Akzeptiert Cookie-Banner automatisch falls vorhanden."""
    try:
        btn = driver.find_element(By.XPATH,
            '//*[contains(text(),"Accept all") or contains(text(),"Alle akzeptieren") '
            'or contains(text(),"Accept cookies") or contains(text(),"I accept")]')
        btn.click()
        log.info("Cookie-Banner akzeptiert")
        time.sleep(1)
    except NoSuchElementException:
        pass


def _is_logged_in(driver: webdriver.Chrome) -> bool:
    """Prüft ob wir eingeloggt sind — URL nicht /login und kein Login-Button."""
    if "/login" in driver.current_url:
        return False
    try:
        driver.find_element(By.CSS_SELECTOR, SEL["login_check"])
        return False
    except NoSuchElementException:
        return True


def login_interactive(driver: webdriver.Chrome):
    """
    Öffnet Claude im nicht-headless Modus damit der User einloggen kann.
    Cookies werden danach gespeichert.
    """
    log.warning("Manueller Login erforderlich. Browser wird geöffnet...")
    driver.get(CLAUDE_URL)
    print("\n>>> Bitte in Claude einloggen, dann Enter drücken <<<")
    input()
    _save_session(driver)
    print("Session gespeichert.")


def _wait_for_response(driver: webdriver.Chrome, timeout: int = 90) -> str:
    """Pollt auf Antwort-Selektor bis Text stabil ist."""
    deadline = time.time() + timeout
    last_text = ""
    stable_count = 0

    while time.time() < deadline:
        time.sleep(3)
        for selector in (SEL["response"], '[data-testid="assistant-message"]', '.prose'):
            els = driver.find_elements(By.CSS_SELECTOR, selector)
            if els:
                text = els[-1].text.strip()
                if text and text == last_text:
                    stable_count += 1
                    if stable_count >= 2:   # 2x gleich = fertig
                        return text
                else:
                    stable_count = 0
                    last_text = text
                break

    log.warning("Timeout — gebe letzten bekannten Text zurück")
    return last_text


class ClaudeAdapter:
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None

    def start(self, headless: bool = True) -> bool:
        """Startet Browser. Profil enthält Session wenn schon eingeloggt wurde."""
        _clear_singleton_lock()
        self.driver = _make_driver(headless=headless)
        self.driver.get(CLAUDE_URL)
        import time as _t; _t.sleep(3)
        _accept_cookies_if_needed(self.driver)

        if _is_logged_in(self.driver):
            log.info("Claude-Session aktiv (Profil erkannt)")
            return True

        if headless:
            log.error("Nicht eingeloggt und headless — erst 'setup-login' ausführen")
            self.stop()
            return False

        log.info("GUI-Modus: warte auf manuellen Login...")
        print("\n>>> Bitte in Claude einloggen, dann Enter drücken <<<")
        input()
        return _is_logged_in(self.driver)

    def ask(self, prompt: str) -> str:
        """Sendet einen Prompt und gibt die Antwort zurück."""
        if not self.driver:
            raise RuntimeError("Adapter nicht gestartet")

        # Neue Unterhaltung starten
        self.driver.get(f"{CLAUDE_URL}/new")
        time.sleep(2)

        maybe_scroll(self.driver, probability=HUM["scroll_probability"])
        think(HUM["min_delay_ms"], HUM["max_delay_ms"])

        # ProseMirror Editor — div[role="textbox"] fängt die Eingabe
        try:
            wait = WebDriverWait(self.driver, 15)
            editor = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, SEL['editor'])
            ))
        except TimeoutException:
            log.error("Editor nicht gefunden")
            return ""

        hover_move(self.driver, editor)
        editor.click()
        time.sleep(0.5)

        # Text tippen
        type_text(self.driver, editor, prompt, typo_rate=HUM["typo_rate"])

        think(400, 900)

        # Absenden
        from selenium.webdriver.common.keys import Keys
        editor.send_keys(Keys.RETURN)

        log.info("Prompt gesendet (%d Zeichen), warte auf Antwort...", len(prompt))

        # Antwort lesen
        response = _wait_for_response(self.driver, timeout=CFG["orchestrator"]["task_timeout_seconds"])

        if response:
            read_pause(len(response))
            _save_session(self.driver)  # Session frisch halten

        return response

    def stop(self):
        if self.driver:
            self.driver.quit()
            self.driver = None


# Schnelltest
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    adapter = ClaudeAdapter()

    print("Starte im GUI-Modus für ersten Login...")
    if adapter.start(headless=False):
        response = adapter.ask("Sag kurz Hallo und nenn deinen Namen.")
        print("Antwort:", response[:200])
    adapter.stop()
