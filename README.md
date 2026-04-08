---
title: Ticket Triage OpenEnv
emoji: 🎫
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Support Ticket Triage — OpenEnv (Round 1)

Real-world **customer-support triage**: classify **intent**, **priority**, and **routing queue** from short ticket text. Three **graded tasks** (easy → medium → hard) with deterministic scores in **\[0, 1\]**.

## Submission checklist (do these in order)

1. **Sync both remotes** — Keep `main` on **GitHub** and on your **Hugging Face Space** in sync (Space builds from the HF repo, not from GitHub unless you linked them in Space settings).
2. **Confirm the Space URL** — After each push, wait for the Docker build; open the Space **direct** app URL (`https://*.hf.space`) when the validator asks for a runtime endpoint.
3. **Smoke-test the API** — `POST /reset` → 200, `GET /health` → 200, `GET /` → 200 (HF probes use `/?logs=container`).
4. **Run validation locally** — From repo root: `./scripts/run_all_steps.sh` (or `openenv validate` + `openenv validate --url http://127.0.0.1:8000` with `uvicorn` running).
5. **Run `validate-submission.sh` against the live Space** — `./scripts/validate-submission.sh "https://YOUR_SPACE.hf.space" .`
6. **Run `inference.py` with real tokens** — Set `HF_TOKEN`, `OPENENV_BASE_URL` (or Docker `LOCAL_IMAGE_NAME`), and confirm **`[START]` / `[STEP]` / `[END]`** lines appear on stdout.
7. **Submit** — Paste the **GitHub repo URL**, **HF Space URL**, and any other fields the hackathon form requests.

## Design (what this repo actually does)

This is a **custom environment**, not a stock template: the three ticket bodies and instructions live in `ticket_triage_openenv/server/support_environment.py` as `TASK_SPECS`. Each `reset()` rotates tasks in order (intent → priority → route). The grader **`grade_response`** gives **1.0** on an exact normalized match, partial credit when the target substring appears or when token overlap (Jaccard-style) is high, and caps steps per episode at **8**. Observations carry **ticket text**, **instruction**, **task_id**, **hint**, and **last_feedback** so an LLM can iterate. The baseline agent in **`inference.py`** uses **`GenericEnvClient`** (WebSocket) plus the Hugging Face router **`API_BASE_URL`** and your **`HF_TOKEN`** for the chat model—swap **`MODEL_NAME`** or temperature via env vars if you tune behavior.

## Requirements

- **Python 3.10+** (3.11 recommended; matches `Dockerfile` / `uv` lockfile)
- `openenv-core` (package imports `openenv.core`), `fastapi`, `uvicorn`, `openai`

## Action / observation

- **Action:** `TriageAction(message: str)` — one line of structured output (e.g. `intent:billing`).
- **Observation:** ticket text, instruction, `task_id`, optional hints/feedback, `reward`, `done`.

## Tasks

| Task ID | Difficulty | Target format (example) |
|---------|------------|---------------------------|
| `triage_intent_easy` | easy | `intent:billing` |
| `triage_priority_medium` | medium | `priority:urgent` |
| `triage_route_hard` | hard | `route:refund_queue` |

Each `reset()` advances to the next task in order (cycles). Rewards use partial credit until the exact canonical line is produced.

## Local server

```bash
cd scaler-openenv-hackathon
pip install -r requirements.txt
export PYTHONPATH=.
uvicorn ticket_triage_openenv.server.app:app --host 127.0.0.1 --port 8000
```

Smoke test:

```bash
curl -s -X POST http://127.0.0.1:8000/reset -H "Content-Type: application/json" -d '{}' | head -c 400
```

## Docker

```bash
docker build -t ticket-triage-openenv:latest .
# Image listens on 7860 (same as Hugging Face Docker Spaces)
docker run --rm -p 7860:7860 ticket-triage-openenv:latest
```

## Baseline inference (`inference.py`)

Set **HF_TOKEN** (required). Set either:

- **OPENENV_BASE_URL** = local `http://127.0.0.1:7860` or your Space **direct** URL (often `https://*.hf.space`, not the `huggingface.co/spaces/...` HTML page), or  
- **LOCAL_IMAGE_NAME** = Docker image tag for `from_docker_image()`.

```bash
export HF_TOKEN=hf_...
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export OPENENV_BASE_URL=http://127.0.0.1:7860
python inference.py
```

Stdout follows **`[START]` / `[STEP]` / `[END]`** as required by the hackathon.

## Hugging Face Space ([`deepakjss/ticket-triage-openenv`](https://huggingface.co/spaces/deepakjss/ticket-triage-openenv))

1. **Connect GitHub (recommended):** Space **Settings → Repository** → link **`deepakjss/ticket-triage-openenv`** so pushes to `main` rebuild the Space.  
2. **Or push to Space git:** add remote `https://huggingface.co/spaces/deepakjss/ticket-triage-openenv` and `git push` (use an HF token with write access when prompted).

The container must listen on **port 7860** (configured in this repo’s `Dockerfile`). After build succeeds, test:

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" -d '{}' \
  "https://YOUR_SPACE_DIRECT_URL/reset"
```

Expect **200**. Use that **direct** URL in the hackathon validator if required.

## Validate (organiser script pattern)

```bash
chmod +x scripts/validate-submission.sh
./scripts/validate-submission.sh "https://your-space.hf.space" .
```

## One-shot local checks (automated)

From the repo root (requires [uv](https://github.com/astral-sh/uv) for Python 3.11 + lockfile):

```bash
chmod +x scripts/run_all_steps.sh
./scripts/run_all_steps.sh
```

This creates `.venv`, installs deps, runs `uv lock`, `openenv validate`, starts `uvicorn` on port 8000 if needed, and `openenv validate --url http://127.0.0.1:8000`. With Docker installed it also builds the image.

**Confirm locally:** `openenv validate` (static checks) and `openenv validate --url http://127.0.0.1:8000` with `uvicorn` on port 8000 (runtime API contract).

## Repo layout

```
openenv.yaml
Dockerfile
inference.py          # baseline LLM + GenericEnvClient, [START]/[STEP]/[END] logs
requirements.txt
pyproject.toml
server/
  app.py              # re-exports FastAPI app; entry for `openenv validate`
ticket_triage_openenv/
  models.py           # TriageAction / TriageObservation / TriageState
  server/
    app.py            # create_app(...) + GET /
    support_environment.py
scripts/
  validate-submission.sh
  run_all_steps.sh
  push_hf_space.sh
  push_github_and_hf.sh
```
