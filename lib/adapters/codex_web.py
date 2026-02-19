"""
Codex Web Adapter — OpenAI Codex via browser automation

This adapter extends the existing OpenAIAdapter to work with Codex's web interface.
It handles navigation to Codex-specific UI, code generation workflows, and result extraction.

Usage:
    python3 codex_web.py --task "Write a function to..." --type coding
    python3 codex_web.py --help
"""

import sys
import time
import logging
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.adapters.openai_web import OpenAIAdapter
from lib.utils.humanizer import think, read_pause

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
log = logging.getLogger(__name__)

# Codex-specific selectors (may need updates as UI changes)
CODEX_SELECTORS = {
    # Codex web UI may have different elements than ChatGPT
    'editor': '#codex-input, #prompt-textarea, div[role="textbox"][aria-label*="message"]',
    'response': '.codex-response, .assistant-message, [data-testid="codex-output"]',
    'code_block': 'pre code, .code-block code',
    'apply_button': 'button[data-testid="apply-changes"], button:contains("Apply")',
    'run_button': 'button[data-testid="run-code"], button:contains("Run")',
}

# Task type prompts for better context
TASK_TYPE_PROMPTS = {
    'coding': "Generate production-ready code. Include error handling and edge cases.",
    'refactor': "Refactor this code following best practices. Maintain behavior, improve structure.",
    'test': "Write comprehensive unit tests. Cover happy path, edge cases, and error conditions.",
    'debug': "Analyze this error and provide a fix. Explain root cause briefly.",
    'feature': "Implement this feature following existing patterns. Include tests and documentation.",
}


class CodexWebAdapter(OpenAIAdapter):
    """Codex-specific web adapter with enhanced code workflows."""
    
    def __init__(self):
        super().__init__()
        self.selectors = CODEX_SELECTORS
    
    def navigate_to_codex(self):
        """Navigate to Codex web interface."""
        if not self.driver:
            raise RuntimeError("Adapter not started")
        
        # Codex may be at a different URL than ChatGPT
        # For now, assume same session works
        self.driver.get("https://chat.openai.com")
        time.sleep(3)
        log.info("Navigated to OpenAI chat (Codex session)")
    
    def send_task(self, prompt: str, task_type: str = "coding") -> str:
        """Send a coding task with appropriate context."""
        if not self.driver:
            raise RuntimeError("Adapter not started")
        
        # Enhance prompt with task-type context
        context = TASK_TYPE_PROMPTS.get(task_type, "")
        enhanced_prompt = f"{context}\n\nTask: {prompt}"
        
        # Use parent class ask method (handles humanization)
        return self.ask(enhanced_prompt)
    
    def extract_code(self, response: str) -> str:
        """Extract code blocks from response."""
        import re
        
        # Find markdown code blocks
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
        
        if code_blocks:
            return '\n\n'.join(code_blocks)
        
        # If no code blocks, return full response
        return response
    
    def apply_changes(self, code: str, target_file: str = None):
        """Apply generated code to file system (with safety checks)."""
        if target_file:
            log.info(f"Would apply code to {target_file}")
            # In production: write to file with backup
            # For safety: require explicit confirmation
        else:
            log.info("Code generated, awaiting target file specification")
        
        return True


def main():
    parser = argparse.ArgumentParser(description="Codex Web Adapter")
    parser.add_argument("--task", required=True, help="Task description")
    parser.add_argument("--type", default="coding", 
                       choices=["coding", "refactor", "test", "debug", "feature"])
    parser.add_argument("--output", "-o", help="Output file for generated code")
    parser.add_argument("--headless", action="store_true", default=True,
                       help="Run browser in headless mode")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    adapter = CodexWebAdapter()
    
    try:
        # Start browser
        log.info("Starting Codex web adapter...")
        if not adapter.start(headless=args.headless):
            log.error("Failed to start adapter (not logged in?)")
            sys.exit(1)
        
        # Send task
        log.info(f"Sending {args.type} task to Codex...")
        response = adapter.send_task(args.task, task_type=args.type)
        
        if not response:
            log.error("No response from Codex")
            sys.exit(1)
        
        # Extract and output code
        code = adapter.extract_code(response)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(code)
            log.info(f"Code written to {args.output}")
        else:
            print(code)
        
        log.info("Task completed successfully")
        
    except Exception as e:
        log.error(f"Task failed: {e}")
        sys.exit(1)
    
    finally:
        adapter.stop()


if __name__ == "__main__":
    main()
