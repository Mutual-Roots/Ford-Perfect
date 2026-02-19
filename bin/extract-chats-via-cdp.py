#!/usr/bin/env python3
"""
Extrahiert ChatGPT Chats via Chrome DevTools Protocol (CDP)
Funktioniert remote über Tailscale ohne Cloudflare-Probleme
"""
import json
import requests
import websocket
import time
from pathlib import Path
from datetime import datetime

CDP_HOST = "100.117.140.79"
CDP_PORT = 9223
OUTPUT_DIR = Path(f"/opt/ai-orchestrator/var/chat-exports/openai-cdp-{datetime.now().strftime('%Y%m%d-%H%M%S')}")

def get_debugger_url():
    """Get WebSocket URL for ChatGPT tab"""
    resp = requests.get(f"http://{CDP_HOST}:{CDP_PORT}/json/list", timeout=10)
    tabs = resp.json()
    
    for tab in tabs:
        if "chatgpt.com" in tab.get("url", ""):
            return tab["webSocketDebuggerUrl"]
    
    raise Exception("No ChatGPT tab found")

def cdp_command(ws, method, params=None):
    """Send CDP command and get response"""
    cmd = {
        "id": 1,
        "method": method,
        "params": params or {}
    }
    ws.send(json.dumps(cmd))
    resp = json.loads(ws.recv())
    return resp.get("result", {})

def extract_chat_messages(ws):
    """Extract messages from current page using JavaScript"""
    js_code = """
    () => {
        const messages = [];
        const msgElements = document.querySelectorAll('[data-message-author-role]');
        
        msgElements.forEach(el => {
            const role = el.getAttribute('data-message-author-role');
            const contentEl = el.querySelector('.prose');
            const content = contentEl ? contentEl.innerText : '';
            
            messages.push({
                role: role === 'assistant' ? 'assistant' : 'user',
                content: content.trim()
            });
        });
        
        return {
            url: window.location.href,
            title: document.title,
            messages: messages,
            messageCount: messages.length
        };
    }
    """
    
    result = cdp_command(ws, "Runtime.evaluate", {"expression": js_code})
    if "result" in result and "value" in result["result"]:
        return json.loads(result["result"]["value"])
    return None

def main():
    print("=" * 60)
    print("ChatGPT Chat Extractor via CDP")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput: {OUTPUT_DIR}")
    
    try:
        # Get WebSocket URL
        print("\n[1/4] Connecting to Chromium...")
        ws_url = get_debugger_url()
        print(f"  Found: {ws_url}")
        
        # Connect
        print("[2/4] Opening WebSocket...")
        ws = websocket.create_connection(ws_url, timeout=30)
        
        # Enable required domains
        print("[3/4] Enabling CDP domains...")
        cdp_command(ws, "Page.enable")
        cdp_command(ws, "Runtime.enable")
        
        # Navigate to ensure we're on chatgpt.com
        print("  Navigating to chatgpt.com...")
        cdp_command(ws, "Page.navigate", {"url": "https://chatgpt.com"})
        time.sleep(5)  # Wait for page load
        
        # Extract messages
        print("[4/4] Extracting messages...")
        chat_data = extract_chat_messages(ws)
        
        if chat_data:
            print(f"\n✓ Found {chat_data['messageCount']} messages")
            
            # Save as JSON
            output_file = OUTPUT_DIR / "chat.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "exported_at": datetime.now().isoformat(),
                    "source": "CDP Extraction",
                    **chat_data
                }, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Saved: {output_file}")
            
            # Also save as markdown
            md_file = OUTPUT_DIR / "chat.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# {chat_data['title']}\n\n")
                f.write(f"**URL:** {chat_data['url']}\n\n")
                f.write(f"**Messages:** {chat_data['messageCount']}\n\n---\n\n")
                
                for i, msg in enumerate(chat_data['messages']):
                    emoji = "🤖" if msg['role'] == 'assistant' else "👤"
                    f.write(f"### {emoji} {msg['role'].title()}\n\n")
                    f.write(f"{msg['content']}\n\n---\n\n")
            
            print(f"✓ Saved: {md_file}")
            
            print(f"\n{'=' * 60}")
            print("EXTRACTION COMPLETE")
            print(f"  Location: {OUTPUT_DIR}")
            print(f"{'=' * 60}")
        else:
            print("✗ No messages found - page may not be fully loaded")
        
        ws.close()
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
