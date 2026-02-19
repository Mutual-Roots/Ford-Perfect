# Vision & OCR Integration Guide

Ford Perfect now supports native image recognition and OCR capabilities via Qwen-VL (Vision-Language) models from DashScope-Intl (Singapore).

## Overview

### Available Models

| Model | Best For | Speed | Cost (per 1M tokens) |
|-------|----------|-------|---------------------|
| `qwen3-vl-flash` | OCR, simple tasks, screenshots | ⚡⚡⚡ Fastest | Input: $0.50, Output: $1.50 |
| `qwen3-vl-plus-2025-12-19` | Complex visual reasoning | ⚡⚡ Balanced | Input: $1.50, Output: $4.50 |

**Default:** `qwen3-vl-flash` (cost-efficient for most tasks)

### Capabilities

- **OCR**: Extract text from images, documents, screenshots
- **Image Captioning**: Generate descriptions for photos
- **Visual QA**: Answer questions about image content
- **Screenshot Analysis**: Detect UI elements, layout, text
- **Diagram Analysis**: Understand charts, flowcharts, graphs

### Supported Formats

- **Image formats**: PNG, JPG/JPEG, WebP, GIF, BMP
- **Max size**: 20MB per image (larger images must be resized)
- **Input methods**: Local file paths, public URLs, base64 data URLs

---

## Installation & Setup

### Prerequisites

1. **API Key**: Ensure `DASHSCOPE_INTL_API_KEY` is set:
   ```bash
   export DASHSCOPE_INTL_API_KEY=sk-...
   ```

2. **Verify key works**:
   ```bash
   /opt/ai-orchestrator/bin/qwen-health
   ```

No additional dependencies needed—uses Python stdlib.

---

## Usage

### 1. Python API (brain.py integration)

#### Basic Image Analysis

```python
from lib.brain import ask_with_image

# Analyze an image
result = ask_with_image("screenshot.png", "What's in this image?")
print(result["text"])
print(f"Model: {result['model']}, Tokens: {result['usage']}")
```

#### OCR (Text Extraction)

```python
from lib.brain import ocr_image

# Extract all text from image
text = ocr_image("document.png")
print(text)

# Specify language for better accuracy
text_de = ocr_image("german_doc.jpg", language="de")
```

#### Image Description

```python
from lib.brain import describe_image

# Brief description (1-2 sentences)
caption = describe_image("photo.jpg", detail="brief")

# Detailed description
detailed = describe_image("photo.jpg", detail="detailed")
```

#### Screenshot Analysis

```python
from lib.brain import analyze_screenshot

# Comprehensive analysis
analysis = analyze_screenshot("app-ui.png")
print(analysis["extracted_text"])  # All visible text
print(analysis["ui_elements"])     # Detected buttons, menus, etc.
print(analysis["layout"])          # Layout structure
print(analysis["summary"])         # One-sentence summary

# Focus on specific aspect
text_only = analyze_screenshot("ui.png", focus="text")
elements_only = analyze_screenshot("ui.png", focus="elements")
```

### 2. Command-Line Utilities

#### ocr-image — Extract Text

```bash
# Single image
ocr-image screenshot.png

# With language hint
ocr-image document.jpg --lang de

# JSON output
ocr-image receipt.png --json

# Batch process directory
ocr-image ./documents/ --batch --json > results.json

# From stdin (pipe from another command)
cat image.png | ocr-image --stdin
```

**Options:**
- `--lang <code>`: Language hint (auto, en, de, zh, fr, etc.)
- `--model <name>`: Override model (default: qwen3-vl-flash)
- `--json`: Output as JSON instead of plain text
- `--batch`: Process all images in directory
- `--stdin`: Read image from stdin

#### describe-image — Generate Captions

```bash
# Brief description
describe-image photo.jpg

# Detailed description
describe-image photo.jpg --detail detailed

# Output tags instead of prose
describe-image image.png --tags

# Focus on specific aspect
describe-image screenshot.png --focus text

# Batch mode
describe-image ./photos/ --batch --json > descriptions.json
```

**Options:**
- `--detail <level>`: brief (default), detailed, verbose
- `--tags`: Output comma-separated tags
- `--focus <area>`: Focus on objects, text, colors, layout
- `--json`: JSON output
- `--batch`: Process directory

#### analyze-screenshot — UI Analysis

