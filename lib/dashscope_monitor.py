"""
DashScope-Intl Cost Monitor for Qwen Models.

Provides API-based and log-based cost tracking for Alibaba DashScope-Intl.
Minimizes token usage by pulling data directly from APIs or local logs.

Usage:
    from lib.dashscope_monitor import DashScopeMonitor
    
    monitor = DashScopeMonitor()
    usage = monitor.get_usage(period='today')
    cost = monitor.get_cost(period='week')
    credit = monitor.get_remaining_credit()
    projection = monitor.project_monthly()
"""

import sqlite3
import json
import logging
import time
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import csv
from io import StringIO

log = logging.getLogger(__name__)

# Configuration
_BASE = Path("/opt/ai-orchestrator")
_LOG_FILE = _BASE / "var" / "logs" / "qwen-usage.tsv"
_DB_FILE = _BASE / "var" / "api_costs.db"
_CACHE_DIR = _BASE / "var" / "cache"
_PROVIDERS_YAML = _BASE / "etc" / "providers.yaml"

# Welcome credit and budget constants
WELCOME_CREDIT_TOKENS = 70_000_000  # 70M tokens
TEST_BUDGET_TOKENS = 1_000_000      # 1M tokens initial testing
WARN_THRESHOLD = 0.50               # 50% of test budget
CRITICAL_THRESHOLD = 0.80           # 80% of test budget

# Model pricing (USD per 1M tokens) - from providers.yaml
MODEL_PRICING = {
    'qwen-max': {'input': 0.40, 'output': 1.20},
    'qwen-max-latest': {'input': 0.40, 'output': 1.20},
    'qwen3-max-2026-01-23': {'input': 0.40, 'output': 1.20},
    'qwen3.5-plus': {'input': 0.08, 'output': 0.20},
    'qwen3.5-plus-2026-02-15': {'input': 0.08, 'output': 0.20},
    'qwen-plus': {'input': 0.08, 'output': 0.20},
    'qwen-plus-latest': {'input': 0.08, 'output': 0.20},
    'qwen-coder-plus': {'input': 0.08, 'output': 0.20},
    'qwen-turbo': {'input': 0.02, 'output': 0.06},
    'qwen-turbo-latest': {'input': 0.02, 'output': 0.06},
    'qwen-flash': {'input': 0.01, 'output': 0.03},
    'qwq-plus': {'input': 0.14, 'output': 0.56},
    'qwen3-coder-480b-a35b-instruct': {'input': 0.25, 'output': 1.00},
    'qwen3-235b-a22b': {'input': 0.14, 'output': 0.56},
    'qwen3-32b': {'input': 0.05, 'output': 0.20},
    # Vision models
    'qwen3-vl-max': {'input': 0.20, 'output': 0.60},
    'qwen3-vl-plus': {'input': 0.10, 'output': 0.30},
}


@dataclass
class UsageStats:
    """Usage statistics for a given period."""
    period: str
    start_date: str
    end_date: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    total_cost_usd: float
    calls_count: int
    by_model: Dict[str, Dict[str, Any]]
    daily_breakdown: List[Dict[str, Any]]


@dataclass
class BudgetStatus:
    """Budget and credit status."""
    test_budget_tokens: int
    test_budget_used: int
    test_budget_remaining: int
    test_budget_pct: float
    welcome_credit_total: int
    welcome_credit_used: int
    welcome_credit_remaining: int
    projected_exhaustion_days: Optional[int]
    alert_level: str  # 'ok', 'warn', 'critical'


