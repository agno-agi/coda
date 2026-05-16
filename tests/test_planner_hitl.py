"""Planner HITL wiring tests (commit 7)."""

import os

# Planner's GithubTools() construction at module import requires GITHUB_ACCESS_TOKEN.
# Token value is irrelevant for kwargs-only assertions (no network calls happen).
os.environ.setdefault("GITHUB_ACCESS_TOKEN", "test-token-no-network")

from coda.agents.planner import planner  # noqa: E402


def _get_github_tools():
    """Find the GithubTools toolkit in planner.tools."""
    for tool in planner.tools:  # type: ignore[union-attr]
        if tool.__class__.__name__ == "GithubTools":
            return tool
    raise AssertionError("GithubTools not found on planner")


def test_planner_gates_create_issue():
    """create_issue is gated for multi-row HITL approval."""
    github = _get_github_tools()
    assert "create_issue" in (github.requires_confirmation_tools or [])


def test_planner_read_ops_not_gated():
    """Read-only ops (list_issues, get_issue, search_*) stay un-gated."""
    github = _get_github_tools()
    confirmed = set(github.requires_confirmation_tools or [])
    read_ops = {
        "list_issues",
        "get_issue",
        "list_issue_comments",
        "search_issues_and_prs",
        "get_pull_requests",
        "search_code",
    }
    assert confirmed.isdisjoint(read_ops), f"Read ops should not be gated: {confirmed & read_ops}"
