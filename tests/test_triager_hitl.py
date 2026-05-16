"""Triager HITL wiring tests.

Verify that destructive GithubTools ops are gated behind agno's HITL
requires_confirmation_tools mechanism (commit 3 of slack-hitl-coda PR).
"""

import os

# Set GITHUB_ACCESS_TOKEN before importing triager — its module-load-time
# GithubTools() construction requires the token. Token value is irrelevant
# for kwargs-only assertions (no network calls happen).
os.environ.setdefault("GITHUB_ACCESS_TOKEN", "test-token-no-network")

from coda.agents.triager import triager  # noqa: E402

DESTRUCTIVE_OPS = {
    "close_issue",
    "comment_on_issue",
    "label_issue",
    "create_issue",
    "reopen_issue",
    "assign_issue",
    "edit_issue",
}


def _get_github_tools():
    """Find the GithubTools toolkit in triager.tools."""
    for tool in triager.tools:  # type: ignore[union-attr]
        if tool.__class__.__name__ == "GithubTools":
            return tool
    raise AssertionError("GithubTools not found on triager")


def test_triager_github_tools_has_requires_confirmation_tools():
    """All 7 public-write GithubTools ops are flagged for HITL confirmation."""
    github = _get_github_tools()
    confirmed = set(github.requires_confirmation_tools or [])
    assert confirmed == DESTRUCTIVE_OPS, f"Expected {DESTRUCTIVE_OPS}, got {confirmed}"


def test_triager_github_read_ops_not_gated():
    """Read-only ops (list_issues, get_issue, search_*) are NOT gated."""
    github = _get_github_tools()
    confirmed = set(github.requires_confirmation_tools or [])
    read_ops = {
        "list_issues",
        "get_issue",
        "list_issue_comments",
        "search_issues_and_prs",
        "search_code",
    }
    assert confirmed.isdisjoint(read_ops), f"Read ops should not be gated: {confirmed & read_ops}"
