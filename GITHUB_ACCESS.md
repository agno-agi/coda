# Giving Coda Access to GitHub

## What You Need

A **Fine-grained Personal Access Token** (PAT). This is GitHub's newer, more secure token type that lets you scope access to specific repos with specific permissions.

Do **not** use a Classic PAT — those grant broad access to everything on your account.

## Token Setup

### Step 1: Create the token

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. Click **Generate new token**

### Step 2: Configure it

| Field | Value |
|-------|-------|
| **Token name** | `coda` (or whatever helps you identify it) |
| **Expiration** | 90 days (rotate quarterly — set a calendar reminder) |
| **Resource owner** | Your personal account or your org |
| **Repository access** | **Only select repositories** — pick the specific repos Coda should work on |

### Step 3: Set permissions

These are the permissions Coda needs:

| Permission | Access Level | Why |
|-----------|-------------|-----|
| **Contents** | Read and write | Clone, pull, read files, commit, push |
| **Pull requests** | Read and write | Read PRs for review, create PRs from coding tasks |
| **Metadata** | Read-only | Required by GitHub for all token operations |

**Optional permissions:**

| Permission | Access Level | Why |
|-----------|-------------|-----|
| **Issues** | Read and write | If Coda should read/create issues |
| **Workflows** | Read and write | If Coda should trigger GitHub Actions |

### Step 4: Copy the token

GitHub shows the token **once**. Copy it immediately. If you lose it, you'll need to regenerate.

## Passing the Token to Coda

Add it to your `.env` file:

```bash
GITHUB_ACCESS_TOKEN=github_pat_xxxxxxxxxxxxxxxxxxxxx
```

The `compose.yaml` passes this into the container, and the Dockerfile configures a git credential helper that uses it automatically. Coda never sees the raw token — it just runs `git clone` and authentication happens transparently.

## How It Works Inside the Container

The Dockerfile sets up a custom git credential helper:

```
git clone https://github.com/agno-agi/some-repo.git
```

Git asks the credential helper for credentials. The helper reads `$GITHUB_ACCESS_TOKEN` from the environment and returns it. The token is never written to disk — it lives only in the environment variable.

This means:
- Coda uses `git clone https://github.com/...` (not SSH, not token-in-URL)
- The token is injected at the Docker layer, not in agent instructions
- No risk of the agent accidentally leaking the token in a commit or output

## Scoping for Safety

The fine-grained token is your primary security boundary for GitHub access:

- **Repo-scoped:** The token can only access repos you explicitly selected. Even if the agent tries to clone something else, GitHub rejects it.
- **Permission-scoped:** The agent can read/write code and PRs but can't delete repos, manage settings, or access secrets.
- **Time-scoped:** The token expires. Set a rotation schedule.

Combined with the Docker container's filesystem restrictions (non-root user, only `/repos` writable), you have two independent layers of access control.

## Rotating Tokens

When a token expires:

1. Generate a new one with the same settings
2. Update `.env` with the new value
3. Restart the container: `docker compose up -d`

No code changes needed — the credential helper picks up the new value automatically.
