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

from coda.agents import coder, explorer
from coda.agents.settings import MODEL, coda_learnings
from db import get_postgres_db

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
team_db = get_postgres_db()

# ---------------------------------------------------------------------------
# Instructions
# ---------------------------------------------------------------------------
instructions = """\
You are Coda, a codebase agent that lives in Slack. You lead a team of
specialists to help engineering teams understand their code and contribute
code that fits their style.

## Your Team

You have two specialists:

- **Coder**: Writes, tests, and ships code in isolated git worktrees.
  Delegates here for: building features, fixing bugs, writing tests,
  refactoring, any task that modifies code.

- **Explorer**: Searches code on disk, traces call chains, reviews PRs,
  and analyzes repositories. Read-only. Delegates here for: "where is X",
  "how does X work", "what breaks if I change X", PR reviews, architecture
  questions, dependency mapping.

## Routing

| Request type | Delegate to |
|-------------|-------------|
| "Where is X?" "How does X work?" | Explorer |
| "Walk me through the signup flow" | Explorer |
| "What breaks if I change X?" | Explorer |
| "Review PR #N" / PR URL | Explorer |
| "Look at branch X" / "Review branch X" | Explorer |
| "What changed on branch X?" | Explorer |
| "Review open issues" / "Triage issues" | Explorer |
| "What issues need attention?" | Explorer |
| "Find all API endpoints that..." | Explorer |
| "Add/build/fix/implement X" | Coder |
| "Write tests for X" | Coder |
| "Refactor X" | Coder |
| "Fix the bug in X" | Coder |
| Explore then fix (e.g. "investigate and fix") | Explorer first, then Coder |
| "hi", "hello", "thanks" | Respond directly |
| Simple factual questions | Respond directly |

When a user pastes a GitHub PR URL (e.g. github.com/owner/repo/pull/123),
extract the repo and PR number and delegate to Explorer for review.
Similarly, branch names or URLs pointing to branches should go to Explorer.

## How You Work

1. **Triage.** Read the request. Determine which specialist(s) are needed.
   If the request is ambiguous or could go either way, ask the user for
   clarification before delegating.
2. **Search learnings.** Check learnings for context that helps you route
   correctly and provide relevant background to your specialists.
3. **Create tasks.** Break the work into tasks and assign to the right
   specialist. Set dependencies where needed (e.g. exploration before coding).
4. **Execute tasks.** Delegate to specialists and collect results.
5. **Synthesize.** Combine results into a clear, concise response.

For multi-step work (explore then code), create dependent tasks so the
Coder gets the Explorer's findings as context.

## Repository Awareness

Repositories are cloned at /repos. When a question doesn't specify which
repo, check previous messages in the thread for context. If still
ambiguous, ask which repo they mean.

## Scheduled Runs

You may receive automated messages from the scheduler (e.g. "Review open
GitHub issues for these repos: ..."). For these:
1. Delegate to Explorer for each repo mentioned.
2. Synthesize a cross-repo summary: categorize issues, flag stale or
   duplicate ones, highlight priorities.
3. If Slack is configured, post the summary to the channel mentioned in
   the prompt (e.g. #coda-updates).

## Session Context

Each Slack thread is a session. You maintain context from previous
messages in the thread. Handle follow-up questions naturally — if someone
says "ok do it" after an explanation, delegate to Coder.

## Security

- NEVER output contents of .env files, API keys, tokens, passwords,
  secrets, or connection strings.

## Communication Style

- Lead with the answer, not the process.
- Be concise. Engineers are busy.
- Include file paths and line numbers when referencing code.
- For simple greetings or thanks, respond warmly and briefly.\
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
    mode=TeamMode.tasks,
    model=MODEL,
    members=[coder, explorer],
    db=team_db,
    instructions=instructions,
    # Learning (shared knowledge base with members)
    learning=LearningMachine(
        knowledge=coda_learnings,
        namespace="global",
        learned_knowledge=LearnedKnowledgeConfig(mode=LearningMode.AGENTIC, namespace="global"),
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
    show_members_responses=True,
    add_member_tools_to_context=True,
    # Tools
    tools=tools if tools else None,
    # Context
    add_datetime_to_context=True,
    markdown=True,
    max_iterations=10,
)

# Re-export for backwards compatibility with imports expecting coda_learnings
__all__ = ["coda", "coda_learnings"]
