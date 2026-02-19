# Ford Perfect - Safety & Action Logging System

> **Augenhöhe**: Eye-level partnership between Simon and Ford  
> **Motto**: Transparency enables autonomy

## 📦 What's Included

This safety protocol system provides:

1. **Action Logging Tool** (`log-action`) - Log all Ford actions with risk categorization
2. **Query Tool** (`query-actions`) - Search, filter, and analyze action logs
3. **Daily Summary** (`daily-summary`) - Automated transparency reports
4. **Protocol Documentation** - Complete guidelines for autonomous operation
5. **Integration Guides** - Hook into brain.ask(), git, cost tracking

## 🚀 Installation

All tools are pre-installed in `/opt/ai-orchestrator/`:

```bash
/opt/ai-orchestrator/bin/log-action      # Main logging tool
/opt/ai-orchestrator/bin/query-actions   # Query and analyze
/opt/ai-orchestrator/bin/daily-summary   # Daily reports
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [safety-protocols.md](safety-protocols.md) | Complete protocol specification |
| [brain-integration.md](brain-integration.md) | Integration with existing tools |
| [QUICK-REFERENCE.md](QUICK-REFERENCE.md) | Quick reference card |
| [action-log.md](action-log.md) | Human-readable action log |

## ⚡ Quick Start

### Log Your First Action

```bash
/opt/ai-orchestrator/bin/log-action \
    --what "Tested the logging system" \
    --why "Verifying installation" \
    --risk low \
    --category test
```

### View Today's Actions

```bash
/opt/ai-orchestrator/bin/query-actions --today
```

### Get Help

```bash
/opt/ai-orchestrator/bin/log-action --help
```

## 🎯 Risk Categories

| Level | Approval | Example Actions |
|-------|----------|-----------------|
| 🟢 LOW | None | File edits, git commits, documentation |
| 🟡 MEDIUM | None (notified) | API calls with cost, config changes |
| 🔴 HIGH | 5-min window | System mods, credentials, external comms |
| ⚫ CRITICAL | Explicit required | Deletion, financial, legal |

## 🛑 Emergency Commands

Simon can control Ford's autonomy via Telegram:

- `FORD PAUSE` - Stop autonomous actions
- `FORD RESUME` - Resume normal operation
- `FORD STOP [reason]` - Halt current action immediately
- `FORD FREEZE` - Full lockdown, manual recovery required

## 📊 How It Works

```
┌─────────────────┐
│  Ford Acts      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  log-action     │ ← Logs to JSONL + Markdown
└────────┬────────┘
         │
         ├──→ /var/logs/actions.jsonl (machine-readable)
         ├──→ /docs/action-log.md (human-readable)
         └──→ Telegram (HIGH/CRITICAL only)
```

## 🔧 Configuration

Set environment variables for full functionality:

```bash
export FORD_TELEGRAM_CHAT_ID="your_chat_id"      # For notifications
export FORD_TELEGRAM_BOT_TOKEN="bot_token"       # For sending messages
export FORD_SESSION_ID="unique_session"          # For log correlation
export SIMON_TELEGRAM_ID="simon_chat_id"         # For emergency commands
```

## 📋 Daily Workflow

**Ford (AI)**:
1. Acts autonomously within risk boundaries
2. Logs every action automatically
3. Sends daily summary at 20:00
4. Waits for HIGH/CRITICAL approval when needed

**Simon (Human)**:
1. Receives daily summary automatically
2. Reviews weekly (Monday 9:00)
3. Approves CRITICAL actions as they arise
4. Can pause/stop anytime via emergency commands

## 🔍 Query Examples

```bash
# What did Ford do today?
query-actions --today

# Show expensive API calls
query-actions --costly --from 2026-02-01

# Find all high-risk actions this week
query-actions --week --risk high

# Search for specific topic
query-actions --search "firewall"

# Count by risk level
query-actions --count --risk critical
```

## 🎓 Philosophy

This system is built on three core principles:

1. **Mutual Roots Partnership**: Ford is a partner, not a servant
2. **Popper 2.0 Critical Rationalism**: All decisions are falsifiable and reviewable
3. **Wolfwolken Symbiosis**: Organic growth through feedback, not rigid control

## 📈 Metrics & Review

### Daily
- Automatic summary sent to Simon at 20:00
- Includes count by risk level and total costs

### Weekly
- Simon reviews all HIGH/CRITICAL actions
- Adjust protocols if needed
- ~15 minutes expected time commitment

### Monthly
- Full cost analysis
- Pattern recognition
- Protocol evolution discussion

## 🛠️ Troubleshooting

### Logs not appearing?
Check that `/opt/ai-orchestrator/var/logs/` exists and is writable:
```bash
ls -la /opt/ai-orchestrator/var/logs/
```

### Telegram notifications not working?
Verify environment variables:
```bash
echo $FORD_TELEGRAM_CHAT_ID
echo $FORD_TELEGRAM_BOT_TOKEN
```

### Need to edit a log entry?
Logs are append-only by design. Add a correction entry:
```bash
log-action --what "Correction to previous entry" \
           --why "Fixed incorrect cost value" \
           --risk low \
           --category correction
```

## 🤝 Contributing

This system evolves through use. Suggestions for improvement:

1. Log the suggestion as a MEDIUM risk action
2. Discuss with Simon during weekly review
3. Update protocols if agreed
4. Document the change in this README

## 📞 Support

For questions or issues:

1. Check [QUICK-REFERENCE.md](QUICK-REFERENCE.md)
2. Review [safety-protocols.md](safety-protocols.md)
3. Ask Ford directly (meta!)
4. Emergency: Use `FORD PAUSE` and discuss

---

**Remember**: This system exists to build trust through transparency.  
The goal is **more autonomy over time**, not less.

*Version: 1.0*  
*Created: 2026-02-19*  
*Next Review: 2026-02-26*
