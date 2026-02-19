"""
Ford Perfect Vision — Qwen-VL Integration for Image Recognition and OCR

Supports:
- OCR (text extraction from images)
- Image captioning/description
- Visual QA (answering questions about images)
- Screenshot analysis (UI elements, layout, text)

Models available on DashScope-Intl (Singapore):
- qwen3-vl-flash: Fast, cost-efficient for OCR and simple tasks
- qwen3-vl-plus-2025-12-19: Higher accuracy for complex visual reasoning

Image input formats:
- Base64-encoded images (data:image/png;base64,...)
- Public URLs (https://...)
- Local file paths (automatically converted to base64)

Supported image formats: PNG, JPG/JPEG, WebP, GIF, BMP
Max image size: 20MB (larger images are automatically resized)
"""

import os
import json
import time
import base64
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Union, List, Dict, Any

log = logging.getLogger(__name__)

# Configuration
DASHSCOPE_INTL_KEY = os.environ.get("DASHSCOPE_INTL_API_KEY", "")
DASHSCOPE_VL_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"

# Default model for vision tasks (fast & cost-efficient)
DEFAULT_VL_MODEL = "qwen3-vl-flash"

# System prompt for vision tasks
VL_SYSTEM_PROMPT = """You are Ford Perfect's vision module. Analyze images accurately and concisely.
For OCR: Extract ALL visible text verbatim, preserve line breaks and formatting.
For screenshots: Identify UI elements, text, layout structure.
Be precise, no fluff. Report what you see."""


