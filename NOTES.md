# Ford Perfect Orchestrator — Notes

## 2026-02-19: qwen-code + qwen-task agents

### brain.py: _log_usage forward-reference bug

**Issue:** `_log_usage` is defined *after* the `if __name__ == "__main__"` block in
`lib/brain.py`. When run as `python3 lib/brain.py`, the `__main__` block executes before
`_log_usage` is defined, causing:
```
NameError: name '_log_usage' is not defined
```
This triggers the fallback to `qwen-max` (still Qwen, not Anthropic — cost-safe).

**Impact:** Minor. brain still works via qwen-max fallback. Usage logging in the main block
self-test is skipped. `brain_cli.py` imports brain as a module (not `__main__`), so
`_log_usage` is defined before `ask()` is ever called there — no issue for qwen-code/qwen-task.

**Fix (one-liner):** Move the `_log_usage` function and its `import datetime` to the top of
brain.py (before `ask()`). Low priority since it only affects the self-test.

---

### New scripts

| Script | Path | Description |
|--------|------|-------------|
| qwen-code | bin/qwen-code | Coding agent → qwen-coder-plus |
| qwen-task | bin/qwen-task | Task router → coding/research/philosophy |
| brain_cli.py | lib/brain_cli.py | Subprocess bridge for brain.ask() |

**Log file:** `var/logs/tasks.log` (TSV: timestamp, type, model, input_tokens,
output_tokens, cost_usd, latency_ms)

**Test result (2026-02-19):**
```
$ qwen-code "write a bash one-liner to count lines in a file"
`wc -l < filename`
```
✓ qwen-coder-plus responded correctly in ~1s.
