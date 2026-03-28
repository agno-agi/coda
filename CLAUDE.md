# Coda

Multi-agent codebase team built with Agno. Lives in Slack, understands code by searching it directly on disk, learns team conventions, and contributes code via isolated git worktrees.

## Architecture

- Team definition: `coda/team.py` (Coda team leader, TasksMode)
- Member agents: `coda/agents/coder.py` (Coder), `coda/agents/explorer.py` (Explorer)
- Shared settings: `coda/agents/settings.py` (DB, REPOS_DIR, learnings KB)
- API server: `app/main.py` (FastAPI + AgentOS + Slack interface)
- Custom tools: `coda/tools/git.py` (GitTools), `coda/tools/github.py` (GitHubTools)
- Database: PostgreSQL + pgvector (for learnings only, not code indexing)
- Repos: `/repos` volume (cloned repos, searched on disk)

## Team Structure

```
Coda (Team, TasksMode, gpt-5.4)
├── Coder — writes code in worktrees, opens PRs
├── Explorer — searches code, traces flows, reviews PRs (read-only)
└── [leader responds directly for greetings/simple questions]
```

- **Coda (leader):** Triages requests, delegates to specialists, synthesizes results
- **Coder:** CodingTools (full), GitTools, GitHubTools, ReasoningTools
- **Explorer:** CodingTools (read-only), GitTools, GitHubTools, ReasoningTools

All agents share the same `coda_learnings` knowledge base via individual LearningMachine instances.

## Key Concepts

- **TasksMode:** Leader decomposes goals into tasks, delegates to members, loops until done
- **CodingTools:** file read/write/edit, shell, grep, find, ls (Coder: all=True, Explorer: read-only)
- **GitTools:** git log/diff/blame/show, repo listing, worktree lifecycle (create/list/remove)
- **GitHubTools:** PR read/review, PR creation via GitHub REST API
- **ReasoningTools:** `think` tool for complex reasoning chains
- **LearningMachine:** saves and retrieves team conventions, patterns, gotchas (AGENTIC mode)
- **Agentic Memory:** tracks user preferences and observations (team-level only)
- **Worktrees:** each coding task gets a `coda/*` branch via `git worktree add`

## Structure

```
coda/
├── app/
│   ├── main.py          # AgentOS + Slack interface
│   └── config.yaml      # Quick prompts config
├── coda/
│   ├── team.py           # Coda team definition (leader)
│   ├── agents/
│   │   ├── settings.py   # Shared DB, paths, knowledge
│   │   ├── coder.py      # Coder agent
│   │   └── explorer.py   # Explorer agent
│   └── tools/
│       ├── git.py        # GitTools toolkit
│       └── github.py     # GitHubTools toolkit
├── db/
│   ├── session.py        # PostgreSQL session factory + knowledge factory
│   └── url.py            # Database URL builder
├── tasks/
│   └── sync_repos.py     # Repo sync scheduled task
├── evals/
│   ├── run_evals.py      # Eval runner
│   ├── test_cases.py     # Test cases
│   └── grader.py         # Grading logic
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

Connect via os.agno.com or Slack (requires SLACK_TOKEN + SLACK_SIGNING_SECRET).

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
python -m evals.run_evals              # Run all evals
python -m evals.run_evals --category security  # Run security evals
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `GITHUB_TOKEN` | Yes | Fine-grained PAT (Contents RW, PRs RW, Metadata R) |
| `SLACK_TOKEN` | No | Slack bot token |
| `SLACK_SIGNING_SECRET` | No | Slack request verification |
| `DB_*` | No | Database config (defaults to localhost) |
| `REPOS_DIR` | No | Path to cloned repos (default: /repos in Docker) |
