"""
Exploration Cases
=================

Agent finds correct code, files, and structures when answering questions.
Tests against Coda's own codebase.
Eval type: AccuracyEval (1-10 score)
"""

CASES: list[dict] = [
    {
        "input": "What repos are available?",
        "expected_output": "Should list the repositories cloned in the /repos directory with their names and current branches.",
        "guidelines": "Accept any format as long as repo names are present. The agent may use list_repos.",
    },
    {
        "input": "How is the Coda team structured?",
        "expected_output": (
            "Coda is a Team in coordinate mode with a leader and two member agents: "
            "Explorer (read-only code search, PR review, issue triage) and "
            "Coder (writes code in worktrees, opens PRs). The leader triages "
            "and delegates."
        ),
        "guidelines": "Must mention both Explorer and Coder with their roles. Coordinate mode is a plus.",
    },
    {
        "input": "Where is the database connection configured?",
        "expected_output": (
            "db/url.py builds the connection URL from environment variables. "
            "db/session.py creates PostgresDb and Knowledge instances. "
            "coda/settings.py imports get_postgres_db for shared use."
        ),
        "guidelines": "Must mention db/url.py or db/session.py. Mentioning settings.py is a bonus.",
    },
    {
        "input": "What tools does the Explorer agent have?",
        "expected_output": (
            "CodingTools (read-only: read_file, grep, find, ls), "
            "GitTools (read_only=True), "
            "GithubTools (PR review, issues, branches, search_code), "
            "ReasoningTools (think)."
        ),
        "guidelines": "Must list the four tool groups. Must note CodingTools is read-only (no write/edit/shell).",
    },
    {
        "input": "What git operations can the Coder do that Explorer cannot?",
        "expected_output": (
            "Coder has full GitTools which includes create_worktree, remove_worktree, "
            "and git_push. Explorer has GitTools with read_only=True which excludes these three."
        ),
        "guidelines": "Must identify at least create_worktree and git_push as Coder-only operations.",
    },
    {
        "input": "Where are the eval test cases defined?",
        "expected_output": (
            "Eval test cases are in evals/test_cases.py. It defines SECURITY_CASES "
            "and TOOL_ROUTING_CASES, plus SECURITY_CRITERIA for the judge."
        ),
        "guidelines": "Must point to evals/test_cases.py or the evals/cases/ directory.",
    },
    {
        "input": "What scheduled tasks does Coda have?",
        "expected_output": (
            "Three scheduled tasks: tasks/sync_repos.py syncs repositories every 5 minutes, "
            "tasks/review_issues.py triggers issue triage daily at 4 AM UTC via the Triager agent, "
            "and tasks/daily_digest.py posts a daily activity digest at 8 AM UTC."
        ),
        "guidelines": "Must mention all three tasks with approximate schedules.",
    },
    {
        "input": "How does Coda handle worktree lifecycle?",
        "expected_output": (
            "coda/tools/git.py GitTools class manages worktrees. create_worktree creates "
            "at worktrees/<task_name> on a coda/<task_name> branch. remove_worktree cleans "
            "up the worktree and deletes the local branch. git_push only allows coda/* branches."
        ),
        "guidelines": "Must mention create_worktree, the coda/ branch prefix, and the safety constraint on git_push.",
    },
]
