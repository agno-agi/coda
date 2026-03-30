#!/bin/bash

############################################################################
#
#    Agno Railway Setup (first-time provisioning)
#
#    Usage: ./scripts/railway_up.sh
#    Redeploy: ./scripts/railway_redeploy.sh
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
railway add -s pgvector -i agnohq/pgvector:18 \
    -v "POSTGRES_USER=${DB_USER:-ai}" \
    -v "POSTGRES_PASSWORD=${DB_PASS:-ai}" \
    -v "POSTGRES_DB=${DB_DATABASE:-ai}" \
    -v "PGDATA=/var/lib/postgresql/data"

echo ""
echo ""
echo -e "${BOLD}Adding database volume...${NC}"
railway service link pgvector
railway volume add -m /var/lib/postgresql/data 2>/dev/null || echo -e "${DIM}Volume already exists or skipped${NC}"

echo ""
echo -e "${DIM}Waiting 15s for database...${NC}"
sleep 15

echo ""
echo -e "${BOLD}Creating application service...${NC}"
echo ""
railway add -s coda \
    -v "DB_USER=${DB_USER:-ai}" \
    -v "DB_PASS=${DB_PASS:-ai}" \
    -v "DB_HOST=pgvector.railway.internal" \
    -v "DB_PORT=${DB_PORT:-5432}" \
    -v "DB_DATABASE=${DB_DATABASE:-ai}" \
    -v "DB_DRIVER=postgresql+psycopg" \
    -v "WAIT_FOR_DB=True" \
    -v "REPOS_DIR=/repos" \
    -v "OPENAI_API_KEY=${OPENAI_API_KEY}" \
    -v "GITHUB_ACCESS_TOKEN=${GITHUB_ACCESS_TOKEN:-}" \
    -v "SLACK_TOKEN=${SLACK_TOKEN:-}" \
    -v "SLACK_SIGNING_SECRET=${SLACK_SIGNING_SECRET:-}" \
    -v "TRIAGE_CHANNEL=${TRIAGE_CHANNEL:-}" \
    -v "PORT=8000"

echo ""
echo ""
echo -e "${BOLD}Adding repos volume...${NC}"
railway service link coda
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
