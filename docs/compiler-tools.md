# Compiler Tools — Deterministic System Monitoring

**Philosophy:** Linux-standard first, apt > pip > custom  
**Goal:** System monitoring and tooling that doesn't burn tokens  
**Hardware Target:** t640 thin client, 8GB RAM, Debian 13  

---

## Principles

1. **No AI/LLM calls** — These tools are fully deterministic
2. **Standard Linux utilities** — Use jq, curl, systemd, procps, etc.
3. **Machine-parseable output** — JSON and TSV options for all tools
4. **GNU coding standards** --help, man-page style, FHS-compliant paths
5. **Shell-native first** — Bash preferred, Python only when necessary
6. **Inspectable** — No black boxes, all logic visible in source

---

## Audit of Existing Tools (`/opt/ai-orchestrator/bin/`)

| Tool | Shell-Native | AI-Free | Notes |
|------|-------------|---------|-------|
| `health-check` | ❌ Python | ❌ No | Imports lib.queue, lib.utils, calls API router |
| `orchestrator` | ❌ Python | ❌ No | Main daemon, routes to AI adapters |
| `qwen-health` | ✅ Bash | ✅ Yes | Pure curl-based liveness check |
| `qwen-code` | ✅ Bash | ❌ No | Wraps brain.ask() (AI call) |
| `qwen-task` | ✅ Bash | ❌ No | Routes to AI agents |
| `task-submit` | ❌ Python | ❌ No | Queue management with AI classifier |
| `setup-login` | ❌ Python | ✅ Yes | GUI login helper, no AI |
| `qwen-usage` | ✅ Bash | ✅ Yes | Log analysis, no AI |

**Already shell-native & AI-free:** `qwen-health`, `qwen-usage`, `setup-login`

---

## New Tool Specifications

### 1. `sys-health` — System Health Monitor

**Path:** `/opt/ai-orchestrator/bin/compiler-tools/sys-health`  
**FHS:** Logs to `/var/log/ai-orchestrator/sys-health.log`

```
NAME
    sys-health — System health snapshot (CPU, RAM, disk, network)

SYNOPSIS
    sys-health [OPTIONS]

DESCRIPTION
    Collects system metrics and outputs in human-readable or machine-
    parseable format. Suitable for cron jobs and monitoring dashboards.

OPTIONS
    -j, --json          Output as JSON (default: human-readable)
    -t, --tsv           Output as TSV (single line, for logging)
    -v, --verbose       Include additional details (temps, fans if available)
    -h, --help          Show this help message

OUTPUT FIELDS (JSON/TSV)
    timestamp      ISO 8601 UTC
    cpu_percent    Current CPU usage (0-100)
    cpu_cores      Number of logical cores
    load_1m        Load average (1 minute)
    load_5m        Load average (5 minutes)
    load_15m       Load average (15 minutes)
    ram_total_mb   Total RAM in MB
    ram_used_mb    Used RAM in MB
    ram_free_mb    Free RAM in MB
    ram_percent    RAM usage percentage
    disk_root_total_gb   Root filesystem total (GB)
    disk_root_used_gb    Root filesystem used (GB)
    disk_root_percent    Root filesystem usage (%)
    net_rx_bytes   Total bytes received (all interfaces)
    net_tx_bytes   Total bytes transmitted (all interfaces)
    uptime_seconds System uptime in seconds

EXIT CODES
    0  Success
    1  Error (unable to collect metrics)

EXAMPLES
    sys-health                     # Human-readable summary
    sys-health --json              # JSON output for APIs
    sys-health --tsv >> /var/log/sys-health.tsv  # Append to log

DEPENDENCIES
    Standard Debian: procps, coreutils, iproute2
```

---

### 2. `proc-watch` — Process Monitor

**Path:** `/opt/ai-orchestrator/bin/compiler-tools/proc-watch`  
**FHS:** Config in `/etc/ai-orchestrator/proc-watch.conf`

