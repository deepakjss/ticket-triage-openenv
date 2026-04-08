#!/usr/bin/env bash
# Push main to Hugging Face Space git (use HF token as password when prompted).
#
# Usage:
#   export HF_TOKEN=hf_xxx   # write access
#   ./scripts/push_hf_space.sh
#
# Or: git push https://USER:TOKEN@huggingface.co/spaces/deepakjss/ticket-triage-openenv main

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "Set HF_TOKEN (write) from https://huggingface.co/settings/tokens"
  echo "  export HF_TOKEN=hf_..."
  echo "  $0"
  exit 1
fi

REMOTE="https://deepakjss:${HF_TOKEN}@huggingface.co/spaces/deepakjss/ticket-triage-openenv.git"

echo "Pushing main to Hugging Face Space..."
command git push "$REMOTE" main
echo "Done. Space will rebuild at https://huggingface.co/spaces/deepakjss/ticket-triage-openenv"
