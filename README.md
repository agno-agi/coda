# Coda — a code companion that lives in Slack

Coding agents help you write code faster, but most engineering work isn't writing code — it's understanding how things work, reviewing PRs, figuring out what broke, and triaging the backlog. That work happens in Slack and GitHub, not in an editor. Coda fills that gap: it answers architecture questions with file-and-line citations, reviews PRs against your conventions, triages issues, plans work, and (when asked) writes code in isolated worktrees that never touch `main`. It's built for engineering teams who want a teammate that knows the codebase and is always available to talk about it.

## How it works

Coda is a coordinate-mode [Agno](https://github.com/agno-agi/agno) team. A leader routes each request to a specialist:

| Agent | Access | Does |
|---|---|---|
| **Explorer** | read-only code + git + GitHub | code questions, flow tracing, PR/branch review |
| **Planner** | read-only code + GitHub issues | breaks features into ordered, scoped GitHub issues |
| **Triager** | read-only code + GitHub issues | categorizes, labels, comments on, and closes issues |
| **Coder** | read-write code, git worktrees, PRs | features, fixes, tests — always on a branch, never `main` |
| **Researcher** | web search (only if `PARALLEL_API_KEY` is set) | docs, library APIs, advisories, error messages |

Around the team:

- **Learning loop** — a shared [Learning Machine](https://docs.agno.com/learning/overview) (agentic mode) picks up your conventions and patterns from every interaction; agentic memory tracks user context. Coda gets sharper the more you use it.
- **Repos** — listed in `repos.yaml`, cloned into a persistent volume, and re-synced every 5 minutes by a built-in schedule.
- **Daily digest** — with `DIGEST_CHANNEL` and Slack credentials set, Coda posts a morning summary (merged PRs, PRs awaiting review, new and stale issues) at 08:00 UTC. Schedules are registered idempotently on startup; scheduled *issue triage* is currently disabled — run it manually with `python -m tasks.review_issues`.
- **Guardrails** — Coda opens PRs, humans merge them. All code work happens in isolated worktrees. Code never leaves your infrastructure except calls to your configured LLM provider.

## Quick start

Requires Docker. Get an [OpenAI API key](https://platform.openai.com/api-keys) and a fine-grained GitHub PAT ([docs/GITHUB_ACCESS.md](docs/GITHUB_ACCESS.md)).

```bash
git clone https://github.com/agno-agi/coda.git && cd coda

cp example.env .env
# edit .env: set OPENAI_API_KEY and GITHUB_ACCESS_TOKEN

# edit repos.yaml: list the repos Coda should learn
```

```bash
docker compose up -d --build
```

This starts Postgres (pgvector) and the API with hot reload. Confirm it's up at [http://localhost:8000/docs](http://localhost:8000/docs).

## Interfaces

- **Slack** — the main interface. Follow [docs/SLACK_CONNECT.md](docs/SLACK_CONNECT.md) to create the Slack app, then set `SLACK_TOKEN` and `SLACK_SIGNING_SECRET` in `.env` and `docker compose up -d` to restart. DM Coda directly, or `/invite @Coda` to a channel and mention it. Each thread is its own session; follow-ups in a thread don't need a re-mention.
- **AgentOS web UI** — open [os.agno.com](https://os.agno.com), add OS → Local → `http://localhost:8000`, and connect. Gives you chat plus sessions, traces, metrics, memory, and evals.
- **Terminal** — `python -m coda` runs a CLI chat loop against the team (needs the venv and a running database; see [Evals](#evals) for setup).

## Deploy

Coda ships with Railway scripts. Install the [Railway CLI](https://docs.railway.app/guides/cli), `railway login`, then:

```bash
./scripts/railway_up.sh        # first-time: project, pgvector DB, app service, domain
./scripts/railway_env.sh       # sync env vars after changing .env (handles multiline PEM keys)
./scripts/railway_redeploy.sh  # redeploy after code changes
```

Then point your Slack app's **Event Subscriptions** Request URL at `https://<your-domain>/slack/events`.

Two production notes:

- **Run a single replica.** The built-in scheduler (repo sync, daily digest) assumes one instance; multiple replicas double-fire scheduled tasks.
- **Auth is enforced in production.** With `RUNTIME_ENV=prd` (the default outside compose), AgentOS RBAC is on: set `JWT_VERIFICATION_KEY` to the public key from [os.agno.com](https://os.agno.com) → Settings, or all requests are rejected. From agno 2.7 the key is required at boot, so set it before deploying. Local compose runs `RUNTIME_ENV=dev` with auth off.

## Configuration

Set in `.env` (see [`example.env`](example.env); never commit it):

| Variable | Required | Description |
|---|---|---|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `GITHUB_ACCESS_TOKEN` | Yes | Fine-grained PAT ([setup](docs/GITHUB_ACCESS.md)) |
| `SLACK_TOKEN` | For Slack | Bot token ([setup](docs/SLACK_CONNECT.md)) |
| `SLACK_SIGNING_SECRET` | For Slack | Slack request verification |
| `PARALLEL_API_KEY` | No | Enables the Researcher agent ([parallel.ai](https://parallel.ai)) |
| `DIGEST_CHANNEL` | No | Slack channel ID for the daily digest |
| `TRIAGE_CHANNEL` | No | Slack channel ID for issue-triage summaries (manual runs) |
| `JWT_VERIFICATION_KEY` | Production | RBAC public key from [os.agno.com](https://os.agno.com) |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASS` / `DB_DATABASE` | No | Postgres connection (defaults: `localhost`/`5432`/`ai`/`ai`/`ai`) |

## Evals

```bash
./scripts/venv_setup.sh && source .venv/bin/activate
docker compose up -d coda-db   # evals need the database

python -m evals                        # all categories
python -m evals --category security    # one of: security, routing, exploration, synthesis, refusal
python -m evals --verbose              # show response previews and failure reasons
```

Lint and type-check with `./scripts/format.sh` and `./scripts/validate.sh`.

## Source / links

- [docs/SPEC.md](docs/SPEC.md) — full product and architecture spec
- [docs/GITHUB_ACCESS.md](docs/GITHUB_ACCESS.md) — GitHub token setup
- [docs/SLACK_CONNECT.md](docs/SLACK_CONNECT.md) — Slack app setup (to run local and production side by side, create a second "Coda Dev" Slack app and start compose with `--env-file .env.local`)
- [Agno docs](https://docs.agno.com) · [AgentOS security](https://docs.agno.com/agent-os/security/overview)

<p align="center">Built on <a href="https://github.com/agno-agi/agno">Agno</a> · the runtime for agentic software</p>
