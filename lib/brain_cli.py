#!/usr/bin/env python3
"""
brain_cli.py — Thin subprocess bridge for brain.ask()

Usage:
  echo "task" | python3 brain_cli.py [OPTIONS]
  python3 brain_cli.py --prompt "task" [OPTIONS]

Options:
  --model MODEL         Model to use (default: qwen-plus-latest)
  --system-file FILE    Path to system prompt file (default: none)
  --system TEXT         Inline system prompt text
  --max-tokens N        Max output tokens (default: 2000)
  --json                Output full JSON (text + usage) instead of just text
  --help                Show this help

Exit codes: 0=success, 1=error
"""

import sys
import os
import json
import argparse

# Add the lib dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain


def main():
    p = argparse.ArgumentParser(
        description="brain_cli — subprocess bridge to brain.ask()",
        add_help=False
    )
    p.add_argument("--model", default="qwen-plus-latest")
    p.add_argument("--system-file", default=None)
    p.add_argument("--system", default=None)
    p.add_argument("--max-tokens", type=int, default=2000)
    p.add_argument("--json", action="store_true", dest="output_json")
    p.add_argument("--help", "-h", action="store_true")
    p.add_argument("prompt", nargs="*")
    args = p.parse_args()

    if args.help:
        print(__doc__)
        sys.exit(0)

    # System prompt: file > inline > brain default
    system = None
    if args.system_file:
        try:
            with open(args.system_file) as f:
                system = f.read().strip()
        except Exception as e:
            print(f"[brain_cli] ERROR: cannot read system file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.system:
        system = args.system

    # Prompt: args > stdin
    if args.prompt:
        prompt = " ".join(args.prompt)
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    else:
        print("[brain_cli] ERROR: no prompt provided (use --prompt or pipe stdin)", file=sys.stderr)
        sys.exit(1)

    if not prompt:
        print("[brain_cli] ERROR: empty prompt", file=sys.stderr)
        sys.exit(1)

    messages = [{"role": "user", "content": prompt}]

    try:
        result = brain.ask(
            messages,
            model=args.model,
            max_tokens=args.max_tokens,
            system=system
        )
    except Exception as e:
        print(f"[brain_cli] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output_json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(result["text"])

    sys.exit(0)


if __name__ == "__main__":
    main()
