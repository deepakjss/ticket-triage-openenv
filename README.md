# Support Ticket Triage — OpenEnv (Round 1)

Real-world **customer-support triage**: classify **intent**, **priority**, and **routing queue** from short ticket text. Three **graded tasks** (easy → medium → hard) with deterministic scores in **\[0, 1\]**.

## Requirements

- **Python 3.10+** (3.11 recommended; matches `Dockerfile`)
- `openenv-core`, `fastapi`, `uvicorn`, `openai`

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
docker run --rm -p 8000:8000 ticket-triage-openenv:latest
```

## Baseline inference (`inference.py`)

Set **HF_TOKEN** (required). Set either:

- **OPENENV_BASE_URL** = `http://127.0.0.1:8000` (or your HF Space URL), or  
- **LOCAL_IMAGE_NAME** = Docker image tag for `from_docker_image()`.

```bash
export HF_TOKEN=hf_...
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export OPENENV_BASE_URL=http://127.0.0.1:8000
python inference.py
```

Stdout follows **`[START]` / `[STEP]` / `[END]`** as required by the hackathon.

## Hugging Face Space

- Use this repo as the Space **Docker** SDK.
- Ensure **`POST /reset`** returns **200** (validator script).
- Tag / document as OpenEnv per organiser instructions.

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

**Already run successfully in this workspace:** `openenv validate` (local) and `openenv validate --url http://127.0.0.1:8000` (runtime API contract).

## Repo layout

```
openenv.yaml
Dockerfile
inference.py
requirements.txt
ticket_triage_openenv/
  models.py
  client.py
  server/
    app.py
    support_environment.py
```
