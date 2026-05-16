"""GitTools HITL kwargs forwarding test (commit 5)."""

from coda.tools.git import GitTools


def test_git_tools_forwards_requires_confirmation_tools():
    """GitTools.__init__ must forward **kwargs so HITL flags reach Toolkit base."""
    gt = GitTools(read_only=False, requires_confirmation_tools=["git_push"])
    assert "git_push" in (gt.requires_confirmation_tools or [])


def test_git_tools_default_has_no_confirmation_tools():
    """Default GitTools (no kwarg) has no requires_confirmation_tools set."""
    gt = GitTools(read_only=False)
    assert not gt.requires_confirmation_tools
