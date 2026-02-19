#!/usr/bin/env python3
"""
Direct Selenium screenshot with existing Chromium profile
Non-headless so we can SEE what's happening
"""
import time
import json
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PROFILE = "/opt/ai-orchestrator/var/chromium-profile"
OUTPUT_DIR = Path(f"/opt/ai-orchestrator/var/screenshots/{int(time.time())}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("Selenium Screenshot Session (Non-Headless)")
print("=" * 60)
print(f"\nOutput: {OUTPUT_DIR}")

opts = Options()
opts.add_argument(f"--user-data-dir={PROFILE}")
opts.add_argument("--password-store=basic")
opts.add_argument("--no-sandbox")
opts.add_argument("--window-size=1920,1080")
# NOT headless - we want to see it!

from selenium.webdriver.chrome.service import Service
svc = Service("/usr/bin/chromedriver")

driver = None
try:
    print("\n[1/5] Starting browser...")
    driver = webdriver.Chrome(service=svc, options=opts)
    print("  ✓ Browser started")
    
    print("\n[2/5] Taking initial screenshot...")
    driver.save_screenshot(str(OUTPUT_DIR / "00-initial.png"))
    print(f"  ✓ Saved: {OUTPUT_DIR}/00-initial.png")
    
    print("\n[3/5] Navigating to ChatGPT...")
    driver.get("https://chatgpt.com")
    time.sleep(8)  # Wait for load + potential Cloudflare
    
    print("\n[4/5] Post-navigation screenshot...")
    driver.save_screenshot(str(OUTPUT_DIR / "01-after-nav.png"))
    print(f"  ✓ Saved: {OUTPUT_DIR}/01-after-nav.png")
    
    # Page info
    print("\n[5/5] Page analysis:")
    print(f"  Title: {driver.title}")
    print(f"  URL: {driver.current_url}")
    
    # Check for login button
    try:
        login_btn = driver.find_element(By.CSS_SELECTOR, 'a[href="/login"]')
        print("  ⚠️  NOT LOGGED IN (login button found)")
    except:
        print("  ✓ Appears logged in (no login button)")
    
    # Check for sidebar
    try:
        sidebar = driver.find_element(By.CSS_SELECTOR, 'nav')
        print("  ✓ Sidebar found")
        
        # Get chat links
        chats = driver.find_elements(By.CSS_SELECTOR, 'nav a[href^="/c/"]')
        print(f"  ✓ Found {len(chats)} chat links")
        
        if chats:
            for i, chat in enumerate(chats[:10]):
                title = chat.text.strip() or f"Chat {i+1}"
                print(f"    [{i+1}] {title[:50]}")
            
            # Save chat list
            chat_data = []
            for chat in chats:
                chat_data.append({
                    "title": chat.text.strip(),
                    "href": chat.get_attribute("href")
                })
            
            with open(OUTPUT_DIR / "chats.json", "w") as f:
                json.dump({"count": len(chat_data), "chats": chat_data}, f, indent=2)
            print(f"\n  ✓ Exported: {OUTPUT_DIR}/chats.json")
            
    except Exception as e:
        print(f"  ✗ Sidebar not found: {e}")
    
    # Final screenshot
    driver.save_screenshot(str(OUTPUT_DIR / "99-final.png"))
    print(f"\n✓ Final screenshot: {OUTPUT_DIR}/99-final.png")
    
    print(f"\n{'=' * 60}")
    print(f"SESSION COMPLETE")
    print(f"  Location: {OUTPUT_DIR}")
    print(f"  Files: {len(list(OUTPUT_DIR.glob('*')))}")
    print(f"{'=' * 60}")
    
    print("\nBrowser stays open for 60 seconds for inspection...")
    print("Close it manually or wait for timeout.")
    time.sleep(60)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    if driver:
        try:
            driver.quit()
        except:
            pass
