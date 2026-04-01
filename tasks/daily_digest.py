"""
Daily Digest
=============

Posts a morning summary to Slack: merged PRs, open PRs waiting for review,
new issues, and stale issues across all configured repositories.

Manual trigger:
    python -m tasks.daily_digest

Register/update schedule:
    python -m tasks.daily_digest --schedule
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

GITHUB_API = "https://api.github.com"
STALE_DAYS = 7
REVIEW_WINDOW_DAYS = 3
MAX_REVIEW_PRS = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_owner_repo(url: str) -> str:
    """Extract 'owner/repo' from a GitHub URL."""
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", url.rstrip("/"))
    if not match:
        raise ValueError(f"Cannot parse GitHub owner/repo from: {url}")
    return match.group(1)


def _github_headers() -> dict[str, str]:
    token = getenv("GITHUB_ACCESS_TOKEN", "")
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


# ---------------------------------------------------------------------------
# 1. Fetch
# ---------------------------------------------------------------------------
def fetch_merged_prs(owner_repo: str, since_hours: int = 24) -> list[dict]:
    """Fetch PRs merged in the last N hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    merged: list[dict] = []
    page = 1

    with httpx.Client(timeout=30) as client:
        while True:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner_repo}/pulls",
                headers=_github_headers(),
                params={
                    "state": "closed",
                    "sort": "updated",
                    "direction": "desc",
                    "per_page": 100,
                    "page": page,
                },
            )
            resp.raise_for_status()
            batch = resp.json()

            if not batch:
                break

            for pr in batch:
                if not pr.get("merged_at"):
                    continue
                merged_at = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                if merged_at < cutoff:
                    continue
                merged.append(
                    {
                        "number": pr["number"],
                        "title": pr["title"],
                        "user": pr["user"]["login"],
                        "url": pr["html_url"],
                    }
                )

            # Stop if the oldest PR in batch was updated before our window
            oldest_updated = batch[-1].get("updated_at", "")
            if oldest_updated:
                oldest_dt = datetime.fromisoformat(oldest_updated.replace("Z", "+00:00"))
                if oldest_dt < cutoff:
                    break

            if len(batch) < 100:
                break
            page += 1

    return merged


