#!/usr/bin/env python3
"""
Microsoft Copilot Chat History Extractor

Extracts all conversations from Microsoft Copilot (copilot.microsoft.com) using Selenium.
Note: Copilot chat history availability depends on account settings and region.

Output: JSONL (one conversation per line) + Markdown summary

Usage: python3 extract-copilot-chats.py [--output-dir /path/to/output]
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuration
CHROMIUM_PROFILE_PATH = "/opt/ai-orchestrator/var/chromium-profile"
BASE_URL = "https://copilot.microsoft.com"
CHAT_URL = "https://copilot.microsoft.com"
DEFAULT_OUTPUT_DIR = "/opt/ai-orchestrator/var/chat-exports"
CHROMEDRIVER_PATH = "/usr/bin/chromedriver"
CHROME_BINARY_PATH = "/usr/bin/chromium"

def setup_driver():
    """Configure Chrome driver with existing profile."""
    options = Options()
    options.add_argument(f"--user-data-dir={CHROMIUM_PROFILE_PATH}")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.binary_location = CHROME_BINARY_PATH
    
    service = Service(executable_path=CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def wait_for_element(driver, selector, timeout=15):
    """Wait for element to be present."""
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
    except TimeoutException:
        return None

def extract_conversation_list(driver):
    """Navigate to chat history and extract conversation metadata."""
    print(f"[{datetime.now().isoformat()}] Navigating to Copilot...")
    driver.get(CHAT_URL)
    time.sleep(5)  # Let page load
    
    conversations = []
    
    try:
        # Wait for main interface to load
        wait_for_element(driver, "main, [role='main'], cib-serp", timeout=20)
        
        # Look for chat history sidebar
        # Copilot's UI structure - trying multiple selectors
        history_selectors = [
            "[data-testid='chat-history-item']",
            "cib-conversation-history a",
            ".chat-history-item",
            "[class*='history'] a",
            "nav ul li a",
            "aside a[href*='/chat/']",
        ]
        
        history_items = None
        for selector in history_selectors:
            items = driver.find_elements(By.CSS_SELECTOR, selector)
            if items:
                history_items = items
                print(f"[INFO] Found {len(items)} items with selector: {selector}")
                break
        
        if not history_items:
            print("[WARN] Could not find chat history sidebar.")
            print("[INFO] Copilot may require manual history enablement or uses different storage.")
            # Try to get current conversation at least
            return [{"id": "current", "title": "Current Session", "url": CHAT_URL}]
        
        for item in history_items[:50]:  # Limit to avoid rate issues
            try:
                href = item.get_attribute("href")
                text = item.text.strip()
                
                if not text or len(text) < 3:
                    continue
                
                # Extract ID from URL if available
                conv_id = href.split('/chat/')[-1].split('?')[0] if href else f"conv_{len(conversations)}"
                
                conversations.append({
                    "id": conv_id,
                    "title": text[:100],
                    "url": href or CHAT_URL,
                    "timestamp": None,
                    "extracted_at": datetime.now().isoformat()
                })
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"[ERROR] Error extracting conversation list: {e}")
        return [{"id": "fallback", "title": "Fallback Export", "url": CHAT_URL}]
    
    return conversations

def extract_conversation_details(driver, conv_url, conv_id):
    """Navigate to individual conversation and extract messages."""
    print(f"  [{datetime.now().isoformat()}] Extracting: {conv_url}")
    
    try:
        driver.get(conv_url)
        time.sleep(3)  # Let page load
        
        # Wait for content
        wait_for_element(driver, "main, cib-serp, [role='main']", timeout=10)
        
        messages = []
        
        try:
            # Copilot uses specific web components
            # Try to find message elements
            message_selectors = [
                "[data-testid='user-message']",
                "[data-testid='bot-message']",
                ".user-message",
                ".bot-message",
                "cib-message[source='user']",
                "cib-message[source='bot']",
                "[class*='user'] .message-content",
                "[class*='assistant'] .message-content",
            ]
            
            all_messages = []
            for selector in message_selectors:
                elems = driver.find_elements(By.CSS_SELECTOR, selector)
                if elems:
                    all_messages.extend(elems)
                    break
            
            if not all_messages:
                # Fallback: look for any text content in main area
                main_content = driver.find_element(By.CSS_SELECTOR, "main, [role='main']")
                paragraphs = main_content.find_elements(By.CSS_SELECTOR, "p, div[role='paragraph'], span")
                
                for p in paragraphs:
                    text = p.text.strip()
                    if text and len(text) > 10:
                        all_messages.append(p)
            
            for msg_elem in all_messages:
                try:
                    # Determine role
                    class_name = msg_elem.get_attribute("class", "").lower()
                    tag_name = msg_elem.tag_name.lower()
                    data_testid = msg_elem.get_attribute("data-testid", "")
                    
                    is_user = ("user" in class_name or 
                              data_testid == "user-message" or 
                              "user" in data_testid.lower())
                    is_assistant = ("bot" in class_name or 
                                   "assistant" in class_name or
                                   data_testid == "bot-message" or
                                   "bot" in data_testid.lower())
                    
                    # Get content
                    content = msg_elem.text.strip()
                    
                    if content and len(content) > 5:
                        messages.append({
                            "role": "user" if is_user else ("assistant" if is_assistant else "unknown"),
                            "content": content
                        })
                except Exception as e:
                    continue
            
            # Deduplicate consecutive same-role messages
            deduped_messages = []
            last_role = None
            for msg in messages:
                if msg["role"] != last_role:
                    deduped_messages.append(msg)
                    last_role = msg["role"]
                elif deduped_messages:
                    deduped_messages[-1]["content"] += "\n\n" + msg["content"]
                    
        except Exception as e:
            print(f"    [WARN] Error parsing messages: {e}")
            body_text = driver.find_element(By.TAG_NAME, "body").text
            messages = [{"role": "unknown", "content": body_text}]
        
        return {
            "id": conv_id,
            "messages": deduped_messages,
            "message_count": len(deduped_messages),
            "extracted_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"    [ERROR] Failed to extract conversation: {e}")
        return None

def estimate_tokens(text):
    """Rough token estimation (4 chars ≈ 1 token for English)."""
    if not text:
        return 0
    return len(str(text)) // 4

def categorize_conversation(title, messages):
    """Lightweight categorization based on keywords."""
    title_lower = (title or "").lower()
    content_sample = " ".join([m.get("content", "") for m in messages[:3]]).lower()
    
    categories = []
    
    # Coding indicators
    if any(kw in title_lower or kw in content_sample for kw in 
           ["code", "python", "javascript", "function", "api", "debug", "error", "script", "program", "microsoft"]):
        categories.append("coding")
    
    # Research indicators
    if any(kw in title_lower or kw in content_sample for kw in 
           ["research", "study", "paper", "article", "learn", "explain", "what is", "how does"]):
        categories.append("research")
    
    # Planning indicators
    if any(kw in title_lower or kw in content_sample for kw in 
           ["plan", "schedule", "todo", "task", "project", "goal", "strategy"]):
        categories.append("planning")
    
    # Casual indicators
    if any(kw in title_lower or kw in content_sample for kw in 
           ["hello", "hi ", "thanks", "creative", "story", "joke", "fun"]):
        categories.append("casual")
    
    return categories if categories else ["general"]

def main():
    parser = argparse.ArgumentParser(description="Extract Copilot chat history")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of conversations")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) / f"copilot-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    jsonl_path = output_dir / "conversations.jsonl"
    summary_path = output_dir / "summary.md"
    
    print(f"[{datetime.now().isoformat()}] Starting Copilot extraction")
    print(f"[INFO] Output directory: {output_dir}")
    print(f"[INFO] Using Chromium profile: {CHROMIUM_PROFILE_PATH}")
    print("[NOTE] Copilot chat history must be enabled in settings for full extraction.")
    
    driver = None
    try:
        driver = setup_driver()
        
        # Step 1: Get conversation list
        conversations_meta = extract_conversation_list(driver)
        
        if not conversations_meta:
            print("[ERROR] No conversations found. Exiting.")
            sys.exit(1)
        
        print(f"[INFO] Found {len(conversations_meta)} conversations")
        
        if args.limit:
            conversations_meta = conversations_meta[:args.limit]
            print(f"[INFO] Limited to {args.limit} conversations")
        
        # Step 2: Extract each conversation
        extracted_conversations = []
        total_messages = 0
        total_tokens = 0
        
        for i, conv_meta in enumerate(conversations_meta, 1):
            print(f"\n[{i}/{len(conversations_meta)}] Processing: {conv_meta['title']}")
            
            conv_data = extract_conversation_details(driver, conv_meta['url'], conv_meta['id'])
            
            if conv_data and conv_data.get('messages'):
                # Merge metadata
                conv_data['title'] = conv_meta['title']
                conv_data['timestamp'] = conv_meta['timestamp']
                conv_data['url'] = conv_meta['url']
                
                # Calculate stats
                conv_tokens = sum(estimate_tokens(m.get('content', '')) for m in conv_data['messages'])
                conv_data['token_estimate'] = conv_tokens
                conv_data['categories'] = categorize_conversation(conv_meta['title'], conv_data['messages'])
                
                extracted_conversations.append(conv_data)
                total_messages += conv_data['message_count']
                total_tokens += conv_tokens
                
                # Write to JSONL immediately
                with open(jsonl_path, 'a') as f:
                    f.write(json.dumps(conv_data, ensure_ascii=False) + '\n')
            
            # Rate limiting
            time.sleep(2)
        
        # Generate summary
        print(f"\n[{datetime.now().isoformat()}] Generating summary...")
        
        with open(summary_path, 'w') as f:
            f.write("# Microsoft Copilot Chat Export Summary\n\n")
            f.write(f"**Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Conversations:** {len(extracted_conversations)}\n")
            f.write(f"**Total Messages:** {total_messages}\n")
            f.write(f"**Estimated Tokens:** {total_tokens:,}\n\n")
            
            f.write("## Conversations by Category\n\n")
            categories = {}
            for conv in extracted_conversations:
                for cat in conv.get('categories', ['general']):
                    categories[cat] = categories.get(cat, 0) + 1
            
            for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
                f.write(f"- **{cat.title()}:** {count}\n")
            
            f.write("\n## Conversations (Newest First)\n\n")
            f.write("| # | Title | Messages | Tokens | Categories |\n")
            f.write("|---|-------|----------|--------|------------|\n")
            
            for i, conv in enumerate(extracted_conversations, 1):
                title = conv.get('title', 'Untitled')[:50]
                msgs = conv.get('message_count', 0)
                tokens = conv.get('token_estimate', 0)
                cats = ", ".join(conv.get('categories', ['general']))
                f.write(f"| {i} | {title} | {msgs} | {tokens:,} | {cats} |\n")
        
        print(f"\n[{datetime.now().isoformat()}] Extraction complete!")
        print(f"[SUCCESS] JSONL: {jsonl_path}")
        print(f"[SUCCESS] Summary: {summary_path}")
        print(f"[STATS] {len(extracted_conversations)} conversations, {total_messages} messages, ~{total_tokens:,} tokens")
        
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    main()
