# ===========================================================================
# Coda - Codebase Agent
# ===========================================================================
# Runs as a non-root user (coda) with filesystem access restricted to:
#   /repos   - persistent volume for cloned repos and worktrees
#   /app     - read-only application code (writable only in dev via bind mount)
# ===========================================================================

FROM agnohq/python:3.12

# ---------------------------------------------------------------------------
# System dependencies
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    git-lfs \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Git configuration (safe defaults for agent use)
# ---------------------------------------------------------------------------
RUN git config --system init.defaultBranch main \
    && git config --system user.name "Coda" \
    && git config --system user.email "coda@agno.com" \
    && git config --system advice.detachedHead false

# ---------------------------------------------------------------------------
# Create non-root user
# ---------------------------------------------------------------------------
RUN groupadd -r coda && useradd -r -g coda -m -s /bin/bash coda

# ---------------------------------------------------------------------------
# Application code
# ---------------------------------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONPATH=/app

# ---------------------------------------------------------------------------
# Directory setup & permissions
# ---------------------------------------------------------------------------
# /repos - persistent volume for cloned repos and worktrees
RUN mkdir -p /repos \
    && chown -R coda:coda /repos \
    && chmod 755 /app

# ---------------------------------------------------------------------------
# GitHub token configuration
# ---------------------------------------------------------------------------
# The GITHUB_TOKEN env var is used for cloning private repos and GitHub API.
# Git credential helper stores it in memory (never written to disk).
# ---------------------------------------------------------------------------
RUN git config --system credential.helper 'store --file=/dev/null' \
    && printf '%s\n' \
        '#!/bin/bash' \
        'if [ -n "$GITHUB_TOKEN" ]; then' \
        '    echo "protocol=https"' \
        '    echo "host=github.com"' \
        '    echo "username=x-access-token"' \
        '    echo "password=$GITHUB_TOKEN"' \
        'fi' \
        > /usr/local/bin/git-credential-coda \
    && chmod +x /usr/local/bin/git-credential-coda \
    && git config --system credential.helper '/usr/local/bin/git-credential-coda'

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
RUN chmod +x /app/scripts/entrypoint.sh
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# ---------------------------------------------------------------------------
# Switch to non-root user
# ---------------------------------------------------------------------------
USER coda
WORKDIR /app

# ---------------------------------------------------------------------------
# Default command (overridden by compose)
# ---------------------------------------------------------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
