#!/usr/bin/env python3
"""
Extract chats from ALL platforms via CDP
Uses existing logged-in browser session (no headless, no Cloudflare issues)
"""
import json
import websocket
import requests
import time
from pathlib import Path
from datetime import datetime

CDP_URL = "ws://127.0.0.1:9222/devtools/page/"
OUTPUT_DIR = Path("/opt/ai-orchestrator/var/chat-exports")

def get_tab_url(pattern):
    """Find tab matching pattern"""
    resp = requests.get("http://127.0.0.1:9222/json/list", timeout=5)
    tabs = resp.json()
    for tab in tabs:
        if pattern.lower() in tab.get('url', '').lower():
            return tab['webSocketDebuggerUrl']
    return None

class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=120)
        self.id = 0
    
    def send(self, method, params=None):
        self.id += 1
        cmd = {"id": self.id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(cmd))
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self.id:
                return resp
    
    def eval_js(self, js, await_promise=True):
        result = self.send("Runtime.evaluate", {
            "expression": js,
            "returnByValue": True,
            "awaitPromise": await_promise
        })
        if result and "result" in result and "value" in result["result"]:
            return result["result"]["value"]
        return None
    
    def navigate(self, url):
        self.send("Page.navigate", {"url": url})
        time.sleep(5)
    
    def screenshot(self, path="screenshot.jpg"):
        result = self.send("Page.captureScreenshot", {"format": "jpeg", "quality": 80})
        if result and "data" in result:
            import base64
            with open(path, "wb") as f:
                f.write(base64.b64decode(result["data"]))
            return path
        return None
    
    def click(self, selector):
        js = f"""
        () => {{
            const el = document.querySelector('{selector}');
            if (el) {{ el.click(); return true; }}
            return false;
        }}
        """
        return self.eval_js(js)
    
    def type_text(self, selector, text):
        js = f"""
        () => {{
            const el = document.querySelector('{selector}');
            if (el) {{
                el.value = '{text}';
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return true;
            }}
            return false;
        }}
        """
        return self.eval_js(js)

def extract_gemini(cdp):
    """Extract Gemini chat history"""
    print("\n=== GEMINI ===")
    cdp.navigate("https://gemini.google.com/app")
    time.sleep(8)
    
    # Check login
    logged_in = cdp.eval_js('() => !!document.querySelector(\'[jsname="b2VHfe"]\')')
    if not logged_in:
        print("  ✗ Not logged in")
        return []
    print("  ✓ Logged in")
    
    # Get chat list from sidebar
    chats = cdp.eval_js("""
    () => {
        const items = document.querySelectorAll('nav [role="listitem"], .conversation-item');
        return Array.from(items).slice(0, 50).map(item => ({
            title: item.innerText?.trim() || 'Untitled',
            dataId: item.getAttribute('data-id') || item.id
        })).filter(c => c.title && c.title.length > 3);
    }
    """)
    
    if chats:
        print(f"  Found {len(chats)} chats")
        # Save to file
        output = OUTPUT_DIR / f"gemini-chats-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(output, 'w') as f:
            json.dump({"count": len(chats), "chats": chats, "exported_at": datetime.now().isoformat()}, f, indent=2)
        print(f"  ✓ Saved: {output}")
        return chats
    
    print("  No chats found")
    return []

def extract_copilot(cdp):
    """Extract Microsoft Copilot chat history"""
    print("\n=== COPILOT ===")
    cdp.navigate("https://copilot.microsoft.com")
    time.sleep(8)
    
    # Check login
    logged_in = cdp.eval_js('() => !!document.querySelector(\'[data-testid="user-icon"]\')')
    if not logged_in:
        print("  ✗ Not logged in")
        return []
    print("  ✓ Logged in")
    
    # Get chat list
    chats = cdp.eval_js("""
    () => {
        const items = document.querySelectorAll('ul[role="list"] li, [class*="chat-history"] a');
        return Array.from(items).slice(0, 50).map(item => ({
            title: item.innerText?.trim() || 'Untitled',
            href: item.href || window.location.href
        })).filter(c => c.title && c.title.length > 3);
    }
    """)
    
    if chats:
        print(f"  Found {len(chats)} chats")
        output = OUTPUT_DIR / f"copilot-chats-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(output, 'w') as f:
            json.dump({"count": len(chats), "chats": chats, "exported_at": datetime.now().isoformat()}, f, indent=2)
        print(f"  ✓ Saved: {output}")
        return chats
    
    print("  No chats found")
    return []

