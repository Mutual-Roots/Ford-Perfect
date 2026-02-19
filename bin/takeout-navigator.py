#!/usr/bin/env python3
"""
Navigate to Google Takeout and prepare export via CDP
Runs locally on t640, controls existing Chromium session
No Selenium needed - direct WebSocket CDP
"""
import json
import websocket
import time
import requests
from pathlib import Path

CDP_HOST = "127.0.0.1"
CDP_PORT = 9222

def get_ws_url():
    """Get WebSocket URL from CDP"""
    resp = requests.get(f"http://{CDP_HOST}:{CDP_PORT}/json/list", timeout=5)
    tabs = resp.json()
    if tabs:
        return tabs[0]["webSocketDebuggerUrl"]
    raise Exception("No tabs found")

class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60)
        self.id = 0
    
    def send(self, method, params=None):
        self.id += 1
        cmd = {"id": self.id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(cmd))
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self.id:
                return resp
    
    def eval_js(self, js):
        result = self.send("Runtime.evaluate", {
            "expression": js,
            "returnByValue": True,
            "awaitPromise": True
        })
        if result and "result" in result and "value" in result["result"]:
            return result["result"]["value"]
        return None
    
    def click(self, selector):
        """Click element by CSS selector"""
        js = f"""
        () => {{
            const el = document.querySelector('{selector}');
            if (el) {{ el.click(); return true; }}
            return false;
        }}
        """
        return self.eval_js(js)
    
    def navigate(self, url):
        self.send("Page.navigate", {"url": url})
        time.sleep(5)
    
    def screenshot(self, path="screenshot.jpg"):
        result = self.send("Page.captureScreenshot", {"format": "jpeg", "quality": 80})
        if result and "data" in result:
            import base64
            img_data = base64.b64decode(result["data"])
            with open(path, "wb") as f:
                f.write(img_data)
            return path
        return None

def main():
    print("=" * 60)
    print("Google Takeout Navigator (CDP Direct)")
    print("=" * 60)
    
    try:
        # Connect
        print("\n[1/6] Connecting to browser...")
        ws_url = get_ws_url()
        cdp = CDP(ws_url)
        print(f"  ✓ Connected to {ws_url}")
        
        # Navigate to Takeout
        print("[2/6] Opening Google Takeout...")
        cdp.navigate("https://takeout.google.com")
        
        # Wait for page load
        print("[3/6] Waiting for page to load...")
        time.sleep(8)
        
        # Check login status
        print("[4/6] Checking login status...")
        logged_in = cdp.eval_js("""
        () => {
            const avatar = document.querySelector('[jsname="b2VHfe"]');
            return !!avatar;
        }
        """)
        
        if logged_in:
            print("  ✓ Logged in as Google user")
        else:
            print("  ⚠️  Not logged in - please login manually")
            # Take screenshot for debugging
            cdp.screenshot("/opt/ai-orchestrator/var/chat-exports/takeout-login-needed.jpg")
            print("  Screenshot saved for debugging")
            return
        
        # Find and click "Deselect all"
        print("[5/6] Deselecting all products...")
        
        # Try multiple selectors for "Deselect all"
        selectors = [
            'button[data-tooltip="Deselect all"]',
            '[aria-label="Deselect all"]',
            'div[role="button"]:contains("Deselect all")',
            'span:contains("Alle aufheben")',
            'button:contains("Deselect")'
        ]
        
        deselected = False
        for sel in selectors:
            try:
                # Simplified JS that works better
                js = f"""
                () => {{
                    const buttons = document.querySelectorAll('button, [role="button"], div[role="checkbox"]');
                    for (let btn of buttons) {{
                        const text = (btn.innerText || btn.textContent || '').toLowerCase();
                        if (text.includes('deselect') || text.includes('alle aufheben')) {{
                            btn.click();
                            return true;
                        }}
                    }}
                    return false;
                }}
                """
                result = cdp.eval_js(js)
                if result:
                    print("  ✓ Deselected all products")
                    deselected = True
                    break
            except:
                continue
        
        if not deselected:
            print("  ⚠️  Could not find deselect button - manual step needed")
        
        time.sleep(2)
        
        # Find and select Gemini
        print("[6/6] Selecting Gemini only...")
        
        js_gemini = """
        () => {
            const items = document.querySelectorAll('[role="listitem"], .product-item, div[role="checkbox"]');
            for (let item of items) {
                const text = (item.innerText || item.textContent || '').toLowerCase();
                if (text.includes('gemini') || text.includes('bard')) {
                    // Click the checkbox associated with this item
                    const checkbox = item.querySelector('input[type="checkbox"], [role="checkbox"]') || item;
                    checkbox.click();
                    return true;
                }
            }
            return false;
        }
        """
        
        selected = cdp.eval_js(js_gemini)
        if selected:
            print("  ✓ Selected Gemini")
        else:
            print("  ⚠️  Could not find Gemini - manual selection needed")
        
        # Final screenshot
        screenshot_path = "/opt/ai-orchestrator/var/chat-exports/takeout-ready.jpg"
        cdp.screenshot(screenshot_path)
        print(f"\n  ✓ Screenshot saved: {screenshot_path}")
        
        print("\n" + "=" * 60)
        print("TAKEOUT PREPARED")
        print("=" * 60)
        print("\nNext steps (manual):")
        print("1. Scroll down and click 'Next'")
        print("2. Choose: JSON format, 2GB file size")
        print("3. Click 'Create export'")
        print("4. Wait for email (10-60 minutes)")
        print("\nOR: I can try to automate the rest...")
        
        # Keep browser open for inspection
        print("\nBrowser stays open for 120 seconds...")
        time.sleep(120)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
