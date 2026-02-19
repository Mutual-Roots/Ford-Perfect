#!/usr/bin/env python3
"""
Extract chats from Microsoft Copilot and Google Gemini
Uses existing Chromium profile (already logged in via KDE session)
"""
import json
import time
import requests
import websocket
from pathlib import Path
from datetime import datetime

CDP_HOST = "100.117.140.79"
CDP_PORT = 9223
OUTPUT_DIR = Path(f"/opt/ai-orchestrator/var/chat-exports/{datetime.now().strftime('%Y%m%d-%H%M%S')}")

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
    
    def navigate(self, url):
        self.send("Page.navigate", {"url": url})
        time.sleep(5)
    
    def screenshot(self, name="screenshot.jpg"):
        result = self.send("Page.captureScreenshot", {"format": "jpeg", "quality": 80})
        if "data" in result:
            import base64
            img_data = base64.b64decode(result["data"])
            img_path = OUTPUT_DIR / name
            with open(img_path, "wb") as f:
                f.write(img_data)
            return img_path
        return None

def extract_copilot_chats(cdp):
    """Extract Microsoft Copilot chat history"""
    print("\n=== EXTRACTING COPILOT ===")
    
    cdp.navigate("https://copilot.microsoft.com")
    time.sleep(5)
    
    # Check if logged in
    logged_in = cdp.eval_js("""
    () => {
        const userIcon = document.querySelector('[data-testid="user-icon"], .user-icon, [aria-label*="account"]');
        const signInBtn = document.querySelector('button[href*="login"], a[href*="login"]');
        return {
            hasUserIcon: !!userIcon,
            hasSignInBtn: !!signInBtn,
            loggedIn: !signInBtn
        };
    }
    """)
    
    if logged_in and not logged_in.get('loggedIn'):
        print("  ⚠️  Not logged into Copilot")
        return []
    
    print("  ✓ Logged in!")
    
    # Try to get chat history from sidebar
    chats = cdp.eval_js("""
    () => {
        const items = document.querySelectorAll('[class*="chat-history"] li, [class*="conversation"] a');
        return Array.from(items).slice(0, 20).map(item => ({
            title: item.innerText?.trim() || 'Untitled',
            href: item.href || window.location.href
        }));
    }
    """)
    
    if chats:
        print(f"  Found {len(chats)} chats in sidebar")
        for i, chat in enumerate(chats[:5]):
            print(f"    [{i+1}] {chat['title'][:50]}")
        
        # Extract full conversations
        conversations = []
        for i, chat in enumerate(chats[:10]):
            print(f"    Extracting chat {i+1}/{min(len(chats), 10)}...")
            # Would need to click each chat and extract messages
            # For now, just save the list
            conversations.append(chat)
        
        return conversations
    
    print("  No chat history found in sidebar")
    return []

def extract_gemini_chats(cdp):
    """Extract Google Gemini chat history"""
    print("\n=== EXTRACTING GEMINI ===")
    
    cdp.navigate("https://gemini.google.com")
    time.sleep(5)
    
    # Check if logged in
    logged_in = cdp.eval_js("""
    () => {
        const avatar = document.querySelector('[jsname="b2VHfe"], img[src*="lh3.googleusercontent"]');
        return !!avatar;
    }
    """)
    
    if not logged_in:
        print("  ⚠️  Not logged into Gemini")
        return []
    
    print("  ✓ Logged in!")
    
    # Get chat history from sidebar
    chats = cdp.eval_js("""
    () => {
        const items = document.querySelectorAll('nav [role="listitem"], .conversation-item, [class*="chat-item"]');
        return Array.from(items).slice(0, 20).map(item => ({
            title: item.innerText?.trim() || 'Untitled Chat',
            dataId: item.getAttribute('data-id') || item.id
        })).filter(c => c.title);
    }
    """)
    
    if chats:
        print(f"  Found {len(chats)} chats")
        for i, chat in enumerate(chats[:10]):
            print(f"    [{i+1}] {chat['title'][:50]}")
        return chats
    
    print("  No chats found - trying alternative selector...")
    
    # Alternative: Check recent activity page
    cdp.navigate("https://myactivity.google.com/page?product=gemini")
    time.sleep(5)
    
    activities = cdp.eval_js("""
    () => {
        const items = document.querySelectorAll('[data-locale="en"] .mdl-card, .activity-item');
        return Array.from(items).slice(0, 20).map(item => ({
            title: item.innerText?.slice(0, 100) || 'Activity',
            timestamp: item.querySelector('time')?.dateTime || 'unknown'
        }));
    }
    """)
    
    if activities:
        print(f"  Found {len(activities)} activities via My Activity")
        return activities
    
    return []