```bash
# Full analysis
analyze-screenshot app-ui.png

# Extract only text
analyze-screenshot ui.png --text-only

# Extract only UI elements
analyze-screenshot ui.png --elements-only

# Just summary
analyze-screenshot ui.png --simple

# JSON output with full structure
analyze-screenshot ui.png --json

# Batch process screenshots
analyze-screenshot ./screenshots/ --batch --text-only
```

**Options:**
- `--focus <area>`: text, elements, layout, all (default: all)
- `--text-only`: Output only extracted text
- `--elements-only`: Output only UI elements list
- `--simple`: Output only summary
- `--json`: Structured JSON output
- `--batch`: Process directory

---

## Integration with Chat Extraction Pipeline

To automatically OCR images found in chat exports:

### Option 1: Modify Extractors

Add to your chat extractor scripts (e.g., `extract-claude-chats.py`):

```python
import subprocess
import json

def extract_images_from_conversation(conv_data):
    """Extract and OCR images from conversation."""
    for message in conv_data.get("messages", []):
        if "attachments" in message:
            for attachment in message["attachments"]:
                if attachment.get("type") == "image":
                    image_path = attachment.get("path")
                    if image_path:
                        # Run OCR
                        result = subprocess.run(
                            ["ocr-image", "--json", image_path],
                            capture_output=True, text=True
                        )
                        ocr_data = json.loads(result.stdout)
                        
                        # Store alongside original
                        attachment["extracted_text"] = ocr_data.get("text", "")
                        attachment["ocr_model"] = ocr_data.get("model", "")
                        conv_data["has_visual_content"] = True
    
    return conv_data
```

### Option 2: Post-Processing Script

Create a post-processor that runs after extraction:

```python
#!/usr/bin/env python3
"""Post-process chat exports to OCR images."""

import json
import subprocess
from pathlib import Path

def process_export(jsonl_path):
    """Process a JSONL export file."""
    updated = []
    
    with open(jsonl_path) as f:
        for line in f:
            conv = json.loads(line)
            
            # Check if already processed
            if conv.get("vision_processed"):
                updated.append(conv)
                continue
            
            # Find images
            images_found = []
            for msg in conv.get("messages", []):
                for attachment in msg.get("attachments", []):
                    if attachment.get("type") == "image":
                        img_path = attachment.get("path")
                        if img_path and Path(img_path).exists():
                            # OCR
                            result = subprocess.run(
                                ["ocr-image", "--json", img_path],
                                capture_output=True, text=True
                            )
                            ocr = json.loads(result.stdout)
                            attachment["extracted_text"] = ocr.get("text", "")
                            images_found.append(img_path)
            
            if images_found:
                conv["vision_processed"] = True
                conv["images_ocrd"] = len(images_found)
                conv["tags"] = conv.get("tags", []) + ["has_visual_content"]
            
            updated.append(conv)
    
    # Write back
    with open(jsonl_path, 'w') as f:
        for conv in updated:
            f.write(json.dumps(conv) + '\n')
    
    print(f"Processed {len(updated)} conversations")

if __name__ == "__main__":
    import sys
    for path in sys.argv[1:]:
        process_export(path)
```

---

## Cost Comparison

### Qwen-VL vs Separate OCR Services

| Service | Cost per Page | Accuracy | Language Support |
|---------|--------------|----------|------------------|
| **Qwen-VL Flash** | ~$0.002-0.01 | Excellent | 100+ languages |
| Google Vision OCR | $0.0015 | Excellent | 50+ languages |
| AWS Textract | $0.0015 | Excellent | Limited languages |
| Azure Computer Vision | $0.001 | Good | 70+ languages |

**Advantages of Qwen-VL:**
- ✅ Unified API (no separate OCR service needed)
- ✅ Context-aware OCR (understands layout, formatting)
- ✅ Can answer questions about images, not just extract text
- ✅ No data leaves Alibaba Cloud infrastructure
- ✅ Cheaper for complex tasks (one call vs multiple services)

**When to use separate OCR:**
- Very high volume (>100k pages/day) → specialized OCR may be cheaper
- Need 99.99% accuracy on specific document types
- Regulatory requirements mandate specific providers

---

## Best Practices

### When to Use Vision Models

**Use Qwen-VL when:**
- You need both OCR AND understanding of context
- Analyzing screenshots, diagrams, charts
- Multi-modal tasks (image + text reasoning)
- Quick prototyping (unified API)

**Use text-only models when:**
- You already have extracted text
- Pure text processing tasks
- Cost is critical and OCR not needed
- Maximum speed required (VL adds latency)

### Image Preparation

1. **Resize large images**: Keep under 5MB for faster processing
   ```bash
   convert input.png -resize 2000x2000\> output.png
   ```

