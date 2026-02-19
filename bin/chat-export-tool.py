#!/usr/bin/env python3
"""
Universal Chat Export Tool
Extrahiert Chats von OpenAI, Gemini, Claude, Copilot via offizielle Export-APIs
Kompiliert als native Binary mit PyInstaller
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime

try:
    import requests
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    print("⚠️  Selenium not available - browser automation disabled")

OUTPUT_DIR = Path("/opt/ai-orchestrator/var/chat-exports")
PROFILE = "/opt/ai-orchestrator/var/chromium-profile"

def export_openai_manual():
    """Guide user through manual OpenAI export"""
    print("\n" + "="*60)
    print("OpenAI ChatGPT Export")
    print("="*60)
    print("\nMANUAL EXPORT (official, guaranteed):")
    print("1. Open: https://chat.openai.com/#settings/data-controls")
    print("2. Click 'Export Data'")
    print("3. Wait 10-30 minutes for email")
    print("4. Download JSON and save to:")
    print(f"   {OUTPUT_DIR}/openai-export.json")
    print("\nAutomation blocked by Cloudflare - manual is the way!")
    return None

def export_gemini_takeout():
    """Guide user through Google Takeout"""
    print("\n" + "="*60)
    print("Google Gemini Export (Takeout)")
    print("="*60)
    print("\nMANUAL EXPORT (official, GDPR):")
    print("1. Open: https://takeout.google.com")
    print("2. Click 'Deselect all'")
    print("3. Find and select 'Gemini' or 'Bard'")
    print("4. Click 'Next step'")
    print("5. Choose format: JSON")
    print("6. Click 'Create export'")
    print("7. Wait for email (may take hours)")
    print(f"\nSave to: {OUTPUT_DIR}/gemini-export.json")
    return None

def check_existing_exports():
    """Check if exports already exist"""
    print("\n" + "="*60)
    print("Checking for existing exports...")
    print("="*60)
    
    exports = {
        "openai": OUTPUT_DIR / "openai-export.json",
        "gemini": OUTPUT_DIR / "gemini-export.json",
        "claude": OUTPUT_DIR / "claude-export.json",
        "copilot": OUTPUT_DIR / "copilot-export.json"
    }
    
    found = []
    for name, path in exports.items():
        if path.exists():
            size = path.stat().st_size
            found.append((name, path, size))
            print(f"  ✓ {name.upper()}: {path.name} ({size:,} bytes)")
    
    if not found:
        print("  No exports found yet.")
    
    return found

def parse_and_index(exports):
    """Parse exported JSON files and create index"""
    if not exports:
        print("\nNo exports to parse.")
        return
    
    print("\n" + "="*60)
    print("Parsing and indexing exports...")
    print("="*60)
    
    index = {
        "created_at": datetime.now().isoformat(),
        "sources": [],
        "total_chats": 0,
        "total_messages": 0
    }
    
    for name, path, size in exports:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Count chats/messages (format varies by provider)
            chats = data.get('chats', []) or data.get('conversations', []) or []
            msg_count = sum(len(c.get('messages', [])) for c in chats)
            
            index['sources'].append({
                "provider": name,
                "file": path.name,
                "chats": len(chats),
                "messages": msg_count
            })
            index['total_chats'] += len(chats)
            index['total_messages'] += msg_count
            
            print(f"  ✓ {name.upper()}: {len(chats)} chats, {msg_count} messages")
            
        except Exception as e:
            print(f"  ✗ {name.upper()}: Error parsing - {e}")
    
    # Save index
    index_file = OUTPUT_DIR / "export-index.json"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Index saved: {index_file}")
    print(f"\nSUMMARY:")
    print(f"  Total Chats: {index['total_chats']}")
    print(f"  Total Messages: {index['total_messages']}")
    
    return index

def main():
    print("="*60)
    print("Ford Perfect Chat Export Tool v1.0")
    print("="*60)
    print(f"Output directory: {OUTPUT_DIR}")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Menu
    print("\nOptions:")
    print("  1. Guide: OpenAI Export (manual)")
    print("  2. Guide: Gemini Export (manual)")
    print("  3. Check existing exports")
    print("  4. Parse and index all exports")
    print("  5. Run all guides + check")
    print("  0. Exit")
    
    choice = input("\nYour choice [1-5, 0]: ").strip()
    
    if choice == "1":
        export_openai_manual()
    elif choice == "2":
        export_gemini_takeout()
    elif choice == "3":
        check_existing_exports()
    elif choice == "4":
        exports = check_existing_exports()
        parse_and_index(exports)
    elif choice == "5":
        export_openai_manual()
        export_gemini_takeout()
        exports = check_existing_exports()
        parse_and_index(exports)
    elif choice == "0":
        print("Exiting.")
        sys.exit(0)
    else:
        print("Invalid choice.")
        sys.exit(1)
    
    print("\nDone!")

if __name__ == "__main__":
    main()
