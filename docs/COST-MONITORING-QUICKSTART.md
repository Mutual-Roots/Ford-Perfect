# Cost Monitoring - Quick Start Guide

## 🚀 30-Second Setup

Everything is already installed! Just run:

```bash
# Check current usage
qwen-cost

# See budget status
qwen-cost --budget

# Generate HTML dashboard
qwen-usage-dashboard --open
```

## 📋 Common Commands

### Daily Checks

```bash
# Today's usage
qwen-cost

# Budget status (with alerts)
qwen-cost --budget

# Quick one-liner for scripts
qwen-cost --quiet
# Output: tokens	cost	calls
```

### Weekly/Monthly Reports

```bash
# Week summary
qwen-cost --week

# Month summary as JSON
qwen-cost --month --json

# Generate HTML report
qwen-usage-dashboard --period week
```

### Projections

```bash
# When will budget run out?
qwen-cost --project
```

### All Providers

```bash
# Unified view (Qwen + others)
tokenmeter

# Filter by provider
tokenmeter --provider qwen
```

## 🎯 What Each Tool Does

| Tool | Purpose | Best For |
|------|---------|----------|
| `qwen-cost` | Quick CLI stats | Daily checks, scripts |
| `qwen-usage-dashboard` | HTML reports | Visual analysis, presentations |
| `tokenmeter` | Multi-provider view | Comparing providers |
| Python module | Programmatic access | Custom integrations |

## 📊 Sample Workflow

### Morning Check (2 minutes)

```bash
# 1. Quick overview
qwen-cost

# 2. Budget check
qwen-cost --budget

# 3. If concerned, see projections
qwen-cost --project
```

### Weekly Review (5 minutes)

```bash
# 1. Generate weekly dashboard
qwen-usage-dashboard --period week --open

# 2. Export data for analysis
qwen-cost --week --csv > weekly.csv

# 3. Check trends
qwen-cost --week --json | jq '.by_model'
```

### Monthly Report (10 minutes)

```bash
# 1. Full month dashboard
qwen-usage-dashboard --period month --output monthly-report.html

# 2. Compare with previous month
qwen-cost --month --json > this_month.json
# (compare with last month's export)

# 3. Update projections
qwen-cost --project
```

## ⚠️ Alert Thresholds

| Level | Test Budget | Action |
|-------|-------------|--------|
| ✅ OK | < 50% (< 500k tokens) | Normal operation |
| ⚠️ Warning | ≥ 50% (≥ 500k tokens) | Review usage patterns |
| 🛑 Critical | ≥ 80% (≥ 800k tokens) | Immediate action needed |

**Current Status**: Check anytime with `qwen-cost --budget`

## 🔧 Automation

### Already Configured

- ✅ Daily reports at 23:00 UTC
- ✅ Weekly summaries on Mondays
- ✅ Budget checks every 6 hours
- ✅ Auto-commit to git

### Add Telegram Alerts (Optional)

Edit `/opt/ai-orchestrator/scripts/daily-cost-report.sh`:

```bash
# Add after line "Send alert if needed"
if [ "$BUDGET_ALERT" = "critical" ]; then
    # Send to your Telegram channel
    curl -X POST "https://api.telegram.org/botTOKEN/sendMessage" \
         -d chat_id=CHANNEL_ID \
         -d text="🛑 Qwen Budget Critical: ${BUDGET_USED}% used!"
fi
```

## 📁 File Locations

| File | Purpose |
|------|---------|
| `/opt/ai-orchestrator/var/logs/qwen-usage.tsv` | Raw usage logs |
| `/opt/ai-orchestrator/var/reports/` | HTML dashboards |
| `/opt/ai-orchestrator/var/api_costs.db` | SQLite database |
| `/opt/ai-orchestrator/docs/cost-monitoring.md` | Full documentation |

## 💡 Pro Tips

1. **Use `--quiet` for scripts** - Minimal output, easy to parse
2. **Cache is automatic** - Results cached for 5 minutes
3. **Export to JSON** - Easy integration with other tools
4. **Check exit codes** - `qwen-cost --budget` returns 1/2 on alerts
5. **HTML works offline** - Once generated, dashboards work without internet

## 🆘 Troubleshooting

### No Data Showing?

```bash
# Check if log file exists
ls -la /opt/ai-orchestrator/var/logs/qwen-usage.tsv

# Check permissions
chmod 644 /opt/ai-orchestrator/var/logs/qwen-usage.tsv
```

### Wrong Costs?

Update pricing in `/opt/ai-orchestrator/lib/dashscope_monitor.py`:

```python
MODEL_PRICING = {
    'qwen-max': {'input': 0.40, 'output': 1.20},
    # ... update as needed
}
```

### Need Fresh Data?

```python
from lib.dashscope_monitor import DashScopeMonitor
monitor = DashScopeMonitor()
monitor.clear_cache()  # Clear cache
```

## 📞 More Help

- Full docs: `/opt/ai-orchestrator/docs/cost-monitoring.md`
- Python API: See `lib/dashscope_monitor.py` docstrings
- Alicloud console: https://dashscope-intl.aliyuncs.com/console/usage

---

**Remember**: Monitoring itself costs ZERO tokens - all data comes from local logs! 🎉
