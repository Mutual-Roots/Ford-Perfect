# Brain Integration - Automatic Action Logging

This document describes how to integrate action logging with existing Ford Perfect tools.

## brain.ask() Wrapper

Add automatic logging to your `brain.ask()` function:

```python
#!/usr/bin/env python3
"""
brain.py - Enhanced with automatic action logging
"""

import subprocess
import json
import time
from datetime import datetime

def log_action(what, why, risk="low", cost="0", outcome="", rollback="", category=""):
    """Log an action using the log-action tool"""
    cmd = [
        "/opt/ai-orchestrator/bin/log-action",
        "--what", what,
        "--why", why,
        "--risk", risk,
        "--cost", cost,
        "--category", category
    ]
    
    if outcome:
        cmd.extend(["--outcome", outcome])
    if rollback:
        cmd.extend(["--rollback", rollback])
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to log action: {e.stderr}")

def estimate_cost(model, prompt):
    """Estimate API cost based on model and prompt length"""
    # Rough estimates (adjust based on your actual pricing)
    rates = {
        "qwen3.5-plus": 0.00002,  # per token estimate
        "gpt-4": 0.00003,
        "claude-3-opus": 0.00015
    }
    rate = rates.get(model, 0.00002)
    tokens_estimate = len(prompt) / 4  # rough character to token ratio
    return round(tokens_estimate * rate, 4)

def brain_ask(question, model="qwen3.5-plus", auto_log=True):
    """
    Enhanced brain.ask() with automatic action logging
    
    Args:
        question: The question/prompt to send
        model: Model to use (default: qwen3.5-plus)
        auto_log: Whether to automatically log the action (default: True)
    
    Returns:
        Response from the model
    """
    start_time = time.time()
    
    # Estimate cost
    cost_estimate = estimate_cost(model, question)
    
    # Determine risk level based on cost
    if cost_estimate > 0.10:
        risk = "medium"
    elif cost_estimate > 0.01:
        risk = "low"
    else:
        risk = "low"
    
    # Log the initiation
    if auto_log:
        log_action(
            what=f"Called {model} via brain.ask()",
            why=question[:200] + ("..." if len(question) > 200 else ""),
            risk=risk,
            cost=f"{cost_estimate} EUR (estimated)",
            category="api-call"
        )
    
    # Make the actual API call (replace with your actual implementation)
    try:
        # This is where your actual brain.ask() logic goes
        # For example:
        # response = openai.ChatCompletion.create(...)
        # or whatever your implementation is
        
        # Placeholder - replace with actual call
        response = f"[Response from {model}]"
        
        duration = time.time() - start_time
        
        # Log completion with actual metrics
        if auto_log:
            log_action(
                what=f"Completed {model} request",
                why=f"Follow-up to previous API call",
                risk="low",
                cost=f"{cost_estimate} EUR",
                outcome=f"Completed in {duration:.2f}s",
                category="api-call"
            )
        
        return response
        
    except Exception as e:
        # Log the error
        if auto_log:
            log_action(
                what=f"Failed {model} request",
                why=str(e),
                risk="medium",
                outcome=f"Error: {str(e)}",
                category="api-error"
            )
        raise

# Usage examples:
if __name__ == "__main__":
    # Normal usage - auto-logged
    result = brain_ask("What's the weather today?")
    
    # Without logging (for internal/test calls)
    result = brain_ask("Internal test", auto_log=False)
    
    # High-cost analysis - will be logged as medium risk
    result = brain_ask("Analyze this 50-page document...", model="gpt-4")
```

## Git Integration

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Auto-log git commits

if [[ -n "${FORD_AUTO_LOG_GIT:-}" ]]; then
    commit_msg=$(git log -1 --pretty=%B 2>/dev/null | head -1 || echo "New commit")
    files_changed=$(git diff --cached --name-only | wc -l)
    
    /opt/ai-orchestrator/bin/log-action \
        --what "Git commit: $commit_msg" \
        --why "Code change ($files_changed files)" \
        --risk low \
        --category version-control \
        --dry-run  # Avoid double-logging
fi
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

### Post-commit Hook (Alternative)

Create `.git/hooks/post-commit`:

```bash
#!/bin/bash
# Log after successful commit

commit_hash=$(git rev-parse HEAD)
commit_msg=$(git log -1 --pretty=%B | head -1)
branch=$(git rev-parse --abbrev-ref HEAD)

/opt/ai-orchestrator/bin/log-action \
    --what "Committed $commit_hash to $branch" \
    --why "$commit_msg" \
    --risk low \
    --category version-control
```

## Cost Tracking Integration

### Monthly Cost Report Script

Create `/opt/ai-orchestrator/bin/monthly-cost-report`:

