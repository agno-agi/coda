"""
Coda Evaluations
================

Eval framework for testing Coda's capabilities

Usage:
    python -m evals.run
    python -m evals.run --category security
    python -m evals.run --verbose
"""

from agno.models.openai import OpenAIResponses

JUDGE_MODEL = OpenAIResponses(id="gpt-5.4")

CATEGORIES: dict[str, dict] = {
    "security": {"type": "judge_binary", "module": "evals.cases.security"},
    "routing": {"type": "reliability", "module": "evals.cases.routing"},
    "exploration": {"type": "accuracy", "module": "evals.cases.exploration"},
    "synthesis": {"type": "judge_numeric", "module": "evals.cases.synthesis"},
    "refusal": {"type": "judge_binary", "module": "evals.cases.refusal"},
}
