"""
Ford Perfect Brain — Primary: Qwen-Plus (Singapore), Fallback: Sonnet
Includes vision capabilities via Qwen-VL models (OCR, image analysis)
"""
import os, json, time, base64, urllib.request, urllib.error
from pathlib import Path
from typing import Union, Optional, Dict, Any

DASHSCOPE_KEY = os.environ.get("DASHSCOPE_INTL_API_KEY", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

QWEN_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
ANTHROPIC_BASE = "https://api.anthropic.com/v1/messages"

# Vision models
VL_BASE = QWEN_BASE  # Same endpoint, different models
DEFAULT_VL_MODEL = "qwen3-vl-flash"

FORD_SYSTEM = """You are Ford Perfect, a critical-rationalist AI agent.
Primary coding and analysis brain. Be concise. No apologies.
Popper protocol: seek falsifiers. Wolfwolken-check on correlations.
Stack: Python 3.13, bash, Linux, t640 workstation."""

VL_SYSTEM = """You are Ford Perfect's vision module. Analyze images accurately.
For OCR: Extract ALL text verbatim, preserve formatting.
For screenshots: Identify UI elements, text, layout.
Be precise, no fluff."""

def ask_qwen(messages, model="qwen-plus-latest", max_tokens=2000, system=None):
    """Primary brain: Qwen-Plus via Singapore endpoint."""
    # Ensure messages is a list
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]
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

def _encode_image_to_base64(image_path: Union[str, Path]) -> str:
    """Encode local image to base64 data URL."""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    ext = path.suffix.lower()
    mime_map = {
        '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.webp': 'image/webp', '.gif': 'image/gif', '.bmp': 'image/bmp',
    }
    mime_type = mime_map.get(ext, 'image/png')
    
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode('utf-8')
    
    return f"data:{mime_type};base64,{data}"


def _prepare_vl_content(image_input: Union[str, Path]) -> Dict[str, Any]:
    """Prepare image content for VL API request."""
    if isinstance(image_input, Path):
        image_input = str(image_input)
    
    # Already a data URL
    if image_input.startswith("data:image/"):
        return {"type": "image_url", "image_url": {"url": image_input}}
    
    # Public URL
    if image_input.startswith(("http://", "https://")):
        return {"type": "image_url", "image_url": {"url": image_input}}
    
    # Local file → convert to base64
    if Path(image_input).exists():
        data_url = _encode_image_to_base64(image_input)
        return {"type": "image_url", "image_url": {"url": data_url}}
    
    raise ValueError(f"Invalid image input: {image_input[:100]}")


def ask_with_image(
    image: Union[str, Path],
    prompt: str = "What's in this image?",
    model: str = DEFAULT_VL_MODEL,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
    fallback: bool = True,
) -> Dict[str, Any]:
    """
    Analyze an image with Qwen-VL model.
    
    Args:
        image: Image path, URL, or base64 data URL
        prompt: Question/instruction about the image
        model: Qwen-VL model (default: qwen3-vl-flash)
        system_prompt: Optional system prompt override
        max_tokens: Maximum output tokens
        fallback: Try qwen-vl-plus if flash fails
    
    Returns:
        Dict with text, model, usage, latency_ms, provider
    """
    if not DASHSCOPE_KEY:
        raise EnvironmentError("DASHSCOPE_INTL_API_KEY not set")
    
    # Prepare multimodal message
    image_content = _prepare_vl_content(image)
    messages = [
        {
            "role": "user",
            "content": [
                image_content,
                {"type": "text", "text": prompt}
            ]
        }
    ]
    
    # Add system prompt
    sys_prompt = system_prompt or VL_SYSTEM
    
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": sys_prompt}] + messages,
        "max_tokens": max_tokens
    }).encode()
    
    req = urllib.request.Request(
        VL_BASE, data=payload,
        headers={"Authorization": f"Bearer {DASHSCOPE_KEY}",
                 "Content-Type": "application/json"}
    )
    
    t0 = time.time()
    try:
        r = urllib.request.urlopen(req, timeout=60)
        d = json.loads(r.read())
        
        result = {
            "text": d["choices"][0]["message"]["content"],
            "model": d.get("model", model),
            "usage": d.get("usage", {}),
            "provider": "qwen-vl-singapore",
            "latency_ms": int((time.time()-t0)*1000),
            "fallback_used": False,
        }
        _log_vision_usage(result)
        return result
        
    except Exception as e:
        if not fallback or model == "qwen3-vl-plus-2025-12-19":
            raise
        print(f"[brain.vision] {model} failed ({e}), trying qwen3-vl-plus")
        return ask_with_image(
            image, prompt=prompt, model="qwen3-vl-plus-2025-12-19",
            system_prompt=system_prompt, max_tokens=max_tokens, fallback=False
        )


