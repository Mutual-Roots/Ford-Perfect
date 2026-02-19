#!/usr/bin/env python3
"""
CDP Browser Automation MIT visuellem Feedback
Jeder Schritt macht einen Screenshot → du siehst was passiert
"""
import json
import requests
import websocket
import time
import base64
from pathlib import Path
from datetime import datetime

CDP_HOST = "100.117.140.79"
CDP_PORT = 9223
OUTPUT_DIR = Path(f"/opt/ai-orchestrator/var/cdp-sessions/session-{datetime.now().strftime('%Y%m%d-%H%M%S')}")

class VisualCDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60)
        self.id = 0
        self.step = 0
    
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
    
    def screenshot(self, name=None):
        self.step += 1
        result = self.send("Page.captureScreenshot", {
            "format": "jpeg",
            "quality": 85,
            "fromSurface": True
        })
        if "data" in result:
            img_data = base64.b64decode(result["data"])
            filename = name or f"step-{self.step:03d}.jpg"
            img_path = OUTPUT_DIR / filename
            with open(img_path, "wb") as f:
                f.write(img_data)
            print(f"  📸 Screenshot: {img_path} ({len(img_data):,} bytes)")
            return img_path
        return None
    
    def navigate(self, url):
        print(f"\n  → Navigating: {url}")
        self.send("Page.navigate", {"url": url})
        time.sleep(3)
        self.screenshot(f"navigate-{self.step:03d}.jpg")
    
    def click(self, selector):
        print(f"  → Clicking: {selector}")
        js = f"""
        () => {{
            const el = document.querySelector('{selector}');
            if (el) {{
                el.click();
                el.style.outline = '3px solid red';
                return {{clicked: true, text: el.innerText?.slice(0,50)}};
            }}
            return {{clicked: false}};
        }}
        """
        result = self.eval_js(js)
        time.sleep(2)
        self.screenshot(f"click-{self.step:03d}.jpg")
        return result

def main():
    print("=" * 60)
    print("Visual CDP Browser Automation")
    print("Jeder Schritt wird gescreenshoted!")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Session Folder: {OUTPUT_DIR}")
    
    # Get WebSocket URL
    print("\n[CONNECT] Getting browser connection...")
    try:
        resp = requests.get(f"http://{CDP_HOST}:{CDP_PORT}/json/list", timeout=10)
        tabs = resp.json()
        
        ws_url = None
        for tab in tabs:
            if "chatgpt.com" in tab.get("url", ""):
                ws_url = tab["webSocketDebuggerUrl"]
                print(f"  ✓ Found ChatGPT tab")
                break
        
        if not ws_url:
            # Use first available tab
            if tabs:
                ws_url = tabs[0]["webSocketDebuggerUrl"]
                print(f"  ✓ Using first available tab")
            else:
                print("  ✗ No tabs found!")
                return
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return
    
    # Connect
    print(f"\n[INIT] Connecting to CDP...")
    cdp = VisualCDP(ws_url)
    cdp.send("Page.enable")
    cdp.send("Runtime.enable")
    cdp.send("DOM.enable")
    
    # Initial screenshot
    print("\n[STEP 1] Initial state:")
    cdp.screenshot("000-initial.jpg")
    
    # Show current page info
    page_info = cdp.eval_js("""
    () => ({
        url: window.location.href,
        title: document.title,
        readyState: document.readyState,
        bodyLength: document.body?.innerText?.length || 0
    })
    """)
    if page_info:
        print(f"  URL: {page_info.get('url', 'N/A')}")
        print(f"  Title: {page_info.get('title', 'N/A')}")
        print(f"  Ready: {page_info.get('readyState', 'N/A')}")
        print(f"  Body: {page_info.get('bodyLength', 0)} chars")
    
    # Navigate to ChatGPT
    print("\n[STEP 2] Navigate to ChatGPT:")
    cdp.navigate("https://chatgpt.com")
    
    # Wait and check for Cloudflare
    time.sleep(5)
    cf_check = cdp.eval_js('document.title.includes("Just a moment")')
    if cf_check:
        print("  ⚠️  CLOUDFLARE DETECTED!")
        cdp.screenshot("cloudflare-challenge.jpg")
        
        # Try to interact
        print("\n[STEP 3] Attempting Cloudflare bypass:")
        
        # Look for verify button
        buttons = cdp.eval_js("""
        () => {
            const btns = document.querySelectorAll('button, input[type="checkbox"], [role="button"]');
            return Array.from(btns).map(b => ({
                text: b.innerText || b.value || b.textContent?.slice(0,30),
                visible: b.offsetParent !== null
            })).filter(b => b.text && b.visible);
        }
        """)
        
        if buttons:
            print(f"  Found {len(buttons)} interactive elements:")
            for btn in buttons[:5]:
                print(f"    - {btn['text'][:40]}")
            
            # Click first visible button
            cdp.click('button, input[type="checkbox"]')
            
            # Wait for challenge
            print("\n  Waiting for challenge completion...")
            for i in range(15):
                time.sleep(2)
                still_cf = cdp.eval_js('document.title.includes("Just a moment")')
                if not still_cf:
                    print(f"  ✓ Challenge passed after {(i+1)*2}s!")
                    cdp.screenshot("challenge-passed.jpg")
                    break
                if i % 5 == 4:
                    print(f"    Still waiting... ({(i+1)*2}s)")
                    cdp.screenshot(f"waiting-{i+1}.jpg")
    else:
        print("  ✓ No Cloudflare detected!")
    
    # Check login status
    print("\n[STEP 4] Checking authentication:")
    auth = cdp.eval_js("""
    () => {
        const hasLogin = !!document.querySelector('a[href="/login"]');
        const hasUserMenu = !!document.querySelector('[data-testid="user-menu"], [data-testid="avatar"]');
        const hasSidebar = !!document.querySelector('nav');
        return {hasLogin, hasUserMenu, hasSidebar};
    }
    """)
    
    if auth:
        print(f"  Has Login Button: {auth.get('hasLogin', False)}")
        print(f"  Has User Menu: {auth.get('hasUserMenu', False)}")
        print(f"  Has Sidebar: {auth.get('hasSidebar', False)}")
        
        if auth.get('hasLogin'):
            print("  ⚠️  NOT LOGGED IN")
        elif auth.get('hasUserMenu'):
            print("  ✓ Logged in!")
            
            # Try to get chat list
            print("\n[STEP 5] Scanning for chats:")
            chats = cdp.eval_js("""
            () => {
                const links = document.querySelectorAll('nav a[href^="/c/"]');
                return Array.from(links).slice(0,10).map(l => ({
                    title: l.innerText?.trim() || 'Untitled',
                    href: l.href
                }));
            }
            """)
            
            if chats:
                print(f"  ✓ Found {len(chats)} chats:")
                for chat in chats:
                    print(f"    - {chat['title'][:50]}")
                cdp.screenshot("chat-list.jpg")
            else:
                print("  No chats found in sidebar")
                cdp.screenshot("empty-sidebar.jpg")
    
    # Final screenshot
    print("\n[FINAL] Session complete!")
    cdp.screenshot("999-final.jpg")
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"SESSION SUMMARY")
    print(f"  Location: {OUTPUT_DIR}")
    print(f"  Screenshots: {cdp.step} images")
    print(f"  View all: ls -la {OUTPUT_DIR}/*.jpg")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    main()
