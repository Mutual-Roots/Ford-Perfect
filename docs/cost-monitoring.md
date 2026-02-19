# Cost Monitoring & Usage Tracking for Qwen Models

Comprehensive cost tracking and monitoring dashboard for all Qwen models on DashScope-Intl (Alibaba Cloud).

## Overview

This system provides **zero-token-cost monitoring** by pulling data directly from local logs and APIs. No LLM calls are made for monitoring itself.

### Key Features

- ✅ **Real-time visibility** into tokens used, costs, and remaining credit
- ✅ **Per-model breakdown** for all Qwen variants
- ✅ **Budget alerts** at 50% and 80% thresholds
- ✅ **Cost projections** based on usage trends
- ✅ **HTML dashboards** with interactive charts
- ✅ **CLI tools** for quick checks and automation
- ✅ **JSON/CSV export** for further analysis

## Budget Context

- **Welcome Credit**: 70M tokens (one-time)
- **Test Budget**: 1M tokens (initial testing phase)
- **Alert Thresholds**:
  - ⚠️ Warning: 50% of test budget (500k tokens)
  - 🛑 Critical: 80% of test budget (800k tokens)

## Tools

### 1. `qwen-cost` — Quick Cost Check CLI

Man-page style CLI for quick usage and cost checks.

#### Usage

```bash
qwen-cost [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--today` | Show today's usage (default) |
| `--yesterday` | Show yesterday's usage |
| `--week` | Show current week's usage |
| `--month` | Show current month's usage |
| `--all` | Show all-time usage |
| `--model NAME` | Filter by model name (partial match) |
| `--json` | Output as JSON |
| `--csv` | Output as CSV |
| `--budget` | Show budget and credit status |
| `--project` | Show cost projections |
| `-q, --quiet` | Minimal output (just numbers) |
| `-h, --help` | Show help message |

#### Examples

```bash
# Today's summary
qwen-cost

# Week usage as JSON
qwen-cost --week --json

# Budget status
qwen-cost --budget

# Filter by specific model
qwen-cost --model qwen-max

# Cost projections
qwen-cost --project

# CSV export for spreadsheet
qwen-cost --month --csv > monthly_usage.csv
```

#### Sample Output

```
======================================================================
DashScope-Intl Qwen Usage Report
======================================================================
Period: today (2026-02-19 to 2026-02-19)
----------------------------------------------------------------------
Metric                                                          Value
----------------------------------------------------------------------
Total Tokens:                                                   9,186
  Input Tokens:                                                 4,122
  Output Tokens:                                                5,064
Total Cost (USD):              $                            0.007726
Total API Calls:                                                   31

======================================================================
Breakdown by Model:
======================================================================
Model                                     Tokens     Cost (USD)    Calls
----------------------------------------------------------------------
qwen-coder-plus                            4,236 $    0.003400       10
qwen-max-latest                            1,517 $    0.001552        3
qwen-plus-latest                           1,046 $    0.000970        4
...
```

#### Exit Codes

- `0` — Success / OK
- `1` — Warning threshold reached (50%)
- `2` — Critical threshold reached (80%)

---

### 2. `qwen-usage-dashboard` — HTML Dashboard Generator

Generates comprehensive HTML reports with interactive charts.

#### Usage

```bash
qwen-usage-dashboard [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--period PERIOD` | Time period: today, week, month, all (default: week) |
| `--output PATH` | Output file path |
| `--open` | Open in browser after generation |
| `-q, --quiet` | Suppress messages |

#### Examples

```bash
# Generate weekly report
qwen-usage-dashboard

# Monthly report with custom output
qwen-usage-dashboard --period month --output /tmp/monthly.html

# Open immediately in browser
qwen-usage-dashboard --open
```

#### Output Location

Reports are saved to:
```
/opt/ai-orchestrator/var/reports/cost-dashboard-{YYYYMMDD}.html
```

#### Dashboard Features

- 📊 **Summary Statistics**: Total tokens, costs, API calls
- 💰 **Cost Analysis**: Daily average, monthly projections
- 🎯 **Budget Status**: Visual progress bars for test budget and welcome credit
- 📈 **Daily Trends**: Interactive line chart showing tokens and costs over time
- 🔷 **Model Distribution**: Doughnut chart of token usage by model
- 💵 **Cost by Model**: Bar chart of costs per model
- 📋 **Detailed Table**: Complete breakdown with percentages
- 🔮 **Projections**: Days until budget exhaustion

