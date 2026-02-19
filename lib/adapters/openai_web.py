"""OpenAI ChatGPT Web-Adapter via Selenium + System-Chromium."""
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

PROFILE_DIR = "/opt/ai-orchestrator/var/chromium-profile"
OPENAI_URL  = CFG["services"]["openai"]["url"]
BR          = CFG["browser"]
HUM         = CFG["humanizer"]
SEL         = CFG.get("selectors", {}).get("openai", {
    # ChatGPT DOM ist relativ stabil — trotzdem TODO-Marker
    "editor":      '#prompt-textarea, div[contenteditable="true"][data-id="root"]',
    "response":    '.markdown.prose, [data-message-author-role="assistant"] .prose',
    "login_check": '[href="/auth/login"], a[data-testid="login-button"]',
})


def _clear_singleton_lock():
    lock = Path(PROFILE_DIR) / "SingletonLock"
    if lock.exists():
        lock.unlink()


def _make_driver(headless: bool = True) -> webdriver.Chrome:
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
    opts.add_argument("--password-store=basic")
    if headless:
        opts.add_argument("--headless=new")
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


def _is_logged_in(driver: webdriver.Chrome) -> bool:
    if "auth/login" in driver.current_url or "login" in driver.current_url:
        return False
    try:
        driver.find_element(By.CSS_SELECTOR, SEL["login_check"])
        return False
    except NoSuchElementException:
        return True


def _wait_for_response(driver: webdriver.Chrome, timeout: int = 90) -> str:
    deadline = time.time() + timeout
    last_text = ""
    stable_count = 0

    while time.time() < deadline:
        time.sleep(3)
        # ChatGPT zeigt Stop-Button während Streaming — warte bis er weg ist
        stop_btns = driver.find_elements(By.CSS_SELECTOR,
            'button[aria-label="Stop streaming"], button[data-testid="stop-button"]')
        if stop_btns:
            stable_count = 0  # noch am streamen
            continue

        for selector in SEL["response"].split(", "):
            els = driver.find_elements(By.CSS_SELECTOR, selector.strip())
            if els:
                text = els[-1].text.strip()
                if text and text == last_text:
                    stable_count += 1
                    if stable_count >= 2:
                        return text
                else:
                    stable_count = 0
                    last_text = text
                break

    return last_text


class OpenAIAdapter:
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None

    def start(self, headless: bool = True) -> bool:
        _clear_singleton_lock()
        self.driver = _make_driver(headless=headless)
        self.driver.get(OPENAI_URL)
        time.sleep(4)

        if _is_logged_in(self.driver):
            log.info("ChatGPT-Session aktiv")
            return True

        if headless:
            log.error("Nicht eingeloggt — erst setup-login für openai ausführen")
            self.stop()
            return False

        print("\n>>> Bitte in ChatGPT einloggen, dann Enter <<<")
        input()
        return _is_logged_in(self.driver)

    def ask(self, prompt: str) -> str:
        if not self.driver:
            raise RuntimeError("Adapter nicht gestartet")

        self.driver.get(OPENAI_URL)
        time.sleep(3)
        maybe_scroll(self.driver, probability=HUM["scroll_probability"])
        think(HUM["min_delay_ms"], HUM["max_delay_ms"])

        try:
            wait = WebDriverWait(self.driver, 15)
            editor = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, SEL["editor"])
            ))
        except TimeoutException:
            log.error("Eingabefeld nicht gefunden — TODO: Selektor prüfen")
            return ""

        hover_move(self.driver, editor)
        editor.click()
        time.sleep(0.5)
        type_text(self.driver, editor, prompt, typo_rate=HUM["typo_rate"])
        think(400, 900)

        from selenium.webdriver.common.keys import Keys
        editor.send_keys(Keys.RETURN)

        log.info("Prompt gesendet, warte auf Antwort...")
        response = _wait_for_response(self.driver, timeout=CFG["orchestrator"]["task_timeout_seconds"])
        if response:
            read_pause(len(response))
        return response

    def stop(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
