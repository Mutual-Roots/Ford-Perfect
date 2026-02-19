# Vision & OCR Quick Reference

## Python API (brain.py)

```python
from lib.brain import ask_with_image, ocr_image, describe_image, analyze_screenshot

# General image analysis
result = ask_with_image("image.png", "What's in this image?")
print(result["text"])

# OCR - extract text
text = ocr_image("document.png", language="auto")

# Image description
caption = describe_image("photo.jpg", detail="brief")  # or "detailed"

# Screenshot analysis
analysis = analyze_screenshot("ui.png", focus="all")  # or "text", "elements", "layout"
print(analysis["extracted_text"])
print(analysis["ui_elements"])
print(analysis["summary"])
```

## Command Line

### OCR
```bash
ocr-image screenshot.png                    # Extract text
ocr-image doc.jpg --lang de                 # German document
ocr-image ./dir/ --batch --json > out.json  # Batch mode
cat img.png | ocr-image --stdin             # From stdin
```

### Description
```bash
describe-image photo.jpg                    # Brief caption
describe-image photo.jpg --detail detailed  # Detailed
describe-image img.png --tags               # Comma-separated tags
```

### Screenshot Analysis
```bash
analyze-screenshot ui.png                   # Full analysis
analyze-screenshot ui.png --text-only       # Just text
analyze-screenshot ui.png --elements-only   # Just UI elements
analyze-screenshot ui.png --simple          # Just summary
analyze-screenshot ui.png --json            # Structured JSON
```

## Models

| Model | Use Case | Cost (per 1M tokens) |
|-------|----------|---------------------|
| `qwen3-vl-flash` | Default, OCR, screenshots | $0.50 in / $1.50 out |
| `qwen3-vl-plus-2025-12-19` | Complex reasoning | $1.50 in / $4.50 out |

## Supported Formats

- **Images**: PNG, JPG, JPEG, WebP, GIF, BMP
- **Max size**: 20MB
- **Input**: File path, URL, base64 data URL

## Examples

### Extract all text from screenshot
```bash
analyze-screenshot app.png --text-only
```

### OCR receipt with German text
```bash
ocr-image receipt.jpg --lang de --json | jq .text
```

### Describe photo for accessibility
```bash
describe-image vacation.jpg --detail detailed
```

### Batch process all screenshots in folder
```bash
for f in ~/screenshots/*.png; do
    ocr-image "$f" --json >> ocr-results.jsonl
done
```

### Python batch processing
```python
from lib.vision import process_images_batch

images = ["img1.png", "img2.png", "img3.png"]
results = process_images_batch(images, "Extract all text")
for r in results:
    print(r["text"])
```

## Logs & Monitoring

```bash
# View vision usage
tail -f /opt/ai-orchestrator/var/logs/qwen-vision-usage.tsv

# Check today's costs
grep "^$(date +%Y-%m-%d)" /opt/ai-orchestrator/var/logs/qwen-vision-usage.tsv | \
    awk -F'\t' '{sum+=$6} END {print "Total: $" sum}'
```

## Troubleshooting

**API key error:**
```bash
export DASHSCOPE_INTL_API_KEY=sk-...
```

**Image too large:**
```bash
convert input.png -resize 50% output.png
```

**Poor OCR accuracy:**
```bash
ocr-image doc.png --lang de  # Specify language
```

## Testing

```bash
# Run test suite
test-vision.py --all

# Test with specific image
test-vision.py --ocr --image /path/to/image.png
```

---

For full documentation: `/opt/ai-orchestrator/docs/vision-ocr-guide.md`
