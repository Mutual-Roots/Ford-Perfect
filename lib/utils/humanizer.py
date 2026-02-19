"""Simuliert menschliches Tipp- und Leseverhalten."""
import time
import random
import math


def _gauss_delay(min_ms: int, max_ms: int) -> float:
    """Gaussian-verteilte Verzögerung — natürlicher als uniform."""
    mid = (min_ms + max_ms) / 2
    sigma = (max_ms - min_ms) / 6
    delay = random.gauss(mid, sigma)
    return max(min_ms, min(max_ms, delay)) / 1000


def think(min_ms: int = 800, max_ms: int = 2500):
    """Pause vor dem Tippen — wie ein Mensch der nachdenkt."""
    time.sleep(_gauss_delay(min_ms, max_ms))


def read_pause(text_length: int):
    """Pause proportional zur Antwortlänge — als würde man lesen."""
    words = text_length / 5  # ~5 Zeichen/Wort
    read_time = words / 250  # ~250 Wörter/Minute
    jitter = random.uniform(0.7, 1.3)
    time.sleep(max(1.0, read_time * jitter))


def type_text(driver, element, text: str, typo_rate: float = 0.02):
    """Tippt Text zeichenweise mit menschlichen Delays und gelegentlichen Tippfehlern."""
    from selenium.webdriver.common.keys import Keys

    for char in text:
        # Tippfehler simulieren
        if random.random() < typo_rate and char.isalpha():
            wrong = random.choice('abcdefghijklmnopqrstuvwxyz')
            element.send_keys(wrong)
            time.sleep(_gauss_delay(80, 200))
            element.send_keys(Keys.BACKSPACE)
            time.sleep(_gauss_delay(100, 300))

        element.send_keys(char)

        # Interpunktion → etwas längere Pause
        if char in '.!?,;:':
            time.sleep(_gauss_delay(150, 500))
        elif char == ' ':
            time.sleep(_gauss_delay(60, 180))
        else:
            time.sleep(_gauss_delay(40, 130))


def maybe_scroll(driver, probability: float = 0.3):
    """Scrollt manchmal etwas runter — wie ein Mensch der die Seite scannt."""
    if random.random() < probability:
        scroll_px = random.randint(100, 400)
        driver.execute_script(f"window.scrollBy(0, {scroll_px})")
        time.sleep(_gauss_delay(400, 1200))


def hover_move(driver, element):
    """Bewegt Maus zu Element — vermeidet direktes Teleportieren."""
    from selenium.webdriver.common.action_chains import ActionChains
    actions = ActionChains(driver)
    actions.move_to_element(element)
    actions.pause(_gauss_delay(200, 600))
    actions.perform()
