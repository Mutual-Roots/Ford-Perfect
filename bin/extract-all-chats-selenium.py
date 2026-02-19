#!/usr/bin/env python3
"""
Extract chats from Copilot, Gemini, and Drive using Selenium
Runs in KDE session with existing profile (already logged in)
"""
import json
import time
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

PROFILE = "/opt/ai-orchestrator/var/chromium-profile"
OUTPUT_DIR = Path(f"/opt/ai-orchestrator/var/chat-exports/{datetime.now().strftime('%Y%m%d-%H%M%S')}")

def make_driver():
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE}")
    opts.add_argument("--password-store=basic")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    # NOT headless - runs visible in KDE
    return webdriver.Chrome(options=opts)

def extract_copilot(driver):
    """Extract Microsoft Copilot chats"""
    print("\n=== COPILOT ===")
    driver.get("https://copilot.microsoft.com")
    time.sleep(8)
    
    driver.save_screenshot(str(OUTPUT_DIR / "copilot.jpg"))
    
    # Check login
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="user-icon"], .user-icon'))
        )
        print("  ✓ Logged in")
    except:
        print("  ⚠️  Not logged in or different UI")
        return []
    
    # Get chat history
    chats = []
    try:
        items = driver.find_elements(By.CSS_SELECTOR, 'ul[role="list"] li, [class*="chat-history"] a')
        for item in items[:20]:
            text = item.text.strip()
            if text and len(text) > 3:
                chats.append({"title": text[:200]})
        print(f"  Found {len(chats)} chats")
    except Exception as e:
        print(f"  Could not extract: {e}")
    
    return chats

def extract_gemini(driver):
    """Extract Google Gemini chats"""
    print("\n=== GEMINI ===")
    driver.get("https://gemini.google.com")
    time.sleep(8)
    
    driver.save_screenshot(str(OUTPUT_DIR / "gemini.jpg"))
    
    # Check login
    try:
        avatar = driver.find_element(By.CSS_SELECTOR, '[jsname="b2VHfe"], img[src*="lh3.googleusercontent"]')
        print("  ✓ Logged in")
    except:
        print("  ⚠️  Not logged in")
        return []
    
    # Get chat history
    chats = []
    try:
        items = driver.find_elements(By.CSS_SELECTOR, 'nav [role="listitem"], .conversation-item')
        for item in items[:20]:
            text = item.text.strip()
            if text and len(text) > 3:
                chats.append({"title": text[:200]})
        print(f"  Found {len(chats)} chats")
    except Exception as e:
        print(f"  Could not extract: {e}")
    
    return chats

def extract_drive(driver):
    """List recent Google Drive files"""
    print("\n=== GOOGLE DRIVE ===")
    driver.get("https://drive.google.com/drive/recent")
    time.sleep(8)
    
    driver.save_screenshot(str(OUTPUT_DIR / "drive.jpg"))
    
    # Check login
    try:
        avatar = driver.find_element(By.CSS_SELECTOR, '[jsname="b2VHfe"]')
        print("  ✓ Logged in")
    except:
        print("  ⚠️  Not logged in")
        return []
    
    # Get recent files
    files = []
    try:
        items = driver.find_elements(By.CSS_SELECTOR, '[role="row"][aria-label]')
        seen = set()
        for item in items[:50]:
            name = item.get_attribute('aria-label')
            if name and name not in seen and len(name) > 3:
                seen.add(name)
                files.append({"name": name[:200]})
        print(f"  Found {len(files)} recent files")
    except Exception as e:
        print(f"  Could not extract: {e}")
    
    return files

def main():
    print("=" * 60)
    print("Copilot + Gemini + Drive Extractor (Selenium)")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput: {OUTPUT_DIR}")
    
    driver = None
    try:
        print("\n[1/5] Starting browser...")
        driver = make_driver()
        print("  ✓ Browser started (visible in KDE)")
        
        # Extract all
        copilot_chats = extract_copilot(driver)
        gemini_chats = extract_gemini(driver)
        drive_files = extract_drive(driver)
        
        # Save results
        print("\n" + "=" * 60)
        print("SAVING RESULTS")
        print("=" * 60)
        
        results = {
            "exported_at": datetime.now().isoformat(),
            "copilot": {"count": len(copilot_chats), "chats": copilot_chats},
            "gemini": {"count": len(gemini_chats), "chats": gemini_chats},
            "drive": {"count": len(drive_files), "files": drive_files}
        }
        
        output_file = OUTPUT_DIR / "export-summary.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Summary: {output_file}")
        print(f"  Copilot: {len(copilot_chats)} chats")
        print(f"  Gemini: {len(gemini_chats)} chats")
        print(f"  Drive: {len(drive_files)} files")
        print(f"\nScreenshots: {OUTPUT_DIR}/*.jpg")
        
        print(f"\n{'=' * 60}")
        print("EXTRACTION COMPLETE")
        print(f"  Location: {OUTPUT_DIR}")
        print(f"{'=' * 60}")
        
        print("\nBrowser stays open for 60 seconds...")
        time.sleep(60)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
