#!/usr/bin/env python3
"""
Full interaction test: send prompt to AI Studio, capture response, discover response selectors.
"""
import os
import sys
import time
import json
from pathlib import Path

os.environ['WAYLAND_DISPLAY'] = 'wayland-0'
os.environ['XDG_RUNTIME_DIR'] = '/run/user/1000'

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException

PROFILE_DIR = "/opt/ai-orchestrator/var/chromium-profile"
URL = "https://aistudio.google.com/prompts/new_chat"
TEST_PROMPT = "Write a bash one-liner to count files in a directory recursively"

def clear_locks():
    for lock in Path(PROFILE_DIR).glob("Singleton*"):
        lock.unlink()
        print(f"  Removed: {lock.name}")

def make_driver():
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
    opts.add_argument("--password-store=basic")
    opts.add_argument("--ozone-platform=wayland")
    opts.add_argument("--enable-features=UseOzonePlatform")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--remote-debugging-port=9222")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.binary_location = "/usr/bin/chromium"
    svc = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def find_input(driver, wait):
    """Find the textarea input. Try multiple selectors."""
    selectors = [
        'textarea[aria-label="Enter a prompt"]',
        'textarea.cdk-textarea-autosize',
        'textarea[placeholder*="prompt"]',
        'textarea',
        'div[contenteditable="true"][aria-label*="prompt"]',
        'div[contenteditable="true"]',
    ]
    for sel in selectors:
        try:
            el = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, sel)))
            print(f"  ✓ Found input with: {sel}")
            return el, sel
        except TimeoutException:
            print(f"  ✗ Not found: {sel}")
            continue
    return None, None

def find_submit(driver):
    """Find the Run/Submit button."""
    selectors = [
        'button.ctrl-enter-submits',
        'button[class*="ctrl-enter-submits"]',
        'button[aria-label="Run"]',
        'button[mattooltip*="Run"]',
    ]
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                print(f"  ✓ Found submit with: {sel}")
                return el, sel
        except NoSuchElementException:
            print(f"  ✗ Not found: {sel}")
    
    # Fallback: find button with text "Run"
    buttons = driver.find_elements(By.TAG_NAME, 'button')
    for btn in buttons:
        if btn.is_displayed():
            txt = btn.text.strip()
            if 'Run' in txt and btn.size['width'] > 0:
                print(f"  ✓ Found run button by text: '{txt[:30]}'")
                return btn, f"button[text contains 'Run']"
    return None, None

def dump_response_elements(driver):
    """Dump all candidate response elements after sending prompt."""
    script = """
    var results = [];
    var selectors = [
        'ms-cmark-node', 'ms-chat-turn', 'ms-model-response', 
        'ms-prompt-chunk', 'ms-text-chunk', 'ms-code-chunk',
        '.model-response-text', 'message-content',
        '[class*="response-text"]', '[class*="model-response"]',
        '[class*="turn-content"]', '[class*="response-container"]',
        'ms-zero-state', '.chat-container',
        '[class*="chat-turn"]', '[class*="chat-response"]',
        'ms-autorender-default', 'ms-markdown',
        'p.default-text', '[data-turn-index]'
    ];
    selectors.forEach(function(sel) {
        try {
            document.querySelectorAll(sel).forEach(function(el) {
                var txt = (el.innerText || '').substring(0, 200).trim();
                if (txt.length > 10) {
                    results.push({
                        selector: sel,
                        tag: el.tagName,
                        class: el.className.substring(0, 100),
                        id: el.id,
                        text_preview: txt,
                        visible: el.offsetParent !== null
                    });
                }
            });
        } catch(e) {}
    });
    return results;
    """
    return driver.execute_script(script)

