#!/usr/bin/env python3
"""
Selector discovery script for Google AI Studio.
Launches Chromium with Wayland, navigates to AI Studio, and dumps DOM info.
"""
import os
import sys
import time
import json
import subprocess
from pathlib import Path

# Set Wayland environment
os.environ['WAYLAND_DISPLAY'] = 'wayland-0'
os.environ['XDG_RUNTIME_DIR'] = '/run/user/1000'

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

PROFILE_DIR = "/opt/ai-orchestrator/var/chromium-profile"
URL = "https://aistudio.google.com/prompts/new_chat"

def clear_locks():
    for lock in Path(PROFILE_DIR).glob("Singleton*"):
        lock.unlink()
        print(f"Removed lock: {lock}")

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
    # Point to system chromium binary
    opts.binary_location = "/usr/bin/chromium"
    svc = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=svc, options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def dump_inputs(driver):
    """Dump all input-like elements."""
    print("\n=== ALL INPUT-LIKE ELEMENTS ===")
    script = """
    var results = [];
    // textareas
    document.querySelectorAll('textarea').forEach(function(el) {
        results.push({
            tag: 'textarea',
            id: el.id,
            name: el.name,
            class: el.className.substring(0, 80),
            placeholder: el.placeholder,
            'aria-label': el.getAttribute('aria-label'),
            'data-testid': el.getAttribute('data-testid'),
            visible: el.offsetParent !== null,
            rect: JSON.stringify(el.getBoundingClientRect())
        });
    });
    // contenteditable divs
    document.querySelectorAll('[contenteditable="true"]').forEach(function(el) {
        results.push({
            tag: el.tagName,
            id: el.id,
            class: el.className.substring(0, 80),
            'aria-label': el.getAttribute('aria-label'),
            'data-testid': el.getAttribute('data-testid'),
            'role': el.getAttribute('role'),
            visible: el.offsetParent !== null,
            rect: JSON.stringify(el.getBoundingClientRect())
        });
    });
    return results;
    """
    elements = driver.execute_script(script)
    for el in elements:
        print(json.dumps(el, indent=2))
    return elements

def dump_buttons(driver):
    """Dump submit/send buttons."""
    print("\n=== BUTTONS ===")
    script = """
    var results = [];
    document.querySelectorAll('button').forEach(function(el) {
        var txt = el.innerText || '';
        var lbl = el.getAttribute('aria-label') || '';
        if (txt.toLowerCase().includes('send') || lbl.toLowerCase().includes('send') ||
            txt.toLowerCase().includes('run') || lbl.toLowerCase().includes('run') ||
            txt.toLowerCase().includes('submit') || el.type === 'submit') {
            results.push({
                tag: 'button',
                id: el.id,
                class: el.className.substring(0, 80),
                text: txt.substring(0, 50),
                'aria-label': lbl,
                'data-testid': el.getAttribute('data-testid'),
                type: el.type,
                visible: el.offsetParent !== null,
                rect: JSON.stringify(el.getBoundingClientRect())
            });
        }
    });
    // Also check mat-icon-button, mat-fab-button etc
    document.querySelectorAll('[mat-icon-button], [matIconButton], .send-button, [class*="send"]').forEach(function(el) {
        var lbl = el.getAttribute('aria-label') || '';
        results.push({
            tag: el.tagName,
            id: el.id,
            class: el.className.substring(0, 80),
            text: (el.innerText || '').substring(0, 50),
            'aria-label': lbl,
            'data-testid': el.getAttribute('data-testid'),
            visible: el.offsetParent !== null,
            rect: JSON.stringify(el.getBoundingClientRect())
        });
    });
    return results;
    """
    elements = driver.execute_script(script)
    for el in elements:
        print(json.dumps(el, indent=2))
    return elements

