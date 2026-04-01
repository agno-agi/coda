"""
Daily Issue Triage
==================

Fetches recent GitHub issues, classifies them (Major Bug, Low-Hanging Fruit,
Slop, Other), and posts a summary to Slack. Runs daily via scheduler.

Manual trigger:
    python -m tasks.review_issues

Register/update schedule:
    python -m tasks.review_issues --schedule
"""

from __future__ import annotations

import argparse
import logging
import re
from datetime import datetime, timedelta, timezone
from os import getenv
from typing import Literal

import httpx
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from pydantic import BaseModel, Field
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from tasks.sync_repos import load_repos_config

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
GITHUB_API = "https://api.github.com"
DEFAULT_SINCE_HOURS = 24


# ---------------------------------------------------------------------------
# 1. Fetch
# ---------------------------------------------------------------------------
def _parse_owner_repo(url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url.rstrip("/"))
    if not match or match.group(1) is None:
        raise ValueError(f"Cannot parse GitHub owner/repo from: {url}")
    return match.group(1)


def fetch_recent_issues(repo_url: str, since_hours: int = DEFAULT_SINCE_HOURS) -> list[dict]:
    """Fetch open issues created in the last N hours via GitHub API."""
    owner_repo = _parse_owner_repo(repo_url)
    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    token = getenv("GITHUB_ACCESS_TOKEN", "")

    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    issues: list[dict] = []
    page = 1

    with httpx.Client(timeout=30) as client:
        while True:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner_repo}/issues",
                headers=headers,
                params={
                    "state": "open",
                    "since": since,
                    "sort": "created",
                    "direction": "desc",
                    "per_page": 100,
                    "page": page,
                },
            )
            resp.raise_for_status()
            batch = resp.json()

            if not batch:
                break

            for item in batch:
                if "pull_request" in item:
                    continue
                issues.append(
                    {
                        "number": item["number"],
                        "title": item["title"],
                        "body": (item.get("body") or "")[:2000],
                        "labels": [label["name"] for label in item.get("labels", [])],
                        "url": item["html_url"],
                        "created_at": item["created_at"],
                        "user": item["user"]["login"],
                    }
                )

            if len(batch) < 100:
                break
            page += 1

    return issues


# ---------------------------------------------------------------------------
# 2. Classify
# ---------------------------------------------------------------------------
class IssueClassification(BaseModel):
    index: int = Field(description="Index of the issue in the input list")
    category: Literal["MAJOR_BUG", "LOW_HANGING_FRUIT", "SLOP", "OTHER"]
    summary: str = Field(description="One-line plain English summary explaining the actual problem or request")


class ClassificationResult(BaseModel):
    classifications: list[IssueClassification] = Field(description="Classification for each issue")


_classifier = Agent(
    name="Issue Classifier",
    model=OpenAIResponses(id="gpt-5.4"),
    instructions="""\
You triage GitHub issues for a busy open-source project. For each issue,
assign exactly one category and write a clear 1-line summary.

## Categories

MAJOR_BUG — Something is broken and users are affected:
- Runtime crashes, exceptions, tracebacks
- Data loss or corruption
- Security vulnerabilities
- Core functionality that stopped working (especially after a release)
- Regressions ("worked before, broken now")

LOW_HANGING_FRUIT — Quick wins a contributor could knock out fast:
- Typos, docs fixes, small config changes
- Clear bug with an obvious fix (e.g. missing null check)
- Good first issue for new contributors
- Small enhancements with well-defined scope

SLOP — AI-generated low-quality issues (common on popular repos):
- Vague "improve code quality" or "add better error handling" with no specifics
- Descriptions that read like ChatGPT output (generic, no real context)
- Suggestions that don't reference actual code or real problems
- "Refactor X for readability" with no concrete motivation
- Issues where the body is clearly auto-generated boilerplate

OTHER — Legitimate but not urgent:
- Feature requests with clear motivation
- Questions about usage
- Discussion / RFC / design proposals
- Enhancement requests that need design work

## Summary Guidelines

Write summaries that a maintainer can scan in 2 seconds:
- BAD: "Feature request to add a fintech/KYB compliance cookbook example demonstrating Strale API integrations."
- GOOD: "Wants a cookbook example for KYB/compliance verification using Strale API"
- BAD: "Bug report about workflow condition evaluation"
- GOOD: "Workflow else_steps never trigger even when condition evaluates to False"

Focus on WHAT is broken or wanted, not meta-description of the issue type.\
""",
    output_schema=ClassificationResult,
)


def classify_issues(issues: list[dict]) -> list[dict]:
    """Classify issues using an Agno agent with structured output."""
    if not issues:
        return []

    issues_text = ""
    for i, issue in enumerate(issues):
        labels = ", ".join(issue["labels"]) if issue["labels"] else "none"
        body = issue["body"] or "(no description)"
        issues_text += (
            f"--- Issue {i} ---\nTitle: {issue['title']}\nLabels: {labels}\nUser: {issue['user']}\nBody: {body}\n\n"
        )

    try:
        response = _classifier.run(f"Classify these GitHub issues:\n\n{issues_text}")
        result: ClassificationResult = response.content
        index_map = {c.index: c for c in result.classifications}
    except Exception:
        log.exception("Classification failed — marking all as OTHER")
        return [{**issue, "category": "OTHER", "summary": issue["title"]} for issue in issues]

    results = []
    for i, issue in enumerate(issues):
        c = index_map.get(i)
        if c:
            results.append({**issue, "category": c.category, "summary": c.summary})
        else:
            results.append({**issue, "category": "OTHER", "summary": issue["title"]})

    return results