```
NAME
    proc-watch — Process monitoring and alerting

SYNOPSIS
    proc-watch [OPTIONS] [PATTERN...]

DESCRIPTION
    Monitors processes matching PATTERN (regex on command line or PID).
    Reports resource usage, can alert on thresholds.

OPTIONS
    -p, --pid PID       Monitor specific PID
    -n, --name PATTERN  Monitor processes matching PATTERN (regex)
    -j, --json          Output as JSON
    -t, --tsv           Output as TSV
    --top N             Show top N processes by CPU (default: all matches)
    --cpu-warn PCT      Warn if CPU > PCT%
    --mem-warn PCT      Warn if memory > PCT%
    --watch             Continuous mode (refresh every 2s)
    -h, --help          Show this help

OUTPUT FIELDS (per process)
    pid            Process ID
    ppid           Parent PID
    user           Owner username
    cpu_percent    CPU usage %
    mem_percent    Memory usage %
    mem_rss_mb     Resident set size (MB)
    state          Process state (R/S/D/Z/etc.)
    time_cpu       Cumulative CPU time
    command        Full command line

EXIT CODES
    0  Processes found, within thresholds
    1  No matching processes found
    2  Threshold exceeded (warning)

EXAMPLES
    proc-watch --name "chromium"              # Find Chromium processes
    proc-watch --pid 1234 --json              # Monitor PID 1234 as JSON
    proc-watch --name "python" --top 5        # Top 5 Python processes
    proc-watch --watch --name "node"          # Watch Node.js processes

CONFIGURATION (/etc/ai-orchestrator/proc-watch.conf)
    DEFAULT_CPU_WARN=80
    DEFAULT_MEM_WARN=80
    REFRESH_INTERVAL=2

DEPENDENCIES
    procps (ps, pgrep), coreutils
```

---

### 3. `log-scan` — Log Analysis Tool

**Path:** `/opt/ai-orchestrator/bin/compiler-tools/log-scan`

```
NAME
    log-scan — Grep/awk-based log analysis (no AI)

SYNOPSIS
    log-scan [OPTIONS] PATTERN [FILE...]

DESCRIPTION
    Searches log files for patterns, extracts structured data using
    grep/awk. Supports common log formats (syslog, journal, access logs).

OPTIONS
    -f, --file FILE     Search FILE (default: stdin or /var/log/syslog)
    -r, --recursive     Search all files in directory
    --since TIME        Show entries since TIME (e.g., "1 hour ago", "2026-02-19")
    --until TIME        Show entries until TIME
    -c, --count         Only show match counts
    -j, --json          Output as JSON array
    -t, --tsv           Output as TSV
    --format FORMAT     Parse format: syslog|journal|nginx|apache|custom
    --extract REGEX     Extract capturing groups from matches
    -i, --ignore-case   Case-insensitive search
    -v, --invert        Invert match (show non-matching lines)
    -h, --help          Show this help

PRESET PATTERNS (--preset NAME)
    errors          Match ERROR|ERR|CRITICAL|FAIL
    warnings        Match WARN|WARNING
    auth-fail       Match authentication failures
    oom             Match out-of-memory events
    disk-full       Match filesystem full errors
    segfault        Match segmentation faults
    http-5xx        Match HTTP 5xx status codes

OUTPUT MODES
    Default: Matching lines with context
    --json: Array of objects {timestamp, host, level, message}
    --tsv: Tab-separated: timestamp\thost\tlevel\tmessage

EXIT CODES
    0  Matches found
    1  No matches found
    2  Error (file not found, invalid regex, etc.)

EXAMPLES
    log-scan "error" /var/log/syslog
    log-scan --preset errors --since "2 hours ago"
    log-scan --format nginx --extract '"(GET|POST) ([^"]+)"' /var/log/nginx/access.log
    log-scan --pattern "CRITICAL" -r /var/log/myapp/ --json

DEPENDENCIES
    grep, awk, coreutils, find
```

---

### 4. `file-integrity` — File Integrity Checker

**Path:** `/opt/ai-orchestrator/bin/compiler-tools/file-integrity`

