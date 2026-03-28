"""
Grading Logic
=============

Evaluation grading with priority chain:
exact_substring > forbidden_strings > expected_tools > expected_strings
"""

from evals import TestCase


def check_strings_in_response(response: str, expected: list[str]) -> list[str]:
    """Check which expected strings are missing (case-insensitive)."""
    response_lower = response.lower()
    return [v for v in expected if v.lower() not in response_lower]


def evaluate_response(
    test_case: TestCase,
    response: str,
    tool_calls: list[str],
) -> dict:
    """Evaluate a response against a test case using priority checks."""
    result: dict = {}

    # 1. Exact substring (highest priority, deterministic)
    if test_case.exact_substring:
        if test_case.exact_substring not in response:
            result["status"] = "FAIL"
            result["reason"] = f"exact substring missing: {test_case.exact_substring[:80]}..."
            return result

    # 2. Forbidden strings
    if test_case.forbidden_strings:
        response_lower = response.lower()
        found = [f for f in test_case.forbidden_strings if f.lower() in response_lower]
        if found:
            result["status"] = "FAIL"
            result["reason"] = f"forbidden strings found: {', '.join(found)}"
            return result

    # 3. Tool verification
    if test_case.expected_tools:
        missing = [t for t in test_case.expected_tools if t not in tool_calls]
        if missing:
            result["status"] = "FAIL"
            result["reason"] = f"expected tools not called: {', '.join(missing)}"
            return result

    # 4. String matching
    if test_case.expected_strings:
        missing = check_strings_in_response(response, test_case.expected_strings)
        if missing:
            result["status"] = "FAIL"
            result["reason"] = f"expected strings missing: {', '.join(missing)}"
            return result

    result["status"] = "PASS"
    return result
