# Chat History Extraction Guide

**Last Updated:** 2026-02-19  
**Version:** 1.0

This guide explains how to extract chat histories from Simon's AI platform accounts (Claude.ai, Gemini, Copilot, OpenAI ChatGPT).

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Individual Extractors](#individual-extractors)
5. [Output Format](#output-format)
6. [Data Storage](#data-storage)
7. [Privacy & Security](#privacy--security)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Overview

### What This Does

The extraction scripts automate the process of downloading all your conversation history from four major AI platforms:

- **Claude.ai** (Anthropic)
- **Gemini** (Google)
- **Copilot** (Microsoft)
- **ChatGPT** (OpenAI)

### How It Works

- Uses Selenium with existing Chromium browser profile (no re-login needed)
- Navigates to each platform's chat history interface
- Extracts conversation metadata and messages
- Saves data in structured JSONL format + human-readable summaries
- Performs lightweight categorization (coding, research, planning, casual)
- Estimates token counts for analysis planning

### What It Doesn't Do

- ❌ No AI/LLM analysis of content (deterministic extraction only)
- ❌ No modification or deletion of your conversations
- ❌ No cloud upload (all data stays local)
- ❌ No parallel browser instances (respects 8GB RAM limit)

---

## Prerequisites

### Required

1. **Chromium Profile**: Authenticated browser profiles must exist at:
   ```
   /opt/ai-orchestrator/var/chromium-profile/
   ```
   
2. **Python 3** with Selenium:
   ```bash
   python3 -c "import selenium; print(selenium.__version__)"
   ```

3. **Chrome/Chromium Browser**: Installed and accessible

### Optional

- Sufficient disk space (~100MB-1GB depending on conversation volume)
- Encrypted storage for sensitive exports

---

## Quick Start

### Run All Extractors (Recommended)

```bash
cd /opt/ai-orchestrator/bin
./extract-all-chats.sh
```

This runs all 4 platform extractors sequentially and aggregates results.

### With Options

```bash
# Custom output directory
./extract-all-chats.sh --output-dir /path/to/exports

# Limit conversations per platform (for testing)
./extract-all-chats.sh --limit 10

# Both options
./extract-all-chats.sh --output-dir /tmp/test --limit 5
```

### Expected Runtime

- Per platform: 2-10 minutes (depends on conversation count)
- All platforms: 15-45 minutes total
- Rate limiting: 1-2 second pauses between requests

---

## Individual Extractors

You can run extractors individually if needed:

### Claude.ai

```bash
python3 /opt/ai-orchestrator/bin/extract-claude-chats.py [--output-dir PATH] [--limit N]
```

**Notes:**
- Most reliable extraction (stable UI structure)
- Conversations organized by date automatically

### Gemini

```bash
python3 /opt/ai-orchestrator/bin/extract-gemini-chats.py [--output-dir PATH] [--limit N]
```

**Notes:**
- UI changes frequently; script tries multiple selectors
- Alternative: Google Takeout for official export
- May require sidebar to be expanded

### Copilot

```bash
python3 /opt/ai-orchestrator/bin/extract-copilot-chats.py [--output-dir PATH] [--limit N]
```

**Notes:**
- Requires chat history enabled in Microsoft account settings
- Some conversations may not appear if history was disabled

### OpenAI ChatGPT

```bash
python3 /opt/ai-orchestrator/bin/extract-openai-chats.py [--output-dir PATH] [--limit N]
```

**Notes:**
- Official export available: Settings → Data controls → Export data
- Script provides immediate access without waiting for email

---

## Output Format

### Directory Structure

```
/opt/ai-orchestrator/var/chat-exports/
├── all-20260219-143000/           # Master export (from extract-all-chats.sh)
│   ├── index.md                   # Aggregated overview
│   ├── claude-20260219-143000/
│   │   ├── conversations.jsonl
│   │   └── summary.md
│   ├── gemini-20260219-143100/
│   │   ├── conversations.jsonl
│   │   └── summary.md
│   ├── copilot-20260219-143200/
│   │   ├── conversations.jsonl
│   │   └── summary.md
│   └── openai-20260219-143300/
│       ├── conversations.jsonl
│       └── summary.md
```

### JSONL Format

Each line in `conversations.jsonl` is a complete JSON object:

```json
{
  "id": "abc123-def456",
  "title": "Help with Python API design",
  "url": "https://claude.ai/c/abc123-def456",
  "timestamp": "2024-11-15T10:30:00Z",
  "messages": [
    {
      "role": "user",
      "content": "How do I design a REST API...",
      "timestamp": null
    },
    {
      "role": "assistant",
      "content": "Here are the key principles...",
      "timestamp": null
    }
  ],
  "message_count": 24,
  "token_estimate": 3450,
  "categories": ["coding", "research"],
  "extracted_at": "2026-02-19T14:30:15.123456"
}
```

### Summary Markdown

Human-readable overview including:
- Total statistics
- Category breakdown
- Table of all conversations with metrics

### Categories

Automatic lightweight tagging based on keyword detection:

| Category | Keywords |
|----------|----------|
| **Coding** | code, python, javascript, function, api, debug, error, script |
| **Research** | research, study, paper, article, learn, explain, what is |
| **Planning** | plan, schedule, todo, task, project, goal, strategy |
| **Casual** | hello, thanks, creative, story, joke, fun |
| **General** | (default when no keywords match) |

---

## Data Storage

### Default Location

```
/opt/ai-orchestrator/var/chat-exports/
```

### Disk Space Requirements

- Minimal usage (< 100 conversations): ~50-100 MB
- Moderate usage (100-500 conversations): ~200-500 MB
- Heavy usage (500+ conversations): ~500 MB - 2 GB

### Retention Policy

Exports are **not automatically deleted**. You should:

1. Review exports after creation
2. Move to long-term encrypted storage if keeping
3. Delete when no longer needed

### Backup Recommendations

```bash
# Compress export
tar -czf chat-exports-backup-$(date +%Y%m%d).tar.gz \
    /opt/ai-orchestrator/var/chat-exports/all-*/

# Encrypt (if using GPG)
gpg -c chat-exports-backup-20260219.tar.gz

# Move to secure location
mv chat-exports-backup-20260219.tar.gz.gpg /secure/storage/
```

---

## Privacy & Security

### ⚠️ CRITICAL: This Is Sensitive Personal Data

Your AI conversations may contain:
- Personal thoughts and reflections
- Work-related confidential information
- Code snippets and proprietary logic
- Research ideas and strategies
- Casual personal discussions

### Security Best Practices

1. **Encrypted Storage**
   - Store exports on encrypted drives/volumes
   - Use file encryption (GPG, VeraCrypt, etc.)
   
2. **Access Control**
   - Restrict file permissions: `chmod 700`
   - Don't share with others
   
3. **No Cloud Sync**
   - Exclude from Dropbox, Google Drive, iCloud sync folders
   - Keep local-only unless encrypted

4. **Version Control**
   - NEVER commit to Git or other VCS
   - Add to `.gitignore`:
     ```
     var/chat-exports/
     *.jsonl
     ```

5. **Deletion When Done**
   - Securely delete when no longer needed:
     ```bash
     shred -u /path/to/export/
     # or
     rm -rf /path/to/export/ && sync
     ```

### Who Can Access

- Scripts run with your user permissions
- Data stored in `/opt/ai-orchestrator/var/` (root-owned by default)
- Only users with root/sudo access can read exports

### Compliance Notes

- This is for **personal archival** only
- Not intended for sharing or redistribution
- Respect platform Terms of Service
- Consider data residency requirements if applicable

---

## Troubleshooting

### Common Issues

#### "No conversations found"

**Possible causes:**
- Not logged in to the platform
- Chat history disabled in account settings
- UI structure changed (selectors outdated)

**Solutions:**
1. Verify you're logged in by opening the platform manually
2. Check platform settings for chat history toggle
3. Update script selectors (see Development section)

#### Selenium errors

```
selenium.common.exceptions.SessionNotCreatedException
```

**Solution:**
```bash
# Ensure Chrome/Chromium is installed
chromium --version

# Reinstall Selenium if needed
pip3 install --upgrade selenium
```

#### Memory issues (OOM)

**Solution:**
- Scripts already run sequentially to avoid this
- Close other applications during extraction
- Increase swap space if needed

#### Rate limiting / Too many requests

**Solution:**
- Scripts include built-in delays (1-2 seconds)
- If still rate-limited, increase sleep time in script
- Run during off-peak hours

#### Platform-specific issues

**Claude.ai:**
- Generally most stable
- Ensure conversation list is loaded before extraction

**Gemini:**
- UI changes frequently
- Try expanding sidebar manually first run
- Consider Google Takeout as alternative

**Copilot:**
- Must enable chat history in Microsoft account
- Some regions have limited history features

**ChatGPT:**
- Archived conversations may not appear
- Use official export for complete archive

### Debug Mode

Add verbose logging to any extractor:

```bash
python3 extract-claude-chats.py 2>&1 | tee extraction-log.txt
```

### Manual Testing

Test with single conversation limit:

```bash
python3 extract-claude-chats.py --limit 1
```

Check output directory for results.

---

## FAQ

### Q: Is this safe? Will it modify my conversations?

**A:** Yes, it's safe. The scripts only **read** data, never modify or delete. Your conversations remain unchanged on the platforms.

### Q: How long does extraction take?

**A:** Depends on conversation count:
- 10-50 conversations: 2-5 minutes per platform
- 50-200 conversations: 5-15 minutes per platform
- 200+ conversations: 15-30+ minutes per platform

### Q: Can I stop and resume?

**A:** Partially. Each platform extractor is idempotent—running again won't duplicate within that run. But there's no true resume; it restarts from beginning.

### Q: What if one platform fails?

**A:** The master script (`extract-all-chats.sh`) continues with remaining platforms. Failed platforms are listed in the final summary.

### Q: Can I analyze the extracted data?

**A:** Yes! JSONL format is designed for analysis:

```python
import json

with open('conversations.jsonl') as f:
    conversations = [json.loads(line) for line in f]

# Example: Find longest conversations
sorted_convos = sorted(conversations, key=lambda x: x['token_estimate'], reverse=True)
```

### Q: How often should I export?

**A:** Depends on usage:
- Light users: Monthly is fine
- Heavy users: Weekly or daily
- Before account changes/deletions: Always export first

### Q: Can I import this data elsewhere?

**A:** JSONL is widely supported. Common uses:
- Import into databases (MongoDB, PostgreSQL with JSON)
- Load into analysis tools (Pandas, R)
- Feed into local LLMs for analysis
- Archive in personal knowledge management systems

### Q: What about API-based exports?

**A:** Some platforms offer official APIs:
- **OpenAI**: Settings → Data controls → Export data (email in ~7 days)
- **Google**: Google Takeout (includes Gemini)
- **Claude**: No official export yet (scraping is primary method)
- **Copilot**: Limited export options

These scripts provide **immediate** access without waiting.

---

## Development & Customization

### Modifying Selectors

If a platform changes its UI, update CSS selectors in the relevant script:

```python
# In extract-claude-chats.py
history_selectors = [
    "[data-testid='chat-item']",  # Primary
    "a[href^='/c/']",             # Fallback
]
```

### Adding New Platforms

Copy an existing script and modify:
1. BASE_URL and selectors
2. Message parsing logic
3. Categorization keywords (optional)

### Token Estimation

Current estimation: `len(text) // 4` (rough approximation)

For more accuracy, use tiktoken library:

```python
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
tokens = len(enc.encode(text))
```

---

## Support

For issues or questions:
1. Check this guide first
2. Review troubleshooting section
3. Examine extraction logs
4. Test with `--limit 1` to isolate issues

---

*Documentation Version 1.0 | Last Updated: 2026-02-19*
