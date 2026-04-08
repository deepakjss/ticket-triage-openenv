#!/usr/bin/env bash
# Run local checks: venv, deps, uv lock, openenv validate, optional docker, optional inference.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== 1. Python venv (uv, 3.11) =="
if [[ ! -d .venv ]]; then
  uv venv --python 3.11 .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate

echo "== 2. Install deps =="
uv pip install -r requirements.txt --python .venv/bin/python

echo "== 3. uv lock =="
uv lock

echo "== 4. openenv validate (local files) =="
.venv/bin/openenv validate --verbose

echo "== 5. Start server (if not running on :8000) =="
if ! curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health | grep -q 200; then
  export PYTHONPATH="$ROOT"
  nohup .venv/bin/uvicorn server.app:app --host 127.0.0.1 --port 8000 > /tmp/openenv_local.log 2>&1 &
  sleep 2
fi
curl -s http://127.0.0.1:8000/health || { echo "Server failed"; cat /tmp/openenv_local.log; exit 1; }

echo "== 6. openenv validate --url =="
.venv/bin/openenv validate --url http://127.0.0.1:8000 --timeout 10

if command -v docker &>/dev/null; then
  echo "== 7. docker build =="
  docker build -t ticket-triage-openenv:local .
  echo "== 8. validate-submission (HF URL is placeholder; skip ping) =="
  echo "    Run: ./scripts/validate-submission.sh 'https://YOUR_SPACE.hf.space' '$ROOT'"
else
  echo "== 7-8. SKIP docker (install Docker Desktop to build image)"
fi

echo ""
echo "== 9. inference.py (needs real HF_TOKEN for LLM) =="
echo "    export HF_TOKEN=hf_..."
echo "    export OPENENV_BASE_URL=http://127.0.0.1:8000"
echo "    python inference.py"
echo ""
echo "Done."
