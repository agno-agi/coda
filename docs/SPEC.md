# Coda Specification

Coda is a code companion that lives in Slack. Helps engineering teams understand their code, review changes, triage issues, and contribute code that fits their style. Built on [Agno](https://github.com/agno-agi/agno).

## Architecture

### Team Structure

```
Coda (Team leader, Coordinate mode, gpt-5.4)
├── Coder — writes code in isolated worktrees, opens PRs
├── Explorer — searches code, reviews PRs/branches (read-only)
├── Triager — categorizes, labels, comments on, and closes issues
└── Leader responds directly for simple questions
```

### Infrastructure

- **Framework:** Agno (AgentOS, Team, Agent)
- **Interface:** Slack (via Agno Slack interface)
- **Database:** PostgreSQL + pgvector (learnings only, not code indexing)
- **Repos:** cloned to `/repos`, searched directly on disk (ephemeral in production, persistent volume in local dev)
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

### 4. Manage Issues (Triager)

Review, categorize, label, comment on, and close GitHub issues — backed
by code investigation.

- **Tools:** GithubTools (list_issues, get_issue, create_issue, comment_on_issue, close_issue, reopen_issue, assign_issue, label_issue, edit_issue, list_issue_comments, search_issues_and_prs), CodingTools (read-only), GitTools (read-only), ReasoningTools
- **Categories:** Major Bug, Bug, Low-Hanging Fruit, Enhancement, Question, Duplicate, Slop, Stale
- **Actions:** Labels issues, posts constructive comments, closes slop/duplicates, flags priority items
- **Examples:** "review the last 10 issues", "clean up issues on agno", "triage open bugs"

### 5. Write Code (Coder)

Build features, fix bugs, write tests in isolated git worktrees.

- **Tools:** CodingTools (full), GitTools (full), GithubTools (create_pull_request), ReasoningTools
- **Workflow:** explore on main clone → create worktree → plan → edit → verify (run tests) → commit → push (via git_push) → open PR → check CI
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
- **Daily issue triage:** classifies new issues and posts to Slack (`POST /triage-issues`)
- **Daily digest:** morning activity summary — merged PRs, open PRs, new/stale issues (`POST /digest`)
- **Startup sync:** repos are synced on application startup

### 8. Daily Issue Triage

Automated daily scan that uses the Triager agent — the same agent that
handles interactive issue management requests from Slack. This ensures the
agent is continuously exercised and issues get labeled on GitHub.

**Pipeline:** Fetch (GitHub API) → Triage (Triager agent) → Post (Slack SDK)

The Triager agent categorizes each issue, labels it on GitHub, and
optionally comments with code-backed analysis. During automated runs
it does **not** close or reopen issues — only categorizes, labels, and comments.

**Schedule:** Daily at 4 AM UTC. Register with `python -m tasks.review_issues --schedule`.

**Manual trigger:** `POST /triage-issues` or `python -m tasks.review_issues`.

**Configuration:**
- Set `TRIAGE_CHANNEL` to the Slack channel ID (e.g. `C0ADMCGSJ8H`).
  Find it in Slack: right-click channel → View details → ID at the bottom.
- Requires `GITHUB_ACCESS_TOKEN` and `SLACK_TOKEN` (already required by Coda).
- Repos are read from `repos.yaml` — all configured repos are triaged.

**Extending:** To change categories or triage behavior, update the Triager
agent instructions in `coda/agents/triager.py`. To change the schedule,
update the cron in the `__main__` block of `tasks/review_issues.py`.

### 9. Daily Digest

Morning summary posted to Slack: merged PRs, open PRs waiting for
review, new issues, and stale issues. Pure GitHub API — no agent involved.

**Pipeline:** Fetch (GitHub API) → Format → Post (Slack SDK)

**Sections:**
- Merged — PRs merged in the last 24h
- Waiting for Review — all open PRs
- New Issues — issues created in the last 24h
- Stale — issues with no activity in 7+ days (shows top 10)

**Schedule:** Daily at 8 AM UTC. Register with `python -m tasks.daily_digest --schedule`.

**Manual trigger:** `POST /digest` or `python -m tasks.daily_digest`.

**Configuration:**
- Set `DIGEST_CHANNEL` to the Slack channel ID.
- Requires `GITHUB_ACCESS_TOKEN` and `SLACK_TOKEN`.
- Repos are read from `repos.yaml`.

## Agents

### Coda (Team Leader)

- **Role:** Triage requests, delegate to specialists, synthesize results
- **Mode:** Coordinate — picks members when needed, responds directly for simple things
- **Tools:** SlackTools (send_message, list_channels only)
- **Features:** agentic memory, session history (5 past sessions, 10 history runs), learnings in context
- **Routing:** see routing table in `coda/team.py` instructions

### Triager

- **Role:** Review, categorize, label, and manage GitHub issues
- **Tools:**
  - CodingTools (read_file, grep, find, ls — no write/edit/shell)
  - GitTools (read_only=True)
  - GithubTools (list_issues, get_issue, create_issue, comment_on_issue, close_issue, reopen_issue, assign_issue, label_issue, edit_issue, list_issue_comments, search_issues_and_prs, get_pull_request, get_pull_requests, get_pull_request_with_details, search_code)
  - ReasoningTools (think)

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
  - GitTools (full — includes create_worktree, remove_worktree, git_push)
  - GithubTools (get_pull_request, get_pull_requests, get_pull_request_changes, get_pull_request_comments, create_pull_request, get_issue, list_issues, create_issue, comment_on_issue)
  - ReasoningTools (think)

## Custom Tools

### GitTools (`coda/tools/git.py`)

Custom Agno Toolkit wrapping git CLI operations:

- **Read-only:** git_log, git_diff, git_blame, git_show, git_fetch, git_branches, list_repos, repo_summary, get_github_remote, list_worktrees
- **Write (Coder only):** create_worktree, remove_worktree, git_push
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
- `POST /triage-issues` — run daily issue triage via Triager agent
- `POST /digest` — run daily activity digest
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
│   │   ├── explorer.py  # Explorer agent
│   │   └── triager.py   # Triager agent
│   └── tools/
│       └── git.py       # GitTools toolkit
├── db/
│   ├── session.py       # PostgreSQL session factory + knowledge factory
│   └── url.py           # Database URL builder
├── tasks/
│   ├── sync_repos.py     # Repo sync (every 5 min)
│   ├── review_issues.py  # Issue triage (daily)
│   └── daily_digest.py   # Activity digest (daily)
├── evals/
│   ├── run.py           # Unified eval runner
│   └── cases/           # Test cases by category
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
