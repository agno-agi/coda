"""
Shared settings for Coda agents.

Centralizes the database, repos directory, and learnings knowledge base
so all agents share the same resources.
"""

from os import getenv
from pathlib import Path

from agno.models.openai import OpenAIResponses

from db import create_knowledge, get_postgres_db

agent_db = get_postgres_db()
REPOS_DIR = Path(getenv("REPOS_DIR", str(Path(__file__).parent.parent / "repos")))
REPOS_DIR.mkdir(exist_ok=True)
MODEL = OpenAIResponses(id="gpt-5.4")

# Learnings knowledge base (vector search over learned patterns — NOT code).
# Created once here, shared by all agents via their own LearningMachine instances.
coda_learnings = create_knowledge("Coda Learnings", "coda_learnings")