def dump_response_areas(driver):
    """Dump likely response container elements."""
    print("\n=== RESPONSE-LIKE ELEMENTS ===")
    script = """
    var results = [];
    var selectors = [
        'ms-cmark-node', '.model-response-text', 'message-content',
        '[class*="response"]', '[class*="message"]', '[class*="model"]',
        '[class*="chat"]', '[class*="content"]', '[data-testid*="response"]',
        '[data-testid*="message"]', 'ms-chat-turn', 'ms-prompt-chunk',
        'ms-model-response', 'ms-text-chunk', 'ms-code-chunk'
    ];
    selectors.forEach(function(sel) {
        try {
            document.querySelectorAll(sel).forEach(function(el) {
                var txt = (el.innerText || '').substring(0, 100);
                if (txt.length > 5) {
                    results.push({
                        selector: sel,
                        tag: el.tagName,
                        id: el.id,
                        class: el.className.substring(0, 80),
                        text_preview: txt,
                        visible: el.offsetParent !== null
                    });
                }
            });
        } catch(e) {}
    });
    return results;
    """
    elements = driver.execute_script(script)
    for el in elements:
        print(json.dumps(el, indent=2))
    return elements

def dump_page_source_snippet(driver):
    """Get a snippet around the textarea/contenteditable area."""
    print("\n=== PAGE TITLE & URL ===")
    print(f"URL: {driver.current_url}")
    print(f"Title: {driver.title}")

def check_login(driver):
    """Check if logged in."""
    script = """
    var loginLinks = document.querySelectorAll('a[href*="accounts.google.com/signin"], button[aria-label*="Sign in"]');
    return loginLinks.length;
    """
    count = driver.execute_script(script)
    logged_in = count == 0
    print(f"\n=== LOGIN STATUS ===")
    print(f"Login links found: {count}")
    print(f"Logged in: {logged_in}")
    return logged_in

def main():
    print("Clearing singleton locks...")
    clear_locks()
    
    print("Starting Chromium driver...")
    driver = make_driver()
    
    try:
        print(f"\nNavigating to: {URL}")
        driver.get(URL)
        print("Waiting 8s for page load...")
        time.sleep(8)
        
        dump_page_source_snippet(driver)
        logged_in = check_login(driver)
        
        if not logged_in:
            print("\n⚠️  NOT LOGGED IN — trying to proceed anyway...")
        
        print("\nWaiting additional 5s for dynamic content...")
        time.sleep(5)
        
        inputs = dump_inputs(driver)
        buttons = dump_buttons(driver)
        responses = dump_response_areas(driver)
        
        print("\n=== RAW PAGE SOURCE AROUND INPUTS ===")
        source = driver.page_source
        # Find textarea or contenteditable sections
        import re
        # Look for textarea tags
        ta_matches = [m.start() for m in re.finditer(r'<textarea', source, re.IGNORECASE)]
        for pos in ta_matches[:3]:
            snippet = source[max(0, pos-100):pos+500]
            print(f"\n--- textarea at pos {pos} ---")
            print(snippet)
        
        # Look for contenteditable
        ce_matches = [m.start() for m in re.finditer(r'contenteditable', source, re.IGNORECASE)]
        for pos in ce_matches[:3]:
            snippet = source[max(0, pos-200):pos+300]
            print(f"\n--- contenteditable at pos {pos} ---")
            print(snippet)
        
        # Save full results
        results = {
            'url': driver.current_url,
            'title': driver.title,
            'logged_in': logged_in,
            'inputs': inputs,
            'buttons': buttons,
            'responses': responses
        }
        
        with open('/opt/ai-orchestrator/var/selector_discovery.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("\n✓ Full results saved to /opt/ai-orchestrator/var/selector_discovery.json")
        
        return driver
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        driver.quit()
        return None

if __name__ == "__main__":
    driver = main()
    if driver:
        print("\n=== DRIVER KEPT OPEN ===")
        print("Run subsequent scripts to interact with page")
        # Keep alive briefly for inspection
        time.sleep(2)
        driver.quit()
        print("Driver closed.")