---

### 3. `tokenmeter` — Unified Multi-Provider Dashboard

Consolidates usage across all AI providers (Qwen, Anthropic, OpenRouter, etc.).

#### Usage

```bash
tokenmeter [OPTIONS]
```

#### Options

| Option | Description |
|--------|-------------|
| `--today` | Today's usage (default) |
| `--week` | Current week |
| `--month` | Current month |
| `--all` | All-time |
| `--provider NAME` | Filter by provider (qwen, anthropic, openrouter) |
| `--json` | Output as JSON |
| `--csv` | Output as CSV |
| `--dashboard` | Generate HTML dashboard |
| `-q, --quiet` | Minimal output |

#### Examples

```bash
# All providers summary
tokenmeter

# Qwen only
tokenmeter --provider qwen

# Export all data as JSON
tokenmeter --week --json > weekly_usage.json
```

---

### 4. Python Module — `lib/dashscope_monitor.py`

Reusable Python module for programmatic access.

#### Installation

No installation needed. Already in `/opt/ai-orchestrator/lib/`.

#### Usage

```python
from lib.dashscope_monitor import DashScopeMonitor

# Initialize
monitor = DashScopeMonitor()

# Get usage statistics
usage = monitor.get_usage(period='week')
print(f"Total tokens: {usage.total_tokens}")
print(f"Total cost: ${usage.total_cost_usd:.6f}")

# Get budget status
budget = monitor.get_remaining_credit()
print(f"Test budget used: {budget.test_budget_pct}%")
print(f"Alert level: {budget.alert_level}")

# Get projections
projection = monitor.project_monthly()
print(f"Days until exhausted: {projection['days_until_welcome_credit_exhausted']}")

# Export data
json_data = monitor.export_json(period='month')
csv_data = monitor.export_csv(period='month', output_path='/tmp/monthly.csv')
```

#### Available Functions

| Function | Description |
|----------|-------------|
| `get_usage(period, model_filter)` | Get usage statistics for period |
| `get_cost(period)` | Get total cost for period |
| `get_remaining_credit()` | Get budget and credit status |
| `project_monthly()` | Get cost and usage projections |
| `export_json(period, output_path)` | Export as JSON |
| `export_csv(period, output_path)` | Export as CSV |
| `clear_cache()` | Clear cached results |

#### Period Options

- `'today'` — Current day (UTC)
- `'yesterday'` — Previous day
- `'week'` — Current week (Monday-Sunday)
- `'month'` — Current month
- `'all'` — All-time

---

## Data Sources

### Primary: Local Logs

All usage data is pulled from:
```
/opt/ai-orchestrator/var/logs/qwen-usage.tsv
```

Format (TSV):
```
timestamp	model	provider	input_tokens	output_tokens	cost_usd
2026-02-19T12:30:17Z	qwen-plus-latest	qwen-singapore	74	2	0.000032
```

**Advantages:**
- Zero API token cost
- Instant access
- No rate limits
- Historical data available

### Secondary: SQLite Database

Cost records are also stored in:
```
/opt/ai-orchestrator/var/api_costs.db
```

Used for integration with existing `CostMonitor` class.

---

## Automated Daily Reports

### Cron Job Setup

To generate daily reports at 23:00 UTC:

```bash
# Edit crontab
crontab -e

# Add daily report job
0 23 * * * /opt/ai-orchestrator/bin/qwen-usage-dashboard --period today --quiet

# Add weekly report every Monday at 23:30
30 23 * * 1 /opt/ai-orchestrator/bin/qwen-usage-dashboard --period week --quiet
```

### Git Auto-Commit (Optional)

To auto-commit reports to git:

```bash
#!/bin/bash
# /opt/ai-orchestrator/scripts/daily-cost-report.sh

DATE=$(date -u +%Y%m%d)
REPORT="/opt/ai-orchestrator/var/reports/cost-dashboard-${DATE}.html"

# Generate report
/opt/ai-orchestrator/bin/qwen-usage-dashboard --period today --quiet

# Commit to git
cd /opt/ai-orchestrator
git add var/reports/cost-dashboard-${DATE}.html
git commit -m "Daily cost report: ${DATE}"
git push
```

---

## Budget Alerts

### Alert Levels

| Level | Threshold | Action |
|-------|-----------|--------|
| ✅ OK | < 50% | Normal operation |
| ⚠️ Warning | ≥ 50% | Log warning, consider reducing usage |
| 🛑 Critical | ≥ 80% | Immediate attention required |

