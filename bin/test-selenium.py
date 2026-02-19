#!/usr/bin/env python3
"""
Quick Selenium test to verify browser automation works with existing profile.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

CHROMIUM_PROFILE_PATH = "/opt/ai-orchestrator/var/chromium-profile"
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
CHROME_BINARY_PATH = "/usr/bin/chromium"

def test_browser():
    options = Options()
    options.add_argument(f"--user-data-dir={CHROMIUM_PROFILE_PATH}")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.binary_location = CHROME_BINARY_PATH
    
    service = Service(executable_path=CHROMEDRIVER_PATH)
    
    print("Starting browser...")
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Test 1: Simple page
        print("Test 1: Loading example.com...")
        driver.get("https://example.com")
        time.sleep(2)
        print(f"  Title: {driver.title}")
        assert "Example" in driver.title
        print("  ✓ Passed")
        
        # Test 2: Check if we can access authenticated sites
        print("\nTest 2: Checking Claude.ai login status...")
        driver.get("https://claude.ai")
        time.sleep(5)
        print(f"  Title: {driver.title}")
        print(f"  URL: {driver.current_url}")
        
        # Check for signs of being logged in
        page_source = driver.page_source
        if "sign in" in page_source.lower() or "log in" in page_source.lower():
            print("  ⚠ Appears NOT logged in (login prompts detected)")
        else:
            print("  ✓ May be logged in (no obvious login prompts)")
        
        # Test 3: Try to find conversation elements
        print("\nTest 3: Looking for conversation selectors...")
        selectors_to_try = [
            "[data-testid='chat-item']",
            "a[href^='/c/']",
            "[class*='chat']",
            "nav a",
        ]
        
        for selector in selectors_to_try:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"  ✓ Found {len(elements)} elements with: {selector}")
                    for elem in elements[:3]:
                        text = elem.text.strip()[:50]
                        href = elem.get_attribute("href", "")[:60]
                        print(f"    - Text: '{text}' Href: {href}")
                else:
                    print(f"  - No elements with: {selector}")
            except Exception as e:
                print(f"  ✗ Error with {selector}: {e}")
        
        print("\n✅ All basic tests passed!")
        
    finally:
        driver.quit()
        print("\nBrowser closed.")

if __name__ == "__main__":
    test_browser()
