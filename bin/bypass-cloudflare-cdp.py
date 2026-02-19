#!/usr/bin/env python3
"""
Bypass Cloudflare challenge via CDP by simulating user interaction
"""
import json
import requests
import websocket
import time
import base64
from pathlib import Path

CDP_HOST = "100.117.140.79"
CDP_PORT = 9223

class CDPClient:
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
        if "result" in result and "value" in result["result"]:
            return result["result"]["value"]
        return None
    
    def click(self, selector):
        """Click an element using JavaScript"""
        js = f"""
        () => {{
            const el = document.querySelector('{selector}');
            if (el) {{
                el.click();
                return true;
            }}
            return false;
        }}
        """
        return self.eval_js(js)
    
    def screenshot(self):
        result = self.send("Page.captureScreenshot", {"format": "jpeg", "quality": 80})
        return base64.b64decode(result.get("data", ""))

def main():
    print("=" * 60)
    print("Cloudflare Bypass via CDP")
    print("=" * 60)
    
    # Get WebSocket URL
    resp = requests.get(f"http://{CDP_HOST}:{CDP_PORT}/json/list", timeout=10)
    tabs = resp.json()
    
    ws_url = None
    for tab in tabs:
        if "chatgpt.com" in tab.get("url", ""):
            ws_url = tab["webSocketDebuggerUrl"]
            break
    
    if not ws_url:
        print("✗ No ChatGPT tab found!")
        return
    
    print(f"\nConnected: {ws_url}")
    cdp = CDPClient(ws_url)
    
    cdp.send("Page.enable")
    cdp.send("Runtime.enable")
    
    # Navigate to chatgpt.com
    print("\n[1/4] Navigating to ChatGPT...")
    cdp.send("Page.navigate", {"url": "https://chatgpt.com"})
    time.sleep(5)
    
    # Check for Cloudflare
    print("[2/4] Checking for Cloudflare...")
    title = cdp.eval_js("document.title")
    print(f"  Page title: {title}")
    
    if "Just a moment" in title:
        print("  ⚠️  Cloudflare detected - attempting bypass...")
        
        # Try to find and click the challenge button
        print("\n[3/4] Attempting to solve challenge...")
        
        # Wait for challenge to load
        time.sleep(3)
        
        # Try various selectors for Cloudflare verify button
        selectors = [
            'input[type="checkbox"]',
            'button[type="submit"]',
            '[data-testid="challenge-checkbox"]',
            '.cf-turnstile',
            '#cf-stage'
        ]
        
        for selector in selectors:
            clicked = cdp.click(selector)
            if clicked:
                print(f"  ✓ Clicked: {selector}")
                break
            else:
                print(f"  ✗ Not found: {selector}")
        
        # Also try clicking anywhere on the page (sometimes helps)
        cdp.eval_js("""
        () => {
            // Simulate mouse movement
            const event = new MouseEvent('mousemove', {
                bubbles: true,
                clientX: Math.random() * window.innerWidth,
                clientY: Math.random() * window.innerHeight
            });
            document.dispatchEvent(event);
            
            // Random scroll
            window.scrollBy(0, Math.random() * 100);
        }
        """)
        
        # Wait for challenge to complete
        print("\n  Waiting for challenge completion...")
        for i in range(20):
            time.sleep(2)
            new_title = cdp.eval_js("document.title")
            if "Just a moment" not in new_title:
                print(f"  ✓ Challenge passed after {(i+1)*2}s!")
                print(f"  New title: {new_title}")
                break
            if i % 5 == 4:
                print(f"    Still waiting... ({(i+1)*2}s)")
        else:
            print("  ✗ Challenge timeout")
    
    # Take screenshot
    print("\n[4/4] Taking screenshot...")
    try:
        img = cdp.screenshot()
        img_path = "/tmp/chatgpt-after-bypass.jpg"
        with open(img_path, "wb") as f:
            f.write(img)
        print(f"✓ Screenshot: {img_path} ({len(img)} bytes)")
        print(f"  View: display-im7 {img_path} &")
    except Exception as e:
        print(f"✗ Screenshot failed: {e}")
    
    # Show current state
    print("\nCurrent page state:")
    state = cdp.eval_js("""
    () => ({
        url: window.location.href,
        title: document.title,
        hasCloudflare: document.title.includes("Just a moment"),
        bodyLength: document.body.innerText.length
    })
    """)
    if state:
        print(f"  URL: {state.get('url', 'N/A')}")
        print(f"  Title: {state.get('title', 'N/A')}")
        print(f"  Has Cloudflare: {state.get('hasCloudflare', False)}")
        print(f"  Body text length: {state.get('bodyLength', 0)} chars")

if __name__ == "__main__":
    main()
