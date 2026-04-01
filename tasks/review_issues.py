"""
Daily Issue Triage
==================

Fetches recent GitHub issues and runs the Triager agent to categorize,
label, and comment on them. Posts a summary to Slack. Runs daily via
scheduler.

The Triager categorizes issues and takes action (labeling, commenting)
but does NOT close issues during automated daily runs.

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

import httpx
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
    if not match:
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
# 2. Triage via Triager agent
# ---------------------------------------------------------------------------
def triage_issues(issues: list[dict], owner_repo: str) -> str:
    """Run the Triager agent to categorize and label issues.

    The agent reads each issue, categorizes it, labels it, and optionally
    comments — but never closes issues during automated runs.

    Returns the agent's text summary for posting to Slack.
    """
    from coda.agents.triager import triager

    issues_text = "\n".join(
        f"- #{i['number']}: {i['title']} (by @{i['user']}, labels: {', '.join(i['labels']) or 'none'})" for i in issues
    )

    response = triager.run(
        f"Daily automated triage for **{owner_repo}**.\n\n"
        f"Review these {len(issues)} recent issues:\n\n{issues_text}\n\n"
        f"For each issue:\n"
        f"1. Read the full details with `get_issue`\n"
        f"2. Categorize it\n"
        f"3. Label it appropriately\n"
        f"4. Comment if it adds value (code pointers, duplicate links)\n\n"
        f"**DO NOT close or reopen any issues** — this is an automated scan.\n\n"
        f"Format your response as a Slack summary with these sections:\n"
        f"- :red_circle: *Major Bugs* (if any)\n"
        f"- :large_green_circle: *Low-Hanging Fruit* (if any)\n"
        f"- :wastebasket: *Slop* (if any)\n"
        f"- Other categories as needed (Bug, Enhancement, Question, etc.)\n"
        f"Each item: `• <issue_url|#number title> — summary (action: labeled X)`\n"
        f"End with a line: `Scanned N issues | YYYY-MM-DD HH:MM UTC`"
    )

    return response.content  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# 3. Post to Slack
# ---------------------------------------------------------------------------
def post_triage_to_slack(summary: str, repo_name: str) -> None:
    """Send triage summary to Slack. Fails gracefully if not configured."""
    token = getenv("SLACK_TOKEN", "")
    channel = getenv("TRIAGE_CHANNEL", "")
    message = f"*Coda Issue Triage — {repo_name}*\n\n{summary}"

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
    """Fetch → triage (via Triager agent) → post for all configured repos."""
    repos = load_repos_config()

    if not repos:
        log.warning("No repos configured in repos.yaml — nothing to triage")
        return

    for repo_config in repos:
        url = repo_config.get("url")
        if not url:
            continue

        name = url.rstrip("/").split("/")[-1].removesuffix(".git")
        owner_repo = _parse_owner_repo(url)
        log.info("Triaging issues for %s...", name)

        try:
            issues = fetch_recent_issues(url)
        except Exception:
            log.exception("Failed to fetch issues for %s — skipping", name)
            continue

        total = len(issues)
        log.info("Found %d new issue(s) in the last 24h for %s", total, name)

        if not issues:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            post_triage_to_slack(
                f"Scanned 0 new issues in the last 24h. Nothing to triage.\n———\n{now}",
                name,
            )
            continue

        try:
            summary = triage_issues(issues, owner_repo)
        except Exception:
            log.exception("Triager agent failed for %s — skipping", name)
            continue

        post_triage_to_slack(summary, name)

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
