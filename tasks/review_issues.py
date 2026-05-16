"""
Daily Issue Triage
==================

Fetches recent GitHub issues and runs the Triager agent to categorize,
label, and comment on them. Triager's destructive ops (close, label,
comment) are gated by Slack HITL — when Triager wants to act, a
multi-row approval card posts to TRIAGE_CHANNEL and only approved
actions execute.

If SLACK_TOKEN/TRIAGE_CHANNEL aren't set, the run still proceeds but
pauses persist in the agno dashboard for browser approval.

Manual trigger:
    python -m tasks.review_issues

Register/update schedule:
    python -m tasks.review_issues --schedule
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from os import getenv
from typing import Any, Optional

import httpx
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from coda.agents.triager import triager
from db.session import get_postgres_db
from tasks.sync_repos import load_repos_config

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
DEFAULT_SINCE_HOURS = 24


# ---------------------------------------------------------------------------
# Fetch
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
# Session ID
# ---------------------------------------------------------------------------
def _build_session_id(repo_name: str, header_ts: Optional[str]) -> str:
    """Build the Triager run session_id for a cron triage run.

    The ``f"{triager.id}:{header_ts}"`` form lets agno's Slack interactions
    router resume the run when a user clicks Approve. Without a Slack header
    a synthetic id is used — such runs are never resumed via Slack.
    """
    if header_ts:
        return f"{triager.id}:{header_ts}"
    return f"cron-triage-{repo_name}-{int(time.time())}"


# ---------------------------------------------------------------------------
# Slack header + HITL card
# ---------------------------------------------------------------------------
def _post_header(client: WebClient, channel: str, repo_name: str) -> Optional[str]:
    """Post the daily-triage header to TRIAGE_CHANNEL.

    Returns the message timestamp, used as thread_ts for any HITL card
    Triager produces. Returns None on failure.
    """
    try:
        resp = client.chat_postMessage(
            channel=channel,
            text=f":robot_face: *Daily issue triage starting* — `{repo_name}`",
        )
        return resp.get("ts")
    except SlackApiError as exc:
        log.error("Failed to post header to %s: %s", channel, exc.response.get("error"))
        return None


async def _post_hitl_card(token: str, paused_response: Any, channel: str, thread_ts: str) -> None:
    """Post the HITL approval card for a paused Triager run."""
    from agno.os.interfaces.slack.pause import post_pause_card

    client = AsyncWebClient(token=token)
    await post_pause_card(client, paused_response, channel, thread_ts)


# ---------------------------------------------------------------------------
# Triage one repo
# ---------------------------------------------------------------------------
def triage_repo(owner_repo: str, issues: list[dict], session_id: str) -> Any:
    """Run Triager on the issues for one repo. Returns the (possibly paused) RunOutput.

    The session_id format f"{triager.id}:{thread_ts}" is required by agno's
    Slack interactions router so it can resume the run when a user clicks
    Approve. Destructive ops are gated by requires_confirmation_tools on
    Triager's GithubTools — the LLM emits the call, agno pauses, the card
    posts, only approved rows execute.
    """
    issues_text = "\n".join(
        f"- #{i['number']}: {i['title']} (by @{i['user']}, labels: {', '.join(i['labels']) or 'none'})"
        for i in issues
    )
    return triager.run(
        f"Daily automated triage for **{owner_repo}**.\n\n"
        f"Review these {len(issues)} recent issues:\n\n{issues_text}\n\n"
        f"For each issue:\n"
        f"1. Read the full details with `get_issue`\n"
        f"2. Categorize it\n"
        f"3. Label, comment, or close as appropriate.\n\n"
        f"All destructive actions are gated by Slack HITL approval — a card "
        f"will appear; only approved actions execute.\n\n"
        f"Format your final response as a Slack summary:\n"
        f"- :red_circle: *Major Bugs* (if any)\n"
        f"- :large_green_circle: *Low-Hanging Fruit* (if any)\n"
        f"- :wastebasket: *Slop* (if any)\n"
        f"- Other categories as needed\n"
        f"Each item: `• <issue_url|#number title> — summary (action: X)`\n"
        f"End with: `Scanned N issues | YYYY-MM-DD HH:MM UTC`",
        session_id=session_id,
    )


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------
def run_daily_triage() -> None:
    """Fetch → triage (with HITL) → post HITL card if paused, for all configured repos.

    Falls back to dashboard-only mode if SLACK_TOKEN/TRIAGE_CHANNEL not set.
    """
    repos = load_repos_config()
    if not repos:
        log.warning("No repos configured in repos.yaml — nothing to triage")
        return

    token = getenv("SLACK_TOKEN", "")
    channel = getenv("TRIAGE_CHANNEL", "")
    slack_client = WebClient(token=token) if (token and channel) else None
    if not slack_client:
        log.info("SLACK_TOKEN/TRIAGE_CHANNEL not set — dashboard-only mode")

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

        if not issues:
            log.info("No new issues for %s in the last 24h", name)
            if slack_client:
                try:
                    slack_client.chat_postMessage(
                        channel=channel,
                        text=f"_No new issues to triage in `{name}`._",
                    )
                except SlackApiError as exc:
                    log.error("Slack post failed for %s: %s", name, exc.response.get("error"))
            continue

        header_ts: Optional[str] = None
        if slack_client:
            header_ts = _post_header(slack_client, channel, name)

        if slack_client and header_ts is None:
            log.warning("Header post failed for %s — skipping (no Slack delivery path)", name)
            continue

        session_id = _build_session_id(name, header_ts)

        try:
            response = triage_repo(owner_repo, issues, session_id)
        except Exception:
            log.exception("Triager agent failed for %s — skipping", name)
            continue

        status = getattr(response, "status", None)

        if status == "PAUSED" and slack_client and header_ts:
            try:
                asyncio.run(_post_hitl_card(token, response, channel, header_ts))
                log.info("HITL card posted for %s — awaiting approval", name)
            except Exception:
                log.exception("Failed to post HITL card for %s — fall back to dashboard", name)
        elif status == "PAUSED":
            log.info("Triager paused for %s — approve via agno dashboard /approvals", name)
        else:
            if slack_client and header_ts:
                summary = getattr(response, "content", "") or "Triage complete."
                try:
                    slack_client.chat_postMessage(
                        channel=channel, text=summary, mrkdwn=True, thread_ts=header_ts,
                    )
                except SlackApiError as exc:
                    log.error("Slack summary post failed for %s: %s", name, exc.response.get("error"))

    log.info("Daily triage complete.")


# ---------------------------------------------------------------------------
# CLI + Schedule
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Daily issue triage with HITL gating")
    parser.add_argument("--schedule", action="store_true", help="Register/update the schedule")
    args = parser.parse_args()

    if args.schedule:
        from agno.scheduler import ScheduleManager

        mgr = ScheduleManager(get_postgres_db())
        schedule = mgr.create(
            name="daily-issue-triage",
            cron="0 4 * * *",
            endpoint="/triage-issues",
            timezone="UTC",
            description="Daily issue triage with Slack HITL approval gating",
            if_exists="update",
        )
        print(f"Schedule ready: {schedule.name} (next: {schedule.next_run_at})")
    else:
        run_daily_triage()
