# Coda Specification

This is the canonical specification for Coda. All other documentation (README, CLAUDE.md, agent instructions) is derived from this file.

## What Coda Is

A code companion that lives in Slack. Helps engineering teams understand their code, review changes, triage issues, and contribute code that fits their style. Built on [Agno](https://github.com/agno-agi/agno).

## Architecture

### Team Structure

```
Coda (Team leader, Coordinate mode, gpt-5.4)
├── Coder — writes code in isolated worktrees, opens PRs
├── Explorer — searches code, reviews PRs/branches, triages issues (read-only)
└── Leader responds directly for greetings and simple questions
```

### Infrastructure

- **Framework:** Agno (AgentOS, Team, Agent)
- **Interface:** Slack (via Agno Slack interface)
- **Database:** PostgreSQL + pgvector (learnings only, not code indexing)
- **Repos:** cloned to `/repos` volume, searched directly on disk
- **Model:** gpt-5.4 (all agents)

### Key Design Decisions

- Code is searched on disk (grep, find, read), not vector indexed
- All code writing happens in git worktrees, never on main
- Learnings are stored in pgvector for semantic search
- Each Slack thread is an independent session

## Capabilities

### 1. Explore Code (Explorer)

Search files on disk, trace call chains, answer architecture questions.

- **Tools:** CodingTools (read-only: read, grep, find, ls), GitTools (read-only), ReasoningTools
- **Examples:** "where is X", "how does X work", "what breaks if I change X"
- Returns file paths and line numbers as evidence

### 2. Review PRs (Explorer)

Read PR details, diff changed files, check against conventions, leave comments.

- **Tools:** GithubTools (get_pull_request, get_pull_request_changes, get_pull_request_comments, create_pull_request_comment, comment_on_issue)
- **Workflow:** fetch PR → read changed files → check conventions → post inline comments → post summary

### 3. Review Branches (Explorer)

Compare branches against main, summarize what changed.

- **Tools:** GitTools (git_fetch, git_branches, git_log, git_diff)
- **Workflow:** fetch → confirm branch exists → log commits → diff stat → read key files → synthesize

### 4. Triage Issues (Explorer)

Read open issues, understand them in context of the code, prioritize.

- **Tools:** GithubTools (list_issues, get_issue, list_issue_comments, comment_on_issue)
- Categorizes by effort/urgency, flags low-hanging fruit and stale items

### 5. Write Code (Coder)

Build features, fix bugs, write tests in isolated git worktrees.

- **Tools:** CodingTools (full), GitTools (full), GithubTools (create_pull_request), ReasoningTools
- **Workflow:** create worktree → read first → plan → edit → verify (run tests) → commit → push → open PR
- Never touches main. Each task gets a `coda/<task-name>` branch.

### 6. Learn Over Time (All agents)

Picks up coding standards, conventions, patterns from interactions.

- **Storage:** LearningMachine with shared `coda_learnings` knowledge base (pgvector)
- **Mode:** AGENTIC — agents decide what to learn and when to recall
- **Namespace:** "global" (shared across all agents)
- **Categories:** convention, architecture, gotcha, preference, process

### 7. Scheduled Tasks

Background tasks on a cron schedule via Agno ScheduleManager.

- **Repo sync:** pulls latest changes every 5 minutes (`POST /sync`)
- **Issue triage:** reviews open issues daily, weekdays 9 AM UTC (`POST /teams/coda/runs`)
- **Startup sync:** repos are synced on application startup

## Agents

### Coda (Team Leader)

- **Role:** Triage requests, delegate to specialists, synthesize results
- **Mode:** Coordinate — picks members when needed, responds directly for simple things
- **Tools:** SlackTools (send_message, list_channels only)
- **Features:** agentic memory, session history (5 past sessions, 10 history runs), learnings in context
- **Routing:** see routing table in `coda/team.py` instructions

### Explorer

- **Role:** Search code, trace flows, review PRs, analyze repositories
- **Tools:**
  - CodingTools (read_file, grep, find, ls — no write/edit/shell)
  - GitTools (read_only=True — log, diff, blame, show, fetch, branches, list_repos, repo_summary, get_github_remote, list_worktrees)
  - GithubTools (get_pull_request, get_pull_requests, get_pull_request_changes, get_pull_request_comments, get_pull_request_with_details, create_pull_request_comment, get_issue, list_issues, list_issue_comments, comment_on_issue, list_branches, search_code)
  - ReasoningTools (think)

### Coder

- **Role:** Write, test, and ship code in isolated git worktrees
- **Tools:**
  - CodingTools (all=True, shell_timeout=120)
  - GitTools (full — includes create_worktree, remove_worktree)
  - GithubTools (get_pull_request, get_pull_requests, get_pull_request_changes, get_pull_request_comments, create_pull_request, get_issue, list_issues, create_issue, comment_on_issue)
  - ReasoningTools (think)

## Custom Tools

### GitTools (`coda/tools/git.py`)

Custom Agno Toolkit wrapping git CLI operations:

- **Read-only:** git_log, git_diff, git_blame, git_show, git_fetch, git_branches, list_repos, repo_summary, get_github_remote, list_worktrees
- **Write (Coder only):** create_worktree, remove_worktree
- All paths validated to stay within `base_dir` (`/repos`)
- Diff output truncated at 20,000 chars

## Interfaces

### Slack

- Each thread = independent session
- DM or @mention in channels
- Leader has SlackTools for proactive messaging (send_message, list_channels)
- Thread replies handled by AgentOS Slack interface, not agent tools

### CLI

- `python -m coda` for local testing
- Same team, no Slack tools

### API

- FastAPI via AgentOS at `:8000`
- `POST /sync` — trigger repo sync
- `POST /review-issues` — return triage prompt (debug)
- `/docs` — Swagger UI

## Constraints

- Never auto-merges. Opens PRs for human review.
- Never touches main branch. All code work in worktrees.
- Never sends code outside your environment. Only calls the configured LLM.
- Never outputs secrets, API keys, tokens, or .env contents.

## File Structure

```
coda/
├── app/
│   ├── main.py          # AgentOS + Slack interface + endpoints
│   └── config.yaml      # Quick prompts for chat UI
├── coda/
│   ├── team.py          # Coda team definition (leader)
│   ├── settings.py      # Shared DB, REPOS_DIR, MODEL, learnings KB
│   ├── agents/
│   │   ├── coder.py     # Coder agent
│   │   └── explorer.py  # Explorer agent
│   └── tools/
│       └── git.py       # GitTools toolkit
├── db/
│   ├── session.py       # PostgreSQL session factory + knowledge factory
│   └── url.py           # Database URL builder
├── tasks/
│   ├── sync_repos.py    # Repo sync (every 5 min)
│   └── review_issues.py # Issue triage (daily, weekdays)
├── evals/
│   ├── run_evals.py     # Eval runner
│   └── test_cases.py    # Test cases
├── docs/
│   ├── SPEC.md          # This file (canonical spec)
│   ├── GITHUB_ACCESS.md # GitHub PAT setup guide
│   └── SLACK_CONNECT.md # Slack app setup guide
├── scripts/
├── compose.yaml
├── Dockerfile
├── repos.yaml
├── pyproject.toml
└── requirements.txt
```
