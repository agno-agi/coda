"""
Repo Sync
=========

Scheduled task that keeps all configured repositories up to date.
Runs every 5 minutes. Only syncs the main clone — worktrees are unaffected.

Register/update schedule:
    python -m tasks.sync_repos
"""

from __future__ import annotations

import subprocess
from os import getenv
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from agno.scheduler import ScheduleManager

from coda.agents.settings import REPOS_DIR
from db import get_postgres_db

REPOS_CONFIG = Path(getenv("REPOS_CONFIG", str(Path(__file__).parents[1] / "repos.yaml")))


def load_repos_config() -> list[dict]:
    """Load repository configuration from repos.yaml."""
    if not REPOS_CONFIG.exists():
        return []
    with open(REPOS_CONFIG) as f:
        config = yaml.safe_load(f) or {}
    return config.get("repos", []) or []


def sync_all_repos() -> None:
    """Clone missing repos and pull existing ones."""
    repos = load_repos_config()
    REPOS_DIR.mkdir(exist_ok=True)

    for repo_config in repos:
        url = repo_config.get("url")
        if not url:
            print(f"Skipping repo config with missing url: {repo_config}")
            continue
        branch = repo_config.get("branch", "main")
        # Derive repo name from URL: https://github.com/org/name → name
        name = url.rstrip("/").split("/")[-1].removesuffix(".git")
        repo_path = REPOS_DIR / name

        if not repo_path.exists():
            # Clone
            print(f"Cloning {url} → {repo_path}")
            result = subprocess.run(
                ["git", "clone", "--branch", branch, url, str(repo_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                print(f"  FAILED to clone {name}: {result.stderr.strip()}")
            else:
                print(f"  Cloned {name}")
        else:
            # Fetch and reset main clone (worktrees are unaffected)
            print(f"Syncing {name} ({branch})")
            result = subprocess.run(
                ["git", "fetch", "origin"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                print(f"  FAILED to fetch {name}: {result.stderr.strip()}")
                continue
            result = subprocess.run(
                ["git", "reset", "--hard", f"origin/{branch}"],
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                print(f"  FAILED to reset {name}: {result.stderr.strip()}")
            else:
                print(f"  Synced {name}")


# ---------------------------------------------------------------------------
# Schedule
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mgr = ScheduleManager(get_postgres_db())
    schedule = mgr.create(
        name="sync-repos",
        cron="*/5 * * * *",
        endpoint="/teams/coda/runs",
        payload={
            "message": (
                "Sync all configured repositories. "
                "For each repo in repos.yaml: git fetch origin && git reset --hard origin/<branch>. "
                "Report which repos were synced."
            ),
        },
        timezone="UTC",
        description="Sync all configured repos every 5 minutes",
        if_exists="update",
    )
    print(f"Schedule ready: {schedule.name} (next run: {schedule.next_run_at})")
