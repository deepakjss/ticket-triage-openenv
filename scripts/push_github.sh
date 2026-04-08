#!/usr/bin/env bash
# Push main to GitHub using a PAT provided at runtime (not saved in repo).
#
# Usage:
#   export GITHUB_TOKEN=ghp_xxxxxxxx
#   ./scripts/push_github.sh
#
# Or one line:
#   GITHUB_TOKEN=ghp_xxx ./scripts/push_github.sh
#
# Create token: GitHub → Settings → Developer settings → Personal access tokens → repo scope

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "Set GITHUB_TOKEN first (classic PAT with 'repo' scope), e.g.:"
  echo "  export GITHUB_TOKEN=ghp_..."
  echo "  $0"
  exit 1
fi

REMOTE_URL="https://${GITHUB_TOKEN}@github.com/deepakjss/ticket-triage-openenv.git"

echo "Pushing main to github.com/deepakjss/ticket-triage-openenv ..."
command git push -u "$REMOTE_URL" main

echo "Done. Clear token from shell: unset GITHUB_TOKEN"