class DashScopeMonitor:
    """Monitor for DashScope-Intl Qwen model usage and costs."""
    
    def __init__(self, log_file: Path = _LOG_FILE, db_file: Path = _DB_FILE):
        self.log_file = Path(log_file)
        self.db_file = Path(db_file)
        self.cache_dir = Path(_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache settings
        self.cache_ttl = 300  # 5 minutes cache
        self._cache = {}
        
    def _load_log_data(self) -> List[Dict[str, Any]]:
        """Load usage data from TSV log file."""
        if not self.log_file.exists():
            return []
        
        records = []
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parts = line.split('\t')
                    if len(parts) >= 6:
                        try:
                            record = {
                                'timestamp': parts[0],
                                'model': parts[1],
                                'provider': parts[2],
                                'input_tokens': int(parts[3]),
                                'output_tokens': int(parts[4]),
                                'cost_usd': float(parts[5]),
                            }
                            records.append(record)
                        except (ValueError, IndexError) as e:
                            log.debug(f"Skipping malformed line: {line}")
        except Exception as e:
            log.error(f"Error reading log file: {e}")
        
        return records
    
    def _filter_by_period(self, records: List[Dict], period: str) -> List[Dict]:
        """Filter records by time period."""
        now = datetime.now(timezone.utc)
        
        if period == 'today':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'yesterday':
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'month':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == 'all':
            start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        else:
            # Custom period (expecting 'YYYY-MM-DDtoYYYY-MM-DD')
            try:
                start_str, end_str = period.split('to')
                start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
            except:
                start = now - timedelta(days=7)
        
        filtered = []
        for record in records:
            try:
                ts = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                if period == 'yesterday':
                    if start <= ts < end:
                        filtered.append(record)
                else:
                    if ts >= start:
                        filtered.append(record)
            except:
                continue
        
        return filtered
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a model based on token usage."""
        pricing = MODEL_PRICING.get(model, {'input': 0.08, 'output': 0.20})
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']
        return input_cost + output_cost
    
    def get_usage(self, period: str = 'today', model_filter: Optional[str] = None) -> UsageStats:
        """Get usage statistics for a period."""
        cache_key = f"usage_{period}_{model_filter or 'all'}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        records = self._load_log_data()
        records = self._filter_by_period(records, period)
        
        if model_filter:
            records = [r for r in records if model_filter.lower() in r['model'].lower()]
        
        # Calculate stats
        total_input = sum(r['input_tokens'] for r in records)
        total_output = sum(r['output_tokens'] for r in records)
        total_tokens = total_input + total_output
        total_cost = sum(r['cost_usd'] for r in records)
        
        # By model breakdown
        by_model = {}
        for record in records:
            model = record['model']
            if model not in by_model:
                by_model[model] = {
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'total_tokens': 0,
                    'cost_usd': 0.0,
                    'calls': 0,
                }
            by_model[model]['input_tokens'] += record['input_tokens']
            by_model[model]['output_tokens'] += record['output_tokens']
            by_model[model]['total_tokens'] += record['input_tokens'] + record['output_tokens']
            by_model[model]['cost_usd'] += record['cost_usd']
            by_model[model]['calls'] += 1
        
        # Daily breakdown
        daily = {}
        for record in records:
            date = record['timestamp'][:10]  # YYYY-MM-DD
            if date not in daily:
                daily[date] = {
                    'date': date,
                    'tokens': 0,
                    'cost_usd': 0.0,
                    'calls': 0,
                }
            daily[date]['tokens'] += record['input_tokens'] + record['output_tokens']
            daily[date]['cost_usd'] += record['cost_usd']
            daily[date]['calls'] += 1
        
        now = datetime.now(timezone.utc)
        if period == 'today':
            start_date = now.strftime('%Y-%m-%d')
            end_date = start_date
        elif period == 'week':
            start_date = (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
        elif period == 'month':
            start_date = now.replace(day=1).strftime('%Y-%m-%d')
            end_date = now.strftime('%Y-%m-%d')
        else:
            start_date = now.strftime('%Y-%m-%d')
            end_date = start_date
        
        stats = UsageStats(
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_tokens=total_tokens,
            input_tokens=total_input,
            output_tokens=total_output,
            total_cost_usd=round(total_cost, 6),
            calls_count=len(records),
            by_model=by_model,
            daily_breakdown=list(daily.values()),
        )
        
        self._set_cache(cache_key, stats)
        return stats
    
    def get_cost(self, period: str = 'today') -> float:
        """Get total cost for a period."""
        usage = self.get_usage(period)
        return usage.total_cost_usd
    
    def get_remaining_credit(self) -> BudgetStatus:
        """Get remaining credit and budget status."""
        # Get all-time usage
        all_usage = self.get_usage('all')
        total_used = all_usage.total_tokens
        
        # Test budget (1M tokens)
        test_remaining = max(0, TEST_BUDGET_TOKENS - total_used)
        test_pct = (total_used / TEST_BUDGET_TOKENS) * 100 if TEST_BUDGET_TOKENS > 0 else 0
        
        # Welcome credit (70M tokens)
        welcome_remaining = max(0, WELCOME_CREDIT_TOKENS - total_used)
        
        # Project exhaustion
        # Calculate daily average from last 7 days
        week_usage = self.get_usage('week')
        daily_avg = week_usage.total_tokens / 7 if week_usage.total_tokens > 0 else 0
        
        if daily_avg > 0:
            projected_days = int(welcome_remaining / daily_avg)
        else:
            projected_days = None
        
        # Alert level
        if test_pct >= CRITICAL_THRESHOLD * 100:
            alert_level = 'critical'
        elif test_pct >= WARN_THRESHOLD * 100:
            alert_level = 'warn'
        else:
            alert_level = 'ok'
        
        return BudgetStatus(
            test_budget_tokens=TEST_BUDGET_TOKENS,
            test_budget_used=total_used,
            test_budget_remaining=test_remaining,
            test_budget_pct=round(test_pct, 2),
            welcome_credit_total=WELCOME_CREDIT_TOKENS,
            welcome_credit_used=total_used,
            welcome_credit_remaining=welcome_remaining,
            projected_exhaustion_days=projected_days,
            alert_level=alert_level,
        )
    
    def project_monthly(self) -> Dict[str, Any]:
        """Project monthly cost based on current usage."""
        # Get last 7 days average
        week_usage = self.get_usage('week')
        daily_avg_cost = week_usage.total_cost_usd / 7 if week_usage.total_cost_usd > 0 else 0
        daily_avg_tokens = week_usage.total_tokens / 7 if week_usage.total_tokens > 0 else 0
        
        # Project to 30 days
        projected_monthly_cost = daily_avg_cost * 30
        projected_monthly_tokens = int(daily_avg_tokens * 30)
        
        # Days until test budget exhausted
        budget = self.get_remaining_credit()
        if daily_avg_tokens > 0:
            days_until_test_exhausted = int(budget.test_budget_remaining / daily_avg_tokens)
            days_until_welcome_exhausted = int(budget.welcome_credit_remaining / daily_avg_tokens)
        else:
            days_until_test_exhausted = None
            days_until_welcome_exhausted = None
        
        return {
            'daily_average_cost_usd': round(daily_avg_cost, 6),
            'daily_average_tokens': int(daily_avg_tokens),
            'projected_monthly_cost_usd': round(projected_monthly_cost, 2),
            'projected_monthly_tokens': projected_monthly_tokens,
            'days_until_test_budget_exhausted': days_until_test_exhausted,
            'days_until_welcome_credit_exhausted': days_until_welcome_exhausted,
        }
    
    def export_json(self, period: str = 'today', output_path: Optional[Path] = None) -> str:
        """Export usage data as JSON."""
        usage = self.get_usage(period)
        budget = self.get_remaining_credit()
        projection = self.project_monthly()
        
        data = {
            'period': usage.period,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'usage': asdict(usage),
            'budget': asdict(budget),
            'projection': projection,
        }
        
        json_str = json.dumps(data, indent=2)
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(json_str)
        
        return json_str
    
    def export_csv(self, period: str = 'today', output_path: Optional[Path] = None) -> str:
        """Export usage data as CSV."""
        usage = self.get_usage(period)
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Summary
        writer.writerow(['Period', usage.period])
        writer.writerow(['Start Date', usage.start_date])
        writer.writerow(['End Date', usage.end_date])
        writer.writerow(['Total Tokens', usage.total_tokens])
        writer.writerow(['Input Tokens', usage.input_tokens])
        writer.writerow(['Output Tokens', usage.output_tokens])
        writer.writerow(['Total Cost USD', f"{usage.total_cost_usd:.6f}"])
        writer.writerow(['Total Calls', usage.calls_count])
        writer.writerow([])
        
        # By model
        writer.writerow(['Model', 'Input Tokens', 'Output Tokens', 'Total Tokens', 'Cost USD', 'Calls'])
        for model, stats in sorted(usage.by_model.items(), key=lambda x: x[1]['cost_usd'], reverse=True):
            writer.writerow([
                model,
                stats['input_tokens'],
                stats['output_tokens'],
                stats['total_tokens'],
                f"{stats['cost_usd']:.6f}",
                stats['calls'],
            ])
        
        csv_str = output.getvalue()
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(csv_str)
        
        return csv_str
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Get cached result if not expired."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return data
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Cache result."""
        self._cache[key] = (data, time.time())
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()


# CLI helper
def main():
    """CLI entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='DashScope Cost Monitor')
    parser.add_argument('--period', default='today', 
                       choices=['today', 'yesterday', 'week', 'month', 'all'])
    parser.add_argument('--model', help='Filter by model name')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--csv', action='store_true', help='Output as CSV')
    parser.add_argument('--budget', action='store_true', help='Show budget status')
    parser.add_argument('--project', action='store_true', help='Show projections')
    
    args = parser.parse_args()
    
    monitor = DashScopeMonitor()
    
    if args.budget:
        budget = monitor.get_remaining_credit()
        print(f"Test Budget: {budget.test_budget_used:,} / {budget.test_budget_tokens:,} tokens ({budget.test_budget_pct}%)")
        print(f"Remaining: {budget.test_budget_remaining:,} tokens")
        print(f"Alert Level: {budget.alert_level.upper()}")
        print(f"\nWelcome Credit: {budget.welcome_credit_used:,} / {budget.welcome_credit_total:,} tokens")
        print(f"Remaining: {budget.welcome_credit_remaining:,} tokens")
        if budget.projected_exhaustion_days:
            print(f"Projected exhaustion: {budget.projected_exhaustion_days} days")
        return
    
    if args.project:
        proj = monitor.project_monthly()
        print(f"Daily Average: ${proj['daily_average_cost_usd']:.6f} ({proj['daily_average_tokens']:,} tokens)")
        print(f"Projected Monthly: ${proj['projected_monthly_cost_usd']:.2f} ({proj['projected_monthly_tokens']:,} tokens)")
        if proj['days_until_test_budget_exhausted']:
            print(f"Days until test budget exhausted: {proj['days_until_test_budget_exhausted']}")
        if proj['days_until_welcome_credit_exhausted']:
            print(f"Days until welcome credit exhausted: {proj['days_until_welcome_credit_exhausted']}")
        return
    
    if args.json:
        print(monitor.export_json(args.period))
    elif args.csv:
        print(monitor.export_csv(args.period))
    else:
        usage = monitor.get_usage(args.period, args.model)
        print(f"Period: {usage.period} ({usage.start_date} to {usage.end_date})")
        print(f"Total Tokens: {usage.total_tokens:,} (Input: {usage.input_tokens:,}, Output: {usage.output_tokens:,})")
        print(f"Total Cost: ${usage.total_cost_usd:.6f}")
        print(f"Total Calls: {usage.calls_count}")
        print("\nBy Model:")
        for model, stats in sorted(usage.by_model.items(), key=lambda x: x[1]['cost_usd'], reverse=True):
            print(f"  {model}: {stats['total_tokens']:,} tokens, ${stats['cost_usd']:.6f} ({stats['calls']} calls)")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
