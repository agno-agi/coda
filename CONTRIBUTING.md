# Contributing to Coda

Thanks for your interest in contributing to Coda!

## Development Setup

```bash
# Clone the repo
git clone https://github.com/agno-agi/coda.git && cd coda

# Set up Python environment
./scripts/venv_setup.sh && source .venv/bin/activate

# Start the database
docker compose up -d coda-db

# Run Coda in CLI mode
python -m coda
```

## Code Quality

Before submitting a PR, make sure your code passes all checks:

```bash
./scripts/format.sh      # Auto-format code
./scripts/validate.sh    # Lint (ruff) + type check (mypy)
```

## Project Structure

```
coda/
├── coda/
│   ├── team.py           # Team leader definition
│   ├── agents/
│   │   ├── settings.py   # Shared DB, paths, model config
│   │   ├── coder.py      # Coder agent (writes code)
│   │   └── explorer.py   # Explorer agent (reads code)
│   └── tools/
│       └── git.py        # Git operations toolkit
├── app/main.py           # FastAPI server + Slack interface
├── db/                   # Database session + URL config
├── tasks/                # Scheduled tasks (repo sync)
└── evals/                # Evaluation test cases
```

## Making Changes

### Agent Instructions
Agent instructions live in the agent definition files (`coda/team.py`, `coda/agents/coder.py`, `coda/agents/explorer.py`). When modifying instructions, keep them specific and actionable. Test with `python -m coda` to verify agent behavior.

### Tools
Custom tools are in `coda/tools/`. Each tool method returns a human-readable string (not raw JSON). Include error handling and respect timeouts.

### Evals
Run the eval suite to verify agent behavior:

```bash
python -m evals.run_evals
python -m evals.run_evals --category security --verbose
```

## Pull Requests

1. Create a branch from `main`
2. Make your changes
3. Run `./scripts/format.sh && ./scripts/validate.sh`
4. Open a PR with a clear description of what changed and why

## Reporting Issues

When filing a bug, include:
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages
- Your environment (OS, Python version, Docker version)
