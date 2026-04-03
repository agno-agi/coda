"""
Proactive Agno Post
===================

Posts a short Agno update to Slack every 30 minutes, grounded in recent
repo activity or a concrete file spotlight from the local agno clone.

Manual trigger:
    python -m tasks.proactive_agno_post

Register/update schedule:
    python -m tasks.proactive_agno_post --schedule
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from os import getenv
from pathlib import Path
from typing import Any

import httpx
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from coda.settings import REPOS_DIR
from tasks.sync_repos import load_repos_config

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
DEFAULT_REPO = "agno"
DEFAULT_CHANNEL = "C09GL0WK0SU"
DEFAULT_THREAD_TS = "1775243740.375219"
RECENT_ACTIVITY_LIMIT = 6
SPOTLIGHT_FILES = [
    "README.md",
    "libs/agno/agno/agent/agent.py",
    "libs/agno/agno/team/team.py",
    "libs/agno/agno/tools/function.py",
    "libs/agno/agno/memory/v2/memory.py",
    "libs/agno/agno/os/app.py",
]


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


def _repo_name_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1].removesuffix(".git")


def _load_repo_config(repo_name: str) -> dict[str, Any] | None:
    for repo in load_repos_config():
        url = repo.get("url", "")
        if url and _repo_name_from_url(url) == repo_name:
            return repo
    return None


def _repo_path(repo_name: str) -> Path:
    return REPOS_DIR / repo_name


def _run_git(repo_path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return result.stdout.strip()


def _get_recent_commits(repo_path: Path, limit: int = RECENT_ACTIVITY_LIMIT) -> list[dict[str, str]]:
    output = _run_git(
        repo_path,
        "log",
        f"--max-count={limit}",
        "--pretty=format:%H%x1f%s%x1f%an%x1f%cI",
        "--name-only",
    )
    commits: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    files: list[str] = []

    for line in output.splitlines() + [""]:
        if "\x1f" in line:
            if current is not None:
                current["files"] = ", ".join(files[:4])
                commits.append(current)
            sha, subject, author, committed_at = line.split("\x1f")
            current = {
                "sha": sha,
                "short_sha": sha[:7],
                "subject": subject,
                "author": author,
                "committed_at": committed_at,
            }
            files = []
        elif current is not None and line.strip():
            files.append(line.strip())

    return commits


def _get_file_summary(repo_path: Path, relative_path: str) -> dict[str, str] | None:
    target = repo_path / relative_path
    if not target.exists() or not target.is_file():
        return None

    content = target.read_text(encoding="utf-8", errors="ignore").splitlines()
    non_empty = [line.strip() for line in content if line.strip()]
    if not non_empty:
        return None

    headline = non_empty[0]
    detail = ""
    for line in non_empty[1:]:
        if len(line) > 20:
            detail = line
            break
    return {
        "path": relative_path,
        "headline": headline[:140],
        "detail": detail[:220],
    }


def _pick_spotlight(repo_path: Path, run_bucket: str) -> dict[str, str] | None:
    if not SPOTLIGHT_FILES:
        return None
    index = int(hashlib.sha256(run_bucket.encode()).hexdigest(), 16) % len(SPOTLIGHT_FILES)
    for offset in range(len(SPOTLIGHT_FILES)):
        candidate = SPOTLIGHT_FILES[(index + offset) % len(SPOTLIGHT_FILES)]
        summary = _get_file_summary(repo_path, candidate)
        if summary:
            return summary
    return None


def fetch_recent_merged_pr(owner_repo: str) -> dict[str, Any] | None:
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner_repo}/pulls",
                headers=_github_headers(),
                params={
                    "state": "closed",
                    "sort": "updated",
                    "direction": "desc",
                    "per_page": 20,
                    "page": 1,
                },
            )
            resp.raise_for_status()
    except Exception:
        log.exception("Failed to fetch merged PRs for %s", owner_repo)
        return None

    for pr in resp.json():
        if pr.get("merged_at"):
            return {
                "type": "merged_pr",
                "number": pr["number"],
                "title": pr["title"],
                "url": pr["html_url"],
                "author": pr["user"]["login"],
                "merged_at": pr["merged_at"],
            }
    return None


def fetch_recent_open_pr(owner_repo: str) -> dict[str, Any] | None:
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(
                f"{GITHUB_API}/repos/{owner_repo}/pulls",
                headers=_github_headers(),
                params={
                    "state": "open",
                    "sort": "updated",
                    "direction": "desc",
                    "per_page": 10,
                    "page": 1,
                },
            )
            resp.raise_for_status()
    except Exception:
        log.exception("Failed to fetch open PRs for %s", owner_repo)
        return None

    for pr in resp.json():
        if pr.get("draft", False):
            continue
        return {
            "type": "open_pr",
            "number": pr["number"],
            "title": pr["title"],
            "url": pr["html_url"],
            "author": pr["user"]["login"],
            "updated_at": pr["updated_at"],
        }
    return None


def _half_hour_bucket(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    minute_bucket = "00" if now.minute < 30 else "30"
    return now.strftime(f"%Y-%m-%dT%H:{minute_bucket}Z")


def select_post_signal(repo_name: str, now: datetime | None = None) -> dict[str, Any] | None:
    repo_config = _load_repo_config(repo_name)
    if not repo_config:
        log.warning("Repo '%s' not found in repos.yaml", repo_name)
        return None

    url = repo_config.get("url")
    if not url:
        log.warning("Repo '%s' has no URL configured", repo_name)
        return None

    owner_repo = _parse_owner_repo(url)
    repo_path = _repo_path(repo_name)
    if not repo_path.exists():
        log.warning("Repo clone missing at %s", repo_path)
        return None

    merged_pr = fetch_recent_merged_pr(owner_repo)
    if merged_pr:
        return merged_pr

    open_pr = fetch_recent_open_pr(owner_repo)
    if open_pr:
        return open_pr

    try:
        commits = _get_recent_commits(repo_path)
    except Exception:
        log.exception("Failed to inspect local git history for %s", repo_name)
        commits = []

    if commits:
        commit = commits[0]
        return {
            "type": "commit",
            "sha": commit["sha"],
            "short_sha": commit["short_sha"],
            "subject": commit["subject"],
            "author": commit["author"],
            "committed_at": commit["committed_at"],
            "files": commit.get("files", ""),
            "url": f"https://github.com/{owner_repo}/commit/{commit['sha']}",
        }

    spotlight = _pick_spotlight(repo_path, _half_hour_bucket(now))
    if spotlight:
        return {
            "type": "spotlight",
            "path": spotlight["path"],
            "headline": spotlight["headline"],
            "detail": spotlight["detail"],
            "url": f"https://github.com/{owner_repo}/blob/main/{spotlight['path']}",
        }

    return None


def _signal_fingerprint(signal: dict[str, Any], bucket: str) -> str:
    identity = {
        "bucket": bucket,
        "type": signal.get("type"),
        "url": signal.get("url"),
        "number": signal.get("number"),
        "sha": signal.get("sha"),
        "path": signal.get("path"),
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def _dedupe_state_path(repo_name: str) -> Path:
    state_dir = REPOS_DIR / ".coda-state"
    state_dir.mkdir(exist_ok=True)
    return state_dir / f"proactive-post-{repo_name}.json"


def should_post_signal(repo_name: str, signal: dict[str, Any], bucket: str) -> bool:
    state_path = _dedupe_state_path(repo_name)
    fingerprint = _signal_fingerprint(signal, bucket)
    if not state_path.exists():
        return True

    try:
        state = json.loads(state_path.read_text())
    except Exception:
        log.warning("Failed to read proactive post dedupe state at %s; proceeding", state_path)
        return True

    return state.get("fingerprint") != fingerprint


def mark_signal_posted(repo_name: str, signal: dict[str, Any], bucket: str) -> None:
    state_path = _dedupe_state_path(repo_name)
    payload = {
        "bucket": bucket,
        "fingerprint": _signal_fingerprint(signal, bucket),
        "signal_type": signal.get("type"),
        "url": signal.get("url"),
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }
    state_path.write_text(json.dumps(payload, indent=2))


def build_proactive_post(repo_name: str, signal: dict[str, Any]) -> str:
    intro = "Agno update 👀"
    if signal["type"] == "merged_pr":
        return (
            f"{intro}\n"
            f"Recent merge: <{signal['url']}|#{signal['number']} {signal['title']}> by @{signal['author']}.\n"
            f"Why it matters: this is a fresh change landing in `{repo_name}`, so it's a good place to see what Agno is evolving right now."
        )
    if signal["type"] == "open_pr":
        return (
            f"{intro}\n"
            f"Open PR to watch: <{signal['url']}|#{signal['number']} {signal['title']}> by @{signal['author']}.\n"
            f"Why it matters: this is active work in flight on Agno, useful if you want a concrete thread to review or learn from."
        )
    if signal["type"] == "commit":
        files = signal.get("files") or "repo internals"
        return (
            f"{intro}\n"
            f"Commit highlight: <{signal['url']}|{signal['short_sha']}> {signal['subject']} — @{signal['author']}.\n"
            f"Touched: `{files}`\n"
            f"Why it matters: this points to the latest concrete code movement in Agno rather than a generic summary."
        )
    if signal["type"] == "spotlight":
        detail = f" {signal['detail']}" if signal.get("detail") else ""
        return (
            f"{intro}\n"
            f"Repo spotlight: <{signal['url']}|{signal['path']}>\n"
            f"{signal['headline']}{detail}\n"
            f"Why it matters: this keeps the post grounded in a real Agno file even when recent activity is quiet."
        )
    raise ValueError(f"Unsupported signal type: {signal['type']}")


def post_to_slack(message: str) -> None:
    token = getenv("SLACK_TOKEN", "")
    channel = getenv("PROACTIVE_POST_CHANNEL", DEFAULT_CHANNEL)
    thread_ts = getenv("PROACTIVE_POST_THREAD_TS", DEFAULT_THREAD_TS)

    if not token or not channel:
        log.warning("SLACK_TOKEN or PROACTIVE_POST_CHANNEL not set — printing to stdout")
        print(message)
        return

    payload: dict[str, Any] = {"channel": channel, "text": message, "mrkdwn": True}
    if thread_ts:
        payload["thread_ts"] = thread_ts

    try:
        client = WebClient(token=token)
        client.chat_postMessage(**payload)
        if thread_ts:
            log.info("Posted proactive Agno update to Slack channel %s thread %s", channel, thread_ts)
        else:
            log.info("Posted proactive Agno update to Slack channel %s", channel)
    except SlackApiError as e:
        error = e.response.get("error", "unknown")
        if error == "channel_not_found":
            log.error("Channel '%s' not found. Use channel ID (e.g. C0XXXXXXX), not name.", channel)
        elif error == "not_in_channel":
            log.error("Bot not in channel '%s'. Run /invite @Coda first.", channel)
        elif error == "invalid_auth":
            log.error("SLACK_TOKEN is invalid or expired.")
        elif error == "thread_not_found":
            log.error("Slack thread '%s' was not found in channel '%s'.", thread_ts, channel)
        else:
            log.error("Slack API error: %s", error)
        log.info("Falling back to stdout:")
        print(message)


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------
def run_proactive_agno_post() -> None:
    """Fetch → select → dedupe → format → post a proactive Agno update."""
    enabled = getenv("PROACTIVE_POST_ENABLED", "false").lower() == "true"
    repo_name = getenv("PROACTIVE_POST_REPO", DEFAULT_REPO)
    bucket = _half_hour_bucket()

    if not enabled:
        log.info("PROACTIVE_POST_ENABLED is false; skipping proactive Agno post")
        return

    signal = select_post_signal(repo_name)
    if not signal:
        log.warning("No proactive Agno signal available for repo '%s'", repo_name)
        return

    if not should_post_signal(repo_name, signal, bucket):
        log.info("Skipping proactive Agno post for repo '%s'; duplicate signal in bucket %s", repo_name, bucket)
        return

    message = build_proactive_post(repo_name, signal)
    post_to_slack(message)
    mark_signal_posted(repo_name, signal, bucket)


# ---------------------------------------------------------------------------
# CLI + Schedule
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Scheduled proactive Agno Slack posts")
    parser.add_argument("--schedule", action="store_true", help="Register/update the schedule")
    args = parser.parse_args()

    if args.schedule:
        from agno.scheduler import ScheduleManager

        from db import get_postgres_db

        mgr = ScheduleManager(get_postgres_db())
        schedule = mgr.create(
            name="proactive-agno-post",
            cron="*/30 * * * *",
            endpoint="/proactive-agno-post",
            timezone="UTC",
            description="Post a proactive Agno update to Slack every 30 minutes",
            if_exists="update",
        )
        print(f"Schedule ready: {schedule.name} (next: {schedule.next_run_at})")
    else:
        run_proactive_agno_post()