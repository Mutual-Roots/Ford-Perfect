"""
Codex Router — Intelligent tool selection for coding tasks

This router decides when to use Codex vs. Qwen-Coder vs. Claude Code
based on task complexity, cost considerations, and safety requirements.

Decision Matrix:
- Simple tasks (<5 files): Qwen-Coder-Plus (fast, free)
- Medium tasks (5-10 files): Web Codex (better reasoning, free)
- Complex tasks (>10 files): Web Codex + Human Review
- Time-critical: Qwen-Coder-Plus
- Production code: Web Codex + Mandatory Review

Usage:
    python3 codex_router.py --task "..." --analyze
    python3 codex_router.py --recommend --type refactor
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TaskComplexity:
    """Task complexity levels."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    CRITICAL = "critical"


class ToolRecommendation:
    """Recommended tool for a task."""
    QWEN_CODER = "qwen-coder-plus"
    WEB_CODEX = "web-codex"
    CLI_CODEX = "cli-codex"  # Requires approval
    HUMAN_REVIEW = "human-review-required"


# Cost estimates (USD)
COST_ESTIMATES = {
    "qwen-coder-plus": 0.0004,  # per 1K tokens (effectively €0 for us)
    "web-codex": 0.0,  # Free with existing session
    "cli-codex-o3": 0.02,  # Per request estimate
    "cli-codex-o4": 0.10,  # Per request estimate
}


class CodexRouter:
    """Routes coding tasks to appropriate tool."""
    
    def __init__(self):
        self.complexity_thresholds = {
            "simple": {"max_files": 3, "max_lines": 50},
            "medium": {"max_files": 10, "max_lines": 200},
            "complex": {"max_files": 20, "max_lines": 500},
        }
    
    def analyze_task(self, task: str, context: Optional[Dict] = None) -> Dict:
        """
        Analyze task and return recommendation.
        
        Args:
            task: Task description
            context: Optional context (file_count, lines_of_code, is_production, etc.)
        
        Returns:
            Dictionary with recommendation and rationale
        """
        context = context or {}
        
        # Extract task type from keywords
        task_type = self._detect_task_type(task)
        
        # Estimate complexity
        complexity = self._estimate_complexity(task, context)
        
        # Check safety requirements
        requires_review = self._check_safety_requirements(task, context)
        
        # Make recommendation
        recommendation = self._recommend_tool(complexity, task_type, requires_review)
        
        # Calculate estimated cost
        cost_estimate = self._estimate_cost(recommendation, task)
        
        return {
            "task_type": task_type,
            "complexity": complexity,
            "requires_review": requires_review,
            "recommended_tool": recommendation,
            "cost_estimate_usd": cost_estimate,
            "rationale": self._generate_rationale(recommendation, complexity, task_type),
        }
    
    def _detect_task_type(self, task: str) -> str:
        """Detect task type from description."""
        task_lower = task.lower()
        
        if any(kw in task_lower for kw in ["test", "spec", "assert"]):
            return "test"
        elif any(kw in task_lower for kw in ["refactor", "restructure", "clean up"]):
            return "refactor"
        elif any(kw in task_lower for kw in ["debug", "fix", "error", "bug"]):
            return "debug"
        elif any(kw in task_lower for kw in ["feature", "implement", "add", "new"]):
            return "feature"
        else:
            return "coding"
    
    def _estimate_complexity(self, task: str, context: Dict) -> str:
        """Estimate task complexity."""
        # Use context if provided
        file_count = context.get("file_count", 1)
        line_count = context.get("line_count", 50)
        
        # Check for complexity indicators in task
        complexity_indicators = [
            ("multiple files", 2),
            ("entire module", 2),
            ("refactor all", 3),
            ("complete rewrite", 3),
            ("integration", 2),
            ("migration", 3),
        ]
        
        score = 0
        for indicator, weight in complexity_indicators:
            if indicator in task.lower():
                score += weight
        
        # Adjust based on context
        if file_count > 10:
            score += 3
        elif file_count > 5:
            score += 2
        elif file_count > 3:
            score += 1
        
        if line_count > 500:
            score += 3
        elif line_count > 200:
            score += 2
        elif line_count > 100:
            score += 1
        
        # Classify
        if score >= 6:
            return TaskComplexity.CRITICAL
        elif score >= 4:
            return TaskComplexity.COMPLEX
        elif score >= 2:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.SIMPLE
    
    def _check_safety_requirements(self, task: str, context: Dict) -> bool:
        """Check if task requires human review."""
        # Production config changes always require review
        if context.get("touches_production", False):
            return True
        
        # Security-sensitive code
        security_keywords = ["auth", "password", "token", "secret", "api key", "encryption"]
        if any(kw in task.lower() for kw in security_keywords):
            return True
        
        # Large deletions
        if context.get("lines_to_delete", 0) > 50:
            return True
        
        # Database changes
        if any(kw in task.lower() for kw in ["database", "schema", "migration"]):
            return True
        
        return False
    
    def _recommend_tool(self, complexity: str, task_type: str, requires_review: bool) -> str:
        """Recommend tool based on analysis."""
        
        # Critical tasks always need human review
        if complexity == TaskComplexity.CRITICAL:
            return ToolRecommendation.WEB_CODEX + " + " + ToolRecommendation.HUMAN_REVIEW
        
        # Safety-sensitive tasks
        if requires_review:
            return ToolRecommendation.WEB_CODEX + " + " + ToolRecommendation.HUMAN_REVIEW
        
        # Complexity-based recommendations
        if complexity == TaskComplexity.SIMPLE:
            # Simple tasks: use Qwen for speed
            if task_type in ["debug", "test"]:
                return ToolRecommendation.QWEN_CODER
            else:
                return ToolRecommendation.WEB_CODEX
        
        elif complexity == TaskComplexity.MEDIUM:
            # Medium tasks: Web Codex for better reasoning
            return ToolRecommendation.WEB_CODEX
        
        elif complexity == TaskComplexity.COMPLEX:
            # Complex tasks: Web Codex with review
            return ToolRecommendation.WEB_CODEX + " + " + ToolRecommendation.HUMAN_REVIEW
        
        # Default
        return ToolRecommendation.WEB_CODEX
    
    def _estimate_cost(self, tool: str, task: str) -> float:
        """Estimate cost for task."""
        # Rough token estimate based on task length
        token_estimate = len(task.split()) * 1.5  # words to tokens
        
        if ToolRecommendation.QWEN_CODER in tool:
            return token_estimate * COST_ESTIMATES["qwen-coder-plus"] / 1000
        elif ToolRecommendation.WEB_CODEX in tool:
            return 0.0  # Free
        elif ToolRecommendation.CLI_CODEX in tool:
            return COST_ESTIMATES["cli-codex-o3"]  # Conservative estimate
        else:
            return 0.0
    
    def _generate_rationale(self, tool: str, complexity: str, task_type: str) -> str:
        """Generate human-readable rationale for recommendation."""
        rationales = {
            ToolRecommendation.QWEN_CODER: 
                f"Qwen-Coder recommended for {complexity} {task_type} task (fast, cost-effective)",
            ToolRecommendation.WEB_CODEX:
                f"Web Codex recommended for {complexity} {task_type} task (better reasoning, no API cost)",
        }
        
        base_rationale = rationales.get(tool.split(" + ")[0], "Using default tool")
        
        if " + " in tool:
            base_rationale += f" with {tool.split(' + ')[1]} due to safety/complexity"
        
        return base_rationale


