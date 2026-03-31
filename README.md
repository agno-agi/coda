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
5. Connect to the Web UI.
6. Connect to Slack.
7. Deploy to your cloud provider.

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

Create a GitHub Personal Access Token following [docs/GITHUB_ACCESS.md](/docs/GITHUB_ACCESS.md) and add it to `.env`:

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

### 5. Connect to the Web UI

Coda runs on [Agno AgentOS](https://docs.agno.com/agent-os/introduction?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=coda&utm_term=docs), which gives you a web UI to chat with Coda directly — plus monitoring and debugging tools like sessions, traces, metrics, memory, and evaluations.

1. Open [os.agno.com](https://os.agno.com?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=coda&utm_term=agentos) and log in
2. Add OS → Local → `http://localhost:8000`
3. Click "Connect"

> For production deployments, replace `localhost:8000` with your deployed URL.

### 6. Connect to Slack

With Coda running, follow [docs/SLACK_CONNECT.md](/docs/SLACK_CONNECT.md) to create your Slack app and connect it. Once connected, add the credentials to `.env`:

```bash
SLACK_TOKEN="xoxb-***"
SLACK_SIGNING_SECRET="***"
```

Then restart to pick up the Slack credentials:

```bash
docker compose up -d
```

There are two ways to talk to Coda:

**Direct message** — find Coda under **Apps** in the Slack sidebar and message it directly:

```
what repos are available?
walk me through the auth flow
```

**In a channel** — invite Coda first, then mention it in any message:

```
/invite @Coda
@Coda what are the open PRs?
```

Each thread is its own conversation — follow-up messages in the same thread don't need to @mention Coda again.

### 7. Deploy to your cloud provider

Coda comes with a script to deploy to Railway. Install the [Railway CLI](https://docs.railway.app/guides/cli), then:

```bash
railway login

# First-time setup (creates project, database, volumes)
./scripts/railway_up.sh

# Redeploy the app after code changes
./scripts/railway_redeploy.sh
```

Once deployed, update your Slack app to point at the new URL:

1. Copy your production URL from the Railway dashboard
2. Go to your [Slack App settings](https://api.slack.com/apps) → **Event Subscriptions**
3. Update the Request URL to: `https://your-production-url/slack/events`
4. Wait for Slack to verify the endpoint

If you were using ngrok for local development, you can stop it now — Slack will route all messages to your deployed instance.

> See `railway.json` to adjust CPU, memory, and replica settings.

## What Coda Can Do

### Explore Your Code

Ask a question in Slack and get an answer grounded in the actual code — with file paths and line numbers. Coda reads files, greps through them, and follows call chains to trace how things connect.

```
@Coda where is the webhook handler for Stripe events?
@Coda walk me through the signup flow
@Coda find all API endpoints that accept file uploads
@Coda what breaks if I change get_customer()?
```

### Review PRs and Branches

Coda pulls PR details, reads the changed files, diffs them against your conventions, and leaves inline comments — all from Slack.

```
@Coda review PR #42
@Coda what changed on the feature/payments branch?
@Coda compare this branch against main
```

### Manage Issues

Coda doesn't just read issues — it acts on them. It categorizes, labels, comments with code-backed analysis, flags duplicates, and closes junk. Ask it to review a batch and it'll triage the whole backlog.

```
@Coda review the last 10 issues on agno, let's wrap em up
@Coda triage the open issues and label them
@Coda clean up the stale issues
@Coda what are the open bugs? label them and flag the critical ones
```

### Stay on Top of Things

Coda doesn't just respond — it shows up on its own. Scheduled tasks run in the background and post to your Slack channels automatically.

**Daily Digest** — every morning, Coda posts a summary of your repositories: what merged yesterday, what PRs are waiting for review, what issues were opened, and what's gone stale. Like a standup that writes itself.

**Issue Triage** — on a schedule, Coda's Triager agent reviews your open issues against the actual codebase, categorizes them, labels them on GitHub, and posts a summary to Slack. The same agent that handles interactive triage requests runs the daily scan — so you know it works.

**Repo Sync** — Coda pulls the latest changes from all configured repositories every 5 minutes, so it's always working with current code.

These run out of the box. You can also build your own scheduled tasks — automatic PR review when new PRs are opened, stale branch alerts, or convention drift detection. See `tasks/` for examples.

### Write Code

When you're ready, Coda writes code in isolated git worktrees and opens PRs. Your main branch is never touched.
```
@Coda add rate limiting to /api/v1/users using the same pattern as /orders
@Coda fix the NoResultFound bug in payment_service
@Coda write integration tests for the export endpoint
```

### Learn Over Time

Coda gets sharper the more you use it.
```
Week 1:  @Coda add a new endpoint for exporting invoices
         → Writes working code using generic patterns

Week 4:  @Coda add a new endpoint for exporting invoices
         → Follows your service layer conventions, uses your team's
           error handling pattern, matches your naming style, adds
           the same logging your other export endpoints use
```

Coda's learning is powered by [Agno's Learning Machines](https://docs.agno.com/learning/overview?utm_source=github&utm_medium=example-repo&utm_campaign=agent-example&utm_content=coda&utm_term=docs).

## What Coda Doesn't Do

- **Auto-merge.** Coda opens PRs. A human merges them.
- **Touch your main branch.** All code work happens in isolated worktrees.
- **Send code outside your environment.** Coda runs in your infrastructure. Your code stays on your machines. The only external calls are to your configured LLM provider.

## Architecture

```
Slack → Coda (Team Leader, Coordinate)
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
        ├─ Triager Agent
        │   ├─ CodingTools (read-only: read/grep/find/ls)
        │   ├─ GitTools (log/diff/blame/show)
        │   ├─ GithubTools (issues: label/comment/close/search)
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
| `GITHUB_ACCESS_TOKEN` | Yes | Fine-grained PAT ([setup guide](docs/GITHUB_ACCESS.md)) |
| `SLACK_TOKEN` | No | Slack bot token ([setup guide](docs/SLACK_CONNECT.md)) |
| `SLACK_SIGNING_SECRET` | No | Slack request verification |
| `CODA_MODEL` | No | Model for all agents (default: gpt-5.4) |
| `DB_HOST` | No | PostgreSQL host (default: localhost) |
| `DB_PORT` | No | PostgreSQL port (default: 5432) |
| `DB_USER` | No | PostgreSQL user (default: ai) |
| `DB_PASS` | No | PostgreSQL password (default: ai) |
| `DB_DATABASE` | No | PostgreSQL database (default: ai) |
| `REPOS_DIR` | No | Path to cloned repos (default: /repos) |
| `TRIAGE_CHANNEL` | No | Slack channel ID for daily issue triage |

## Running Local + Production

If Coda is already deployed (e.g. on Railway), you can run a second instance locally for development. The key constraint is that each Slack app can only deliver events to one URL, so you need a separate Slack app for local.

### 1. Create a "Coda Dev" Slack app

Follow the same steps in [docs/SLACK_CONNECT.md](docs/SLACK_CONNECT.md), but create a new app (e.g. "Coda Dev") in your workspace. You'll get a separate bot token and signing secret.

### 2. Set up a local env file

```bash
cp .env .env.local
```

Edit `.env.local` and replace the Slack credentials with the ones from your "Coda Dev" app:

```bash
# .env.local — local development
SLACK_TOKEN=xoxb-***-dev-token
SLACK_SIGNING_SECRET=***-dev-secret

# These can stay the same as production
OPENAI_API_KEY=sk-***
GITHUB_ACCESS_TOKEN=github_pat_***
```

### 3. Expose localhost to Slack

Slack needs a public URL to send events to. Use [ngrok](https://ngrok.com):

```bash
ngrok http 8000
```

Copy the `https://...ngrok.io` URL. In your "Coda Dev" Slack app settings, set the Request URL to:

```
https://<your-id>.ngrok-free.app/slack/events
```

### 4. Run locally

```bash
docker compose --env-file .env.local up -d --build
```

Your production instance on Railway continues to run with `.env` and the production Slack app. Your local instance runs with `.env.local` and the dev Slack app. Both work independently.

> **Tip:** Add `.env.local` to `.gitignore` if it isn't already. Never commit either env file.

<p align="center">Built on <a href="https://github.com/agno-agi/agno">Agno</a> · the runtime for agentic software</p>
