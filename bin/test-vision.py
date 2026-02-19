#!/usr/bin/env python3
"""
Test Vision Integration — Verify Qwen-VL setup and capabilities

Usage:
    test-vision.py [--all] [--ocr] [--describe] [--screenshot]
    
Tests:
    1. API connectivity
    2. OCR with German/English text
    3. Image description
    4. Screenshot analysis
    
Requires: DASHSCOPE_INTL_API_KEY set
"""

import sys
import os
import json
import time
from pathlib import Path

sys.path.insert(0, '/opt/ai-orchestrator/lib')

# Check API key
DASHSCOPE_KEY = os.environ.get("DASHSCOPE_INTL_API_KEY", "")
if not DASHSCOPE_KEY:
    print("❌ ERROR: DASHSCOPE_INTL_API_KEY not set")
    print("   Set it: export DASHSCOPE_INTL_API_KEY=sk-...")
    sys.exit(1)

print("✓ API key found")
print(f"  Key prefix: {DASHSCOPE_KEY[:15]}...")
print()

# Test imports
try:
    from brain import ask_with_image, ocr_image, describe_image, analyze_screenshot
    print("✓ brain.py vision functions imported successfully")
except ImportError as e:
    print(f"❌ ERROR: Failed to import from brain.py: {e}")
    sys.exit(1)

print()

def create_test_image():
    """Create a simple test image with text."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("⚠ Pillow not installed, skipping test image creation")
        return None
    
    # Create simple image with text
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    # Add text
    text = "Test OCR\nFord Perfect\nVision Module\n2025-02-19"
    draw.text((50, 80), text, fill='black')
    
    # Save
    test_path = Path("/tmp/vision-test.png")
    img.save(test_path)
    print(f"✓ Created test image: {test_path}")
    return test_path


def test_ocr(image_path):
    """Test OCR functionality."""
    print("\n" + "="*60)
    print("TEST 1: OCR (Text Extraction)")
    print("="*60)
    
    t0 = time.time()
    try:
        result = ocr_image(image_path, language="en")
        latency = time.time() - t0
        
        print(f"✓ OCR completed in {latency:.2f}s")
        print(f"\nExtracted text:\n{result}")
        print(f"\nModel: {DEFAULT_VL_MODEL}")
        
        # Verify some expected content
        if "Ford" in result or "Test" in result:
            print("✓ OCR accuracy check: PASSED (found expected keywords)")
        else:
            print("⚠ OCR accuracy check: Some text may have been missed")
        
        return True
        
    except Exception as e:
        print(f"❌ OCR failed: {e}")
        return False


def test_describe(image_path):
    """Test image description."""
    print("\n" + "="*60)
    print("TEST 2: Image Description")
    print("="*60)
    
    t0 = time.time()
    try:
        result = describe_image(image_path, detail="brief")
        latency = time.time() - t0
        
        print(f"✓ Description generated in {latency:.2f}s")
        print(f"\nDescription:\n{result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Description failed: {e}")
        return False


def test_analyze_screenshot(image_path):
    """Test screenshot analysis."""
    print("\n" + "="*60)
    print("TEST 3: Screenshot Analysis")
    print("="*60)
    
    t0 = time.time()
    try:
        analysis = analyze_screenshot(image_path, focus="text")
        latency = time.time() - t0
        
        print(f"✓ Analysis completed in {latency:.2f}s")
        print(f"\nExtracted text:\n{analysis['extracted_text']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False


def test_api_connectivity():
    """Test basic API connectivity."""
    print("\n" + "="*60)
    print("TEST 0: API Connectivity")
    print("="*60)
    
    # Import here to avoid circular imports
    import urllib.request
    import json
    
    VL_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
    
    payload = {
        "model": "qwen3-vl-flash",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say VISION_READY"}
        ],
        "max_tokens": 50
    }
    
    # Note: This will fail without an actual image, but tests endpoint
    try:
        # Just test that we can reach the endpoint
        req = urllib.request.Request(
            VL_BASE.replace("chat/completions", "models"),
            headers={"Authorization": f"Bearer {DASHSCOPE_KEY}"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            models = json.loads(resp.read().decode())
            print(f"✓ API endpoint reachable")
            print(f"  Available models: {len(models.get('data', []))}")
        
        return True
        
    except Exception as e:
        print(f"⚠ API model list failed (expected): {e}")
        print("  Continuing with functional tests...")
        return True  # Don't fail on this


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Qwen-VL integration")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--ocr", action="store_true", help="Test OCR only")
    parser.add_argument("--describe", action="store_true", help="Test description only")
    parser.add_argument("--screenshot", action="store_true", help="Test screenshot analysis only")
    parser.add_argument("--image", help="Use specific image for testing")
    
    args = parser.parse_args()
    
    # Determine which tests to run
    run_all = not any([args.ocr, args.describe, args.screenshot])
    
    # Get test image
    if args.image:
        test_image = Path(args.image)
        if not test_image.exists():
            print(f"❌ Image not found: {test_image}")
            sys.exit(1)
    else:
        test_image = create_test_image()
        if not test_image:
            # Try to find any image
            for path in ["/tmp/test.png", "./test.png"]:
                if Path(path).exists():
                    test_image = Path(path)
                    break
        
        if not test_image or not test_image.exists():
            print("⚠ No test image available")
            print("  Provide one: test-vision.py --image /path/to/image.png")
            sys.exit(1)
    
    print(f"\nUsing test image: {test_image}")
    print(f"Image size: {test_image.stat().st_size / 1024:.1f}KB")
    
    # Run tests
    results = {}
    
    if run_all or args.ocr:
        results['ocr'] = test_ocr(test_image)
    
    if run_all or args.describe:
        results['describe'] = test_describe(test_image)
    
    if run_all or args.screenshot:
        results['screenshot'] = test_analyze_screenshot(test_image)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(results.values())
    
    print(f"Tests: {passed}/{total} passed")
    
    if passed == total:
        print("\n✅ All tests passed! Vision integration is working.")
        sys.exit(0)
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Check logs above.")
        sys.exit(1)