def extract_openai(cdp):
    """Extract OpenAI ChatGPT history"""
    print("\n=== OPENAI/CHATGPT ===")
    cdp.navigate("https://chat.openai.com")
    time.sleep(8)
    
    # Check login (look for avatar or user menu)
    logged_in = cdp.eval_js('() => !!document.querySelector(\'[data-testid="user-menu"], [class*="user-avatar"]\')')
    if not logged_in:
        print("  ✗ Not logged in (Cloudflare may block)")
        cdp.screenshot(str(OUTPUT_DIR / "openai-login-check.jpg"))
        return []
    print("  ✓ Logged in")
    
    # Get chat list from sidebar
    chats = cdp.eval_js("""
    () => {
        const items = document.querySelectorAll('nav a[href^="/c/"]');
        return Array.from(items).slice(0, 50).map(item => ({
            title: item.innerText?.trim() || 'Untitled Chat',
            href: item.href
        })).filter(c => c.title && c.title.length > 3);
    }
    """)
    
    if chats:
        print(f"  Found {len(chats)} chats")
        output = OUTPUT_DIR / f"openai-chats-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        with open(output, 'w') as f:
            json.dump({"count": len(chats), "chats": chats, "exported_at": datetime.now().isoformat()}, f, indent=2)
        print(f"  ✓ Saved: {output}")
        return chats
    
    print("  No chats found - may be Cloudflare blocked")
    cdp.screenshot(str(OUTPUT_DIR / "openai-blocked.jpg"))
    return []

def main():
    print("=" * 60)
    print("Multi-Platform Chat Extractor (via CDP)")
    print("=" * 60)
    print(f"\nOutput: {OUTPUT_DIR}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Connect to each tab
        all_chats = {}
        
        # Gemini
        ws_url = get_tab_url("gemini") or get_tab_url("google")
        if ws_url:
            cdp = CDP(ws_url)
            all_chats['gemini'] = extract_gemini(cdp)
            cdp.ws.close()
        else:
            print("\n=== GEMINI ===")
            print("  ⚠ No Gemini tab found - will navigate")
            # Use first available tab
            resp = requests.get("http://127.0.0.1:9222/json/list", timeout=5)
            tabs = resp.json()
            if tabs:
                cdp = CDP(tabs[0]['webSocketDebuggerUrl'])
                all_chats['gemini'] = extract_gemini(cdp)
                cdp.ws.close()
        
        # Copilot
        ws_url = get_tab_url("copilot") or get_tab_url("microsoft")
        if ws_url:
            cdp = CDP(ws_url)
            all_chats['copilot'] = extract_copilot(cdp)
            cdp.ws.close()
        else:
            print("\n=== COPILOT ===")
            print("  ⚠ No Copilot tab found")
        
        # OpenAI
        ws_url = get_tab_url("chatgpt") or get_tab_url("openai")
        if ws_url:
            cdp = CDP(ws_url)
            all_chats['openai'] = extract_openai(cdp)
            cdp.ws.close()
        else:
            print("\n=== OPENAI ===")
            print("  ⚠ No OpenAI tab found")
        
        # Summary
        print("\n" + "=" * 60)
        print("EXTRACTION COMPLETE")
        print("=" * 60)
        for platform, chats in all_chats.items():
            status = f"{len(chats)} chats" if chats else "failed"
            print(f"  {platform}: {status}")
        
        print(f"\nFiles saved to: {OUTPUT_DIR}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
