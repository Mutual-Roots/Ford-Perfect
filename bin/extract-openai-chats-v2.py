#!/usr/bin/env python3
"""
OpenAI ChatGPT Chat History Extractor
Uses Selenium with existing Chromium profile (already logged in via Google OAuth)
Extracts all conversations to JSON + Markdown
"""
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

PROFILE = "/opt/ai-orchestrator/var/chromium-profile"
OUTPUT_DIR = Path("/opt/ai-orchestrator/var/chat-exports/openai-" + datetime.now().strftime("%Y%m%d-%H%M%S"))

def make_driver(headless=True):
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE}")
    opts.add_argument("--password-store=basic")
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    from selenium.webdriver.chrome.service import Service
    svc = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=svc, options=opts)

def wait_for_cloudflare(driver, timeout=30):
    """Wait for Cloudflare challenge to complete"""
    print("Waiting for Cloudflare check...")
    for i in range(timeout):
        if "Just a moment" not in driver.title:
            print(f"✓ Cloudflare passed after {i}s")
            return True
        time.sleep(1)
    print("✗ Cloudflare timeout")
    return False

def extract_chat_history(driver):
    """Extract all chats from sidebar"""
    chats = []
    
    # Navigate to chat history page
    driver.get("https://chatgpt.com/gpts")
    time.sleep(3)
    
    # Try to find chat list in sidebar
    try:
        # Wait for sidebar to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'nav a[href^="/c/"]'))
        )
        
        # Find all chat links
        chat_links = driver.find_elements(By.CSS_SELECTOR, 'nav a[href^="/c/"]')
        print(f"Found {len(chat_links)} chats in sidebar")
        
        for i, link in enumerate(chat_links[:20]):  # Limit to first 20 for testing
            try:
                chat_title = link.text.strip() or f"Chat #{i+1}"
                chat_url = link.get_attribute("href")
                
                print(f"  [{i+1}] {chat_title}")
                
                # Click to open chat
                link.click()
                time.sleep(2)
                
                # Extract conversation
                messages = []
                msg_elements = driver.find_elements(By.CSS_SELECTOR, '[data-message-author-role]')
                
                for msg in msg_elements:
                    role = msg.get_attribute("data-message-author-role")
                    content = msg.find_element(By.CSS_SELECTOR, ".prose").text if msg.find_elements(By.CSS_SELECTOR, ".prose") else ""
                    
                    messages.append({
                        "role": "assistant" if role == "assistant" else "user",
                        "content": content
                    })
                
                chats.append({
                    "title": chat_title,
                    "url": chat_url,
                    "messages": messages,
                    "message_count": len(messages)
                })
                
                # Go back to chat list
                driver.back()
                time.sleep(1)
                
            except Exception as e:
                print(f"    Error extracting chat: {e}")
                continue
                
    except TimeoutException:
        print("Sidebar not found - user may not have chat history enabled")
    
    return chats

def main():
    print("=" * 60)
    print("OpenAI ChatGPT Chat Extractor")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")
    
    driver = None
    try:
        print("\n[1/4] Starting browser...")
        driver = make_driver(headless=True)
        
        print("[2/4] Navigating to chatgpt.com...")
        driver.get("https://chatgpt.com")
        
        # Wait for Cloudflare
        if not wait_for_cloudflare(driver, timeout=20):
            print("ERROR: Cloudflare challenge failed. Try non-headless mode.")
            sys.exit(1)
        
        print("[3/4] Extracting chat history...")
        chats = extract_chat_history(driver)
        
        print(f"\n[4/4] Saving {len(chats)} chats...")
        
        # Save as JSON
        json_file = OUTPUT_DIR / "chats.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({"exported_at": datetime.now().isoformat(), "total_chats": len(chats), "chats": chats}, f, indent=2, ensure_ascii=False)
        print(f"✓ JSON: {json_file}")
        
        # Save as Markdown (one file per chat)
        md_dir = OUTPUT_DIR / "markdown"
        md_dir.mkdir(exist_ok=True)
        
        for i, chat in enumerate(chats):
            md_file = md_dir / f"{i+1:03d}_{chat['title'][:50]}.md"
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# {chat['title']}\n\n")
                f.write(f"**URL:** {chat['url']}\n\n")
                f.write(f"**Messages:** {chat['message_count']}\n\n---\n\n")
                
                for msg in chat['messages']:
                    role_emoji = "👤" if msg['role'] == 'user' else "🤖"
                    f.write(f"### {role_emoji} {msg['role'].title()}\n\n")
                    f.write(f"{msg['content']}\n\n---\n\n")
            
        print(f"✓ Markdown files: {md_dir}/")
        
        # Summary
        total_messages = sum(c['message_count'] for c in chats)
        print(f"\n{'=' * 60}")
        print(f"EXPORT COMPLETE")
        print(f"  Total chats: {len(chats)}")
        print(f"  Total messages: {total_messages}")
        print(f"  Location: {OUTPUT_DIR}")
        print(f"{'=' * 60}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
