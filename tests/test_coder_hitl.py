"""Coder HITL wiring tests (commit 6)."""

import os

# Coder's GithubTools() construction at module import requires GITHUB_ACCESS_TOKEN.
# Token value is irrelevant for kwargs-only assertions (no network calls happen).
os.environ.setdefault("GITHUB_ACCESS_TOKEN", "test-token-no-network")

from coda.agents.coder import coder  # noqa: E402


def _get_tool(class_name: str):
    """Find a tool by class name in coder.tools."""
    for tool in coder.tools:
        if tool.__class__.__name__ == class_name:
            return tool
    raise AssertionError(f"{class_name} not found on coder")


def test_coder_git_tools_gates_git_push():
    """git_push is gated behind HITL confirmation."""
    git = _get_tool("GitTools")
    assert "git_push" in (git.requires_confirmation_tools or [])


def test_coder_github_tools_gates_create_pr():
    """create_pull_request is gated behind HITL confirmation."""
    github = _get_tool("GithubTools")
    assert "create_pull_request" in (github.requires_confirmation_tools or [])


def test_coder_local_only_git_ops_not_gated():
    """Local-only Git ops (create_worktree, remove_worktree) stay free for Coder."""
    git = _get_tool("GitTools")
    confirmed = set(git.requires_confirmation_tools or [])
    local_ops = {"create_worktree", "remove_worktree"}
    assert confirmed.isdisjoint(local_ops), (
        f"Local ops should not be gated: {confirmed & local_ops}"
    )