# ---------------------------------------------------------------------------
# 3. Post to Slack
# ---------------------------------------------------------------------------
def _build_message(classified: list[dict], total_scanned: int, repo_name: str) -> str:
    """Build Slack mrkdwn message from classified issues."""
    major_bugs = [i for i in classified if i["category"] == "MAJOR_BUG"]
    low_hanging = [i for i in classified if i["category"] == "LOW_HANGING_FRUIT"]
    slop = [i for i in classified if i["category"] == "SLOP"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    header = f"*Coda Issue Tracker — {repo_name} — Daily Scan*"

    if not major_bugs and not low_hanging and not slop:
        return f":white_check_mark: {header}\nScanned {total_scanned} new issue(s) in the last 24h. Nothing flagged."

    lines = [f"{header}\n"]

    if major_bugs:
        lines.append(":red_circle: *Major Bugs*")
        for issue in major_bugs:
            lines.append(f"• <{issue['url']}|#{issue['number']} {issue['title']}>  —  _{issue['summary']}_")
        lines.append("")

    if low_hanging:
        lines.append(":large_green_circle: *Low-Hanging Fruit*")
        for issue in low_hanging:
            lines.append(f"• <{issue['url']}|#{issue['number']} {issue['title']}>  —  _{issue['summary']}_")
        lines.append("")

    if slop:
        lines.append(":wastebasket: *Likely Slop*")
        for issue in slop:
            lines.append(f"• <{issue['url']}|#{issue['number']} {issue['title']}>  —  _{issue['summary']}_")
        lines.append("")

    lines.append(f"———\nScanned {total_scanned} issue(s) | {now}")
    return "\n".join(lines)


def post_triage_to_slack(classified: list[dict], total_scanned: int, repo_name: str) -> None:
    """Send triage summary to Slack. Fails gracefully if not configured."""
    token = getenv("SLACK_TOKEN", "")
    channel = getenv("TRIAGE_CHANNEL", "")
    message = _build_message(classified, total_scanned, repo_name)

    if not token or not channel:
        log.warning("SLACK_TOKEN or TRIAGE_CHANNEL not set — printing to stdout instead")
        print(message)
        return

    try:
        client = WebClient(token=token)
        client.chat_postMessage(channel=channel, text=message, mrkdwn=True)
        log.info("Posted triage summary to Slack channel %s", channel)
    except SlackApiError as e:
        error = e.response.get("error", "unknown")
        if error == "channel_not_found":
            log.error(
                "Slack channel '%s' not found. Check TRIAGE_CHANNEL in your env. "
                "Use the channel ID (e.g. C0XXXXXXX), not the name. "
                "You can find it in Slack: right-click channel → View details → copy ID at the bottom.",
                channel,
            )
        elif error == "not_in_channel":
            log.error(
                "Coda bot is not in channel '%s'. Invite it first: /invite @Coda in the channel.",
                channel,
            )
        elif error == "invalid_auth":
            log.error("SLACK_TOKEN is invalid or expired. Check your .env / compose.yaml.")
        else:
            log.error("Slack API error: %s", error)
        log.info("Falling back to stdout:")
        print(message)


# ---------------------------------------------------------------------------
# 4. Main entry
# ---------------------------------------------------------------------------
def run_daily_triage() -> None:
    """Fetch → classify → post for all configured repos."""
    repos = load_repos_config()

    if not repos:
        log.warning("No repos configured in repos.yaml — nothing to triage")
        return

    for repo_config in repos:
        url = repo_config.get("url")
        if not url:
            continue

        name = url.rstrip("/").split("/")[-1].removesuffix(".git")
        log.info("Triaging issues for %s...", name)

        try:
            issues = fetch_recent_issues(url)
        except Exception:
            log.exception("Failed to fetch issues for %s — skipping", name)
            continue

        total = len(issues)
        log.info("Found %d new issue(s) in the last 24h for %s", total, name)

        classified = classify_issues(issues) if issues else []

        major = sum(1 for i in classified if i["category"] == "MAJOR_BUG")
        low = sum(1 for i in classified if i["category"] == "LOW_HANGING_FRUIT")
        slop_count = sum(1 for i in classified if i["category"] == "SLOP")
        log.info("Classification: %d major bugs, %d low-hanging fruit, %d slop", major, low, slop_count)

        post_triage_to_slack(classified, total, name)

    log.info("Daily triage complete.")


# ---------------------------------------------------------------------------
# CLI + Schedule
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Daily issue triage")
    parser.add_argument("--schedule", action="store_true", help="Register/update the schedule")
    args = parser.parse_args()

    if args.schedule:
        from agno.scheduler import ScheduleManager

        from db import get_postgres_db

        mgr = ScheduleManager(get_postgres_db())
        schedule = mgr.create(
            name="daily-issue-triage",
            cron="0 4 * * *",
            endpoint="/triage-issues",
            timezone="UTC",
            description="Daily issue triage — classify and post to Slack",
            if_exists="update",
        )
        print(f"Schedule ready: {schedule.name} (next: {schedule.next_run_at})")
    else:
        run_daily_triage()