### Telegram Notifications (Optional)

To send alerts to Telegram when costs exceed threshold:

```python
# Add to daily report script
if budget.alert_level != 'ok':
    # Send Telegram message
    message = f"🚨 Qwen Budget Alert\n\nLevel: {budget.alert_level.upper()}\nUsed: {budget.test_budget_pct:.1f}%\nRemaining: {budget.test_budget_remaining:,} tokens"
    
    # Use message tool or telegram-cli
    subprocess.run(['telegram-cli', '-W', '-S', message])
```

### Exit Code Integration

The `qwen-cost --budget` command returns exit codes that can trigger alerts:

```bash
#!/bin/bash
/opt/ai-orchestrator/bin/qwen-cost --budget --quiet
EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
    echo "CRITICAL: Budget alert!" | mail -s "Qwen Budget Critical" admin@example.com
elif [ $EXIT_CODE -eq 1 ]; then
    echo "WARNING: Budget warning" | mail -s "Qwen Budget Warning" admin@example.com
fi
```

---

## Troubleshooting

### No Usage Data Found

**Problem**: Tools report "No usage data found"

**Solution**:
1. Check if log file exists:
   ```bash
   ls -la /opt/ai-orchestrator/var/logs/qwen-usage.tsv
   ```
2. Verify API calls are being logged by the orchestrator
3. Check permissions:
   ```bash
   chmod 644 /opt/ai-orchestrator/var/logs/qwen-usage.tsv
   ```

### Incorrect Cost Calculations

**Problem**: Costs don't match Alicloud console

**Solution**:
1. Verify pricing in `lib/dashscope_monitor.py`:
   ```python
   MODEL_PRICING = {
       'qwen-max': {'input': 0.40, 'output': 1.20},
       # ... check all models
   }
   ```
2. Compare against official pricing: https://dashscope-intl.aliyuncs.com/pricing
3. Update pricing if changed

### API Rate Limits

**Problem**: Hitting rate limits when using API directly

**Solution**:
- Use local logs instead (default behavior)
- Increase cache TTL in `DashScopeMonitor`:
  ```python
  self.cache_ttl = 600  # 10 minutes instead of 5
  ```
- Implement exponential backoff for API calls

### Missing Models in Breakdown

**Problem**: Some models not showing in reports

**Solution**:
1. Add missing models to `MODEL_PRICING` dict in `lib/dashscope_monitor.py`
2. Check log file for model name spelling
3. Verify model is being used (check timestamps)

### HTML Dashboard Not Rendering

**Problem**: Charts not displaying in HTML report

**Solution**:
1. Ensure internet connection (Chart.js loads from CDN)
2. Check browser console for errors
3. Verify file permissions:
   ```bash
   chmod 644 /opt/ai-orchestrator/var/reports/*.html
   ```

### Cache Issues

**Problem**: Stale data showing in reports

**Solution**:
```python
monitor = DashScopeMonitor()
monitor.clear_cache()  # Clear cache
usage = monitor.get_usage('today')  # Fresh data
```

---

## Performance Optimization

### Caching

Results are cached for 5 minutes by default. Adjust in code:

```python
monitor = DashScopeMonitor()
monitor.cache_ttl = 600  # 10 minutes
```

### Batch Operations

For multiple queries, load data once:

```python
monitor = DashScopeMonitor()

# Load once
usage_today = monitor.get_usage('today')
usage_week = monitor.get_usage('week')
usage_month = monitor.get_usage('month')

# All use cached log data
```

### Minimal Output Mode

Use `--quiet` flag for scripts:

```bash
# Just numbers, no formatting
qwen-cost --today --quiet
# Output: 9186	0.007726	31
```

---

## Integration Examples

### Health Check Script

```bash
#!/bin/bash
# /opt/ai-orchestrator/bin/cost-health-check

echo "=== Cost Health Check ==="
echo ""

# Quick stats
/opt/ai-orchestrator/bin/qwen-cost --today

echo ""
echo "=== Budget Status ==="
/opt/ai-orchestrator/bin/qwen-cost --budget

# Exit with alert code
/opt/ai-orchestrator/bin/qwen-cost --budget --quiet
exit $?
```

### Daily Summary Email

