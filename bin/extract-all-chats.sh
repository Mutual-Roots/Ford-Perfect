#!/bin/bash
#
# Master Chat History Extractor Orchestrator
# 
# Runs all 4 platform extractors sequentially (to respect RAM limits)
# Aggregates results into timestamped export directory
# Generates index.md with overview
#
# Usage: ./extract-all-chats.sh [--output-dir /path] [--limit N]
#

set -e  # Exit on first error, but we'll handle individual failures

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_OUTPUT_DIR="/opt/ai-orchestrator/var/chat-exports"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DATE_HUMAN=$(date +"%Y-%m-%d %H:%M:%S")

# Parse arguments
OUTPUT_DIR="${DEFAULT_OUTPUT_DIR}"
LIMIT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --limit)
            LIMIT="--limit $2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--output-dir /path] [--limit N]"
            echo ""
            echo "Options:"
            echo "  --output-dir  Base output directory (default: ${DEFAULT_OUTPUT_DIR})"
            echo "  --limit       Limit conversations per platform"
            echo "  -h, --help    Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create main export directory
mkdir -p "${OUTPUT_DIR}"

# Final aggregated output directory
AGGREGATED_DIR="${OUTPUT_DIR}/all-${TIMESTAMP}"
mkdir -p "${AGGREGATED_DIR}"

echo "========================================"
echo "  Chat History Extraction Orchestrator"
echo "========================================"
echo ""
echo "Start Time: ${DATE_HUMAN}"
echo "Output Directory: ${AGGREGATED_DIR}"
echo ""

# Track results
declare -A RESULTS
TOTAL_CONVERSATIONS=0
TOTAL_MESSAGES=0
TOTAL_TOKENS=0
FAILED_PLATFORMS=()

# Function to run extractor
run_extractor() {
    local platform=$1
    local script="${SCRIPT_DIR}/extract-${platform}-chats.py"
    local platform_output="${AGGREGATED_DIR}/${platform}"
    
    echo ""
    echo "----------------------------------------"
    echo "Extracting from: ${platform^^}"
    echo "----------------------------------------"
    
    if [[ ! -f "${script}" ]]; then
        echo "[ERROR] Script not found: ${script}"
        FAILED_PLATFORMS+=("${platform}")
        return 1
    fi
    
    # Run the extractor
    if python3 "${script}" --output-dir "${platform_output}" ${LIMIT}; then
        echo "[SUCCESS] ${platform} extraction completed"
        
        # Try to parse stats from summary if it exists
        local summary_file="${platform_output}-*/summary.md"
        if compgen -G "${summary_file}" > /dev/null; then
            local latest_summary=$(ls -td ${platform_output}-*/summary.md | head -1)
            if [[ -f "${latest_summary}" ]]; then
                # Extract stats using grep
                local convs=$(grep "**Total Conversations:**" "${latest_summary}" | sed 's/.*: //')
                local msgs=$(grep "**Total Messages:**" "${latest_summary}" | sed 's/.*: //')
                local tokens=$(grep "**Estimated Tokens:**" "${latest_summary}" | sed 's/.*: //' | tr -d ',')
                
                RESULTS["${platform}_conversations"]=${convs:-0}
                RESULTS["${platform}_messages"]=${msgs:-0}
                RESULTS["${platform}_tokens"]=${tokens:-0}
                
                TOTAL_CONVERSATIONS=$((TOTAL_CONVERSATIONS + ${convs:-0}))
                TOTAL_MESSAGES=$((TOTAL_MESSAGES + ${msgs:-0}))
                TOTAL_TOKENS=$((TOTAL_TOKENS + ${tokens:-0}))
            fi
        fi
        
        return 0
    else
        echo "[FAILED] ${platform} extraction failed"
        FAILED_PLATFORMS+=("${platform}")
        return 1
    fi
}

# Run extractors sequentially (important for RAM usage)
PLATFORMS=("claude" "gemini" "copilot" "openai")

for platform in "${PLATFORMS[@]}"; do
    run_extractor "${platform}" || true
    echo ""
    echo "[INFO] Waiting 5 seconds before next platform..."
    sleep 5
