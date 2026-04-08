#!/usr/bin/env bash
# Push local main to Hugging Face Space, replacing the default Space template history.
# Run in repo root with HF_TOKEN set (write access).
#
#   export HF_TOKEN=hf_...
#   ./scripts/push_hf_space.sh
#
# Uses --force because HF Spaces start with an unrelated initial commit; we replace it
# with this repo (same as GitHub deepakjss/ticket-triage-openenv).

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "error: set HF_TOKEN (write) — https://huggingface.co/settings/tokens"
  echo "  export HF_TOKEN=hf_..."
  echo "  $0"
  exit 1
fi

REMOTE="https://deepakjss:${HF_TOKEN}@huggingface.co/spaces/deepakjss/ticket-triage-openenv.git"

echo "Force-pushing main to Hugging Face Space (overwrites Space-only template commits)..."
command git push --force "$REMOTE" main

echo "Done. Open Logs: https://huggingface.co/spaces/deepakjss/ticket-triage-openenv"
echo "Optional: unset HF_TOKEN"
