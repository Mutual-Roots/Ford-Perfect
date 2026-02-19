# Ford Perfect AI Orchestrator

Critical-rationalist AI orchestration — Popper 2.0 epistemology, cost-efficient multi-model routing.

## Architecture

**Primary Brain:** `qwen3.5-plus` via DashScope International (Singapore)  
**Fallback:** `claude-sonnet-4-6` (emergency only, explicit calls)  
**Free Tier:** Web adapters (Claude.ai, Gemini, Copilot, OpenAI) via shared Chromium profile

### Cost Discipline
- Qwen: ~$0.0007/1k input, $0.0028/1k output — use for all heavy work
- Sonnet: $15/1M output — coordination only, €10/month cap
- Web adapters: $0 (subscription-based) — autonomous orchestrator runs these without Sonnet in the loop

### Path Layout (FHS Compliant)
```
/opt/ai-orchestrator/     # Main installation
├── bin/                  # CLI tools (qwen-code, qwen-task, health-check)
├── lib/                  # Python modules (brain.py, adapters, router)
├── etc/                  # Config (credentials.enc, providers.yaml, rules.yaml)
├── var/                  # Runtime data (logs, chromium-profile, cache)
└── skills/               # Agent headers (coding, research, philosophy)
```

Why `/opt`? FHS §4.5: add-on application software, self-contained, non-interfering with distro packages.

## Install (Debian 13, t640)

```bash
# System deps
sudo apt update && sudo apt install -y python3-pip python3-selenium chromium-driver systemd curl jq git

# Clone repo
cd /opt
git clone git@github.com:USERNAME/ford-perfect.git ai-orchestrator
chown -R $USER:$USER /opt/ai-orchestrator

# Install Python deps
pip3 install --break-system-packages dashscope openai requests pycryptodome

# Setup credentials (encrypt your API keys)
echo "YOUR_DASHSCOPE_KEY" | ./bin/cred-enc --provider dashscope-intl

# Enable systemd service
sudo cp ford-perfect.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable ford-perfect && sudo systemctl start ford-perfect
```

## CLI Tools

### qwen-code
Coding agent using Qwen-Coder-Plus with coding header (assertions, type safety, Linux-standard).

```bash
qwen-code "write a bash one-liner to count lines in a file"
qwen-code -o script.py "write a python function to reverse a string"
qwen-code -m qwen3.5-plus-2026-02-15 -t 4096 "refactor this module"
```

### qwen-task
Task router with type-specific headers (coding/research/philosophy).

```bash
qwen-task --type coding "implement binary search"
qwen-task --type research "summarize latest LLM papers"
qwen-task --type philosophy "analyze Popper falsification in AI context"
```

### health-check
Endpoint reachability + latency monitoring.

```bash
./bin/health-check
# Tests: OpenRouter, DashScope-Intl, Anthropic, OpenAI
```

## Providers

| Provider | Endpoint | Latency | Models | Cost |
|----------|----------|---------|--------|------|
| OpenRouter | openrouter.ai | ~140ms | 128+ Qwen/DeepSeek/Gemma | Free tier available |
| DashScope-Intl | dashscope-intl.aliyuncs.com | ~660ms | qwen3.5-plus, qwen-max, qwen-coder | ~$0.001/call |
| Anthropic | api.anthropic.com | ~200ms | claude-sonnet-4-6, claude-haiku-4-6 | $15/1M output |

**Never use DashScope mainland** — always `dashscope-intl` (Singapore).

## Web Adapters

Headless browser automation for subscription-based free access:

- **Claude.ai**: Shared Chromium profile, 21 cookies saved
- **Gemini**: Google One Advanced subscription
- **Copilot**: GitHub Copilot subscription
- **OpenAI**: ChatGPT Plus subscription

All share `/opt/ai-orchestrator/var/chromium-profile` with `--password-store=basic`.

## Testing

```bash
# Test brain.py
python3 lib/brain.py --test

# Test web adapter
python3 lib/adapters.py --adapter claude --test

# Run full health check
./bin/health-check --verbose
```

## License

MIT License — see LICENSE file.

## Mutual Roots

This project is part of Mutual Roots — open standards, reproducible paths, shared epistemic hygiene. No black boxes, no faith, only falsifiable interfaces.