done

# Generate aggregated index.md
echo ""
echo "----------------------------------------"
echo "Generating aggregated index..."
echo "----------------------------------------"

cat > "${AGGREGATED_DIR}/index.md" << EOF
# Chat History Export - Master Index

**Export Date:** ${DATE_HUMAN}  
**Platforms Attempted:** ${#PLATFORMS[@]}  
**Successful:** $((${#PLATFORMS[@]} - ${#FAILED_PLATFORMS[@]}))  
**Failed:** ${#FAILED_PLATFORMS[@]}

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total Conversations | ${TOTAL_CONVERSATIONS} |
| Total Messages | ${TOTAL_MESSAGES} |
| Estimated Tokens | ${TOTAL_TOKENS:,} |

## Platform Results

| Platform | Status | Conversations | Messages | Tokens |
|----------|--------|---------------|----------|--------|
EOF

for platform in "${PLATFORMS[@]}"; do
    status="✅ Success"
    if [[ " ${FAILED_PLATFORMS[@]} " =~ " ${platform} " ]]; then
        status="❌ Failed"
    fi
    
    convs=${RESULTS["${platform}_conversations"]:-N/A}
    msgs=${RESULTS["${platform}_messages"]:-N/A}
    tokens=${RESULTS["${platform}_tokens"]:-N/A}
    if [[ "${tokens}" != "N/A" && "${tokens}" != "0" ]]; then
        tokens=$(echo "${tokens}" | awk '{printf "%\047d", $0}')
    fi
    
    echo "| ${platform^} | ${status} | ${convs} | ${msgs} | ${tokens} |" >> "${AGGREGATED_DIR}/index.md"
done

cat >> "${AGGREGATED_DIR}/index.md" << EOF

## Output Structure

\`\`\`
${AGGREGATED_DIR}/
├── index.md                 # This file
├── claude-*/               # Claude.ai export
│   ├── conversations.jsonl
│   └── summary.md
├── gemini-*/               # Gemini export
│   ├── conversations.jsonl
│   └── summary.md
├── copilot-*/              # Copilot export
│   ├── conversations.jsonl
│   └── summary.md
└── openai-*/               # OpenAI ChatGPT export
    ├── conversations.jsonl
    └── summary.md
\`\`\`

## Data Format

Each platform's export contains:

### conversations.jsonl
- One JSON object per line (JSONL format)
- Each object represents one conversation
- Fields: id, title, messages, message_count, token_estimate, categories, extracted_at

### summary.md
- Human-readable summary
- Category breakdown
- Table of all conversations with stats

## Categories

Conversations are automatically tagged with lightweight categories:
- **Coding**: Programming, debugging, API questions
- **Research**: Learning, explanations, studies
- **Planning**: Tasks, projects, goals, strategies
- **Casual**: Creative, stories, casual chat
- **General**: Everything else

## Next Steps

1. Review individual platform summaries in their respective directories
2. Use JSONL files for programmatic analysis
3. Refer to this index for overall statistics

## Privacy & Security

⚠️ **IMPORTANT**: This data contains sensitive personal conversations.

- Store exports securely (encrypted storage recommended)
- Do not commit to version control
- Delete when no longer needed
- See documentation at: /opt/ai-orchestrator/docs/chat-extraction-guide.md

---

*Generated by extract-all-chats.sh on ${DATE_HUMAN}*
EOF

# Print final summary
echo ""
echo "========================================"
echo "  Extraction Complete!"
echo "========================================"
echo ""
echo "Total Conversations: ${TOTAL_CONVERSATIONS}"
echo "Total Messages: ${TOTAL_MESSAGES}"
echo "Estimated Tokens: ${TOTAL_TOKENS:,}"
echo ""
echo "Output Directory: ${AGGREGATED_DIR}"
echo "Index File: ${AGGREGATED_DIR}/index.md"
echo ""

if [[ ${#FAILED_PLATFORMS[@]} -gt 0 ]]; then
    echo "⚠️  Failed Platforms: ${FAILED_PLATFORMS[*]}"
    echo "   Check logs above for details"
fi

echo ""
echo "Done! ✅"
