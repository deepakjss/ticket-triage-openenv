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

Classify **intent**, **priority**, and **routing queue** from short support-ticket text. Three graded tasks (easy → medium → hard) with scores in **[0, 1]**.

## What’s in this repo

Tasks and grading live in `ticket_triage_openenv/server/support_environment.py` (`TASK_SPECS`, `grade_response`). Each `reset()` moves to the next task. The HTTP API is built with `openenv`’s `create_app`; `inference.py` uses `GenericEnvClient` and prints **`[START]` / `[STEP]` / `[END]`** for the baseline run.

## Requirements

- Python **3.10+** (3.11 matches the `Dockerfile`)
- Dependencies: `openenv-core`, `fastapi`, `uvicorn`, `openai` (see `requirements.txt`)

## Action / observation

- **Action:** `TriageAction(message: str)` — one line, e.g. `intent:billing`
- **Observation:** ticket text, instruction, `task_id`, hints/feedback, `reward`, `done`

## Tasks

| Task ID | Difficulty | Example target line |
|---------|------------|---------------------|
| `triage_intent_easy` | easy | `intent:billing` |
| `triage_priority_medium` | medium | `priority:urgent` |
| `triage_route_hard` | hard | `route:refund_queue` |

## Local server

Use a **virtualenv** so `openenv` is installed (avoid a system `uvicorn` without deps):

```bash
cd scaler-openenv-hackathon
python3.11 -m venv .venv && source .venv/bin/activate   # or your 3.10+ venv
pip install -r requirements.txt
export PYTHONPATH=.
uvicorn server.app:app --host 127.0.0.1 --port 8000
```

Smoke test:

```bash
curl -s -X POST http://127.0.0.1:8000/reset -H "Content-Type: application/json" -d '{}' | head -c 400
```

## Docker (same as Space)

```bash
docker build -t ticket-triage-openenv:latest .
docker run --rm -p 7860:7860 ticket-triage-openenv:latest
```

## Baseline inference (`inference.py`)

Set **`HF_TOKEN`** (Hugging Face). Set **`OPENENV_BASE_URL`** to your env (e.g. `http://127.0.0.1:8000` or your `https://*.hf.space` URL), or **`LOCAL_IMAGE_NAME`** for a local Docker image.

```bash
export HF_TOKEN=hf_...
export OPENENV_BASE_URL=http://127.0.0.1:8000
python inference.py
```

## Hugging Face Space

Space: [`deepakjss/ticket-triage-openenv`](https://huggingface.co/spaces/deepakjss/ticket-triage-openenv) — app listens on **7860** (`Dockerfile` / `openenv.yaml`).

Check the live API (use your **direct** `*.hf.space` URL):

```bash
curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{}' \
  "https://YOUR_SPACE_DIRECT_URL/reset"
```

## Validate

Pre-submission script (organiser-style): **4 checks** — (1) `POST /reset` on your Space, (2) **`docker build`**, (3) **`openenv validate`** (uses **`.venv/bin/openenv`** if present), (4) **`openenv validate --url`** against the same Space.

```bash
chmod +x scripts/validate-submission.sh
./scripts/validate-submission.sh "https://your-space.hf.space" .
```

Requires **Docker Desktop running** and **`openenv-core`** installed in the repo `.venv` or on `PATH`.

Optional full local check (needs [uv](https://github.com/astral-sh/uv)):

```bash
chmod +x scripts/run_all_steps.sh
./scripts/run_all_steps.sh
```

## Before you submit

1. Push **`main`** to your **GitHub** repo and to the **Hugging Face Space** repo if you deploy from git.
2. Confirm **`openenv validate`** passes and the Space returns **200** on **`POST /reset`**.
3. Run **`inference.py`** once with a real **`HF_TOKEN`** and see **`[START]` / `[STEP]` / `[END]`** in the terminal.
4. Submit the **GitHub URL** and **Space URL** (and anything else the form asks for).

## Repo layout

```
openenv.yaml
Dockerfile
inference.py
requirements.txt
pyproject.toml
server/app.py                 # app entry for openenv.yaml / Docker
ticket_triage_openenv/
  models.py
  server/app.py
  server/support_environment.py
scripts/validate-submission.sh
scripts/run_all_steps.sh
```
