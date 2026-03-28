# Coda

A multi-agent team that learns your codebase and lives in Slack.

Ask Coda about your code and get answers grounded in what's actually on disk. It traces call chains, maps dependencies, explains architecture decisions, and learns your team's conventions over time. When you're ready, it writes code in isolated worktrees following the patterns it's learned.

## Get Started

To get Coda up and running:

1. Create your Coda repo from this template.
2. Configure Slack, GitHub, and model provider.
3. Run locally or deploy to your cloud.

### 1. Create your repo

Click **Use this template** to create your own repo, then clone it:

```bash
git clone https://github.com/your-org/coda.git && cd coda
```

Or clone directly:

```bash
git clone --depth 1 https://github.com/agno-agi/coda.git && cd coda
git remote remove origin
```

### 2. Configure Slack, GitHub and model provider

```bash
cp example.env .env
# Edit .env: add OPENAI_API_KEY and GITHUB_TOKEN

cp example.repos.yaml repos.yaml
# Edit repos.yaml: add the repositories Coda should learn
```

Example `repos.yaml`

```yaml
repos:
  - url: https://github.com/agno-agi/agno
    branch: main
```

### 3a. Run Coda locally

```bash
docker compose up -d --build

# Confirm Coda is running
open http://localhost:8000/docs
```

### 3b. Run Coda on Railway

```sh
railway login

./scripts/railway_up.sh
```

## What Coda Can Do

Coda earns trust progressively. You start by asking questions. Then you let it write code. Over time, it learns your patterns and its contributions get sharper.

### Explore Your Code

Coda searches code directly on disk. It reads actual files, greps through them, and follows the call chain to give you real answers.

```
@Coda where is the webhook handler for Stripe events?
@Coda walk me through the signup flow
@Coda find all API endpoints that accept file uploads
@Coda what breaks if I change get_customer()?
```

### Write Code

Coda creates isolated git worktrees, writes code following learned conventions, and opens PRs. Your main branch is never touched.

```
@Coda add rate limiting to /api/v1/users using the same pattern as /orders
@Coda fix the NoResultFound bug in payment_service
@Coda write integration tests for the export endpoint
```

### Learn Over Time

Coda is useful immediately for code exploration. Its code contributions improve as it learns your team's patterns.

Every interaction feeds Coda's learning system. It persists what it learns about your codebase: naming conventions, error handling patterns, how your team structures services, which abstractions to use and which to avoid. This knowledge is stored as structured conventions and recalled on every future interaction.

The result is compound improvement. The Coda that writes code in week four understands your codebase in a way that week-one Coda couldn't. It stops suggesting patterns your team has moved away from. It picks up on the way you name things, the way you handle errors, the way you organize modules.

```
Week 1:  @Coda add a new endpoint for exporting invoices
         → Writes working code using generic patterns

Week 4:  @Coda add a new endpoint for exporting invoices
         → Follows your service layer conventions, uses your team's
           error handling pattern, matches your naming style, adds
           the same logging your other export endpoints use
```

Coda's learning is powered by [Agno's Learning Machines](https://docs.agno.com/learning/overview).

## What Coda Doesn't Do

Transparency builds trust. Here's what Coda won't do:

- **Auto-merge.** Coda opens PRs. A human merges them.
- **Touch your main branch.** All code work happens in isolated worktrees.
- **Send code outside your environment.** Coda runs in your infrastructure. Your code stays on your machines. The only external calls are to your configured LLM provider.
- **Hallucinate file paths.** Coda reads real files on disk. If it can't find something, it says so.

## Architecture

```
Slack → Coda (Team Leader, TasksMode)
        ├─ Coder Agent
        │   ├─ CodingTools (read/write/edit/shell/grep/find)
        │   ├─ GitTools (log/diff/blame/worktree)
        │   ├─ GitHubTools (PR read/create)
        │   └─ ReasoningTools (think/analyze)
        ├─ Explorer Agent
        │   ├─ CodingTools (read-only: read/grep/find/ls)
        │   ├─ GitTools (log/diff/blame/show)
        │   ├─ GitHubTools (PR read/review)
        │   └─ ReasoningTools (think/analyze)
        ├─ SlackTools (notifications, leader only)
        ├─ LearningMachine (conventions/patterns, shared)
        └─ Agentic Memory (user context, leader only)
```

## Connect to Slack

Coda works standalone via CLI, but it's designed to live in Slack where your team already asks questions.

See [SLACK_CONNECT.md](SLACK_CONNECT.md) for the full setup guide — creating the Slack app, configuring scopes and events, and connecting it to Coda.

## Local Development

```bash
# Setup
./scripts/venv_setup.sh && source .venv/bin/activate

# Start database
docker compose up -d coda-db

# Run CLI
python -m coda

# Run evals
python -m evals.run_evals --category security

# Format & lint
./scripts/format.sh
./scripts/validate.sh
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `GITHUB_TOKEN` | Yes | Fine-grained PAT ([setup guide](GITHUB_ACCESS.md)) |
| `SLACK_TOKEN` | No | Slack bot token ([setup guide](SLACK_CONNECT.md)) |
| `SLACK_SIGNING_SECRET` | No | Slack request verification |
| `CODA_MODEL` | No | Model for all agents (default: gpt-5.4) |
| `DB_HOST` | No | PostgreSQL host (default: localhost) |
| `DB_PORT` | No | PostgreSQL port (default: 5432) |
| `DB_USER` | No | PostgreSQL user (default: ai) |
| `DB_PASS` | No | PostgreSQL password (default: ai) |
| `DB_DATABASE` | No | PostgreSQL database (default: ai) |
| `REPOS_DIR` | No | Path to cloned repos (default: /repos) |

<p align="center">Built on <a href="https://github.com/agno-agi/agno">Agno</a> · the runtime for agentic software</p>