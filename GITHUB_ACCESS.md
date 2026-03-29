# Giving Coda Access to GitHub

## What You Need

A **Fine-grained Personal Access Token** (PAT). This is GitHub's newer, more secure token type that lets you scope access to specific repos with specific permissions.

Do **not** use a Classic PAT — those grant broad access to everything on your account.

## Create a Token

1. Go to [github.com/settings/personal-access-tokens](https://github.com/settings/personal-access-tokens)
2. Click **Generate new token**
3. Configure it:

| Field | Value |
|-------|-------|
| **Token name** | `coda` |
| **Expiration** | 90 days |
| **Resource owner** | Your personal account or your org |
| **Repository access** | **Only select repositories** — pick the repos Coda should work on |

Click **Generate token** and copy it immediately — GitHub only shows it once.

## Add to Coda

Add the token to your `.env` file:

```bash
GITHUB_ACCESS_TOKEN="github_pat_***"
```

The `compose.yaml` passes this into the container. Coda never sees the raw token — authentication happens transparently via a git credential helper.

## How It Works Inside the Container

The Dockerfile sets up a credential helper that reads `$GITHUB_ACCESS_TOKEN` from the environment when git needs to authenticate. The token is never written to disk.

This means:
- Coda uses `git clone https://github.com/...` (not SSH, not token-in-URL)
- The token is injected at the Docker layer, not in agent instructions
- No risk of the agent accidentally leaking the token in a commit or output

## Rotating Tokens

When a token expires:

1. Generate a new one with the same settings
2. Update `.env` with the new value
3. Restart the container: `docker compose up -d`