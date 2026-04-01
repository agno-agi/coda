#!/bin/bash

############################################################################
#
#    Agno Railway Environment Sync
#
#    Usage: ./scripts/railway_env.sh
#
#    Reads .env and pushes all variables to the Railway coda service.
#    Handles multiline values (e.g. PEM keys) correctly.
#
############################################################################

set -e

# Colors
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

ENV_FILE="${1:-.env}"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "File not found: $ENV_FILE"
    exit 1
fi

if ! command -v railway &> /dev/null; then
    echo "Railway CLI not found. Install: https://docs.railway.app/guides/cli"
    exit 1
fi

if ! railway status &> /dev/null; then
    echo "Not linked to a Railway project. Run ./scripts/railway_up.sh first."
    exit 1
fi

echo ""
echo -e "${BOLD}Syncing env vars from ${ENV_FILE} to Railway...${NC}"
echo ""

# Parse .env handling multiline values (PEM keys, etc.)
count=0
current_key=""
current_value=""

while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines and comments (only when not inside a multiline value)
    if [[ -z "$current_key" ]]; then
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    fi

    if [[ -z "$current_key" ]]; then
        # Start of a new variable
        current_key="${line%%=*}"
        current_value="${line#*=}"
    else
        # Continuation of a multiline value
        current_value="${current_value}
${line}"
    fi

    # Check if the value is complete (not in the middle of a PEM block)
    if [[ "$current_value" == *"-----BEGIN"* && "$current_value" != *"-----END"* ]]; then
        continue
    fi

    # Strip surrounding quotes if present
    current_value="${current_value#\"}"
    current_value="${current_value%\"}"
    current_value="${current_value#\'}"
    current_value="${current_value%\'}"

    echo -e "${DIM}  Setting ${current_key}${NC}"
    railway variables --set "${current_key}=${current_value}" --service coda 2>/dev/null
    count=$((count + 1))

    current_key=""
    current_value=""
done < "$ENV_FILE"

echo ""
echo -e "${BOLD}Done.${NC} Synced ${count} variable(s) to Railway."
echo -e "${DIM}Railway will auto-redeploy if values changed.${NC}"
echo ""