def extract_google_drive_files(cdp):
    """List recent files from Google Drive"""
    print("\n=== EXTRACTING GOOGLE DRIVE FILE LIST ===")
    
    cdp.navigate("https://drive.google.com/drive/recent")
    time.sleep(5)
    
    # Check if logged in
    logged_in = cdp.eval_js("""
    () => {
        const avatar = document.querySelector('[jsname="b2VHfe"]');
        return !!avatar;
    }
    """)
    
    if not logged_in:
        print("  ⚠️  Not logged into Drive")
        return []
    
    print("  ✓ Logged in!")
    
    # Get recent files
    files = cdp.eval_js("""
    () => {
        const items = document.querySelectorAll('[role="row"][aria-label], [data-id]');
        return Array.from(items).slice(0, 50).map(item => ({
            name: item.getAttribute('aria-label') || item.innerText?.slice(0, 100),
            type: item.getAttribute('data-mime-type') || 'unknown'
        })).filter(f => f.name && f.name.length > 3);
    }
    """)
    
    if files:
        print(f"  Found {len(files)} recent files")
        # Deduplicate
        seen = set()
        unique = []
        for f in files:
            if f['name'] not in seen:
                seen.add(f['name'])
                unique.append(f)
        print(f"  {len(unique)} unique files")
        return unique[:30]
    
    print("  No files found")
    return []

def main():
    print("=" * 60)
    print("Copilot + Gemini + Drive Extractor")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput: {OUTPUT_DIR}")
    
    try:
        # Connect to CDP
        print("\n[CONNECT] Connecting to browser...")
        resp = requests.get(f"http://{CDP_HOST}:{CDP_PORT}/json/list", timeout=10)
        tabs = resp.json()
        
        # Use first available tab
        ws_url = tabs[0]["webSocketDebuggerUrl"] if tabs else None
        if not ws_url:
            print("  ✗ No tabs available!")
            return
        
        print(f"  ✓ Connected")
        cdp = CDPClient(ws_url)
        cdp.send("Page.enable")
        cdp.send("Runtime.enable")
        
        # Initial screenshot
        print("\n[SCREENSHOT] Initial state...")
        cdp.screenshot("00-initial.jpg")
        
        # Extract Copilot
        copilot_chats = extract_copilot_chats(cdp)
        cdp.screenshot("01-copilot.jpg")
        
        # Extract Gemini
        gemini_chats = extract_gemini_chats(cdp)
        cdp.screenshot("02-gemini.jpg")
        
        # Extract Drive file list
        drive_files = extract_google_drive_files(cdp)
        cdp.screenshot("03-drive.jpg")
        
        # Save results
        print("\n" + "=" * 60)
        print("SAVING RESULTS")
        print("=" * 60)
        
        results = {
            "exported_at": datetime.now().isoformat(),
            "copilot": {
                "count": len(copilot_chats),
                "chats": copilot_chats
            },
            "gemini": {
                "count": len(gemini_chats),
                "chats": gemini_chats
            },
            "drive": {
                "count": len(drive_files),
                "files": drive_files
            }
        }
        
        output_file = OUTPUT_DIR / "export-summary.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Summary: {output_file}")
        print(f"  Copilot: {len(copilot_chats)} chats")
        print(f"  Gemini: {len(gemini_chats)} chats")
        print(f"  Drive: {len(drive_files)} files listed")
        print(f"\nScreenshots: {OUTPUT_DIR}/*.jpg")
        
        # Final summary
        print(f"\n{'=' * 60}")
        print("EXTRACTION COMPLETE")
        print(f"  Location: {OUTPUT_DIR}")
        print(f"  Files: {len(list(OUTPUT_DIR.glob('*')))}")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
