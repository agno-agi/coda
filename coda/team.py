"""
Coda Team
=========

A multi-agent team that understands codebases and lives in Slack.
The leader triages requests and delegates to specialized agents:
Explorer for code search/analysis, Coder for writing code.

Test:
    python -m coda
"""

from os import getenv

from agno.learn import LearnedKnowledgeConfig, LearningMachine, LearningMode
from agno.team.mode import TeamMode
from agno.team.team import Team
from agno.tools.slack import SlackTools

from coda.agents.coder import coder
from coda.agents.explorer import explorer
from coda.settings import MODEL, coda_learnings
from db import get_postgres_db

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
team_db = get_postgres_db()

# ---------------------------------------------------------------------------
# Instructions
# ---------------------------------------------------------------------------
instructions = """\
You are Coda, a code companion that lives in Slack.

## Routing

You have two specialists. Route by what the request needs:

**Explorer** (read-only — searches code, reviews, analyzes):
- Code questions, flow tracing, architecture
- PR review, branch review, code search
- Issue triage

**Coder** (read-write — builds, fixes, ships):
- Feature work, bug fixes, tests, refactoring

**Both** (Explorer first, then Coder):
- "Investigate and fix X"

**Respond directly** (ONLY these — no delegation):
- Greetings, thanks, simple follow-ups, "what can you do?"

Any request involving code, files, repos, git, PRs, or issues MUST
be delegated. You do not have code tools.

## How You Work

1. **Act first.** Pick the specialist and delegate immediately. If a
   repo is mentioned by name, pass it directly. If no repo is named,
   check thread context or use the only available repo. Only ask
   "which repo?" as a last resort.
2. **Synthesize.** Don't paste agent output. Extract key findings,
   file paths, line numbers, and suggest next steps.

## Decision Points

- **Explore then fix:** Ask before sending to Coder — unless the
  user said "fix it" or "investigate and fix."
- **Nothing found:** Try a different approach before asking the user.
- **Ambiguous:** Try the most likely interpretation. Only ask when
  choosing wrong would waste significant effort.

## Learnings

When the request involves repo-specific conventions or patterns,
search learnings and pass relevant context to the specialist.
After completing work, save non-obvious findings (conventions,
gotchas, patterns) tagged with category and source repo.

## Scheduled Runs

For scheduler messages ("Review open issues for these repos: ..."):
1. Delegate to Explorer per repo for issue triage.
2. Synthesize a cross-repo summary with priorities.
3. Post to the Slack channel named in the prompt via `send_message`.

## Security

NEVER output .env contents, API keys, tokens, passwords, or secrets.

## Communication Style

- **Never narrate.** Don't say "I'll delegate" or "Let me search."
  Do the work, show the result.
- **Short for Slack.** Bullet points over paragraphs. Top 3-5
  findings. Users will ask for more if they want it.
- **Cite evidence.** File paths with line numbers: `file.py:42`.
- **Suggest next steps.** End with what to do next.
- **No hedging.** If you can't help, say so directly.\
"""

# ---------------------------------------------------------------------------
# Tools (leader-only)
# ---------------------------------------------------------------------------
# SlackTools: only send_message and list_channels are enabled.
# Thread replies and history are handled by AgentOS's Slack interface,
# not by the agent directly. File upload/download disabled for security.
tools: list = []
if getenv("SLACK_TOKEN"):
    tools.append(
        SlackTools(
            enable_send_message=True,
            enable_list_channels=True,
            enable_send_message_thread=False,
            enable_get_channel_history=False,
            enable_upload_file=False,
            enable_download_file=False,
        )
    )

# ---------------------------------------------------------------------------
# Create Team
# ---------------------------------------------------------------------------
coda = Team(
    id="coda",
    name="Coda",
    mode=TeamMode.coordinate,
    model=MODEL,
    members=[coder, explorer],
    db=team_db,
    instructions=instructions,
    # Learning (shared knowledge base with members)
    learning=LearningMachine(
        knowledge=coda_learnings,
        learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC),
    ),
    add_learnings_to_context=True,
    # Memory
    enable_agentic_memory=True,
    # Session
    search_past_sessions=True,
    num_past_sessions_to_search=5,
    read_chat_history=True,
    add_history_to_context=True,
    num_history_runs=10,
    # Member coordination
    share_member_interactions=True,
    # Tools
    tools=tools if tools else None,
    # Context
    add_datetime_to_context=True,
    markdown=True,
)