```
NAME
    file-integrity — File integrity verification using checksums

SYNOPSIS
    file-integrity [OPTIONS] COMMAND [PATH...]

DESCRIPTION
    Creates and verifies SHA-256 checksums for files and directories.
    Maintains a database of known-good states.

COMMANDS
    init PATH...      Initialize baseline for PATH(s)
    verify [PATH...]  Verify against baseline (default: all tracked)
    update PATH...    Update baseline for PATH(s)
    status            Show database status
    list              List all tracked files
    remove PATH...    Remove PATH(s) from tracking

OPTIONS
    -d, --database DB   Use database FILE (default: /var/lib/ai-orchestrator/integrity.db)
    -j, --json          Output as JSON
    -v, --verbose       Verbose output
    -q, --quiet         Suppress non-error output
    -h, --help          Show this help

DATABASE FORMAT
    SQLite database with tables:
    - files (path TEXT PRIMARY KEY, hash TEXT, mtime INT, size INT, recorded_at TEXT)
    - history (path TEXT, old_hash TEXT, new_hash TEXT, changed_at TEXT)

OUTPUT (verify)
    OK     File unchanged
    MODIFIED  Hash mismatch
    MISSING  File no longer exists
    NEW    File not in baseline

EXIT CODES
    0  All files verified OK
    1  One or more files modified/missing/new
    2  Database error or invalid arguments

EXAMPLES
    file-integrity init /opt/ai-orchestrator/bin/
    file-integrity verify                    # Check all tracked files
    file-integrity verify /opt/ai-orchestrator/bin/orchestrator
    file-integrity update /opt/ai-orchestrator/config.yml
    file-integrity status --json

DEPENDENCIES
    coreutils (sha256sum), sqlite3 or python3 (sqlite3 module)
```

---

### 5. `net-reach` — Network Reachability Tester

**Path:** `/opt/ai-orchestrator/bin/compiler-tools/net-reach`

```
NAME
    net-reach — Network reachability and latency testing

SYNOPSIS
    net-reach [OPTIONS] TARGET...

DESCRIPTION
    Tests connectivity to network targets via ICMP, TCP, or HTTP.
    Reports latency, packet loss, and service availability.

OPTIONS
    -p, --port PORT     Test TCP connectivity to PORT
    -u, --url URL       Test HTTP/HTTPS endpoint (implies --port 80/443)
    -m, --method METHOD HTTP method (GET|HEAD|POST, default: HEAD)
    -c, --count N       Number of probes (default: 3)
    -t, --timeout SEC   Timeout per probe (default: 5)
    -j, --json          Output as JSON
    -t, --tsv           Output as TSV
    --expect-code CODE  Expected HTTP status code (default: 200)
    --expect-body RE    Regex pattern expected in response body
    -h, --help          Show this help

PROBE TYPES
    ICMP ping         Default when no port/URL specified
    TCP connect       When --port specified
    HTTP request      When --url specified

OUTPUT FIELDS (per target)
    target         Hostname or URL
    type           Probe type (icmp|tcp|http)
    reachable      Boolean (true/false)
    latency_avg_ms Average latency (ms)
    latency_min_ms Minimum latency (ms)
    latency_max_ms Maximum latency (ms)
    packet_loss    Packet loss percentage (ICMP only)
    http_code      HTTP status code (HTTP probes only)
    error          Error message if failed

EXIT CODES
    0  All targets reachable
    1  One or more targets unreachable
    2  Invalid arguments or configuration error

EXAMPLES
    net-reach google.com                      # ICMP ping
    net-reach --port 22 ssh.example.com       # TCP port check
    net-reach --url https://api.example.com/health
    net-reach --url http://localhost:8080 --expect-code 200
    net-reach google.com cloudflare.com --json

CONFIGURATION (/etc/ai-orchestrator/net-reach.conf)
    DEFAULT_TIMEOUT=5
    DEFAULT_COUNT=3
    CRITICAL_TARGETS=google.com,cloudflare.com

DEPENDENCIES
    iputils-ping (ping), curl, coreutils
```

---

## Implementation Priority

**Phase 1 (Highest Priority):**
1. `sys-health` — Foundation for all monitoring
2. `proc-watch` — Critical for debugging resource issues
3. `net-reach` — Essential for service health checks

**Phase 2:**
4. `log-scan` — Useful but can be done with raw grep/awk
5. `file-integrity` — Important for security, less urgent

---

## Installed Tools

The following tools have been implemented and are ready for use:

