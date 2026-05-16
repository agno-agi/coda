"""Explorer HITL wiring tests (commit 8)."""

import os

# Explorer's GithubTools() construction at module import requires GITHUB_ACCESS_TOKEN.
# Token value is irrelevant for kwargs-only assertions (no network calls happen).
os.environ.setdefault("GITHUB_ACCESS_TOKEN", "test-token-no-network")

from coda.agents.explorer import explorer  # noqa: E402

WRITE_OPS = {"create_pull_request_comment", "comment_on_issue"}


def _get_github_tools():
    """Find the GithubTools toolkit in explorer.tools."""
    for tool in explorer.tools:  # type: ignore[union-attr]
        if tool.__class__.__name__ == "GithubTools":
            return tool
    raise AssertionError("GithubTools not found on explorer")


def test_explorer_gates_public_writes():
    """Both public-write ops are gated for HITL confirmation."""
    github = _get_github_tools()
    confirmed = set(github.requires_confirmation_tools or [])
    assert WRITE_OPS.issubset(confirmed), f"Expected {WRITE_OPS}, got {confirmed}"


def test_explorer_read_ops_not_gated():
    """Explorer's read-only ops stay un-gated."""
    github = _get_github_tools()
    confirmed = set(github.requires_confirmation_tools or [])
    read_ops = {
        "get_pull_request",
        "get_pull_requests",
        "get_pull_request_changes",
        "get_pull_request_comments",
        "get_pull_request_with_details",
        "get_issue",
        "list_issues",
        "list_issue_comments",
        "list_branches",
        "search_code",
    }
    assert confirmed.isdisjoint(read_ops), f"Read ops should not be gated: {confirmed & read_ops}"
