#!/usr/bin/env python3
"""
Complete Gemini Takeout Automation
Starts browser, navigates, prepares export - all in one run
"""
import subprocess
import time
import json
import websocket
import requests
import os
import signal
from pathlib import Path

PROFILE = "/opt/ai-orchestrator/var/chromium-profile"
OUTPUT_DIR = Path("/opt/ai-orchestrator/var/chat-exports")
CDP_PORT = 9222

def start_browser():
    """Start Chromium as agency1"""
    # Cleanup
    subprocess.run(["pkill", "-9", "chromium"], capture_output=True)
    time.sleep(2)
    
    # Remove locks
    for f in Path("/tmp").glob("org.chromium.*"):
        subprocess.run(["rm", "-rf", str(f)], capture_output=True)
    
    # Start browser
    env = os.environ.copy()
    env["DISPLAY"] = ":0"
    env["XDG_RUNTIME_DIR"] = "/run/user/1000"
    
    cmd = [
        "/usr/lib/chromium/chromium",
        "--user-data-dir=" + PROFILE,
        "--password-store=basic",
        "--no-sandbox",
        "--remote-debugging-port=" + str(CDP_PORT),
        "--remote-allow-origins=*",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-software-rasterizer",
        "--headless=new",
        "https://takeout.google.com"
    ]
    
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"  Browser started (PID: {proc.pid})")
    
    # Wait for startup
    for i in range(30):
        try:
            resp = requests.get(f"http://127.0.0.1:{CDP_PORT}/json/list", timeout=2)
            if resp.json():
                print("  ✓ Browser ready")
                return proc
        except:
            time.sleep(1)
    
    raise Exception("Browser failed to start")

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
    
    def navigate(self, url):
        self.send("Page.navigate", {"url": url})
        time.sleep(5)
    
    def screenshot(self, path):
        result = self.send("Page.captureScreenshot", {"format": "jpeg", "quality": 80})
        if result and "data" in result:
            import base64
            with open(path, "wb") as f:
                f.write(base64.b64decode(result["data"]))
            return path
        return None

def main():
    print("=" * 60)
    print("Gemini Takeout Full Automation")
    print("=" * 60)
    
    browser_proc = None
    try:
        # Start browser
        print("\n[1/8] Starting browser...")
        browser_proc = start_browser()
        
        # Connect to CDP
        print("[2/8] Connecting to CDP...")
        resp = requests.get(f"http://127.0.0.1:{CDP_PORT}/json/list", timeout=5)
        tabs = resp.json()
        if not tabs:
            raise Exception("No tabs found")
        cdp = CDP(tabs[0]["webSocketDebuggerUrl"])
        print("  ✓ Connected")
        
        # Page is already loading takeout.google.com
        print("[3/8] Waiting for page load...")
        time.sleep(8)
        
        # Check login
        print("[4/8] Checking login...")
        logged_in = cdp.eval_js('() => !!document.querySelector(\'[jsname="b2VHfe"]\')')
        if logged_in:
            print("  ✓ Logged in!")
        else:
            print("  ✗ NOT LOGGED IN")
            cdp.screenshot(str(OUTPUT_DIR / "takeout-not-logged-in.jpg"))
            print("  Screenshot saved")
            return False
        
        # Deselect all
        print("[5/8] Deselecting all products...")
        deselected = cdp.eval_js("""
        () => {
            const buttons = document.querySelectorAll('button, [role="button"]');
            for (let btn of buttons) {
                const text = (btn.innerText || '').toLowerCase();
                if (text.includes('deselect') || text.includes('alle aufheben')) {
                    btn.click();
                    return true;
                }
            }
            return false;
        }
        """)
        print(f"  {'✓ Deselected' if deselected else '⚠ Could not deselect'}")
        
        time.sleep(2)
        
        # Select Gemini
        print("[6/8] Selecting Gemini...")
        selected = cdp.eval_js("""
        () => {
            const items = document.querySelectorAll('[role="listitem"], div[role="checkbox"]');
            for (let item of items) {
                const text = (item.innerText || '').toLowerCase();
                if (text.includes('gemini') || text.includes('bard')) {
                    item.click();
                    return true;
                }
            }
            return false;
        }
        """)
        print(f"  {'✓ Selected Gemini' if selected else '⚠ Could not find Gemini'}")
        
        # Screenshot
        print("[7/8] Taking screenshot...")
        screenshot_path = cdp.screenshot(str(OUTPUT_DIR / "takeout-prepared.jpg"))
        if screenshot_path:
            print(f"  ✓ Saved: {screenshot_path}")
        
        # Get state
        print("[8/8] Current state...")
        current_url = cdp.eval_js('() => window.location.href')
        print(f"  URL: {current_url}")
        
        print("\n" + "=" * 60)
        print("SUCCESS - Takeout prepared!")
        print("=" * 60)
        print("\nNext manual steps:")
        print("1. Click 'Next'")
        print("2. Choose JSON format")
        print("3. Click 'Create export'")
        
        return True
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        if browser_proc:
            print("\nStopping browser...")
            browser_proc.terminate()
            browser_proc.wait(timeout=5)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
