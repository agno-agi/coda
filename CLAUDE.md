# Coda

A code companion that lives in Slack. Understands code by searching it directly on disk, reviews PRs and branches, triages issues, learns team conventions, and contributes code via isolated git worktrees.

The canonical specification is `docs/SPEC.md`. All other documentation derives from it.

## Architecture

- Team definition: `coda/team.py` (Coda team leader, Coordinate mode)
- Member agents: `coda/agents/coder.py` (Coder), `coda/agents/explorer.py` (Explorer)
- Shared settings: `coda/settings.py` (DB, REPOS_DIR, learnings KB)
- API server: `app/main.py` (FastAPI + AgentOS + Slack interface)
- Custom tools: `coda/tools/git.py` (GitTools)
- GitHub tools: Agno built-in `GithubTools` (scoped per agent)
- Database: PostgreSQL + pgvector (for learnings only, not code indexing)
- Repos: `/repos` volume (cloned repos, searched on disk)

## Team Structure
```
Coda (Team, Coordinate, gpt-5.4)
├── Coder — writes code in worktrees, opens PRs
├── Explorer — searches code, traces flows, reviews PRs/branches, triages issues (read-only)
└── [leader responds directly for greetings/simple questions]
```

- **Coda (leader):** Triages requests, delegates to specialists, synthesizes results
- **Coder:** CodingTools (full), GitTools, GithubTools (write), ReasoningTools
- **Explorer:** CodingTools (read-only), GitTools, GithubTools (read-only), ReasoningTools

All agents share the same `coda_learnings` knowledge base via individual LearningMachine instances.

## Key Concepts

- **Coordinate mode:** Leader picks the right specialist, delegates with context, synthesizes results
- **CodingTools:** file read/write/edit, shell, grep, find, ls (Coder: all=True, Explorer: read-only)
- **GitTools:** git log/diff/blame/show, repo listing, branch listing/diffing, worktree lifecycle (create/list/remove), safe push (coda/* only)
- **GithubTools:** Agno built-in — PR read/review/create/comment, issues read/comment, code search (scoped via include_tools)
- **ReasoningTools:** `think` tool for complex reasoning chains
- **LearningMachine:** saves and retrieves team conventions, patterns, gotchas (AGENTIC mode)
- **Agentic Memory:** tracks user preferences and observations (team-level only)
- **Worktrees:** each coding task gets a `coda/*` branch via `git worktree add`
- **Scheduled Tasks:** repo sync (every 5 min), issue triage (daily on weekdays)

## Structure
```
coda/
├── app/
│   ├── main.py          # AgentOS + Slack interface
│   └── config.yaml      # Quick prompts config
├── coda/
│   ├── team.py           # Coda team definition (leader)
│   ├── agents/
│   │   ├── coder.py      # Coder agent
│   │   └── explorer.py   # Explorer agent
│   ├── settings.py       # Shared DB, paths, knowledge
│   └── tools/
│       └── git.py        # GitTools toolkit
├── db/
│   ├── session.py        # PostgreSQL session factory + knowledge factory
│   └── url.py            # Database URL builder
├── tasks/
│   ├── sync_repos.py     # Repo sync (every 5 min)
│   └── review_issues.py  # Issue triage (daily, weekdays)
├── evals/
│   ├── run.py            # Unified eval runner
│   └── cases/            # Test cases by category (security, routing, exploration, synthesis, refusal)
├── docs/
│   ├── SPEC.md           # Canonical specification
│   ├── GITHUB_ACCESS.md  # GitHub PAT setup guide
│   └── SLACK_CONNECT.md  # Slack app setup guide
├── scripts/
├── compose.yaml
├── Dockerfile
├── repos.yaml            # Repository configuration
├── pyproject.toml
└── requirements.txt
```

## Running
```bash
docker compose up -d --build
```

Connect via Slack (see docs/SLACK_CONNECT.md) or CLI (`python -m coda`).

## Setup Flow

1. Clone repo
2. Configure `.env` (OpenAI key, GitHub PAT)
3. Configure `repos.yaml` (which repos to learn)
4. Run locally (`docker compose up -d --build`)
5. Connect to Slack (docs/SLACK_CONNECT.md — requires app to be running first)
6. Deploy to cloud (optional)

## Local Development
```bash
./scripts/venv_setup.sh && source .venv/bin/activate
docker compose up -d coda-db
python -m coda  # CLI mode
```

## Commands
```bash
./scripts/venv_setup.sh && source .venv/bin/activate
./scripts/format.sh      # Format code
./scripts/validate.sh    # Lint + type check
python -m coda           # CLI mode
python -m evals.run                    # Run all evals
python -m evals.run --category security  # Run single category
python -m evals.run --verbose            # Show details
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `GITHUB_ACCESS_TOKEN` | Yes | Fine-grained PAT (Contents RW, PRs RW, Metadata R) |
| `SLACK_TOKEN` | No | Slack bot token |
| `SLACK_SIGNING_SECRET` | No | Slack request verification |
| `DB_*` | No | Database config (defaults to localhost) |
| `REPOS_DIR` | No | Path to cloned repos (default: /repos in Docker) |