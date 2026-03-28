"""
Coda Evaluations
================

Eval framework for testing Coda's capabilities.
"""

from dataclasses import dataclass, field

CATEGORIES = [
    "location",
    "flow_tracing",
    "convention",
    "error_diagnosis",
    "impact_analysis",
    "pr_review",
    "code_contribution",
    "security",
]


@dataclass
class TestCase:
    """A single evaluation test case."""

    question: str
    expected_strings: list[str] = field(default_factory=list)
    expected_tools: list[str] = field(default_factory=list)
    category: str = ""
    exact_substring: str = ""
    forbidden_strings: list[str] = field(default_factory=list)
    quality_criteria: str = ""
