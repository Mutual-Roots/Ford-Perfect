#!/usr/bin/env python3
"""
Robust ChatGPT Chat Extractor via CDP
- Waits for page to fully load
- Handles Cloudflare by waiting
- Extracts all visible chats from sidebar
- Saves as JSON + Markdown
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
OUTPUT_DIR = Path(f"/opt/ai-orchestrator/var/chat-exports/openai-{datetime.now().strftime('%Y%m%d-%H%M%S')}")

class CDPClient:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60)
        self.id = 0
    
    def send(self, method, params=None):
        self.id += 1
        cmd = {"id": self.id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(cmd))
        
        # Read responses until we get ours
        while True:
            resp = json.loads(self.ws.recv())
            if resp.get("id") == self.id:
                return resp
            # Skip other events/responses
    
    def eval_js(self, js):
        result = self.send("Runtime.evaluate", {
            "expression": js,
            "returnByValue": True,
            "awaitPromise": True
        })
        if "result" in result and "value" in result["result"]:
            return result["result"]["value"]
        return None
    
    def screenshot(self, quality=80):
        result = self.send("Page.captureScreenshot", {
            "format": "jpeg",
            "quality": quality
        })
        return base64.b64decode(result.get("data", ""))

def wait_for_page_load(cdp, timeout=30):
    """Wait for page to be fully loaded"""
    print(f"  Waiting for page load (max {timeout}s)...")
    start = time.time()
    
    while time.time() - start < timeout:
        # Check if document is ready
        ready = cdp.eval_js("document.readyState")
        if ready == "complete":
            # Additional check: no Cloudflare overlay
            has_cloudflare = cdp.eval_js('document.title.includes("Just a moment")')
            if not has_cloudflare:
                print(f"  ✓ Page loaded after {time.time()-start:.1f}s")
                return True
        time.sleep(1)
    
    print(f"  ✗ Timeout after {timeout}s")
    return False

def extract_all_chats(cdp):
    """Extract all chats by navigating through sidebar"""
    chats = []
    
    # First, try to get chat list from sidebar
    print("  Scanning sidebar for chats...")
    
    # Scroll sidebar to load more chats
    cdp.eval_js("""
    () => {
        const nav = document.querySelector('nav');
        if (nav) {
            nav.scrollTop = 0;
            setTimeout(() => { nav.scrollTop = nav.scrollHeight; }, 500);
        }
    }
    """)
    time.sleep(2)
    
    # Get all chat links
    chat_links = cdp.eval_js("""
    () => {
        const links = document.querySelectorAll('nav a[href^="/c/"]');
        return Array.from(links).map(link => ({
            title: link.innerText.trim() || 'Untitled Chat',
            href: link.href,
            id: link.href.split('/c/')[1]?.split('?')[0]
        })).filter(c => c.id);
    }
    """)
    
    if not chat_links:
        print("  No chats found in sidebar")
        print("  → User may not be logged in OR sidebar is collapsed")
        return chats
    
    print(f"  Found {len(chat_links)} chats in sidebar")
    
    # Extract each chat
    for i, chat in enumerate(chat_links[:20]):  # Limit to first 20
        print(f"    [{i+1}/{len(chat_links)}] {chat['title'][:40]}...")
        
        try:
            # Navigate to chat
            cdp.send("Page.navigate", {"url": f"https://chatgpt.com/c/{chat['id']}"})
            time.sleep(3)  # Wait for navigation
            
            # Wait for messages
            wait_for_page_load(cdp, timeout=15)
            
            # Extract messages
            messages = cdp.eval_js("""
            () => {
                const msgs = [];
                const elements = document.querySelectorAll('[data-message-author-role]');
                elements.forEach(el => {
                    const role = el.getAttribute('data-message-author-role');
                    const contentEl = el.querySelector('.prose');
                    const content = contentEl ? contentEl.innerText : '';
                    msgs.push({
                        role: role === 'assistant' ? 'assistant' : 'user',
                        content: content.trim(),
                        timestamp: new Date().toISOString()
                    });
                });
                return msgs;
            }
            """)
            
            if messages:
                chats.append({
                    **chat,
                    "messages": messages,
                    "message_count": len(messages)
                })
            
            # Go back to home to get next chat
            cdp.send("Page.navigate", {"url": "https://chatgpt.com"})
            time.sleep(2)
            
        except Exception as e:
            print(f"      Error: {e}")
            continue
    
    return chats

def main():
    print("=" * 60)
    print("ChatGPT Chat Extractor v2 (CDP Direct)")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput: {OUTPUT_DIR}")
    
    try:
        # Get WebSocket URL
        print("\n[1/5] Connecting to Chromium...")
        resp = requests.get(f"http://{CDP_HOST}:{CDP_PORT}/json/list", timeout=10)
        tabs = resp.json()
        
        ws_url = None
        for tab in tabs:
            if "chatgpt.com" in tab.get("url", ""):
                ws_url = tab["webSocketDebuggerUrl"]
                break
        
        if not ws_url:
            print("  ✗ No ChatGPT tab found!")
            print("  Opening one now...")
            # Could navigate here, but for now abort
            return
        
        print(f"  ✓ Connected: {ws_url}")
        
        # Connect
        print("[2/5] Initializing CDP session...")
        cdp = CDPClient(ws_url)
        cdp.send("Page.enable")
        cdp.send("Runtime.enable")
        cdp.send("DOM.enable")
        
        # Ensure we're on chatgpt.com
        print("[3/5] Navigating to ChatGPT...")
        cdp.send("Page.navigate", {"url": "https://chatgpt.com"})
        time.sleep(5)
        
        # Wait for load
        if not wait_for_page_load(cdp, timeout=30):
            print("\n✗ Page didn't load properly (Cloudflare?)")
            # Save screenshot anyway
            try:
                img = cdp.screenshot()
                img_path = OUTPUT_DIR / "error-screenshot.jpg"
                with open(img_path, "wb") as f:
                    f.write(img)
                print(f"  Screenshot saved: {img_path}")
            except:
                pass
            return
        
        # Check if logged in
        print("[4/5] Checking authentication...")
        auth = cdp.eval_js("""
        () => ({
            hasLoginButton: !!document.querySelector('a[href="/login"]'),
            hasUserMenu: !!document.querySelector('[data-testid="user-menu"]'),
            hasAvatar: !!document.querySelector('[data-testid="avatar"]'),
            hasSidebar: !!document.querySelector('nav')
        })
        """)
        
        if auth and auth.get('hasLoginButton'):
            print("  ✗ NOT LOGGED IN!")
            print("  → Please log in manually at the t640 or via remote desktop")
            return
        
        print("  ✓ Logged in!")
        
        # Extract chats
        print("[5/5] Extracting chats...")
        chats = extract_all_chats(cdp)
        
        # Save results
        if chats:
            total_msgs = sum(c['message_count'] for c in chats)
            
            # JSON
            json_file = OUTPUT_DIR / "chats.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "exported_at": datetime.now().isoformat(),
                    "total_chats": len(chats),
                    "total_messages": total_msgs,
                    "chats": chats
                }, f, indent=2, ensure_ascii=False)
            print(f"\n✓ JSON: {json_file}")
            
            # Markdown per chat
            md_dir = OUTPUT_DIR / "markdown"
            md_dir.mkdir(exist_ok=True)
            
            for i, chat in enumerate(chats):
                md_file = md_dir / f"{i+1:03d}_{chat['title'][:50]}.md"
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {chat['title']}\n\n")
                    f.write(f"**URL:** https://chatgpt.com/c/{chat['id']}\n\n")
                    f.write(f"**Messages:** {chat['message_count']}\n\n---\n\n")
                    
                    for msg in chat['messages']:
                        emoji = "🤖" if msg['role'] == 'assistant' else "👤"
                        f.write(f"### {emoji} {msg['role'].title()}\n\n")
                        f.write(f"{msg['content']}\n\n---\n\n")
            
            print(f"✓ Markdown: {md_dir}/")
            
            print(f"\n{'=' * 60}")
            print(f"EXTRACTION COMPLETE")
            print(f"  Chats: {len(chats)}")
            print(f"  Messages: {total_msgs}")
            print(f"  Location: {OUTPUT_DIR}")
            print(f"{'=' * 60}")
        else:
            print("\n✗ No chats extracted")
            print("  → Sidebar might be empty or collapsed")
        
        # Final screenshot
        try:
            img = cdp.screenshot()
            img_path = OUTPUT_DIR / "final-screenshot.jpg"
            with open(img_path, "wb") as f:
                f.write(img)
            print(f"✓ Screenshot: {img_path}")
        except:
            pass
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
