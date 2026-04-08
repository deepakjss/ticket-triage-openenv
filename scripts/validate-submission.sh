#!/usr/bin/env bash
# OpenEnv submission checks: HF /reset, docker build, openenv validate (if installed).
set -uo pipefail

PING_URL="${1:-}"
REPO_DIR="${2:-.}"

if [ -z "$PING_URL" ]; then
  printf "Usage: %s <hf_space_url> [repo_dir]\n" "$0"
  exit 1
fi

REPO_DIR="$(cd "$REPO_DIR" && pwd)"
PING_URL="${PING_URL%/}"

echo "== Step 1: POST $PING_URL/reset"
code=$(curl -s -o /tmp/oenv_reset.json -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" -d '{}' \
  "$PING_URL/reset" --max-time 30 || echo "000")
echo "HTTP $code"
if [ "$code" != "200" ]; then
  echo "FAIL: expected 200"
  exit 1
fi
echo "PASS: Space responds to /reset"

echo "== Step 2: docker build"
if ! command -v docker &>/dev/null; then
  echo "SKIP: docker not installed"
else
  if [ -f "$REPO_DIR/Dockerfile" ]; then
    docker build -t openenv-validate-local "$REPO_DIR" || exit 1
    echo "PASS: docker build"
  else
    echo "FAIL: no Dockerfile at repo root"
    exit 1
  fi
fi

OPENENV_BIN=""
if [[ -x "$REPO_DIR/.venv/bin/openenv" ]]; then
  OPENENV_BIN="$REPO_DIR/.venv/bin/openenv"
elif command -v openenv &>/dev/null; then
  OPENENV_BIN="$(command -v openenv)"
fi

echo "== Step 3: openenv validate (static)"
if [[ -n "$OPENENV_BIN" ]]; then
  (cd "$REPO_DIR" && "$OPENENV_BIN" validate) || exit 1
  echo "PASS: openenv validate"
else
  echo "SKIP: no openenv in .venv/bin or PATH (pip install openenv-core in a venv)"
fi

echo "== Step 4: openenv validate --url (running Space)"
if [[ -n "$OPENENV_BIN" ]]; then
  "$OPENENV_BIN" validate --url "$PING_URL" --timeout 30 || exit 1
  echo "PASS: openenv validate --url"
else
  echo "SKIP: same as step 3"
fi

echo "All checks completed."