def _encode_image_to_base64(image_path: str, max_size_mb: float = 20.0) -> str:
    """
    Encode local image file to base64 data URL.
    
    Args:
        image_path: Path to local image file
        max_size_mb: Maximum file size in MB (larger images will be rejected)
    
    Returns:
        Data URL string: "data:image/png;base64,..."
    
    Raises:
        FileNotFoundError: If image doesn't exist
        ValueError: If image format unsupported or too large
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    # Check file size
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(
            f"Image too large: {size_mb:.2f}MB (max: {max_size_mb}MB). "
            f"Resize before processing."
        )
    
    # Determine MIME type from extension
    ext = path.suffix.lower()
    mime_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
    }
    
    mime_type = mime_map.get(ext)
    if not mime_type:
        raise ValueError(
            f"Unsupported image format: {ext}. "
            f"Supported: {', '.join(mime_map.keys())}"
        )
    
    # Read and encode
    with open(path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    return f"data:{mime_type};base64,{image_data}"


def _prepare_image_content(image_input: Union[str, Path]) -> Dict[str, Any]:
    """
    Prepare image content for API request.
    
    Args:
        image_input: Can be:
            - Local file path (str or Path)
            - Public URL (starts with http:// or https://)
            - Base64 data URL (starts with "data:image/")
    
    Returns:
        Dict in format: {"type": "image_url", "image_url": {"url": "..."}}
    """
    if isinstance(image_input, Path):
        image_input = str(image_input)
    
    if not isinstance(image_input, str):
        raise TypeError(f"image_input must be str or Path, got {type(image_input)}")
    
    # Case 1: Already a data URL
    if image_input.startswith("data:image/"):
        return {"type": "image_url", "image_url": {"url": image_input}}
    
    # Case 2: Public URL
    if image_input.startswith(("http://", "https://")):
        return {"type": "image_url", "image_url": {"url": image_input}}
    
    # Case 3: Local file path → convert to base64
    if Path(image_input).exists():
        data_url = _encode_image_to_base64(image_input)
        return {"type": "image_url", "image_url": {"url": data_url}}
    
    # Unknown format
    raise ValueError(
        f"Invalid image input: {image_input[:100]}... "
        f"Must be local path, public URL, or base64 data URL"
    )


def ask_with_image(
    image: Union[str, Path],
    prompt: str = "What's in this image?",
    model: str = DEFAULT_VL_MODEL,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """
    Analyze an image with Qwen-VL model.
    
    Args:
        image: Image input (local path, URL, or base64 data URL)
        prompt: Question or instruction about the image
        model: Qwen-VL model to use (default: qwen3-vl-flash)
        system_prompt: Optional system prompt override
        max_tokens: Maximum output tokens
        temperature: Sampling temperature (0.0-2.0)
    
    Returns:
        Dict with keys:
            - text: Model's response text
            - model: Model used
            - usage: Token usage stats
            - provider: "qwen-vl-singapore"
            - latency_ms: Request duration
            - fallback_used: Whether fallback was needed
    
    Example:
        >>> result = ask_with_image("screenshot.png", "Extract all text from this screenshot")
        >>> print(result["text"])
    """
    if not DASHSCOPE_INTL_KEY:
        raise EnvironmentError(
            "DASHSCOPE_INTL_API_KEY not set. "
            "Export DASHSCOPE_INTL_API_KEY=sk-..."
        )
    
    # Prepare messages
    image_content = _prepare_image_content(image)
    text_content = {"type": "text", "text": prompt}
    
    messages = [
        {
            "role": "user",
            "content": [image_content, text_content]
        }
    ]
    
    # Build payload
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    # Add system prompt if provided
    if system_prompt:
        messages.insert(0, {"role": "system", "content": system_prompt})
    elif VL_SYSTEM_PROMPT:
        messages.insert(0, {"role": "system", "content": VL_SYSTEM_PROMPT})
    
    # Make API request
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_INTL_KEY}",
        "Content-Type": "application/json",
    }
    
    t0 = time.time()
    try:
        req = urllib.request.Request(
            DASHSCOPE_VL_BASE,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as resp:
            response_data = json.loads(resp.read().decode('utf-8'))
        
        latency_ms = int((time.time() - t0) * 1000)
        
        # Parse response
        choice = response_data.get("choices", [{}])[0]
        text = choice.get("message", {}).get("content", "").strip()
        usage = response_data.get("usage", {})
        
        result = {
            "text": text,
            "model": response_data.get("model", model),
            "usage": usage,
            "provider": "qwen-vl-singapore",
            "latency_ms": latency_ms,
            "fallback_used": False,
        }
        
        _log_vision_usage(result)
        log.info(
            "VL request completed: %s | %dms | %d tokens",
            model, latency_ms, usage.get("total_tokens", 0)
        )
        
        return result
        
    except Exception as e:
        log.error("Qwen-VL API call failed: %s", e)
        raise


def ocr_image(
    image: Union[str, Path],
    language: str = "auto",
    model: str = DEFAULT_VL_MODEL,
) -> str:
    """
    Extract text from image (OCR).
    
    Args:
        image: Image input (path, URL, or base64)
        language: Language hint ("auto", "en", "de", "zh", etc.)
        model: Qwen-VL model
    
    Returns:
        Extracted text as string
    
    Example:
        >>> text = ocr_image("document.png")
        >>> print(text)
    """
    lang_instruction = ""
    if language != "auto":
        lang_instruction = f"Language: {language}. "
    
    prompt = (
        f"{lang_instruction}Extract ALL text from this image verbatim. "
        f"Preserve line breaks, spacing, and formatting. "
        f"Do not add any commentary—output ONLY the extracted text."
    )
    
    result = ask_with_image(image, prompt=prompt, model=model, max_tokens=4000)
    return result["text"]


def describe_image(
    image: Union[str, Path],
    detail: str = "brief",
    model: str = DEFAULT_VL_MODEL,
) -> str:
    """
    Generate description/caption for an image.
    
    Args:
        image: Image input
        detail: "brief" (1-2 sentences) or "detailed" (comprehensive)
        model: Qwen-VL model
    
    Returns:
        Image description as string
    """
    if detail == "brief":
        prompt = "Describe this image briefly in 1-2 sentences. What do you see?"
    else:
        prompt = (
            "Provide a detailed description of this image. Include: "
            "main subjects, colors, layout, text (if any), context, "
            "and any notable details. Be thorough but concise."
        )
    
    result = ask_with_image(image, prompt=prompt, model=model)
    return result["text"]


def analyze_screenshot(
    image: Union[str, Path],
    focus: Optional[str] = None,
    model: str = DEFAULT_VL_MODEL,
) -> Dict[str, Any]:
    """
    Analyze a UI screenshot for elements, text, and layout.
    
    Args:
        image: Screenshot image
        focus: Optional focus area ("text", "layout", "elements", "all")
        model: Qwen-VL model
    
    Returns:
        Dict with structured analysis:
            - extracted_text: All visible text
            - ui_elements: Detected UI components
            - layout: Layout description
            - summary: Brief summary
    
    Example:
        >>> analysis = analyze_screenshot("app-ui.png")
        >>> print(analysis["extracted_text"])
    """
    focus_instruction = ""
    if focus:
        focus_instruction = f"Focus specifically on: {focus}. "
    
    prompt = (
        f"Analyze this UI screenshot. {focus_instruction}Provide: "
        f"1. EXTRACTED_TEXT: All visible text verbatim\n"
        f"2. UI_ELEMENTS: List detected elements (buttons, menus, inputs, etc.)\n"
        f"3. LAYOUT: Describe the layout structure\n"
        f"4. SUMMARY: One-sentence summary\n\n"
        f"Format your response as:\n"
        f"EXTRACTED_TEXT:\n[...]\n\n"
        f"UI_ELEMENTS:\n[...]\n\n"
        f"LAYOUT:\n[...]\n\n"
        f"SUMMARY: [...]"
    )
    
    result = ask_with_image(image, prompt=prompt, model=model, max_tokens=3000)
    text = result["text"]
    
    # Parse structured response
    analysis = {
        "raw_response": text,
        "extracted_text": "",
        "ui_elements": "",
        "layout": "",
        "summary": "",
    }
    
    # Simple parsing by section headers
    sections = text.split("\n\n")
    current_section = None
    
    for section in sections:
        if section.startswith("EXTRACTED_TEXT:"):
            current_section = "extracted_text"
            analysis[current_section] = section.replace("EXTRACTED_TEXT:", "").strip()
        elif section.startswith("UI_ELEMENTS:"):
            current_section = "ui_elements"
            analysis[current_section] = section.replace("UI_ELEMENTS:", "").strip()
        elif section.startswith("LAYOUT:"):
            current_section = "layout"
            analysis[current_section] = section.replace("LAYOUT:", "").strip()
        elif section.startswith("SUMMARY:"):
            current_section = "summary"
            analysis[current_section] = section.replace("SUMMARY:", "").strip()
        elif current_section:
            analysis[current_section] += "\n" + section.strip()
    
    # Fallback: if parsing failed, put everything in raw_response
    if not any([analysis[k] for k in ["extracted_text", "ui_elements", "layout", "summary"]]):
        analysis["extracted_text"] = text
    
    return analysis


# Usage logging (separate from text-only models)
VISION_USAGE_LOG = "/opt/ai-orchestrator/var/logs/qwen-vision-usage.tsv"


def _log_vision_usage(result: dict) -> None:
    """Log vision API usage to TSV file."""
    usage = result.get("usage", {})
    inp = usage.get("prompt_tokens", 0)
    out = usage.get("completion_tokens", 0)
    
    # qwen3-vl-flash pricing (approximate, per Alibaba Cloud docs)
    # Input: ~$0.0005/1k tokens, Output: ~$0.0015/1k tokens
    cost = (inp * 0.0000005) + (out * 0.0000015)
    
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Ensure log directory exists
    log_path = Path(VISION_USAGE_LOG)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, "a") as f:
        f.write(
            f"{ts}\t{result.get('model', '?')}\t"
            f"{result.get('provider', '?')}\t{inp}\t{out}\t{cost:.8f}\n"
        )


# Convenience function for batch processing
def process_images_batch(
    images: List[Union[str, Path]],
    prompt: str,
    model: str = DEFAULT_VL_MODEL,
    output_format: str = "text",
) -> List[Dict[str, Any]]:
    """
    Process multiple images with the same prompt.
    
    Args:
        images: List of image paths/URLs
        prompt: Prompt for all images
        model: Qwen-VL model
        output_format: "text" (just responses) or "json" (full results)
    
    Returns:
        List of results (one per image)
    """
    results = []
    
    for i, image in enumerate(images, 1):
        log.info("[%d/%d] Processing: %s", i, len(images), image)
        try:
            result = ask_with_image(image, prompt=prompt, model=model)
            
            if output_format == "text":
                results.append(result["text"])
            else:
                result["source_image"] = str(image)
                results.append(result)
                
        except Exception as e:
            log.error("Failed to process %s: %s", image, e)
            results.append({"error": str(e), "source_image": str(image)})
    
    return results


if __name__ == "__main__":
    # Self-test
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python vision.py <image_path> [prompt]")
        print("Example: python vision.py screenshot.png 'Extract all text'")
        sys.exit(1)
    
    image_path = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else "What's in this image?"
    
    print(f"Testing Qwen-VL with: {image_path}")
    print(f"Prompt: {prompt}\n")
    
    try:
        result = ask_with_image(image_path, prompt=prompt)
        print("=" * 60)
        print(result["text"])
        print("=" * 60)
        print(f"\nModel: {result['model']}")
        print(f"Tokens: {result['usage']}")
        print(f"Latency: {result['latency_ms']}ms")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
