"""
Eval Runner
===========

Run Coda evaluation test cases.

Usage:
    python -m evals.run_evals
    python -m evals.run_evals --category security
    python -m evals.run_evals --verbose
"""

from __future__ import annotations

import argparse
import time

from evals import TestCase
from evals.grader import evaluate_response
from evals.test_cases import TEST_CASES


def _extract_tool_calls(run_result) -> list[str]:  # type: ignore[no-untyped-def]
    """Extract tool names from a run result (including nested member responses)."""
    tool_calls: list[str] = []
    for msg in getattr(run_result, "messages", None) or []:
        # Tool call requests (dict or object format depending on provider)
        for tc in getattr(msg, "tool_calls", None) or []:
            if isinstance(tc, dict):
                name = (tc.get("function") or {}).get("name")
            else:
                fn = getattr(tc, "function", None)
                name = getattr(fn, "name", None) if fn else None
            if name:
                tool_calls.append(name)
        # Tool response messages carry the tool name directly
        tool_name = getattr(msg, "tool_name", None)
        if tool_name:
            tool_calls.append(tool_name)
    # Check member responses for delegated tool calls (Team runs)
    for member_resp in getattr(run_result, "member_responses", None) or []:
        tool_calls.extend(_extract_tool_calls(member_resp))
    return tool_calls


def run_single_eval(test_case: TestCase, agent, verbose: bool = False) -> dict:  # type: ignore[no-untyped-def]
    """Run a single test case and return the result."""
    start = time.time()
    try:
        run_result = agent.run(test_case.question)
        response = run_result.content or ""
        tool_calls = _extract_tool_calls(run_result)
        duration = time.time() - start

        eval_result = evaluate_response(test_case, response, tool_calls)
        eval_result["question"] = test_case.question
        eval_result["category"] = test_case.category
        eval_result["duration"] = round(duration, 2)
        eval_result["tool_calls"] = tool_calls

        if verbose:
            eval_result["response_preview"] = response[:200]

        return eval_result

    except Exception as e:
        return {
            "question": test_case.question,
            "category": test_case.category,
            "status": "ERROR",
            "reason": str(e),
            "duration": round(time.time() - start, 2),
        }


def run_evals(category: str | None = None, verbose: bool = False) -> None:
    """Run all eval test cases and display results."""
    from coda.team import coda

    tests = TEST_CASES
    if category:
        tests = [tc for tc in tests if tc.category == category]

    if not tests:
        print(f"No test cases found for category: {category}")
        return

    print(f"\nRunning {len(tests)} eval(s)...\n")

    results: list[dict] = []
    total_start = time.time()

    for i, test_case in enumerate(tests, 1):
        print(f"  [{i}/{len(tests)}] {test_case.category}: {test_case.question[:60]}...")
        result = run_single_eval(test_case, coda, verbose)
        results.append(result)

        status = result["status"]
        icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "ERR "
        print(f"         {icon} ({result['duration']}s)")

        if verbose and result.get("reason"):
            print(f"         Reason: {result['reason']}")

    # Summary
    total_duration = round(time.time() - total_start, 2)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed, {errors} errors ({total_duration}s)")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Coda evals")
    parser.add_argument("--category", type=str, help="Filter by category")
    parser.add_argument("--verbose", action="store_true", help="Show details")
    args = parser.parse_args()
    run_evals(category=args.category, verbose=args.verbose)
