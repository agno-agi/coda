"""
Coda AgentOS
============

The main entry point for Coda.

Run:
    python -m app.main
"""

from os import getenv
from pathlib import Path

from agno.os import AgentOS

from coda.team import coda
from db import get_postgres_db

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
runtime_env = getenv("RUNTIME_ENV", "prd")
scheduler_base_url = "http://127.0.0.1:8000" if runtime_env == "dev" else getenv("AGENTOS_URL")

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
            streaming=True,  # type: ignore[call-arg]
            token=SLACK_TOKEN,  # type: ignore[call-arg]
            signing_secret=SLACK_SIGNING_SECRET,  # type: ignore[call-arg]
        )
    )

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
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(
        app="main:app",
        reload=runtime_env == "dev",
    )
