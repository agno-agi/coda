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

from coda.team import coda
from db import get_postgres_db
from tasks.review_issues import run_daily_triage
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
@asynccontextmanager
async def lifespan(app):
    sync_all_repos()
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
    interfaces=interfaces,
    config=str(Path(__file__).parent / "config.yaml"),
    lifespan=lifespan,
)

app = agent_os.get_app()


# ---------------------------------------------------------------------------
# Repo sync endpoints
# ---------------------------------------------------------------------------
@app.post("/sync")
async def sync_repos() -> dict[str, str]:
    """Sync all configured repositories (clone missing, pull existing)."""
    sync_all_repos()
    return {"status": "ok"}


@app.post("/triage-issues")
async def triage_issues() -> dict[str, str]:
    """Run daily issue triage — fetch, classify, post to Slack."""
    run_daily_triage()
    return {"status": "ok"}


if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=runtime_env == "dev",
    )
