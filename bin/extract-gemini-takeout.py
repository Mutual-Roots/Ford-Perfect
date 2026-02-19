#!/usr/bin/env python3
"""
Google Gemini Chat Extractor via Takeout
Uses existing Chromium profile (already logged in)
Outputs plain text for minimal storage
"""
import time
import json
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Paths
PROFILE = "/opt/ai-orchestrator/var/chromium-profile"
OUTPUT_DIR = Path("/opt/ai-orchestrator/var/chat-exports/gemini-takeout")
LOG_FILE = OUTPUT_DIR / "log.txt"

def log(message):
    """Plain text logging (minimal overhead)"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} - {message}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)
    print(f"  {line.strip()}")

def setup_driver():
    """Setup Chrome with existing profile"""
    opts = Options()
    opts.add_argument(f"--user-data-dir={PROFILE}")
    opts.add_argument("--password-store=basic")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    # NOT headless - runs visible in KDE session
    
    svc = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=svc, options=opts)

def main():
    print("=" * 60)
    print("Gemini Takeout Extractor")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    driver = None
    try:
        log("Started Takeout export")
        
        # Setup
        print("\n[1/6] Starting browser...")
        driver = setup_driver()
        log("Browser started with existing profile")
        
        # Navigate to Takeout
        print("[2/6] Opening Google Takeout...")
        driver.get("https://takeout.google.com")
        time.sleep(5)
        log("Navigated to takeout.google.com")
        
        # Deselect all
        print("[3/6] Deselecting all products...")
        try:
            # Look for "Deselect all" button
            deselect_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "Deselect all")]'))
            )
            deselect_btn.click()
            log("Deselected all products")
        except Exception as e:
            log(f"Deselect failed: {e}")
            # Try alternative selector
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, 'button, [role="button"]')
                for btn in buttons:
                    if "deselect" in btn.text.lower() or "alle aufheben" in btn.text.lower():
                        btn.click()
                        log("Deselected via alternative selector")
                        break
            except:
                log("Could not deselect - continuing anyway")
        
        time.sleep(2)
        
        # Select only Gemini
        print("[4/6] Selecting only Gemini...")
        try:
            # Find Gemini checkbox
            gemini_items = driver.find_elements(By.XPATH, '//*[contains(text(), "Gemini") or contains(text(), "Bard")]')
            if gemini_items:
                # Click the checkbox associated with Gemini
                for item in gemini_items:
                    parent = item.find_element(By.XPATH, "./ancestor::div[@role='listitem'] | ./ancestor::div[contains(@class, 'product-item')]")
                    checkbox = parent.find_element(By.CSS_SELECTOR, 'input[type="checkbox"], [role="checkbox"]')
                    if not checkbox.is_selected():
                        checkbox.click()
                        log("Selected Gemini")
                        break
        except Exception as e:
            log(f"Select Gemini failed: {e}")
        
        time.sleep(2)
        
        # Set format to JSON
        print("[5/6] Setting export format to JSON...")
        try:
            # Look for format dropdown
            format_btns = driver.find_elements(By.XPATH, '//*[contains(text(), "Format") or contains(text(), ".zip") or contains(text(), ".tgz")]')
            if format_btns:
                format_btns[0].click()
                time.sleep(1)
                
                # Select JSON if available
                json_options = driver.find_elements(By.XPATH, '//*[contains(text(), "JSON") or contains(text(), "json")]')
                if json_options:
                    json_options[0].click()
                    log("Set format to JSON")
        except Exception as e:
            log(f"Format selection failed: {e}")
        
        # Create export
        print("[6/6] Creating export...")
        try:
            create_btns = driver.find_elements(By.XPATH, '//*[contains(text(), "Create export") or contains(text(), "Export erstellen")]')
            if create_btns:
                create_btns[0].click()
                log("Export created - waiting for email delivery")
        except Exception as e:
            log(f"Create export failed: {e}")
        
        # Wait for confirmation
        time.sleep(10)
        
        # Screenshot for verification
        screenshot = OUTPUT_DIR / "takeout-screenshot.jpg"
        driver.save_screenshot(str(screenshot))
        log(f"Screenshot saved: {screenshot}")
        
        # Final status
        print("\n" + "=" * 60)
        log("EXPORT COMPLETE")
        log("Check your email for download link from Google")
        log(f"Output directory: {OUTPUT_DIR}")
        print("=" * 60)
        
        print("\nBrowser stays open for inspection (60s)...")
        time.sleep(60)
        
    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
