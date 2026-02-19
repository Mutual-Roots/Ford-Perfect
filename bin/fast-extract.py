#!/usr/bin/env python3
"""
FAST extraction - get in, grab data, get out before KDE kills browser
Run as agency1 in the active session
"""
import json
import websocket
import requests
import time
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("/opt/ai-orchestrator/var/chat-exports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def extract_platform(name, url, selector, ws_url):
    """Extract chats from a platform"""
    print(f"\n=== {name.upper()} ===")
    
    ws = websocket.create_connection(ws_url, timeout=30)
    
    def send(method, params=None):
        send.id += 1
        cmd = {"id": send.id, "method": method, "params": params or {}}
        ws.send(json.dumps(cmd))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == send.id:
                return resp
    
    send.id = 0
    
    def js(code):
        r = send("Runtime.evaluate", {"expression": code, "returnByValue": True, "awaitPromise": True})
        return r.get("result", {}).get("value") if r else None
    
    # Navigate
    send("Page.navigate", {"url": url})
    time.sleep(5)
    
    # Extract
    chats = js(selector)
    
    if chats and isinstance(chats, list):
        valid = [c for c in chats if c.get('title') and len(c['title']) > 3][:50]
        print(f"✓ Got {len(valid)} chats")
        
        # Save
        fpath = OUTPUT_DIR / f"{name}-chats-{datetime.now().strftime('%H%M%S')}.json"
        with open(fpath, 'w') as f:
            json.dump({"platform": name, "count": len(valid), "chats": valid, "exported": datetime.now().isoformat()}, f, indent=2)
        print(f"✓ Saved: {fpath.name}")
        
        ws.close()
        return len(valid)
    
    print("✗ No chats")
    ws.close()
    return 0

def main():
    print("=" * 60)
    print("FAST CHAT EXTRACTOR")
    print("=" * 60)
    
    # Get browser connection
    try:
        tabs = requests.get("http://127.0.0.1:9222/json/list", timeout=3).json()
        if not tabs:
            print("✗ No tabs found!")
            return
        ws_url = tabs[0]["webSocketDebuggerUrl"]
        print(f"✓ Connected to browser ({len(tabs)} tabs)")
    except Exception as e:
        print(f"✗ Can't connect: {e}")
        return
    
    results = {}
    
    # Extract each platform FAST
    results['copilot'] = extract_platform(
        "copilot",
        "https://copilot.microsoft.com",
        """() => Array.from(document.querySelectorAll('ul[role="list"] li, [class*="chat-history"] a'))
            .slice(0,50)
            .map(el => ({title: el.innerText?.trim(), href: el.href}))
            .filter(c => c?.title && c.title.length > 3)""",
        ws_url
    )
    
    time.sleep(1)
    
    results['gemini'] = extract_platform(
        "gemini", 
        "https://gemini.google.com/app",
        """() => Array.from(document.querySelectorAll('nav [role="listitem"], .conversation-item'))
            .slice(0,50)
            .map(el => ({title: el.innerText?.trim(), id: el.dataset?.id || el.id}))
            .filter(c => c?.title && c.title.length > 3)""",
        ws_url
    )
    
    time.sleep(1)
    
    results['openai'] = extract_platform(
        "openai",
        "https://chat.openai.com",
        """() => Array.from(document.querySelectorAll('nav a[href^="/c/"]'))
            .slice(0,50)
            .map(el => ({title: el.innerText?.trim(), href: el.href}))
            .filter(c => c?.title && c.title.length > 3)""",
        ws_url
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    for k, v in results.items():
        print(f"  {k}: {v} chats" if v else f"  {k}: FAILED")
    
    total = sum(v for v in results.values() if v)
    print(f"\nTOTAL: {total} chats extracted")
    print(f"Files: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