def fetch_open_prs(owner_repo: str, since_days: int = REVIEW_WINDOW_DAYS) -> list[dict]:
    """Fetch recent non-draft open PRs (created in the last N days, max 10)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
    prs: list[dict] = []
    page = 1

    with httpx.Client(timeout=30) as client:
        while True:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner_repo}/pulls",
                headers=_github_headers(),
                params={
                    "state": "open",
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

            for pr in batch:
                created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                if created < cutoff:
                    return prs[:MAX_REVIEW_PRS]

                if pr.get("draft", False):
                    continue

                prs.append(
                    {
                        "number": pr["number"],
                        "title": pr["title"],
                        "user": pr["user"]["login"],
                        "url": pr["html_url"],
                        "age_days": (datetime.now(timezone.utc) - created).days,
                    }
                )

            if len(batch) < 100:
                break
            page += 1

    return prs[:MAX_REVIEW_PRS]


def fetch_new_issues(owner_repo: str, since_hours: int = 24) -> list[dict]:
    """Fetch issues created in the last N hours."""
    since = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).isoformat()
    issues: list[dict] = []
    page = 1

    with httpx.Client(timeout=30) as client:
        while True:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner_repo}/issues",
                headers=_github_headers(),
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
                        "user": item["user"]["login"],
                        "url": item["html_url"],
                        "labels": [label["name"] for label in item.get("labels", [])],
                    }
                )

            if len(batch) < 100:
                break
            page += 1

    return issues


def fetch_stale_issues(owner_repo: str, stale_days: int = STALE_DAYS) -> list[dict]:
    """Fetch open issues with no activity in N days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
    stale: list[dict] = []
    page = 1

    with httpx.Client(timeout=30) as client:
        while True:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner_repo}/issues",
                headers=_github_headers(),
                params={
                    "state": "open",
                    "sort": "updated",
                    "direction": "asc",
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
                updated = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
                if updated > cutoff:
                    return stale
                stale.append(
                    {
                        "number": item["number"],
                        "title": item["title"],
                        "url": item["html_url"],
                        "days_stale": (datetime.now(timezone.utc) - updated).days,
                    }
                )

            if len(batch) < 100:
                break
            page += 1

    return stale


# ---------------------------------------------------------------------------
# 2. Format
# ---------------------------------------------------------------------------
def build_digest(owner_repo: str) -> str:
    """Build a Slack-formatted digest for one repo."""
    merged = fetch_merged_prs(owner_repo)
    open_prs = fetch_open_prs(owner_repo)
    new_issues = fetch_new_issues(owner_repo)
    stale = fetch_stale_issues(owner_repo)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sections: list[str] = []

    if merged:
        lines = [f"• <{pr['url']}|#{pr['number']}> {pr['title']} — @{pr['user']}" for pr in merged]
        sections.append(f":white_check_mark: *Merged* ({len(merged)})\n" + "\n".join(lines))

    if open_prs:
        lines = []
        for pr in open_prs:
            age = pr.get("age_days", 0)
            age_str = "today" if age == 0 else f"{age}d"
            lines.append(f"• <{pr['url']}|#{pr['number']}> {pr['title']} — @{pr['user']} ({age_str})")
        sections.append(f":eyes: *Waiting for Review* ({len(open_prs)})\n" + "\n".join(lines))

    if new_issues:
        lines = []
        for issue in new_issues:
            labels = f" [{', '.join(issue['labels'])}]" if issue["labels"] else ""
            lines.append(f"• <{issue['url']}|#{issue['number']}> {issue['title']}{labels} — @{issue['user']}")
        sections.append(f":new: *New Issues* ({len(new_issues)})\n" + "\n".join(lines))

    if stale:
        lines = [f"• <{i['url']}|#{i['number']}> {i['title']} ({i['days_stale']}d)" for i in stale[:10]]
        header = f":hourglass: *Stale* ({len(stale)})"
        if len(stale) > 10:
            header += f" — showing 10 of {len(stale)}"
        sections.append(header + "\n" + "\n".join(lines))

    if not sections:
        return f"All quiet — no activity in the last 24h.\n———\n{now}"

    return "\n\n".join(sections) + f"\n———\n{now}"


# ---------------------------------------------------------------------------
# 3. Post to Slack
# ---------------------------------------------------------------------------
def post_digest_to_slack(message: str, repo_name: str) -> None:
    """Send digest to Slack. Falls back to stdout if not configured."""
    token = getenv("SLACK_TOKEN", "")
    channel = getenv("DIGEST_CHANNEL", "")
    text = f"*Coda Daily Digest — {repo_name}*\n\n{message}"

    if not token or not channel:
        log.warning("SLACK_TOKEN or DIGEST_CHANNEL not set — printing to stdout")
        print(text)
        return

    try:
        client = WebClient(token=token)
        client.chat_postMessage(channel=channel, text=text, mrkdwn=True)
        log.info("Posted digest to Slack channel %s", channel)
    except SlackApiError as e:
        error = e.response.get("error", "unknown")
        if error == "channel_not_found":
            log.error("Channel '%s' not found. Use channel ID (e.g. C0XXXXXXX), not name.", channel)
        elif error == "not_in_channel":
            log.error("Bot not in channel '%s'. Run /invite @Coda first.", channel)
        elif error == "invalid_auth":
            log.error("SLACK_TOKEN is invalid or expired.")
        else:
            log.error("Slack API error: %s", error)
        log.info("Falling back to stdout:")
        print(text)


# ---------------------------------------------------------------------------
# 4. Main entry
# ---------------------------------------------------------------------------
def run_daily_digest() -> None:
    """Fetch → format → post for all configured repos."""
    repos = load_repos_config()

    if not repos:
        log.warning("No repos configured in repos.yaml — nothing to digest")
        return

    for repo_config in repos:
        url = repo_config.get("url")
        if not url:
            continue

        name = url.rstrip("/").split("/")[-1].removesuffix(".git")
        owner_repo = _parse_owner_repo(url)
        log.info("Building digest for %s...", name)

        try:
            digest = build_digest(owner_repo)
        except Exception:
            log.exception("Failed to build digest for %s — skipping", name)
            continue

        post_digest_to_slack(digest, name)

    log.info("Daily digest complete.")


# ---------------------------------------------------------------------------
# CLI + Schedule
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Daily activity digest")
    parser.add_argument("--schedule", action="store_true", help="Register/update the schedule")
    args = parser.parse_args()

    if args.schedule:
        from agno.scheduler import ScheduleManager

        from db import get_postgres_db

        mgr = ScheduleManager(get_postgres_db())
        schedule = mgr.create(
            name="daily-digest",
            cron="0 8 * * *",
            endpoint="/digest",
            timezone="UTC",
            description="Daily activity digest — merged PRs, open PRs, new/stale issues",
            if_exists="update",
        )
        print(f"Schedule ready: {schedule.name} (next: {schedule.next_run_at})")
    else:
        run_daily_digest()