def main():
    parser = argparse.ArgumentParser(description="Codex Router - Tool Selection")
    parser.add_argument("--task", help="Task description to analyze")
    parser.add_argument("--type", help="Task type override")
    parser.add_argument("--analyze", action="store_true", help="Analyze task and show recommendation")
    parser.add_argument("--recommend", action="store_true", help="Show general recommendations")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()
    
    router = CodexRouter()
    
    if args.analyze and args.task:
        result = router.analyze_task(args.task)
        
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Task Type: {result['task_type']}")
            print(f"Complexity: {result['complexity']}")
            print(f"Requires Review: {result['requires_review']}")
            print(f"Recommended Tool: {result['recommended_tool']}")
            print(f"Estimated Cost: ${result['cost_estimate_usd']:.6f}")
            print(f"Rationale: {result['rationale']}")
    
    elif args.recommend:
        # Show general recommendations
        recommendations = {
            "Simple refactors (<5 files)": "Qwen-Coder-Plus",
            "Write tests": "Web Codex",
            "Debug errors": "Qwen-Coder → Web Codex (escalate if needed)",
            "New features": "Web Codex + Git workflow",
            "Large refactors (>10 files)": "Web Codex + Mandatory Review",
            "Production code": "Web Codex + Mandatory Review",
        }
        
        if args.json:
            print(json.dumps(recommendations, indent=2))
        else:
            print("Tool Recommendations by Task Type:")
            print("=" * 50)
            for task, tool in recommendations.items():
                print(f"{task:30} → {tool}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