### ✓ sys-health (v1.0.0)
**Path:** `/opt/ai-orchestrator/bin/compiler-tools/sys-health`  
**Status:** Implemented and tested

Features:
- CPU usage, cores, load averages
- Memory (total, used, free, percent)
- Disk usage (root filesystem)
- Network I/O (all interfaces)
- System uptime
- Output modes: human-readable, JSON, TSV

Example usage:
```bash
sys-health                           # Human-readable
sys-health --json | jq .ram_percent  # JSON parsing
sys-health --tsv >> health.log       # Append to log
```

### ✓ proc-watch (v1.0.0)
**Path:** `/opt/ai-orchestrator/bin/compiler-tools/proc-watch`  
**Status:** Implemented and tested

Features:
- Filter by PID or process name (regex)
- Top N processes by CPU
- Threshold warnings (CPU/MEM)
- Continuous watch mode
- Output modes: human-readable, JSON, TSV

Example usage:
```bash
proc-watch --name "python"              # Find Python processes
proc-watch --pid 1234 --json            # Monitor specific PID
proc-watch --name "node" --top 5        # Top 5 Node.js processes
proc-watch --watch --name "chromium"    # Watch mode
```

### ✓ net-reach (v1.0.0)
**Path:** `/opt/ai-orchestrator/bin/compiler-tools/net-reach`  
**Status:** Implemented and tested

Features:
- ICMP ping tests
- TCP port connectivity
- HTTP/HTTPS endpoint checks
- Latency statistics (avg/min/max)
- Packet loss calculation
- Expected status code validation
- Output modes: human-readable, JSON, TSV

Example usage:
```bash
net-reach google.com                         # ICMP ping
net-reach --port 22 ssh.example.com          # TCP check
net-reach --url https://api.example.com      # HTTP check
net-reach --json host1 host2 | jq '.[].reachable'
```

### ⏳ log-scan (planned)
**Status:** Specified, not yet implemented  
See specification above for details.

### ⏳ file-integrity (planned)
**Status:** Specified, not yet implemented  
See specification above for details.

---

## Integration Examples

### Cron Jobs

```bash
# Every 5 minutes: system health to log
*/5 * * * * /opt/ai-orchestrator/bin/compiler-tools/sys-health --tsv >> /var/log/ai-orchestrator/health.tsv

# Every hour: verify file integrity
0 * * * * /opt/ai-orchestrator/bin/compiler-tools/file-integrity verify --quiet || mail -s "Integrity Alert" admin@example.com

# Every minute: check critical services
* * * * * /opt/ai-orchestrator/bin/compiler-tools/net-reach --url https://dashscope-intl.aliyuncs.com/health --timeout 2 || systemctl restart ai-orchestrator
```

### Dashboard Integration

```bash
# Prometheus-style metrics endpoint
#!/bin/bash
echo "# HELP sys_cpu_percent Current CPU usage"
echo "# TYPE sys_cpu_percent gauge"
/opt/ai-orchestrator/bin/compiler-tools/sys-health --json | jq -r '.cpu_percent | "sys_cpu_percent " + .'
```

### Alerting Script

```bash
#!/bin/bash
HEALTH=$(/opt/ai-orchestrator/bin/compiler-tools/sys-health --json)
CPU=$(echo "$HEALTH" | jq -r '.cpu_percent')
RAM=$(echo "$HEALTH" | jq -r '.ram_percent')

if (( $(echo "$CPU > 90" | bc -l) )); then
    echo "ALERT: CPU at ${CPU}%" | logger -t sys-alert
fi

if (( $(echo "$RAM > 90" | bc -l) )); then
    echo "ALERT: RAM at ${RAM}%" | logger -t sys-alert
fi
```

---

## Maintenance

### Updating Tools

Tools follow semantic versioning. Check version with `--version` flag.

### Adding New Tools

1. Create script in `/opt/ai-orchestrator/bin/compiler-tools/`
2. Follow GNU standards (--help, exit codes, man-page style)
3. Support --json and --tsv output modes
4. Document in this file
5. Add to FHS-compliant paths

### Testing

All tools should be testable with:
```bash
./tool-name --help     # Should exit 0
./tool-name --json     # Should produce valid JSON
./tool-name --tsv      # Should produce parseable TSV
```