def wait_for_response(driver, timeout=90):
    """Poll until response stabilizes."""
    response_selectors = [
        'ms-cmark-node',
        'ms-chat-turn',
        'ms-model-response',
        'ms-text-chunk',
        '.model-response-text',
        'message-content',
        '[class*="model-response"]',
        '[class*="response-text"]',
    ]
    
    deadline = time.time() + timeout
    last_text = ""
    stable_count = 0
    found_selector = None
    
    while time.time() < deadline:
        time.sleep(3)
        
        for sel in response_selectors:
            try:
                els = driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    # Get the last/latest model response
                    for el in reversed(els):
                        text = el.text.strip()
                        if text and len(text) > 10:
                            if text == last_text:
                                stable_count += 1
                                if stable_count >= 2:
                                    found_selector = sel
                                    return text, sel
                            else:
                                stable_count = 0
                                last_text = text
                            break
            except Exception:
                pass
        
        elapsed = time.time() - deadline + timeout
        print(f"  Waiting for response... ({elapsed:.0f}s / {timeout}s)")
    
    return last_text, found_selector

def main():
    print("=" * 60)
    print("GEMINI AI STUDIO SELECTOR TEST")
    print("=" * 60)
    
    print("\n[1] Clearing singleton locks...")
    clear_locks()
    
    print("\n[2] Starting Chromium...")
    driver = make_driver()
    wait = WebDriverWait(driver, 20)
    
    try:
        print(f"\n[3] Navigating to AI Studio...")
        driver.get(URL)
        print("  Waiting 10s for page load...")
        time.sleep(10)
        
        print(f"\n  URL: {driver.current_url}")
        print(f"  Title: {driver.title}")
        
        print("\n[4] Finding input field...")
        input_el, input_sel = find_input(driver, wait)
        
        if not input_el:
            print("  ❌ Could not find input field!")
            # Dump all elements for debugging
            els = driver.find_elements(By.TAG_NAME, 'textarea')
            print(f"  Found {len(els)} textarea elements")
            driver.quit()
            return
        
        print("\n[5] Clicking input and typing prompt...")
        input_el.click()
        time.sleep(0.5)
        input_el.clear()
        input_el.send_keys(TEST_PROMPT)
        print(f"  Typed: {TEST_PROMPT}")
        time.sleep(1)
        
        print("\n[6] Finding submit button...")
        submit_el, submit_sel = find_submit(driver)
        
        print("\n[7] Submitting prompt...")
        if submit_el:
            submit_el.click()
            print(f"  Clicked submit button: {submit_sel}")
        else:
            # Fallback: Ctrl+Enter
            input_el.send_keys(Keys.CONTROL, Keys.RETURN)
            print("  Used Ctrl+Enter fallback")
        
        print("\n[8] Waiting for Gemini response (up to 90s)...")
        time.sleep(5)  # Initial wait for response to start
        
        response_text, response_sel = wait_for_response(driver, timeout=90)
        
        print(f"\n[9] Response captured!")
        print(f"  Selector used: {response_sel}")
        print(f"  Response length: {len(response_text)} chars")
        print(f"\n--- RESPONSE ---")
        print(response_text[:500])
        print("--- END ---")
        
        # Now dump all response-like elements for selector confirmation
        print("\n[10] Dumping all response-like elements...")
        resp_elements = dump_response_elements(driver)
        print(f"  Found {len(resp_elements)} response-like elements:")
        seen_selectors = set()
        for el in resp_elements:
            if el['selector'] not in seen_selectors:
                print(f"\n  Selector: {el['selector']}")
                print(f"    Tag: {el['tag']}")
                print(f"    Class: {el['class'][:60]}")
                print(f"    Text: {el['text_preview'][:100]}")
                seen_selectors.add(el['selector'])
        
        # Save results
        results = {
            'input_selector': input_sel,
            'submit_selector': submit_sel,
            'response_selector': response_sel,
            'response_text': response_text,
            'all_response_elements': resp_elements[:20]
        }
        
        with open('/opt/ai-orchestrator/var/interaction_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print("\n✓ Saved to /opt/ai-orchestrator/var/interaction_results.json")
        
        return results
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        # Take screenshot for debugging
        try:
            driver.save_screenshot('/opt/ai-orchestrator/var/debug_screenshot.png')
            print("Screenshot saved to /opt/ai-orchestrator/var/debug_screenshot.png")
        except:
            pass
        raise
    finally:
        print("\nClosing browser...")
        driver.quit()

if __name__ == "__main__":
    main()
