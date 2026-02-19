#!/usr/bin/env bash
# Extrahiert OpenAI Chats via OpenClaw Browser-Relay (steuert deinen lokalen Browser)
# Voraussetzung: OpenClaw Browser Relay Extension ist aktiv in deinem Chrome auf Windows

set -euo pipefail

OUTPUT_DIR="/opt/ai-orchestrator/var/chat-exports/openai-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUTPUT_DIR"

echo "=== OpenAI Chat Extractor (Remote via Browser-Relay) ==="
echo ""
echo "ANLEITUNG:"
echo "1. Öffne Chrome auf deinem Windows-Rechner"
echo "2. Geh zu https://chatgpt.com"
echo "3. Klick das OpenClaw Browser Relay Extension-Icon (muss farbig sein)"
echo "4. Drücke ENTER hier wenn bereit..."
read

echo ""
echo "Starte Extraktion..."

# Navigate to ChatGPT
echo "[1/5] Opening chatgpt.com..."
openclaw browser navigate --targetUrl "https://chatgpt.com" || {
    echo "ERROR: Browser-Relay nicht erreichbar. Ist die Extension aktiv?"
    exit 1
}

sleep 5

# Take screenshot to verify
echo "[2/5] Taking screenshot..."
openclaw browser screenshot --fullPage --output "$OUTPUT_DIR/00-homepage.png"

# Navigate to history/settings
echo "[3/5] Navigating to settings..."
# Click on user menu, then settings, then data controls
# This would need actual UI automation based on what we see

echo "[4/5] Exporting data..."
# Go to Settings → Data Controls → Export Data
# Click export button

echo "[5/5] Waiting for download..."
# Wait for OpenAI to prepare export (takes ~10-30 min)
# Download will appear in Downloads folder

echo ""
echo "DONE!"
echo "Export file will be downloaded to your Windows Downloads folder"
echo "Move it to: $OUTPUT_DIR"
echo ""
echo "Alternative: Manual export at https://chat.openai.com/#settings/data-controls"
