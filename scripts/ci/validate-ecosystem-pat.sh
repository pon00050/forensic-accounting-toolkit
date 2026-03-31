#!/usr/bin/env bash
# validate-ecosystem-pat.sh
#
# Validates that a GitHub PAT has the correct scopes to serve as ECOSYSTEM_PAT.
# Run locally before adding the secret to GitHub:
#
#   export ECOSYSTEM_PAT=ghp_your_token_here
#   bash scripts/ci/validate-ecosystem-pat.sh
#
# What it checks:
#   1. Token is set and non-empty
#   2. Token has 'repo' scope (needed to push to sibling repos)
#   3. Token has 'project' scope (needed to add items to project board)
#   4. Token can access all 13 sibling repos
#
# If all checks pass, follow the instructions at the bottom to save it.

set -euo pipefail

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "${GRN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; FAILED=1; }
warn() { echo -e "${YLW}!${NC} $1"; }

FAILED=0

REPOS=(
  kr-company-registry
  kr-trading-calendar
  kr-beneish
  kr-derivatives
  jfia-catalog
  jfia-forensic
  kr-enforcement-cases
  kr-forensic-core
  krff-shell
  kr-dart-pipeline
  kr-anomaly-scoring
  kr-stat-tests
  kr-real-estate
)

echo "=== ECOSYSTEM_PAT Validation ==="
echo ""

# ------------------------------------------------------------------
# 1. Token is set
# ------------------------------------------------------------------
if [ -z "${ECOSYSTEM_PAT:-}" ]; then
  fail "ECOSYSTEM_PAT is not set. Export it first:"
  echo "    export ECOSYSTEM_PAT=ghp_your_token_here"
  echo ""
  exit 1
fi
pass "ECOSYSTEM_PAT is set (${#ECOSYSTEM_PAT} chars)"

# ------------------------------------------------------------------
# 2. Scopes — check the X-OAuth-Scopes header
# ------------------------------------------------------------------
echo ""
echo "--- Checking token scopes ---"

SCOPES=$(curl -s -I \
  -H "Authorization: Bearer $ECOSYSTEM_PAT" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/user" \
  | grep -i "^x-oauth-scopes:" | tr -d '\r' | sed 's/x-oauth-scopes: //i' || echo "")

if [ -z "$SCOPES" ]; then
  warn "Could not read token scopes (fine-grained PATs don't expose X-OAuth-Scopes). Continuing with repo access checks."
else
  echo "  Scopes: $SCOPES"
  if echo "$SCOPES" | grep -q '\brepo\b'; then
    pass "repo scope present"
  else
    fail "repo scope MISSING — needed to push to sibling repos"
  fi
  if echo "$SCOPES" | grep -q '\bproject\b'; then
    pass "project scope present (or write:project)"
  elif echo "$SCOPES" | grep -q 'write:project'; then
    pass "write:project scope present"
  else
    fail "project scope MISSING — needed to add items to GitHub Projects v2 board"
    warn "Fine-grained PATs: enable 'Projects (read & write)' under account permissions"
    warn "Classic PATs: enable 'project' checkbox"
  fi
fi

# ------------------------------------------------------------------
# 3. Auth as the correct user
# ------------------------------------------------------------------
echo ""
echo "--- Checking identity ---"

USER=$(curl -s \
  -H "Authorization: Bearer $ECOSYSTEM_PAT" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/user" | python3 -c "import json,sys; print(json.load(sys.stdin).get('login','?'))" 2>/dev/null || echo "ERROR")

if [ "$USER" = "pon00050" ]; then
  pass "Authenticated as pon00050"
elif [ "$USER" = "ERROR" ] || [ "$USER" = "?" ]; then
  fail "Token is invalid or expired — could not authenticate"
  exit 1
else
  warn "Authenticated as '$USER' (expected pon00050). This PAT will work but belongs to a different account."
fi

# ------------------------------------------------------------------
# 4. Access to all 13 sibling repos
# ------------------------------------------------------------------
echo ""
echo "--- Checking sibling repo access (${#REPOS[@]} repos) ---"

MISSING=()
for repo in "${REPOS[@]}"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $ECOSYSTEM_PAT" \
    -H "Accept: application/vnd.github+json" \
    "https://api.github.com/repos/pon00050/$repo")
  if [ "$STATUS" = "200" ]; then
    pass "$repo"
  else
    fail "$repo (HTTP $STATUS)"
    MISSING+=("$repo")
  fi
done

# ------------------------------------------------------------------
# 5. Project board access
# ------------------------------------------------------------------
echo ""
echo "--- Checking project board access ---"

PROJECT_ID=$(curl -s \
  -H "Authorization: Bearer $ECOSYSTEM_PAT" \
  -H "Content-Type: application/json" \
  "https://api.github.com/graphql" \
  -d '{"query":"{ user(login: \"pon00050\") { projectV2(number: 1) { id title } } }"}' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
p = d.get('data', {}).get('user', {}).get('projectV2')
if p:
    print(f\"{p['id']} ({p['title']})\")
else:
    errors = d.get('errors', [])
    print('ERROR: ' + (errors[0].get('message','unknown') if errors else 'no data'))
" 2>/dev/null || echo "ERROR")

if echo "$PROJECT_ID" | grep -q "^ERROR"; then
  fail "Cannot access project board: $PROJECT_ID"
  warn "Fine-grained PATs need 'Projects (read & write)' permission."
  warn "Classic PATs need 'project' scope."
else
  pass "Project board accessible: $PROJECT_ID"
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo ""
echo "================================"
if [ "$FAILED" -eq 0 ]; then
  echo -e "${GRN}All checks passed.${NC}"
  echo ""
  echo "Add the secret to GitHub:"
  echo "  1. Go to: https://github.com/pon00050/forensic-accounting-toolkit/settings/secrets/actions"
  echo "  2. Click 'New repository secret'"
  echo "  3. Name:  ECOSYSTEM_PAT"
  echo "  4. Value: paste your token"
  echo "  5. Click 'Add secret'"
  echo ""
  echo "Workflows that unlock once this is set:"
  echo "  - issue-to-board-sync.yml  (adds agent-task issues to project board)"
  echo "  - tier1-doc-drift.yml      (auto-fixes stale names in sibling repos)"
  echo "  - tier4-autofix.yml        (pushes fix branches to sibling repos)"
else
  echo -e "${RED}${FAILED} check(s) failed.${NC}"
  echo ""
  echo "Create a new PAT at:"
  echo "  https://github.com/settings/tokens"
  echo ""
  echo "Classic PAT — required scopes:"
  echo "  [x] repo     (full control of private repositories)"
  echo "  [x] project  (full control of projects)"
  echo ""
  echo "Fine-grained PAT — required permissions:"
  echo "  Repository access: All repositories (or select all 14 repos individually)"
  echo "  Repository permissions:"
  echo "    Contents: Read and write"
  echo "    Pull requests: Read and write"
  echo "    Issues: Read and write"
  echo "  Account permissions:"
  echo "    Projects: Read and write"
  exit 1
fi
