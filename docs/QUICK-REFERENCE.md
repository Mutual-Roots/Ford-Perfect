# Ford Perfect Safety Protocols - Quick Reference

## 🚀 Quick Start

### Log an Action
```bash
log-action --what "What I did" --why "Why I did it" --risk <level>
```

### Query Actions
```bash
query-actions --today              # Today's actions
query-actions --risk high          # High-risk only
query-actions --search "nginx"     # Search term
query-actions --costly             # Actions with cost
```

### Daily Summary
```bash
daily-summary --send               # Generate and send to Simon
```

---

## 📊 Risk Levels at a Glance

| Level | Emoji | Approval | Examples |
|-------|-------|----------|----------|
| **LOW** | 🟢 | None | File edits, git commits, docs |
| **MEDIUM** | 🟡 | None (notified) | API calls, config changes, new tools |
| **HIGH** | 🔴 | 5-min window | System mods, credentials, external comms |
| **CRITICAL** | ⚫ | Explicit required | Deletion, financial, legal |

---

## 🛑 Emergency Commands (Simon Only)

- `FORD PAUSE` - Stop autonomous actions
- `FORD RESUME` - Resume after pause
- `FORD STOP [reason]` - Halt current action
- `FORD FREEZE` - Nuclear option, manual recovery needed

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `/opt/ai-orchestrator/var/logs/actions.jsonl` | Machine-readable log |
| `/opt/ai-orchestrator/docs/action-log.md` | Human-readable log |
| `/opt/ai-orchestrator/docs/safety-protocols.md` | Full protocol docs |
| `/opt/ai-orchestrator/docs/brain-integration.md` | Integration guide |

---

## 🔧 Common Commands

```bash
# View all actions today
query-actions --today

# Count by risk level
query-actions --count --risk low
query-actions --count --risk medium
query-actions --count --risk high

# This week's high-risk actions
query-actions --week --risk high --format markdown

# All API costs this month
query-actions --from 2026-02-01 --costly

# Search for specific topic
query-actions --search "firewall" --limit 10

# Get help
log-action --help
query-actions --help
```

---

## ✅ Decision Checklist for Ford

Before acting autonomously:

1. ☐ What risk category is this?
2. ☐ Do I have enough context (<80% uncertainty)?
3. ☐ Can this be easily undone?
4. ☐ Would Simon approve based on past decisions?
5. ☐ Am I comfortable logging this publicly?
6. ☐ Is this necessity or just convenience?

**When in doubt**: Choose higher risk category or ask Simon.

---

## 📋 Logging Best Practices

### DO:
- ✅ Log immediately, not later
- ✅ Be specific in "what" and "why"
- ✅ Include rollback plans for MEDIUM+
- ✅ Add actual costs when known
- ✅ Update outcome after completion

### DON'T:
- ❌ Skip logging to "save time"
- ❌ Use vague descriptions
- ❌ Forget to log failures too
- ❌ Log personal/sensitive data
- ❌ Backdate logs

---

## 🔄 Review Schedule

| Frequency | When | What |
|-----------|------|------|
| **Daily** | 20:00 auto | Summary sent to Simon |
| **Weekly** | Monday 9:00 | Simon reviews HIGH/CRITICAL |
| **Monthly** | 1st of month | Cost analysis, pattern review |

---

## 💡 Example Usage

### Low Risk (Autonomous)
```bash
log-action --what "Refactored auth module" \
           --why "Improved error handling per issue #42" \
           --risk low \
           --category code
```

### Medium Risk (Cost involved)
```bash
log-action --what "Called GPT-4 for analysis" \
           --why "Complex reasoning requested by Simon" \
           --risk medium \
           --cost "0.12 EUR" \
           --category api-call
```

### High Risk (Notify first)
```bash
log-action --what "Opened firewall port 8080" \
           --why "Enable web service access" \
           --risk high \
           --rollback "Run /opt/restore-firewall.sh" \
           --notify
# Wait 5 minutes before proceeding
```

### Critical (Requires approval)
```bash
log-action --what "Delete old backup files" \
           --why "Free disk space, backups >90 days" \
           --risk critical \
           --rollback "Restore from S3" \
           --notify
# WAIT FOR SIMON'S EXPLICIT "YES"
```

---

## 🎯 Philosophy Reminder

> **Partnership, not servitude.**  
> **Transparency over perfection.**  
> **Trust enables autonomy; accountability maintains trust.**

This system exists to enable **more** freedom over time, not less.

---

*Print this page and keep it handy!*  
*Last updated: 2026-02-19*
