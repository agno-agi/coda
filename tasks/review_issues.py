"""
Scheduled Issue Triage
======================

Triggers Coda to review open GitHub issues for all configured repos.
Default: daily at 9 AM UTC on weekdays.

Register/update schedule:
    python -m tasks.review_issues
"""

from __future__ import annotations

from agno.scheduler import ScheduleManager

from db import get_postgres_db
from tasks.sync_repos import load_repos_config


def build_issue_review_prompt() -> str:
    """Build the prompt that tells Coda which repos to triage."""
    repos = load_repos_config()
    repo_names = [url.rstrip("/").split("/")[-1].removesuffix(".git") for r in repos if (url := r.get("url"))]
    if not repo_names:
        return "No repos configured in repos.yaml. Nothing to review."
    return (
        "Review open GitHub issues for these repos: "
        + ", ".join(repo_names)
        + ". For each repo: list the 10 most recent open issues, "
        "categorize them (bug, feature, question, etc), note any "
        "that look stale or duplicated, and summarize priorities. "
        "Post a summary to #coda-updates."
    )


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mgr = ScheduleManager(get_postgres_db())
    schedule = mgr.create(
        name="review-github-issues",
        cron="0 9 * * 1-5",  # 9 AM UTC, weekdays
        endpoint="/teams/coda/runs",
        payload={"message": build_issue_review_prompt()},
        timeout_seconds=1800,
        max_retries=1,
        description="Coda reviews open GitHub issues and posts triage summary",
        if_exists="update",
    )
    print(f"Schedule ready: {schedule.name} (next: {schedule.next_run_at})")
