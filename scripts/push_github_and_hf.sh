#!/usr/bin/env bash
# Push main to GitHub and to Hugging Face Space (requires tokens in environment).
#
#   export GITHUB_TOKEN=ghp_xxx          # repo scope
#   export HF_TOKEN=hf_xxx               # write access
#   ./scripts/push_github_and_hf.sh
#
# Get tokens:
#   GitHub: https://github.com/settings/tokens
#   HF:     https://huggingface.co/settings/tokens

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${GITHUB_TOKEN:-}" || -z "${HF_TOKEN:-}" ]]; then
  echo "Usage:"
  echo "  export GITHUB_TOKEN=ghp_..."
  echo "  export HF_TOKEN=hf_..."
  echo "  $0"
  exit 1
fi

echo "== 1/2 Pushing to GitHub (deepakjss/ticket-triage-openenv) =="
command git push -u "https://${GITHUB_TOKEN}@github.com/deepakjss/ticket-triage-openenv.git" main

echo "== 2/2 Pushing to Hugging Face Space =="
command git push -u "https://deepakjss:${HF_TOKEN}@huggingface.co/spaces/deepakjss/ticket-triage-openenv.git" main || {
  echo ""
  echo "HF push failed (common if Space has an unrelated initial commit)."
  echo "Fix: In https://huggingface.co/spaces/deepakjss/ticket-triage-openenv/settings"
  echo "     connect Repository -> github.com/deepakjss/ticket-triage-openenv and Rebuild,"
  echo "     or force-push only if you understand the risk: git push -f <hf-remote> main"
  exit 1
}

echo ""
echo "Done. Watch build: https://huggingface.co/spaces/deepakjss/ticket-triage-openenv"
echo "unset GITHUB_TOKEN HF_TOKEN  # optional cleanup"
