#!/usr/bin/env python3
"""Check if logged into OpenAI and list available chats"""
import json
import requests
import websocket
import time

CDP_HOST = "100.117.140.79"
CDP_PORT = 9223

def get_ws_url():
    resp = requests.get(f"http://{CDP_HOST}:{CDP_PORT}/json/list", timeout=10)
    for tab in resp.json():
        if "chatgpt.com" in tab.get("url", ""):
            return tab["webSocketDebuggerUrl"]
    return None

def cdp_cmd(ws, method, params=None):
    cmd = {"id": 1, "method": method, "params": params or {}}
    ws.send(json.dumps(cmd))
    return json.loads(ws.recv()).get("result", {})

def main():
    ws_url = get_ws_url()
    if not ws_url:
        print("No ChatGPT tab found!")
        return
    
    print(f"Connected: {ws_url}")
    ws = websocket.create_connection(ws_url, timeout=30)
    
    cdp_cmd(ws, "Page.enable")
    cdp_cmd(ws, "Runtime.enable")
    
    # Check login status
    js_check_auth = """
    () => {
        const checkAuth = () => {
            // Look for auth indicators
            const userMenu = document.querySelector('[data-testid="user-menu"]');
            const avatar = document.querySelector('[data-testid="avatar"]');
            const loginButton = document.querySelector('a[href="/login"]');
            const sidebar = document.querySelector('nav');
            
            return {
                hasUserMenu: !!userMenu,
                hasAvatar: !!avatar,
                hasLoginButton: !!loginButton,
                hasSidebar: !!sidebar,
                url: window.location.href,
                title: document.title
            };
        };
        return checkAuth();
    }
    """
    
    print("\n[1/3] Checking authentication...")
    result = cdp_cmd(ws, "Runtime.evaluate", {"expression": js_check_auth})
    if "result" in result and "value" in result["result"]:
        auth_status = json.loads(result["result"]["value"])
        print(f"  URL: {auth_status['url']}")
        print(f"  Title: {auth_status['title']}")
        print(f"  Has User Menu: {auth_status['hasUserMenu']}")
        print(f"  Has Avatar: {auth_status['hasAvatar']}")
        print(f"  Has Login Button: {auth_status['hasLoginButton']} ← Should be False if logged in")
        print(f"  Has Sidebar: {auth_status['hasSidebar']}")
        
        if auth_status['hasLoginButton']:
            print("\n⚠️  NOT LOGGED IN! Need to authenticate.")
        else:
            print("\n✓ Appears to be logged in!")
    
    # Try to find chat links in sidebar
    print("\n[2/3] Looking for chat history...")
    js_find_chats = """
    () => {
        const chatLinks = document.querySelectorAll('nav a[href^="/c/"]');
        const chats = [];
        chatLinks.forEach((link, i) => {
            if (i < 10) {  // First 10
                chats.push({
                    title: link.innerText.trim() || `Chat ${i+1}`,
                    href: link.href
                });
            }
        });
        return chats;
    }
    """
    
    result = cdp_cmd(ws, "Runtime.evaluate", {"expression": js_find_chats})
    if "result" in result and "value" in result["result"]:
        chats = json.loads(result["result"]["value"])
        if chats:
            print(f"  Found {len(chats)} chats:")
            for chat in chats:
                print(f"    - {chat['title'][:50]}")
        else:
            print("  No chats found in sidebar")
            print("  → Sidebar might be collapsed or not loaded yet")
    
    # Take screenshot base64
    print("\n[3/3] Taking screenshot...")
    result = cdp_cmd(ws, "Page.captureScreenshot", {"format": "jpeg", "quality": 80})
    if "data" in result:
        import base64
        img_data = base64.b64decode(result["data"])
        img_path = "/tmp/chatgpt-screenshot.jpg"
        with open(img_path, "wb") as f:
            f.write(img_data)
        print(f"  Screenshot saved: {img_path} ({len(img_data)} bytes)")
        print(f"  View with: display-im7 {img_path} &")
    
    ws.close()

if __name__ == "__main__":
    main()
