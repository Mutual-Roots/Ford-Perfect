# Ford Perfect AI Orchestrator

*Critical-rationalist AI orchestration — no black boxes, no faith, only falsifiable interfaces.*

## Philosophy  
Ford Perfect is a Popper 2.0 agent: every model call is a conjecture; every response demands attempted refutation. We enforce *Wolfwolken-check*: correlation ≠ causation — all multi-model outputs are cross-validated for spurious alignment. *Wu Wei* means minimal intervention: the orchestrator routes, logs, and critiques — it does not hallucinate intent. “Mutual Roots” binds us to open standards, reproducible paths, and shared epistemic hygiene.

## Install (Debian 13, t640)  
```bash
sudo apt update && sudo apt install -y python3-pip systemd curl jq git
sudo mkdir -p /opt/ford-perfect/{bin,etc,log,cache}
sudo chown -R $USER:$USER /opt/ford-perfect
git clone https://github.com/ford-perfect/orchestrator.git /opt/ford-perfect/src
pip3 install --break-system-packages -r /opt/ford-perfect/src/requirements.txt
sudo cp /opt/ford-perfect/src/ford-perfect.service /etc/systemd/system/
sudo systemctl daemon-reload
```

**Why `/opt`?** FHS §4.5: `/opt` hosts add-on application software — self-contained, relocatable, non-interfering with distro packages. `/usr/local` is for *locally compiled* software (FHS §4.9); this is a managed deployment.

## Usage  
```bash
# Start service (logs to /opt/ford-perfect/log/)
sudo systemctl enable --now ford-perfect.service

# Query (curl or web client)
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Explain quantum decoherence, then falsify one assumption"}'

# CLI help (man-page style)
/opt/ford-perfect/bin/ford-perfect --help
```

## Architecture  
- **Core**: Python 3.13 async runtime (`/opt/ford-perfect/src/orchestrator.py`)  
- **API Brain**: Qwen-Plus via `https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation` (Singapore endpoint — verified geo-IP & TLS pin)  
- **Free Compute**: Claude Max (Anthropic), Gemini Advanced (Google), Copilot (Microsoft), ChatGPT (OpenAI) — all routed via authenticated HTTPS proxy layer; *no API keys stored in config* (use `systemd` env files)  
- **Logging**: Structured JSON to `/opt/ford-perfect/log/` (rotated daily)  
- **Service**: `systemd`, standard `Type=simple`, `Restart=on-failure`, `ProtectSystem=strict`

## Contributing  
- PRs must include `test_falsification.py` verifying at least one spurious-correlation edge case  
- All paths hardcoded in code → use `pathlib.Path("/opt/ford-perfect")`  
- No `pip install` in `postinst`; deps declared in `requirements.txt` and installed via `apt` where possible  
- Man-page stub at `/opt/ford-perfect/man/ford-perfect.1` (build with `groff -man`)  

> “A theory that explains everything explains nothing.” — K. Popper, *Conjectures and Refutations*  
> `git push origin main` — ready.