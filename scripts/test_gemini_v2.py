#!/usr/bin/env python3
"""
Improved Gemini interaction test - waits for full response and digs deeper into DOM.
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

def get_response_deep(driver):
    """Deep DOM inspection for Gemini response after sending."""
    script = """
    var results = {};
    
    // Strategy 1: Find ms-chat-turn elements and look at their inner content
    var turns = document.querySelectorAll('ms-chat-turn');
    results.chat_turns = [];
    turns.forEach(function(turn, idx) {
        var textContent = turn.innerText || turn.textContent || '';
        var html = turn.innerHTML.substring(0, 500);
        results.chat_turns.push({
            index: idx,
            text_len: textContent.length,
            text_preview: textContent.substring(0, 300),
            classes: turn.className,
            html_preview: html
        });
    });
    
    // Strategy 2: All paragraphs with substantial text 
    var paras = document.querySelectorAll('p, span, div');
    results.substantial_text = [];
    paras.forEach(function(el) {
        var directText = '';
        el.childNodes.forEach(function(node) {
            if (node.nodeType === 3) directText += node.textContent;
        });
        var txt = directText.trim();
        if (txt.length > 50 && txt.length < 2000) {
            results.substantial_text.push({
                tag: el.tagName,
                class: el.className.substring(0, 80),
                id: el.id,
                text: txt.substring(0, 200)
            });
        }
    });
    
    // Strategy 3: Check if response is still streaming
    var spinners = document.querySelectorAll('[class*="loading"], [class*="spinner"], [class*="progress"], mat-progress-spinner, mat-progress-bar');
    results.loading_indicators = spinners.length;
    
    // Strategy 4: Look for code blocks (our prompt asked for bash code)
    var codeBlocks = document.querySelectorAll('code, pre, .code-block, [class*="code"]');
    results.code_blocks = [];
    codeBlocks.forEach(function(el) {
        var txt = (el.innerText || '').trim();
        if (txt.length > 5) {
            results.code_blocks.push({
                tag: el.tagName,
                class: el.className.substring(0, 80),
                text: txt.substring(0, 200)
            });
        }
    });
    
    // Strategy 5: ms-autorender-default or similar Angular components
    var angularComponents = [
        'ms-autorender-default', 'ms-markdown-viewer', 'ms-markdown',
        'ms-prompt-chunk', 'ms-model-response-chunk', 'ms-cmark-node',
        'ms-zero-state', 'ms-response-container', 'ms-run-chip'
    ];
    results.angular_components = {};
    angularComponents.forEach(function(comp) {
        var els = document.querySelectorAll(comp);
        if (els.length > 0) {
            var texts = [];
            els.forEach(function(el) {
                var txt = (el.innerText || '').trim();
                if (txt.length > 5) texts.push(txt.substring(0, 300));
            });
            if (texts.length > 0) {
                results.angular_components[comp] = texts;
            }
        }
    });
    
    return results;
    """
    return driver.execute_script(script)


def wait_for_full_response(driver, timeout=120):
    """Wait for Gemini response to complete streaming."""
    print("  Waiting for response to start appearing...")
    
    # First, wait for zero-state to disappear or chat-turn to appear with content
    deadline = time.time() + timeout
    check_interval = 3
    last_content_len = 0
    stable_count = 0
    
    while time.time() < deadline:
        time.sleep(check_interval)
        
        data = get_response_deep(driver)
        
        loading = data.get('loading_indicators', 0)
        turns = data.get('chat_turns', [])
        code_blocks = data.get('code_blocks', [])
        angular = data.get('angular_components', {})
        substantial = data.get('substantial_text', [])
        
        elapsed = time.time() - deadline + timeout
        
        # Check for code (our test prompt should produce code)
        if code_blocks:
            code_text = ' '.join(cb['text'] for cb in code_blocks)
            if 'find' in code_text.lower() or 'wc' in code_text.lower() or 'ls' in code_text.lower():
                if code_text == last_content_len:
                    stable_count += 1
                    if stable_count >= 2:
                        print(f"  ✓ Code response stable after {elapsed:.0f}s")
                        return data, 'code'
                else:
                    stable_count = 0
                    last_content_len = code_text
        
        # Check turns with substantial content
        total_text = sum(t['text_len'] for t in turns)
        print(f"  [{elapsed:.0f}s] Turns: {len(turns)}, Total text: {total_text} chars, "
              f"Loading: {loading}, Code blocks: {len(code_blocks)}")
        
        if total_text > 100 and loading == 0:
            if total_text == last_content_len:
                stable_count += 1
                if stable_count >= 2:
                    print(f"  ✓ Response stable after {elapsed:.0f}s")
                    return data, 'stable'
            else:
                stable_count = 0
                last_content_len = total_text
    
    print(f"  ⚠ Timeout reached")
    return get_response_deep(driver), 'timeout'

def main():
    print("=" * 60)
    print("GEMINI AI STUDIO FULL INTERACTION TEST v2")
    print("=" * 60)
    
    print("\n[1] Clearing locks and starting Chromium...")
    clear_locks()
    driver = make_driver()
    wait = WebDriverWait(driver, 20)
    
    try:
        print(f"\n[2] Loading AI Studio...")
        driver.get(URL)
        time.sleep(10)
        print(f"  Title: {driver.title}")
        print(f"  URL: {driver.current_url}")
        
        # Take initial screenshot
        driver.save_screenshot('/opt/ai-orchestrator/var/screenshot_initial.png')
        print("  Screenshot: /opt/ai-orchestrator/var/screenshot_initial.png")
        
        print(f"\n[3] Finding and filling input...")
        input_el = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, 'textarea[aria-label="Enter a prompt"]')
        ))
        input_el.click()
        time.sleep(0.5)
        input_el.send_keys(TEST_PROMPT)
        print(f"  Typed prompt: {TEST_PROMPT}")
        time.sleep(1)
        
        print(f"\n[4] Clicking Run button...")
        run_btn = driver.find_element(By.CSS_SELECTOR, 'button.ctrl-enter-submits')
        run_btn.click()
        print("  Run clicked!")
        
        driver.save_screenshot('/opt/ai-orchestrator/var/screenshot_sent.png')
        
        print(f"\n[5] Waiting for response...")
        time.sleep(5)  # Initial grace period
        data, status = wait_for_full_response(driver, timeout=120)
        
        driver.save_screenshot('/opt/ai-orchestrator/var/screenshot_response.png')
        print(f"  Status: {status}")
        
        print(f"\n[6] Response analysis:")
        turns = data.get('chat_turns', [])
        print(f"  Chat turns found: {len(turns)}")
        for i, turn in enumerate(turns):
            print(f"\n  Turn {i}: text_len={turn['text_len']}, class='{turn['classes'][:50]}'")
            print(f"    Text preview: {turn['text_preview'][:200]}")
        
        print(f"\n  Code blocks found: {len(data.get('code_blocks', []))}")
        for cb in data.get('code_blocks', []):
            print(f"    [{cb['tag']}] {cb['text'][:100]}")
        
        print(f"\n  Angular components with content:")
        for comp, texts in data.get('angular_components', {}).items():
            print(f"    {comp}:")
            for txt in texts[:2]:
                print(f"      {txt[:100]}")
        
        print(f"\n  Substantial text elements (top 10):")
        for el in data.get('substantial_text', [])[:10]:
            print(f"    <{el['tag']} class='{el['class'][:40]}'> {el['text'][:80]}")
        
        # Try to extract the best response text
        response_text = ""
        # Prefer the last chat-turn with substantial content
        for turn in reversed(turns):
            if turn['text_len'] > 50:
                response_text = turn['text_preview']
                break
        
        # Or from code blocks
        if not response_text:
            code_texts = [cb['text'] for cb in data.get('code_blocks', []) if len(cb['text']) > 10]
            response_text = '\n'.join(code_texts)
        
        print(f"\n[7] FINAL RESPONSE ({len(response_text)} chars):")
        print("-" * 40)
        print(response_text[:500])
        print("-" * 40)
        
        # Figure out best response selector
        # Run the full page HTML inspection for response
        page_source = driver.page_source
        
        # Save detailed analysis
        results = {
            'status': status,
            'input_selector': 'textarea[aria-label="Enter a prompt"]',
            'submit_selector': 'button.ctrl-enter-submits',
            'response_text': response_text,
            'dom_analysis': data,
        }
        
        with open('/opt/ai-orchestrator/var/interaction_v2_results.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print("\n✓ Results saved to /opt/ai-orchestrator/var/interaction_v2_results.json")
        
        # Save page source for further analysis
        with open('/opt/ai-orchestrator/var/page_source_after_response.html', 'w') as f:
            f.write(page_source)
        print("✓ Page source saved to /opt/ai-orchestrator/var/page_source_after_response.html")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        try:
            driver.save_screenshot('/opt/ai-orchestrator/var/screenshot_error.png')
        except:
            pass
    finally:
        driver.quit()
        print("\nDone.")

if __name__ == "__main__":
    main()
