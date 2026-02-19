#!/bin/bash
#
# Daily Cost Report Generator
# Generates HTML dashboard, commits to git, and sends alerts if needed
#
# Usage: daily-cost-report.sh [--no-commit] [--no-push]
#

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="/opt/ai-orchestrator"
REPORTS_DIR="${BASE_DIR}/var/reports"
LOG_FILE="${BASE_DIR}/var/logs/cost-report.log"
DATE=$(date -u +%Y%m%d)
DATE_HUMAN=$(date -u +"%Y-%m-%d %H:%M UTC")
REPORT_FILE="${REPORTS_DIR}/cost-dashboard-${DATE}.html"

# Parse arguments
NO_COMMIT=false
NO_PUSH=false

for arg in "$@"; do
    case $arg in
        --no-commit)
            NO_COMMIT=true
            shift
            ;;
        --no-push)
            NO_PUSH=true
            shift
            ;;
    esac
done

# Logging function
log() {
    echo "[$(date -u '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handling
error_exit() {
    log "ERROR: $*"
    exit 1
}

log "Starting daily cost report generation"

# Ensure reports directory exists
mkdir -p "$REPORTS_DIR"

# Generate HTML dashboard
log "Generating HTML dashboard for ${DATE_HUMAN}"
if ! "${BASE_DIR}/bin/qwen-usage-dashboard" --period today --output "$REPORT_FILE" --quiet 2>&1 | tee -a "$LOG_FILE"; then
    error_exit "Failed to generate dashboard"
fi

if [ ! -f "$REPORT_FILE" ]; then
    error_exit "Report file not created: ${REPORT_FILE}"
fi

REPORT_SIZE=$(stat -c%s "$REPORT_FILE" 2>/dev/null || stat -f%z "$REPORT_FILE" 2>/dev/null || echo "unknown")
log "Dashboard generated: ${REPORT_FILE} (${REPORT_SIZE} bytes)"

# Get budget status for alert check
log "Checking budget status"
BUDGET_OUTPUT=$("${BASE_DIR}/bin/qwen-cost" --budget --quiet 2>&1) || true
BUDGET_USED=$(echo "$BUDGET_OUTPUT" | cut -f3)
BUDGET_ALERT=$(echo "$BUDGET_OUTPUT" | cut -f4)

log "Budget status: ${BUDGET_USED}% used, alert level: ${BUDGET_ALERT}"

# Send alert if needed
if [ "$BUDGET_ALERT" = "critical" ]; then
    log "🛑 CRITICAL BUDGET ALERT - ${BUDGET_USED}% used!"
    # TODO: Add Telegram/email notification here
    # Example: send_telegram_message "🛑 Qwen Budget Critical: ${BUDGET_USED}% used"
elif [ "$BUDGET_ALERT" = "warn" ]; then
    log "⚠️  WARNING - ${BUDGET_USED}% of budget used"
    # TODO: Add Telegram/email notification here
fi

# Git commit (if enabled and in git repo)
if [ "$NO_COMMIT" = false ] && [ -d "${BASE_DIR}/.git" ]; then
    log "Committing report to git"
    cd "$BASE_DIR"
    
    # Configure git user if not set
    git config user.email "cost-monitor@localhost" >/dev/null 2>&1 || true
    git config user.name "Cost Monitor" >/dev/null 2>&1 || true
    
    # Add and commit
    if git add "var/reports/cost-dashboard-${DATE}.html" 2>&1 | tee -a "$LOG_FILE"; then
        if ! git diff --cached --quiet 2>/dev/null; then
            git commit -m "Daily cost report: ${DATE}" 2>&1 | tee -a "$LOG_FILE"
            
            if [ "$NO_PUSH" = false ]; then
                log "Pushing to remote"
                git push 2>&1 | tee -a "$LOG_FILE" || log "Warning: Git push failed"
            fi
        else
            log "No changes to commit"
        fi
    else
        log "Warning: Failed to add file to git"
    fi
else
    log "Git commit skipped (--no-commit or not a git repo)"
fi

# Cleanup old reports (keep last 30 days)
log "Cleaning up old reports (keeping last 30 days)"
find "$REPORTS_DIR" -name "cost-dashboard-*.html" -type f -mtime +30 -delete 2>/dev/null || true

log "Daily cost report completed successfully"

# Print summary
echo ""
echo "=========================================="
echo "Daily Cost Report Summary"
echo "=========================================="
echo "Date: ${DATE_HUMAN}"
echo "Report: ${REPORT_FILE}"
echo "Size: ${REPORT_SIZE} bytes"
echo "Budget Used: ${BUDGET_USED}%"
echo "Alert Level: ${BUDGET_ALERT}"
echo "=========================================="

exit 0