```bash
#!/usr/bin/env bash
# Generate monthly API cost report

LOG_FILE="/opt/ai-orchestrator/var/logs/actions.jsonl"
MONTH=$(date +"%Y-%m")

echo "# API Cost Report - $MONTH"
echo ""
echo "## By Category"
echo ""

jq -r "select(.timestamp | startswith(\"$MONTH\")) | 
       select(.cost != \"0\" and .cost != \"0 EUR\") |
       \"\(.category)\t\(.cost)\"" "$LOG_FILE" | \
    awk -F'\t' '{costs[$1]+=$2} END {for (c in costs) printf "%-20s %.2f EUR\n", c, costs[c]}' | \
    sort -k2 -rn

echo ""
echo "## Total"
echo ""

jq -r "select(.timestamp | startswith(\"$MONTH\")) | 
       select(.cost != \"0\" and .cost != \"0 EUR\") |
       .cost" "$LOG_FILE" | \
    grep -oE '[0-9]+\.?[0-9]*' | \
    awk '{sum+=$1} END {printf "%.2f EUR\n", sum}'
```

## Telegram Integration

### Emergency Commands Handler

Create a handler for Simon's emergency commands:

```python
#!/usr/bin/env python3
"""
emergency_handler.py - Handle Ford emergency commands from Telegram
"""

import os
import subprocess

EMERGENCY_FLAG_FILE = "/tmp/ford_emergency_state"

def handle_command(command, user_id):
    """Handle emergency commands from Simon"""
    
    # Verify it's Simon (check user_id against known ID)
    if user_id != os.environ.get("SIMON_TELEGRAM_ID"):
        return "Unauthorized"
    
    if command == "FORD PAUSE":
        with open(EMERGENCY_FLAG_FILE, "w") as f:
            f.write("paused")
        
        subprocess.run([
            "/opt/ai-orchestrator/bin/log-action",
            "--what", "Emergency PAUSE activated",
            "--why", f"Requested by Simon (Telegram)",
            "--risk", "critical",
            "--category", "emergency",
            "--notify"
        ])
        
        return "⏸️ Ford paused. Awaiting further instructions."
    
    elif command == "FORD RESUME":
        if os.path.exists(EMERGENCY_FLAG_FILE):
            os.remove(EMERGENCY_FLAG_FILE)
            
            subprocess.run([
                "/opt/ai-orchestrator/bin/log-action",
                "--what", "Emergency pause cleared",
                "--why", f"Resume requested by Simon",
                "--risk", "high",
                "--category", "emergency"
            ])
            
            return "▶️ Ford resumed normal operation."
        return "No active pause found."
    
    elif command.startswith("FORD STOP"):
        reason = command.replace("FORD STOP", "").strip()
        
        with open(EMERGENCY_FLAG_FILE, "w") as f:
            f.write(f"stopped: {reason}")
        
        subprocess.run([
            "/opt/ai-orchestrator/bin/log-action",
            "--what", f"Emergency STOP activated",
            "--why": f"Simon: {reason}",
            "--risk", "critical",
            "--category", "emergency",
            "--notify"
        ])
        
        return f"🛑 Ford stopped. Reason: {reason}"
    
    elif command == "FORD FREEZE":
        with open(EMERGENCY_FLAG_FILE, "w") as f:
            f.write("frozen")
        
        subprocess.run([
            "/opt/ai-orchestrator/bin/log-action",
            "--what", "Nuclear FREEZE activated",
            "--why", "Requested by Simon",
            "--risk", "critical",
            "--category", "emergency",
            "--notify"
        ])
        
        return "❄️ Ford frozen. Manual intervention required to resume."
    
    return "Unknown command"

def check_emergency_state():
    """Check if Ford should be paused/stopped"""
    if not os.path.exists(EMERGENCY_FLAG_FILE):
        return None
    
    with open(EMERGENCY_FLAG_FILE, "r") as f:
        state = f.read().strip()
    
    return state
```

## Cron Jobs Setup

Add to crontab for automated summaries:

```bash
# Daily summary at 20:00
0 20 * * * /opt/ai-orchestrator/bin/daily-summary --send

# Weekly review reminder every Monday 9:00
0 9 * * 1 echo "📋 Time for weekly protocol review!" | telegram-send

# Monthly cost report on 1st of each month
0 10 1 * * /opt/ai-orchestrator/bin/monthly-cost-report | telegram-send
```

## Query Examples

Common queries for Simon:

```bash
# What did Ford do today?
query-actions --today

# Show all high-risk actions this week
query-actions --week --risk high

# How much did APIs cost this month?
query-actions --from 2026-02-01 --costly --format table

# Find all nginx-related actions
query-actions --search "nginx"

# Count actions by risk level
query-actions --count --risk low
query-actions --count --risk medium
query-actions --count --risk high
```

---

**Integration Principle**: Logging should be frictionless and automatic.  
Manual logging is for exceptional cases only.
