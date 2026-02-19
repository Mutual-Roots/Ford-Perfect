#!/usr/bin/env bash
# Extrahiert OpenAI/ChatGPT Chat-Historie via Codex CLI + Browser Automation
# Nutzung: ./extract-openai-chats-direct.sh [--output-dir DIR]

set -euo pipefail

OUTPUT_DIR="${1:-/opt/ai-orchestrator/var/chat-exports/openai-$(date +%Y%m%d-%H%M%S)}"
PROFILE="/opt/ai-orchestrator/var/chromium-profile"
COOKIES="/opt/ai-orchestrator/etc/openai_cookies.json"

echo "=== OpenAI Chat Extractor ==="
echo "Output: $OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Check if Codex CLI available
if ! command -v codex &> /dev/null; then
    echo "ERROR: Codex CLI not found. Install with: npm install -g @anthropic-ai/codex-cli"
    exit 1
fi

# Create a minimal git repo for Codex (it requires git)
TEMP_REPO=$(mktemp -d)
cd "$TEMP_REPO"
git init -q
git config user.email "ford-perfect@local"
git config user.name "Ford Perfect"

echo "Temp repo: $TEMP_REPO"

# Codex Task: Navigate to ChatGPT and extract history
CODEX_PROMPT="
You are extracting chat history from ChatGPT.com.

TASK:
1. Open browser to https://chatgpt.com
2. Navigate to chat history (left sidebar)
3. For each conversation:
   - Click to open it
   - Extract full conversation (user messages + assistant responses)
   - Save as JSON with timestamp if available
4. Export all to: $OUTPUT_DIR/chats.json

IMPORTANT:
- Use Selenium with profile: $PROFILE
- Cookies are already in profile (already logged in)
- Handle Cloudflare by waiting 5 seconds after page load
- Output clean JSON, one chat per line

Write a Python script that does this and execute it.
"

echo "Starting Codex..."
codex exec --full-auto "$CODEX_PROMPT"

# Cleanup
cd /opt/ai-orchestrator
rm -rf "$TEMP_REPO"

echo "Done! Check: $OUTPUT_DIR"
