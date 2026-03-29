# Coda

A code companion that lives in Slack.

Coding agents help us write code faster, but most engineering work isn't writing code. It's understanding how things work, reviewing PRs, figuring out what broke and why, triaging the backlog, and deciding what's safe to change. That work happens in Slack and GitHub, not in an editor.

Coda fills that gap. It answers architecture questions like "how does auth work" or "where is the model API call". It reviews PRs and open branches, diffs them against your conventions, and leaves comments. It reads open issues and flags the urgent ones worth tackling next.

Most importantly, Coda lives in Slack and works alongside your team.

Coda also learns and improves with use. It picks up your coding standards, conventions, and patterns. Over time it stops waiting to be asked — it reviews open issues on a schedule, flags low-hanging fruit, and proposes changes. It shows up in your Slack channel with a summary: here's what's worth tackling, here's why, here's how the code already handles similar cases.

Coda can write code too — in isolated worktrees that never touch main — but that's not its main job. Coda is the teammate who knows what's going on in the codebase, and is always available to talk about it.

## Get Started

1. Create your Coda repo from this template.
2. Configure GitHub and model connections.
3. Tell Coda which repos to learn.
4. Run locally.
5. Connect to Slack.
6. Deploy to your cloud provider.

### 1. Create your repo

Click **Use this template** to create your own repo, then clone it:

```bash
git clone https://github.com/your-org/coda.git && cd coda
```

Or clone directly:
```bash
git clone https://github.com/agno-agi/coda.git && cd coda
```

### 2. Configure GitHub and model connections

Copy the example environment file:

```bash
cp example.env .env
```

Create an [OpenAI API key](https://platform.openai.com/api-keys) and add it to `.env`:

```bash
OPENAI_API_KEY="sk-svcacct-***"
```

Create a GitHub Personal Access Token following [GITHUB_ACCESS.md](/GITHUB_ACCESS.md) and add it to `.env`:

```bash
GITHUB_ACCESS_TOKEN="github_pat_***"
```

### 3. Tell Coda which repos to learn

Edit `repos.yaml` and add your repositories:

```yaml
repos:
  - url: https://github.com/your-org/your-repo
    branch: main
```

> Author's note: I recommend just using the agno repo as a starting point, so you have some test questions you can play around with.

### 4. Run locally

> Make sure Docker Desktop is installed and running.

```bash
docker compose up -d --build
```

Confirm Coda is running at [http://localhost:8000/docs](http://localhost:8000/docs).

### 5. Connect to Slack

With Coda running, follow [SLACK_CONNECT.md](/SLACK_CONNECT.md) to create your Slack app and connect it. Once connected, add the credentials to `.env`:

```bash
SLACK_TOKEN="xoxb-***"
SLACK_SIGNING_SECRET="***"
```

Then restart to pick up the Slack credentials:

```bash
docker compose up -d
```

Try it out in Slack:

```
@Coda hi
@Coda what repos are available?
```

### 6. Deploy to your cloud provider

Coda comes with a script to deploy to Railway. Install the [Railway CLI](https://docs.railway.app/guides/cli), then:

```bash
railway login

./scripts/railway_up.sh
```

## What Coda Can Do

### Explore Your Code

Coda searches code directly on disk. It reads actual files, greps through them, and follows the call chain to give you real answers.

```
@Coda where is the webhook handler for Stripe events?
@Coda walk me through the signup flow
@Coda find all API endpoints that accept file uploads
@Coda what breaks if I change get_customer()?
```

### Review PRs and Branches

Coda pulls PR details, reads the changed files, diffs them against your conventions, and leaves comments — all from Slack.

```
@Coda review PR #42
@Coda what changed on the feature/payments branch?
@Coda compare this branch against main
```

### Triage Issues

Coda reads your open issues and understands them in the context of the actual code. On a schedule, it reviews recent issues and posts a summary to Slack — what's urgent, what's low-hanging, and what the code already does nearby.

```
@Coda what are the open issues?
@Coda which of these issues can we tackle quickly?
```

### Write Code

Coda creates isolated git worktrees, writes code following learned conventions, and opens PRs. Your main branch is never touched.

```
@Coda add rate limiting to /api/v1/users using the same pattern as /orders
@Coda fix the NoResultFound bug in payment_service
@Coda write integration tests for the export endpoint
```

### Learn Over Time

Every interaction feeds Coda's learning system. It picks up naming conventions, error handling patterns, how your team structures services, which abstractions to use and which to avoid. This knowledge is recalled on every future interaction.

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

- **Auto-merge.** Coda opens PRs. A human merges them.
- **Touch your main branch.** All code work happens in isolated worktrees.
- **Send code outside your environment.** Coda runs in your infrastructure. Your code stays on your machines. The only external calls are to your configured LLM provider.

## Architecture

```
Slack → Coda (Team Leader, TasksMode)
        ├─ Coder Agent
        │   ├─ CodingTools (read/write/edit/shell/grep/find)
        │   ├─ GitTools (log/diff/blame/worktree)
        │   ├─ GithubTools (PR read/create, issues)
        │   └─ ReasoningTools (think/analyze)
        ├─ Explorer Agent
        │   ├─ CodingTools (read-only: read/grep/find/ls)
        │   ├─ GitTools (log/diff/blame/show)
        │   ├─ GithubTools (PR read/review, code search)
        │   └─ ReasoningTools (think/analyze)
        ├─ SlackTools (notifications, leader only)
        ├─ LearningMachine (conventions/patterns, shared)
        └─ Agentic Memory (user context, leader only)
```

## Local Development

```bash
# Create and activate virtual environment
./scripts/venv_setup.sh
source .venv/bin/activate

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
| `GITHUB_ACCESS_TOKEN` | Yes | Fine-grained PAT ([setup guide](GITHUB_ACCESS.md)) |
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