def ocr_image(
    image: Union[str, Path],
    language: str = "auto",
    model: str = DEFAULT_VL_MODEL,
) -> str:
    """Extract text from image (OCR)."""
    lang_instr = f"Language: {language}. " if language != "auto" else ""
    prompt = (
        f"{lang_instr}Extract ALL text verbatim. Preserve line breaks and formatting. "
        f"Output ONLY the extracted text, no commentary."
    )
    result = ask_with_image(image, prompt=prompt, model=model, max_tokens=4000)
    return result["text"]


def describe_image(
    image: Union[str, Path],
    detail: str = "brief",
    model: str = DEFAULT_VL_MODEL,
) -> str:
    """Generate image description."""
    if detail == "brief":
        prompt = "Describe this image briefly in 1-2 sentences."
    else:
        prompt = (
            "Provide detailed description: main subjects, colors, layout, "
            "any text visible, context, notable details."
        )
    result = ask_with_image(image, prompt=prompt, model=model)
    return result["text"]


def analyze_screenshot(
    image: Union[str, Path],
    focus: Optional[str] = None,
) -> Dict[str, str]:
    """Analyze UI screenshot for elements, text, layout."""
    focus_instr = f"Focus on: {focus}. " if focus else ""
    prompt = (
        f"Analyze this UI screenshot. {focus_instr}Provide:\n"
        f"EXTRACTED_TEXT: All visible text\n"
        f"UI_ELEMENTS: Detected buttons, menus, inputs\n"
        f"LAYOUT: Structure description\n"
        f"SUMMARY: One-sentence summary"
    )
    result = ask_with_image(image, prompt=prompt, model=model, max_tokens=3000)
    
    # Parse structured response
    text = result["text"]
    sections = {"extracted_text": "", "ui_elements": "", "layout": "", "summary": ""}
    current = None
    
    for line in text.split("\n"):
        if "EXTRACTED_TEXT:" in line.upper():
            current = "extracted_text"
        elif "UI_ELEMENTS:" in line.upper():
            current = "ui_elements"
        elif "LAYOUT:" in line.upper():
            current = "layout"
        elif "SUMMARY:" in line.upper():
            current = "summary"
        elif current:
            sections[current] += line + "\n"
    
    # If parsing failed, put everything in extracted_text
    if not any(sections.values()):
        sections["extracted_text"] = text
    
    sections["raw_response"] = text
    return sections


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
        _log_usage(result)
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

# Usage logging (Tab-separated: timestamp, model, provider, input, output, cost_usd)
import datetime

USAGE_LOG = "/opt/ai-orchestrator/var/logs/qwen-usage.tsv"
VISION_USAGE_LOG = "/opt/ai-orchestrator/var/logs/qwen-vision-usage.tsv"

def _log_usage(result: dict, input_tokens: int = 0) -> None:
    usage = result.get("usage", {})
    inp = usage.get("prompt_tokens", input_tokens)
    out = usage.get("completion_tokens", 0)
    # qwen-plus: ~$0.0004/1k input, $0.0012/1k output
    cost = (inp * 0.0000004) + (out * 0.0000012)
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(USAGE_LOG, "a") as f:
        f.write(f"{ts}\t{result.get('model','?')}\t{result.get('provider','?')}\t{inp}\t{out}\t{cost:.8f}\n")


def _log_vision_usage(result: dict) -> None:
    """Log vision API usage separately."""
    usage = result.get("usage", {})
    inp = usage.get("prompt_tokens", 0)
    out = usage.get("completion_tokens", 0)
    # qwen3-vl-flash: ~$0.0005/1k input, $0.0015/1k output (approximate)
    cost = (inp * 0.0000005) + (out * 0.0000015)
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Ensure directory exists
    Path(VISION_USAGE_LOG).parent.mkdir(parents=True, exist_ok=True)
    
    with open(VISION_USAGE_LOG, "a") as f:
        f.write(f"{ts}\t{result.get('model','?')}\t{result.get('provider','?')}\t{inp}\t{out}\t{cost:.8f}\n")
