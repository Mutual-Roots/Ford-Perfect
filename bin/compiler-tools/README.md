# Compiler Tools — Deterministic System Monitoring

**Version:** 1.0.0  
**Philosophy:** Linux-standard first, no AI/LLM calls  
**Target:** Ford Perfect t640 thin client (Debian 13, 8GB RAM)

---

## Quick Start

All tools support `--help` for detailed usage:

```bash
./sys-health --help
./proc-watch --help
./net-reach --help
```

---

## Available Tools

### sys-health
System health snapshot (CPU, RAM, disk, network, uptime)

```bash
# Human-readable report
./sys-health

# JSON output for APIs/dashboards
./sys-health --json | jq .

# TSV for logging
./sys-health --tsv >> /var/log/health.tsv
```

### proc-watch
Process monitoring with filtering and alerts

```bash
# Find all Python processes
./proc-watch --name "python"

# Monitor specific PID
./proc-watch --pid 1234 --json

# Top 5 CPU consumers matching pattern
./proc-watch --name "node" --top 5

# Watch mode (refreshes every 2s)
./proc-watch --watch --name "chromium"

# Alert if CPU > 80%
./proc-watch --name "myapp" --cpu-warn 80
```

### net-reach
Network reachability and latency testing

```bash
# ICMP ping
./net-reach google.com cloudflare.com

# TCP port check
./net-reach --port 22 ssh.example.com

# HTTP endpoint check
./net-reach --url https://api.example.com/health

# JSON output
./net-reach --json host1 host2 | jq '.[] | select(.reachable == false)'
```

---

## Output Modes

All tools support three output modes:

1. **Human-readable** (default) — Formatted for terminal display
2. **JSON** (`--json`) — Machine-parseable, ideal for APIs
3. **TSV** (`--tsv`) — Tab-separated, ideal for logs/spreadsheets

---

## Integration Examples

### Cron Jobs

```bash
# Every 5 minutes: log system health
*/5 * * * * /opt/ai-orchestrator/bin/compiler-tools/sys-health --tsv >> /var/log/health.tsv

# Every hour: check critical services
0 * * * * /opt/ai-orchestrator/bin/compiler-tools/net-reach --url https://dashscope-intl.aliyuncs.com --quiet || systemctl restart ai-orchestrator

# Continuous process monitoring (in screen/tmux)
while true; do /opt/ai-orchestrator/bin/compiler-tools/proc-watch --name "orchestrator" --cpu-warn 90; sleep 10; done
```

### Dashboard Integration

```bash
# Prometheus-style metrics
#!/bin/bash
echo "# HELP sys_cpu_percent Current CPU usage"
echo "# TYPE sys_cpu_percent gauge"
/opt/ai-orchestrator/bin/compiler-tools/sys-health --json | jq -r '.cpu_percent | "sys_cpu_percent " + .'
```

### Alerting Script

```bash
#!/bin/bash
HEALTH=$(/opt/ai-orchestrator/bin/compiler-tools/sys-health --json)
RAM=$(echo "$HEALTH" | jq -r '.ram_percent')

if (( $(echo "$RAM > 90" | bc -l) )); then
    echo "ALERT: RAM at ${RAM}%" | logger -t sys-alert
    # Send notification, restart services, etc.
fi
```

---

## Testing

Run the smoke test suite:

```bash
./test-compiler-tools.sh
```

Expected output:
```
Results: 14 passed, 0 failed
```

---

## Design Principles

1. **No AI/LLM calls** — Fully deterministic, inspectable code
2. **Standard Linux utilities** — Uses procps, coreutils, curl, etc.
3. **Machine-parseable** — JSON/TSV output for automation
4. **GNU standards** — `--help`, proper exit codes, man-page style
5. **Shell-native** — Bash preferred, minimal dependencies
6. **FHS-compliant** — Proper paths for logs, configs, data

---

## Dependencies

All tools use standard Debian 13 packages:

- `bash` (≥4.0)
- `coreutils` (date, df, etc.)
- `procps` (ps, uptime, etc.)
- `iproute2` (network stats)
- `curl` (HTTP tests in net-reach)
- `iputils-ping` (ICMP tests in net-reach)
- `jq` (optional, for JSON parsing)

Install missing dependencies:

```bash
sudo apt install bash coreutils procps iproute2 curl iputils-ping jq
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Warning / Partial failure |
| 2 | Error / Invalid arguments |

---

## File Locations

| Path | Purpose |
|------|---------|
| `/opt/ai-orchestrator/bin/compiler-tools/` | Tool binaries |
| `/opt/ai-orchestrator/docs/compiler-tools.md` | Full documentation |
| `/var/log/ai-orchestrator/` | Log files (when daemonized) |
| `/etc/ai-orchestrator/` | Configuration files (planned) |

---

## Contributing

When adding new tools:

1. Follow GNU coding standards
2. Support `--help`, `--json`, `--tsv`
3. Use proper exit codes
4. Add to this README
5. Update `test-compiler-tools.sh`
6. Document in `/opt/ai-orchestrator/docs/compiler-tools.md`

---

## License

Part of Ford Perfect AI Orchestrator project.
