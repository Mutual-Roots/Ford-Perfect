#!/usr/bin/env python3
"""
Claude.ai Chat History Extractor

Extracts all conversations from Claude.ai using Selenium with existing Chromium profile.
Output: JSONL (one conversation per line) + Markdown summary

Usage: python3 extract-claude-chats.py [--output-dir /path/to/output]
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
BASE_URL = "https://claude.ai"
CONVERSATIONS_URL = "https://claude.ai/chats"
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
    """Navigate to chat list and extract conversation metadata."""
    print(f"[{datetime.now().isoformat()}] Navigating to conversations page...")
    driver.get(CONVERSATIONS_URL)
    time.sleep(3)  # Let page load
    
    # Wait for conversation list to load
    conversation_items = wait_for_element(driver, "[data-testid='chat-item']", timeout=20)
    if not conversation_items:
        print("[WARNING] Could not find conversation list. Trying alternative selector...")
        # Try alternative selectors
        conversation_items = wait_for_element(driver, "a[href^='/c/']", timeout=10)
    
    if not conversation_items:
        print("[ERROR] Could not locate conversations. Are you logged in?")
        return []
    
    # Get all conversation links
    conversations = []
    try:
        # Find all conversation items
        items = driver.find_elements(By.CSS_SELECTOR, "[data-testid='chat-item']")
        if not items:
            items = driver.find_elements(By.CSS_SELECTOR, "a[href^='/c/']")
        
        print(f"[INFO] Found {len(items)} conversations in list")
        
        for item in items:
            try:
                # Extract conversation metadata
                href = item.get_attribute("href")
                if not href or '/c/' not in href:
                    continue
                    
                conv_id = href.split('/c/')[-1].split('?')[0]
                title_elem = item.find_element(By.CSS_SELECTOR, "div.font-medium, h3, .text-sm")
                title = title_elem.text.strip() if title_elem else "Untitled"
                
                # Try to get timestamp
                time_elem = item.find_element(By.CSS_SELECTOR, "time, [datetime], .text-xs")
                timestamp = time_elem.get_attribute("datetime") if time_elem else None
                
                conversations.append({
                    "id": conv_id,
                    "title": title,
                    "url": f"{BASE_URL}/c/{conv_id}",
                    "timestamp": timestamp,
                    "extracted_at": datetime.now().isoformat()
                })
            except Exception as e:
                print(f"[WARN] Skipping conversation item: {e}")
                continue
                
    except Exception as e:
        print(f"[ERROR] Error extracting conversation list: {e}")
    
    return conversations

def extract_conversation_details(driver, conv_id):
    """Navigate to individual conversation and extract messages."""
    url = f"{BASE_URL}/c/{conv_id}"
    print(f"  [{datetime.now().isoformat()}] Extracting: {url}")
    
    try:
        driver.get(url)
        time.sleep(2)  # Let page load
        
        # Wait for messages to load
        messages_container = wait_for_element(driver, "[data-testid='message']", timeout=10)
        if not messages_container:
            # Try alternative
            messages_container = wait_for_element(driver, ".message-container, .prose", timeout=5)
        
        if not messages_container:
            print(f"    [WARN] No messages found for {conv_id}")
            return None
        
        # Extract all messages
        messages = []
        try:
            # Find message elements - Claude uses different structures
            message_elements = driver.find_elements(By.CSS_SELECTOR, "[data-testid='message']")
            
            if not message_elements:
                # Fallback: try to get all text content
                content = driver.find_element(By.TAG_NAME, "body")
                return {"raw_content": content.text}
            
            for msg_elem in message_elements:
                try:
                    # Determine if user or assistant
                    is_user = "user" in msg_elem.get_attribute("class", "").lower() or \
                              msg_elem.get_attribute("data-role") == "user"
                    
                    # Extract message content
                    content_elem = msg_elem.find_element(By.CSS_SELECTOR, "p, div.prose, .message-content")
                    content = content_elem.text.strip() if content_elem else ""
                    
                    # Try to get timestamp
                    time_elem = msg_elem.find_element(By.CSS_SELECTOR, "time, [datetime]")
                    timestamp = time_elem.get_attribute("datetime") if time_elem else None
                    
                    if content:
                        messages.append({
                            "role": "user" if is_user else "assistant",
                            "content": content,
                            "timestamp": timestamp
                        })
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"    [WARN] Error extracting messages: {e}")
            # Fallback to raw text
            messages = [{"role": "unknown", "content": driver.find_element(By.TAG_NAME, "body").text}]
        
        return {
            "id": conv_id,
            "messages": messages,
            "message_count": len(messages),
            "extracted_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"    [ERROR] Failed to extract conversation {conv_id}: {e}")
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
           ["code", "python", "javascript", "function", "api", "debug", "error", "script", "program"]):
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
    parser = argparse.ArgumentParser(description="Extract Claude.ai chat history")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of conversations")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir) / f"claude-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    jsonl_path = output_dir / "conversations.jsonl"
    summary_path = output_dir / "summary.md"
    
    print(f"[{datetime.now().isoformat()}] Starting Claude.ai extraction")
    print(f"[INFO] Output directory: {output_dir}")
    print(f"[INFO] Using Chromium profile: {CHROMIUM_PROFILE_PATH}")
    
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
            
            conv_data = extract_conversation_details(driver, conv_meta['id'])
            
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
                
                # Write to JSONL immediately (idempotent)
                with open(jsonl_path, 'a') as f:
                    f.write(json.dumps(conv_data, ensure_ascii=False) + '\n')
            
            # Rate limiting: pause between requests
            time.sleep(1)
        
        # Generate summary
        print(f"\n[{datetime.now().isoformat()}] Generating summary...")
        
        with open(summary_path, 'w') as f:
            f.write("# Claude.ai Chat Export Summary\n\n")
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
            f.write("| # | Title | Messages | Tokens | Categories | Date |\n")
            f.write("|---|-------|----------|--------|------------|------|\n")
            
            for i, conv in enumerate(extracted_conversations, 1):
                title = conv.get('title', 'Untitled')[:50]
                msgs = conv.get('message_count', 0)
                tokens = conv.get('token_estimate', 0)
                cats = ", ".join(conv.get('categories', ['general']))
                ts = conv.get('timestamp', '')[:10] if conv.get('timestamp') else 'N/A'
                f.write(f"| {i} | {title} | {msgs} | {tokens:,} | {cats} | {ts} |\n")
        
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