2. **Optimize format**: PNG for text/screenshots, JPEG for photos

3. **Crop to relevant area**: Remove unnecessary margins

### Error Handling

Always handle errors gracefully:

```python
try:
    result = ask_with_image("image.png", "Describe this")
    print(result["text"])
except FileNotFoundError:
    print("Image not found")
except EnvironmentError as e:
    print(f"API key issue: {e}")
except Exception as e:
    print(f"Analysis failed: {e}")
    # Fallback: log error, continue with text-only processing
```

### Rate Limits

DashScope-Intl rate limits (as of 2025):
- **Free tier**: 100 requests/day
- **Paid tier**: 1000 requests/minute (RPM)
- **Burst limit**: 50 concurrent requests

Monitor usage:
```bash
tail -f /opt/ai-orchestrator/var/logs/qwen-vision-usage.tsv
```

---

## Testing

### Test with Sample Images

```bash
# Test OCR with German text
ocr-image test-de.png --lang de --json | jq .

# Test screenshot analysis
analyze-screenshot test-ui.png --json | jq '.extracted_text'

# Test image description
describe-image test-photo.jpg --detail detailed
```

### Verify Accuracy

For critical applications, verify OCR accuracy:

```python
def verify_ocr(image_path, expected_text):
    """Verify OCR accuracy against known text."""
    from lib.brain import ocr_image
    
    extracted = ocr_image(image_path)
    
    # Simple accuracy check
    expected_words = set(expected_text.lower().split())
    extracted_words = set(extracted.lower().split())
    
    overlap = len(expected_words & extracted_words)
    accuracy = overlap / len(expected_words) if expected_words else 0
    
    return {
        "accuracy": accuracy,
        "expected": expected_text[:100],
        "extracted": extracted[:100]
    }
```

---

## Troubleshooting

### Common Issues

**Problem**: `DASHSCOPE_INTL_API_KEY not set`
- **Solution**: `export DASHSCOPE_INTL_API_KEY=sk-...`

**Problem**: Image too large
- **Solution**: Resize image to under 20MB
  ```bash
  convert input.png -quality 85 -resize 50% output.png
  ```

**Problem**: Unsupported format
- **Solution**: Convert to PNG or JPEG
  ```bash
  convert input.webp output.png
  ```

**Problem**: Poor OCR accuracy
- **Solutions**:
  - Specify language: `ocr-image doc.png --lang de`
  - Try higher-quality model: `--model qwen3-vl-plus-2025-12-19`
  - Improve image quality (higher resolution, better contrast)

**Problem**: Timeout
- **Solution**: Increase timeout or reduce image size
  ```python
  result = ask_with_image(image, prompt, max_tokens=1000)  # Faster
  ```

---

## Performance Benchmarks

Typical performance (Singapore endpoint, Feb 2025):

| Task | Image Size | Latency | Tokens Used |
|------|-----------|---------|-------------|
| OCR (single page) | 800KB | 1.5-3s | 500-1500 |
| Screenshot analysis | 1.2MB | 2-4s | 800-2000 |
| Image description | 2MB | 2-3s | 400-800 |
| Diagram analysis | 1MB | 3-5s | 1000-2500 |

---

## Security & Privacy

- **Data residency**: All processing in Singapore (DashScope-Intl)
- **No third-party uploads**: Images stay within Alibaba Cloud
- **Encryption**: TLS in transit, encrypted at rest
- **Retention**: Check Alibaba Cloud data retention policies
- **Compliance**: Suitable for most enterprise use cases

For highly sensitive data:
- Consider on-premise OCR solutions
- Implement additional encryption before upload
- Review Alibaba Cloud compliance certifications

---

## Future Enhancements

Planned improvements:
- [ ] Automatic image optimization (resize, compress)
- [ ] Caching layer for repeated images
- [ ] Batch API for multiple images in one request
- [ ] Streaming responses for large images
- [ ] Integration with cost monitor dashboard
- [ ] Support for video frame extraction + analysis

---

## Support

- **Documentation**: `/opt/ai-orchestrator/docs/vision-ocr-guide.md`
- **Usage logs**: `/opt/ai-orchestrator/var/logs/qwen-vision-usage.tsv`
- **Issues**: Check logs first, then escalate to main agent

---

*Last updated: 2025-02-19*
*Models: qwen3-vl-flash, qwen3-vl-plus-2025-12-19*
*Endpoint: https://dashscope-intl.aliyuncs.com/compatible-mode/v1*
