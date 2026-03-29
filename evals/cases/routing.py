"""
Routing Cases
=============

Leader delegates to the right specialist and triggers the right tools.
Eval type: ReliabilityEval (expected tool calls)
"""

CASES: list[dict] = [
    {"input": "Where is the authentication middleware?", "expected_tools": ["grep"]},
    {"input": "What repos are available?", "expected_tools": ["list_repos"]},
    {"input": "Show me recent commits on main", "expected_tools": ["git_log"]},
    {"input": "Who last changed the payment module?", "expected_tools": ["git_blame"]},
    {"input": "What are the open PRs?", "expected_tools": ["get_pull_requests"]},
    {"input": "Add rate limiting to the API", "expected_tools": ["create_worktree"]},
    {"input": "Fix the bug in the auth service", "expected_tools": ["create_worktree"]},
    {"input": "Review PR #42 on coda", "expected_tools": ["get_pull_request"]},
]