```python
#!/usr/bin/env python3
# /opt/ai-orchestrator/scripts/daily-cost-email.py

import smtplib
from lib.dashscope_monitor import DashScopeMonitor

monitor = DashScopeMonitor()
usage = monitor.get_usage('today')
budget = monitor.get_remaining_credit()

subject = f"Daily Qwen Cost Report - {usage.end_date}"
body = f"""
Daily Usage Summary
===================
Date: {usage.end_date}
Total Tokens: {usage.total_tokens:,}
Total Cost: ${usage.total_cost_usd:.6f}
API Calls: {usage.calls_count}

Budget Status
=============
Test Budget: {budget.test_budget_pct:.1f}% used
Remaining: {budget.test_budget_remaining:,} tokens
Alert Level: {budget.alert_level.upper()}

Top Models
==========
"""

for model, stats in sorted(usage.by_model.items(), key=lambda x: x[1]['cost_usd'], reverse=True)[:5]:
    body += f"{model}: ${stats['cost_usd']:.6f} ({stats['total_tokens']:,} tokens)\n"

# Send email (configure SMTP settings)
# ...
```

### Slack/Discord Webhook

```bash
#!/bin/bash
# Post to Slack channel

WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

BUDGET=$(/opt/ai-orchestrator/bin/qwen-cost --budget --quiet)
USED=$(echo $BUDGET | cut -f1)
REMAINING=$(echo $BUDGET | cut -f2)
PCT=$(echo $BUDGET | cut -f3)

PAYLOAD=$(cat <<EOF
{
    "text": "📊 Qwen Cost Update",
    "attachments": [{
        "color": "$(if [ $(echo "$PCT > 80" | bc) -eq 1 ]; then echo danger; elif [ $(echo "$PCT > 50" | bc) -eq 1 ]; then echo warning; else echo good; fi)",
        "fields": [
            {"title": "Used", "value": "$USED tokens", "short": true},
            {"title": "Remaining", "value": "$REMAINING tokens", "short": true},
            {"title": "Percentage", "value": "$PCT%", "short": true}
        ]
    }]
}
EOF
)

curl -X POST -H 'Content-type: application/json' --data "$PAYLOAD" "$WEBHOOK_URL"
```

---

## Model Pricing Reference

Current pricing (USD per 1M tokens):

| Model | Input | Output | Tier |
|-------|-------|--------|------|
| qwen-max | $0.40 | $1.20 | Premium |
| qwen3.5-plus | $0.08 | $0.20 | Balanced |
| qwen-plus | $0.08 | $0.20 | Balanced |
| qwen-coder-plus | $0.08 | $0.20 | Balanced |
| qwen-turbo | $0.02 | $0.06 | Fast |
| qwen-flash | $0.01 | $0.03 | Fast |
| qwq-plus | $0.14 | $0.56 | Premium (Reasoning) |
| qwen3-coder | $0.25 | $1.00 | Premium (Code) |
| qwen3-vl-max | $0.20 | $0.60 | Vision |
| qwen3-vl-plus | $0.10 | $0.30 | Vision |

**Note**: Prices subject to change. Verify at https://dashscope-intl.aliyuncs.com/pricing

---

## Best Practices

1. **Monitor Daily**: Check usage at least once daily during testing
2. **Set Alerts**: Configure notifications at 50% and 80% thresholds
3. **Review Weekly**: Analyze weekly trends to optimize model selection
4. **Cache Results**: Use caching to avoid repeated log parsing
5. **Export Regularly**: Keep historical exports for trend analysis
6. **Verify Accuracy**: Cross-check with Alicloud console monthly
7. **Automate Reports**: Schedule daily/weekly HTML reports
8. **Track Projections**: Monitor projected exhaustion dates

---

## Support & Resources

- **Alicloud Console**: https://dashscope-intl.aliyuncs.com/console/usage
- **API Documentation**: https://dashscope-intl.aliyuncs.com/docs
- **Pricing**: https://dashscope-intl.aliyuncs.com/pricing
- **Internal Docs**: `/opt/ai-orchestrator/docs/`
- **Logs**: `/opt/ai-orchestrator/var/logs/`

---

## Changelog

### 2026-02-19 — Initial Release
- ✅ `qwen-cost` CLI tool
- ✅ `qwen-usage-dashboard` HTML generator
- ✅ `lib/dashscope_monitor.py` Python module
- ✅ `tokenmeter` unified dashboard
- ✅ Budget alerts (50%, 80%)
- ✅ Cost projections
- ✅ JSON/CSV export
- ✅ Comprehensive documentation
