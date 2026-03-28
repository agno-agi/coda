#!/bin/bash

############################################################################
#
#    Agno Railway Deployment
#
#    Usage: ./scripts/railway_up.sh
#
#    Prerequisites:
#      - Railway CLI installed
#      - Logged in via `railway login`
#      - OPENAI_API_KEY set in environment
#
############################################################################

set -e

# Colors
ORANGE='\033[38;5;208m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${ORANGE}"
cat << 'BANNER'
     █████╗  ██████╗ ███╗   ██╗ ██████╗
    ██╔══██╗██╔════╝ ████╗  ██║██╔═══██╗
    ███████║██║  ███╗██╔██╗ ██║██║   ██║
    ██╔══██║██║   ██║██║╚██╗██║██║   ██║
    ██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝
    ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝
BANNER
echo -e "${NC}"

# Load .env if it exists
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
    echo -e "${DIM}Loaded .env${NC}"
fi

# Preflight
if ! command -v railway &> /dev/null; then
    echo "Railway CLI not found. Install: https://docs.railway.app/guides/cli"
    exit 1
fi

if [[ -z "$OPENAI_API_KEY" ]]; then
    echo "OPENAI_API_KEY not set. Add to .env or export it."
    exit 1
fi

echo -e "${BOLD}Initializing project...${NC}"
echo ""
railway init -n "coda"

echo ""
echo -e "${BOLD}Deploying PgVector database...${NC}"
echo ""
railway deploy -t 3jJFCA

echo ""
echo -e "${DIM}Waiting 10s for database...${NC}"
sleep 10

echo ""
echo -e "${BOLD}Creating application service...${NC}"
echo ""
railway add --service coda \
    --variables 'DB_USER=${{pgvector.PGUSER}}' \
    --variables 'DB_PASS=${{pgvector.PGPASSWORD}}' \
    --variables 'DB_HOST=${{pgvector.PGHOST}}' \
    --variables 'DB_PORT=${{pgvector.PGPORT}}' \
    --variables 'DB_DATABASE=${{pgvector.PGDATABASE}}' \
    --variables "DB_DRIVER=postgresql+psycopg" \
    --variables "WAIT_FOR_DB=True" \
    --variables "REPOS_DIR=/repos" \
    --variables "OPENAI_API_KEY=${OPENAI_API_KEY}" \
    --variables "GITHUB_ACCESS_TOKEN=${GITHUB_ACCESS_TOKEN:-}" \
    --variables "SLACK_TOKEN=${SLACK_TOKEN:-}" \
    --variables "SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET:-}" \
    --variables "PORT=8000"

echo ""
echo -e "${BOLD}Adding persistent volume...${NC}"
echo ""
railway volume add -m /repos 2>/dev/null || echo -e "${DIM}Volume already exists or skipped${NC}"

echo ""
echo -e "${BOLD}Deploying application...${NC}"
echo ""
railway up --service coda -d

echo ""
echo -e "${BOLD}Creating domain...${NC}"
echo ""
railway domain --service coda

echo ""
echo -e "${BOLD}Done.${NC} Domain may take ~5 minutes."
echo -e "${DIM}Logs: railway logs --service coda${NC}"
echo ""
