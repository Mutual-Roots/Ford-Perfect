"""
Ford Perfect Brain — Primary: Qwen-Plus (Singapore), Fallback: Sonnet
"""
import os, json, time, urllib.request, urllib.error

DASHSCOPE_KEY = os.environ.get("DASHSCOPE_INTL_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

QWEN_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
ANTHROPIC_BASE = "https://api.anthropic.com/v1/messages"

FORD_SYSTEM = """You are Ford Perfect, a critical-rationalist AI agent.
Primary coding and analysis brain. Be concise. No apologies.
Popper protocol: seek falsifiers. Wolfwolken-check on correlations.
Stack: Python 3.13, bash, Linux, t640 workstation."""

def ask_qwen(messages, model="qwen-plus-latest", max_tokens=2000, system=None):
    """Primary brain: Qwen-Plus via Singapore endpoint."""
    if system:
        messages = [{"role": "system", "content": system}] + messages
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens
    }).encode()
    req = urllib.request.Request(
        QWEN_BASE, data=payload,
        headers={"Authorization": f"Bearer {DASHSCOPE_KEY}",
                 "Content-Type": "application/json"}
    )
    r = urllib.request.urlopen(req, timeout=30)
    d = json.loads(r.read())
    return {
        "text": d["choices"][0]["message"]["content"],
        "model": d.get("model", model),
        "usage": d.get("usage", {}),
        "provider": "qwen-singapore"
    }

def ask_anthropic(messages, max_tokens=500, system=None):
    """Emergency only — real model name: claude-sonnet-4-5. NEVER use in normal flow."""
    payload = json.dumps({
        "model": "claude-sonnet-4-5",
        "max_tokens": max_tokens,
        "system": system or FORD_SYSTEM,
        "messages": messages
    }).encode()
    req = urllib.request.Request(
        ANTHROPIC_BASE, data=payload,
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    )
    r = urllib.request.urlopen(req, timeout=30)
    d = json.loads(r.read())
    return {
        "text": d["content"][0]["text"],
        "model": "claude-sonnet-4-5",
        "usage": d.get("usage", {}),
        "provider": "anthropic"
    }

def ask(messages, model="qwen-plus-latest", max_tokens=2000, system=None, fallback=True):
    """
    Primary:  qwen-plus-latest (Singapore, ~€0)
    Fallback: qwen-max         (still Qwen, no API cost spike)
    Emergency only: ask_anthropic() — call explicitly, never auto-fallback
    """
    try:
        t0 = time.time()
        result = ask_qwen(messages, model=model, max_tokens=max_tokens, system=system or FORD_SYSTEM)
        result["latency_ms"] = int((time.time()-t0)*1000)
        result["fallback_used"] = False
        return result
    except Exception as e:
        if not fallback:
            raise
        print(f"[brain] qwen-plus failed ({e}), trying qwen-max")
        t0 = time.time()
        result = ask_qwen(messages, model="qwen-max", max_tokens=max_tokens, system=system or FORD_SYSTEM)
        result["latency_ms"] = int((time.time()-t0)*1000)
        result["fallback_used"] = True
        result["primary_error"] = str(e)
        return result

if __name__ == "__main__":
    # Quick self-test
    r = ask([{"role": "user", "content": "Say BRAIN_READY and your model name."}], max_tokens=30)
    print(f"Brain: {r['text']}")
    print(f"Model: {r['model']} | Provider: {r['provider']} | {r['latency_ms']}ms | Fallback: {r['fallback_used']}")
    print(f"Usage: {r['usage']}")
