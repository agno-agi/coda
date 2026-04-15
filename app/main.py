"""
Coda AgentOS
============

The main entry point for Coda.

Run:
    python -m app.main
"""

from contextlib import asynccontextmanager
from os import getenv
from pathlib import Path

from agno.os import AgentOS

from coda.agents.coder import coder
from coda.agents.explorer import explorer
from coda.agents.planner import planner
from coda.agents.researcher import researcher
from coda.agents.triager import triager
from coda.team import coda
from db import get_postgres_db
from tasks.daily_digest import run_daily_digest

# from tasks.review_issues import run_daily_triage
from tasks.sync_repos import sync_all_repos

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
runtime_env = getenv("RUNTIME_ENV", "prd")
scheduler_base_url = getenv("AGENTOS_URL", "http://127.0.0.1:8000")

# ---------------------------------------------------------------------------
# Interfaces
# ---------------------------------------------------------------------------
SLACK_TOKEN = getenv("SLACK_TOKEN", "")
SLACK_SIGNING_SECRET = getenv("SLACK_SIGNING_SECRET", "")

interfaces: list = []
if SLACK_TOKEN and SLACK_SIGNING_SECRET:
    from agno.os.interfaces.slack import Slack

    interfaces.append(
        Slack(
            team=coda,
            streaming=True,
            token=SLACK_TOKEN,
            signing_secret=SLACK_SIGNING_SECRET,
            resolve_user_identity=True,
        )
    )


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
def _register_schedules() -> None:
    """Register all scheduled tasks (idempotent — safe to run on every startup)."""
    from agno.scheduler import ScheduleManager

    mgr = ScheduleManager(get_postgres_db())
    mgr.create(
        name="sync-repos",
        cron="*/5 * * * *",
        endpoint="/sync",
        timezone="UTC",
        description="Sync all configured repos every 5 minutes",
        if_exists="update",
    )
    # if getenv("TRIAGE_CHANNEL") and getenv("SLACK_TOKEN"):
    #     mgr.create(
    #         name="daily-issue-triage",
    #         cron="0 4 * * *",
    #         endpoint="/triage-issues",
    #         timezone="UTC",
    #         description="Daily issue triage — classify and post to Slack",
    #         if_exists="update",
    #     )
    if getenv("DIGEST_CHANNEL") and getenv("SLACK_TOKEN"):
        mgr.create(
            name="daily-digest",
            cron="0 8 * * *",
            endpoint="/digest",
            timezone="UTC",
            description="Daily activity digest — merged PRs, open PRs, new/stale issues",
            if_exists="update",
        )


@asynccontextmanager
async def lifespan(app):
    sync_all_repos()
    _register_schedules()
    yield


# ---------------------------------------------------------------------------
# Create AgentOS
# ---------------------------------------------------------------------------
agent_os = AgentOS(
    name="Coda",
    tracing=True,
    scheduler=True,
    scheduler_base_url=scheduler_base_url,
    db=get_postgres_db(),
    teams=[coda],
    agents=[explorer, researcher, coder, planner, triager],
    interfaces=interfaces,
    config=str(Path(__file__).parent / "config.yaml"),
    lifespan=lifespan,
    authorization=runtime_env == "prd",
)

app = agent_os.get_app()


# ---------------------------------------------------------------------------
# Task endpoints
# ---------------------------------------------------------------------------
@app.post("/sync")
def sync_repos() -> dict[str, str]:
    """Sync all configured repositories (clone missing, pull existing)."""
    sync_all_repos()
    return {"status": "ok"}


# @app.post("/triage-issues")
# def triage_issues() -> dict[str, str]:
#     """Run daily issue triage via Triager agent — categorize, label, post to Slack."""
#     run_daily_triage()
#     return {"status": "ok"}


@app.post("/digest")
def daily_digest() -> dict[str, str]:
    """Run daily activity digest — merged PRs, open PRs, new/stale issues."""
    run_daily_digest()
    return {"status": "ok"}


if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=runtime_env == "dev",
    )
