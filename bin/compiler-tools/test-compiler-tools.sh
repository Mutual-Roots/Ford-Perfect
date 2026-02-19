#!/usr/bin/env bash
# test-compiler-tools.sh — Basic smoke tests for compiler-tools
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

passed=0
failed=0

test_tool() {
    local name="$1"
    local cmd="$2"
    
    printf "Testing %-20s ... " "$name"
    
    if eval "$cmd" >/dev/null 2>&1; then
        printf "${GREEN}PASS${NC}\n"
        ((passed++)) || true
        return 0
    else
        printf "${RED}FAIL${NC}\n"
        ((failed++)) || true
        return 1
    fi
}

echo "╔════════════════════════════════════════════════════╗"
echo "║     Compiler Tools — Smoke Test Suite              ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# sys-health tests
echo "=== sys-health ==="
test_tool "sys-health --help" "$SCRIPT_DIR/sys-health --help"
test_tool "sys-health (human)" "$SCRIPT_DIR/sys-health"
test_tool "sys-health --json" "timeout 5 $SCRIPT_DIR/sys-health --json"
test_tool "sys-health --tsv" "timeout 5 $SCRIPT_DIR/sys-health --tsv"
test_tool "sys-health --version" "$SCRIPT_DIR/sys-health --version"
echo ""

# proc-watch tests
echo "=== proc-watch ==="
test_tool "proc-watch --help" "$SCRIPT_DIR/proc-watch --help"
test_tool "proc-watch --name bash" "$SCRIPT_DIR/proc-watch --name 'bash'"
test_tool "proc-watch --json" "$SCRIPT_DIR/proc-watch --name 'bash' --top 2 --json"
test_tool "proc-watch --tsv" "$SCRIPT_DIR/proc-watch --name 'bash' --top 2 --tsv"
test_tool "proc-watch --version" "$SCRIPT_DIR/proc-watch --version"
echo ""

# net-reach tests
echo "=== net-reach ==="
test_tool "net-reach --help" "$SCRIPT_DIR/net-reach --help"
test_tool "net-reach localhost" "timeout 15 $SCRIPT_DIR/net-reach --count 1 localhost"
test_tool "net-reach --json" "timeout 15 $SCRIPT_DIR/net-reach --count 1 --json localhost"
test_tool "net-reach --version" "$SCRIPT_DIR/net-reach --version"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════╗"
printf "║  Results: ${GREEN}%d passed${NC}, ${RED}%d failed${NC}                          ║\n" "$passed" "$failed"
echo "╚════════════════════════════════════════════════════╝"

if [[ $failed -gt 0 ]]; then
    exit 1
fi
exit 0
