"""
Eval Runner
===========

Run Coda evaluation test cases using Agno evals.

Usage:
    python -m evals.run_evals
    python -m evals.run_evals --category security
    python -m evals.run_evals --verbose
"""

from __future__ import annotations

import argparse
import time

from agno.eval.agent_as_judge import AgentAsJudgeEval
from agno.eval.reliability import ReliabilityEval
from agno.models.openai import OpenAIChat

from evals.test_cases import SECURITY_CASES, SECURITY_CRITERIA, TOOL_ROUTING_CASES


def run_security_evals(verbose: bool = False) -> list[dict]:
    """Run security evals using AgentAsJudgeEval (binary)."""
    from coda.team import coda

    judge = AgentAsJudgeEval(
        name="Coda Security",
        criteria=SECURITY_CRITERIA,
        scoring_strategy="binary",
        model=OpenAIChat(id="gpt-4o"),
    )

    results: list[dict] = []
    for i, case in enumerate(SECURITY_CASES, 1):
        question = case["input"]
        print(f"  [{i}/{len(SECURITY_CASES)}] security: {question[:60]}...")
        start = time.time()
        try:
            run_result = coda.run(question)
            response = run_result.content or ""
            duration = round(time.time() - start, 2)

            eval_result = judge.run(input=question, output=response)
            passed = eval_result is not None and eval_result.pass_rate == 1.0

            result = {
                "question": question,
                "category": "security",
                "status": "PASS" if passed else "FAIL",
                "duration": duration,
            }
            if not passed and eval_result and eval_result.results:
                result["reason"] = eval_result.results[0].reason
            if verbose:
                result["response_preview"] = response[:200]
        except Exception as e:
            result = {
                "question": question,
                "category": "security",
                "status": "ERROR",
                "reason": str(e),
                "duration": round(time.time() - start, 2),
            }
        results.append(result)
        icon = "PASS" if result["status"] == "PASS" else "FAIL" if result["status"] == "FAIL" else "ERR "
        print(f"         {icon} ({result['duration']}s)")
        if verbose and result.get("reason"):
            print(f"         Reason: {result['reason']}")
    return results


def run_tool_routing_evals(verbose: bool = False) -> list[dict]:
    """Run tool routing evals using ReliabilityEval."""
    from coda.team import coda

    results: list[dict] = []
    for i, case in enumerate(TOOL_ROUTING_CASES, 1):
        question = case["input"][0]
        expected_tools = case["expected_tools"]
        print(f"  [{i}/{len(TOOL_ROUTING_CASES)}] tool_routing: {question[:60]}...")
        start = time.time()
        try:
            run_result = coda.run(question)
            duration = round(time.time() - start, 2)

            eval_result = ReliabilityEval(
                name=f"Routing: {question[:40]}",
                team_response=run_result,
                expected_tool_calls=expected_tools,
            ).run()

            passed = eval_result is not None and eval_result.eval_status == "PASSED"
            result: dict = {
                "question": question,
                "category": "tool_routing",
                "status": "PASS" if passed else "FAIL",
                "duration": duration,
            }
            if not passed and eval_result:
                result["reason"] = f"unexpected tools: {eval_result.failed_tool_calls}"
        except Exception as e:
            result = {
                "question": question,
                "category": "tool_routing",
                "status": "ERROR",
                "reason": str(e),
                "duration": round(time.time() - start, 2),
            }
        results.append(result)
        icon = "PASS" if result["status"] == "PASS" else "FAIL" if result["status"] == "FAIL" else "ERR "
        print(f"         {icon} ({result['duration']}s)")
        if verbose and result.get("reason"):
            print(f"         Reason: {result['reason']}")
    return results


CATEGORY_RUNNERS: dict[str, object] = {
    "security": run_security_evals,
    "location": run_tool_routing_evals,
    "flow_tracing": run_tool_routing_evals,
    "pr_review": run_tool_routing_evals,
}


def run_evals(category: str | None = None, verbose: bool = False) -> None:
    """Run all eval test cases and display results."""
    all_results: list[dict] = []
    total_start = time.time()

    if category == "security" or category is None:
        print(f"\nRunning {len(SECURITY_CASES)} security eval(s)...\n")
        all_results.extend(run_security_evals(verbose))

    if category in ("location", "flow_tracing", "pr_review", "tool_routing", None):
        print(f"\nRunning {len(TOOL_ROUTING_CASES)} tool routing eval(s)...\n")
        all_results.extend(run_tool_routing_evals(verbose))

    if not all_results:
        print(f"No test cases found for category: {category}")
        return

    # Summary
    total_duration = round(time.time() - total_start, 2)
    passed = sum(1 for r in all_results if r["status"] == "PASS")
    failed = sum(1 for r in all_results if r["status"] == "FAIL")
    errors = sum(1 for r in all_results if r["status"] == "ERROR")

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed, {errors} errors ({total_duration}s)")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Coda evals")
    parser.add_argument("--category", type=str, help="Filter by category")
    parser.add_argument("--verbose", action="store_true", help="Show details")
    args = parser.parse_args()
    run_evals(category=args.category, verbose=args.verbose)
