#!/usr/bin/env python3
"""Qwen Cost Monitor — Fetch usage stats from DashScope-Intl API"""
import os, json, sys
from argparse import ArgumentParser

API_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/billing/usage"

def fetch_usage(api_key):
    try:
        import requests
    except ImportError:
        print("Error: pip install requests", file=sys.stderr)
        sys.exit(1)
    r = requests.get(API_URL, headers={'Authorization': f'Bearer {api_key}'}, timeout=10)
    r.raise_for_status()
    return r.json()

def main():
    p = ArgumentParser(description='Monitor Qwen API usage and costs', formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--json', action='store_true', help='JSON output')
    p.add_argument('--model', help='Filter by model name')
    args = p.parse_args()
    
    api_key = os.getenv('DASHSCOPE_INTL_API_KEY')
    if not api_key:
        print("Error: DASHSCOPE_INTL_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    
    try:
        data = fetch_usage(api_key)
        usage = data.get('data', [])
        
        total_in = sum(u.get('tokens_in', 0) for u in usage)
        total_out = sum(u.get('tokens_out', 0) for u in usage)
        total_cost = sum(u.get('cost', 0) for u in usage)
        
        if args.json:
            print(json.dumps({'total_tokens_in': total_in, 'total_tokens_out': total_out, 'total_cost_usd': total_cost, 'items': usage}, indent=2))
        else:
            print(f"Total In: {total_in:,} | Out: {total_out:,} | Cost: ${total_cost:.4f}")
            print(f"Remaining from 70M credit: ~{70000000 - int(total_cost*1e9):,} tokens (estimate)")
            for u in usage[:10]:
                model = u.get('model', '?')
                if args.model and args.model not in model: continue
                print(f"  {model}: {u.get('tokens_in',0):,}in / {u.get('tokens_out',0):,}out = ${u.get('cost',0):.6f}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    import argparse
    main()
