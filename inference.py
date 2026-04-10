"""
Baseline inference — OpenEnv hackathon format.

Uses OpenAI client + GenericEnvClient (async) over WebSocket to the Space/server.

Env: API_BASE_URL, MODEL_NAME (defaults OK); HF_TOKEN or API_KEY required.
Either OPENENV_BASE_URL (http://host:port) or LOCAL_IMAGE_NAME for Docker.

Stdout must contain only evaluator lines [START], [STEP], [END] (field names/order/format
per organiser sample). Debug/diagnostics use stderr so parsing stdout stays strict.
"""
from __future__ import annotations

import os
import sys
import textwrap
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openenv.core import GenericEnvClient

try:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except Exception:
    pass


def _struct_stdout(line: str) -> None:
    """Write evaluator lines to stdout fd (fd 1); avoids TextIOWrapper buffering in piped CI."""
    os.write(1, (line + "\n").encode("utf-8", errors="replace"))

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
# Same as sample: HF primary; optional API_KEY alias
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME")
OPENENV_BASE_URL = os.getenv("OPENENV_BASE_URL")

BENCHMARK = os.getenv("OPENENV_BENCHMARK", "ticket_triage_openenv")
try:
    EPISODES = max(1, int(os.getenv("OPENENV_EPISODES", "3")))
except ValueError:
    EPISODES = 3
# Set True after first [START] so we never finish with zero structured lines on stdout.
_STRUCTURED_LOG_EMITTED = False
MAX_STEPS = int(os.getenv("MAX_STEPS", "12"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "120"))

SYSTEM_PROMPT = textwrap.dedent(
    """
    You help route customer-support tickets. Read the ticket and instruction.
    Reply with exactly ONE line of plain text in the format requested
    (e.g. intent:..., priority:..., route:...). No quotes, no markdown, no extra lines.
    """
).strip()


def log_start(task: str, env: str, model: str) -> None:
    global _STRUCTURED_LOG_EMITTED
    _STRUCTURED_LOG_EMITTED = True
    # Validator shape: [START] task=NAME (env/model reserved for callers; not on stdout).
    _ = env, model
    _struct_stdout(f"[START] task={task}")


def log_step(
    step: int,
    action: str,
    reward: float,
    done: bool,
    error: Optional[str],
) -> None:
    err = error if error else "null"
    done_val = str(done).lower()
    a = action.replace("\n", "\\n").replace("\r", "")
    # Validator example order: step= then reward=, then optional fields.
    _struct_stdout(
        f"[STEP] step={step} reward={reward:.2f} action={a} done={done_val} error={err}"
    )


def log_end(
    task: str, success: bool, steps: int, score: float, rewards: List[float]
) -> None:
    # Empty rewards breaks some parsers; sample always has at least one float.
    # Include task= on [END] per validator / organiser examples (e.g. task=NAME score=... steps=...).
    if not rewards:
        rstr = "0.01"
    else:
        rstr = ",".join(f"{r:.2f}" for r in rewards)
    # Validator example: [END] task=NAME score=0.95 steps=1 — put task, score, steps first.
    _struct_stdout(
        f"[END] task={task} score={score:.2f} steps={steps} "
        f"success={str(success).lower()} rewards={rstr}"
    )


def _emit_minimal_failure(task: str) -> None:
    """Always emit [START] + [END] so Phase-2 stdout regex finds structured lines."""
    log_start(task=task, env=BENCHMARK, model=MODEL_NAME)
    log_end(task=task, success=False, steps=0, score=0.01, rewards=[0.01])


def build_user_message(
    ticket: str, instruction: str, task_id: str, hint: str, feedback: str
) -> str:
    return textwrap.dedent(
        f"""
        task_id: {task_id}
        Ticket:
        {ticket}

        Instruction:
        {instruction}

        Hint: {hint}
        Previous feedback: {feedback or "none"}
        Output one line only.
        """
    ).strip()


def get_model_line(
    client: OpenAI,
    ticket: str,
    instruction: str,
    task_id: str,
    hint: str,
    feedback: str,
) -> str:
    user = build_user_message(ticket, instruction, task_id, hint, feedback)
    try:
        comp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        text = (comp.choices[0].message.content or "").strip()
        return text.splitlines()[0].strip() if text else "intent:unknown"
    except Exception as exc:
        print(f"[DEBUG] LLM error: {exc}", file=sys.stderr, flush=True)
        return "intent:unknown"


def _stderr_config() -> None:
    """Helpful context when connect or Docker fails (no secrets)."""
    print(
        "[inference] HF_TOKEN="
        + ("set" if HF_TOKEN else "MISSING")
        + f" OPENENV_BASE_URL={OPENENV_BASE_URL!r} LOCAL_IMAGE_NAME={LOCAL_IMAGE_NAME!r}",
        file=sys.stderr,
        flush=True,
    )
    print(
        "[inference] Use direct Space URL, e.g. https://user-space.hf.space "
        "(not huggingface.co/spaces/... HTML page).",
        file=sys.stderr,
        flush=True,
    )


def _as_obs_dict(res: Any) -> Dict[str, Any]:
    """Observation from StepResult may be dict or missing."""
    if res is None:
        return {}
    raw = getattr(res, "observation", None)
    if isinstance(raw, dict):
        return raw
    return {}


async def _run_async_inference() -> None:
    if not HF_TOKEN:
        print("HF_TOKEN or API_KEY is required.", file=sys.stderr, flush=True)
        _emit_minimal_failure("missing_hf_token")
        raise SystemExit(1)

    oa = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    env: Optional[GenericEnvClient] = None
    if OPENENV_BASE_URL:
        base = OPENENV_BASE_URL.rstrip("/")
        env = GenericEnvClient(base_url=base)
    elif LOCAL_IMAGE_NAME:
        try:
            # from_docker_image() already awaits connect() internally
            env = await GenericEnvClient.from_docker_image(LOCAL_IMAGE_NAME)
        except Exception as exc:
            _stderr_config()
            print(
                f"[inference] from_docker_image({LOCAL_IMAGE_NAME!r}) failed: {exc}",
                file=sys.stderr,
                flush=True,
            )
            _emit_minimal_failure("docker_not_ready")
            raise
    else:
        _stderr_config()
        print(
            "Set OPENENV_BASE_URL or LOCAL_IMAGE_NAME.",
            file=sys.stderr,
            flush=True,
        )
        _emit_minimal_failure("missing_env_url")
        raise SystemExit(1)

    assert env is not None

    try:
        # Only needed when not using from_docker_image (already connected there)
        if OPENENV_BASE_URL:
            try:
                await env.connect()
            except Exception as exc:
                _stderr_config()
                print(
                    f"[inference] WebSocket connect failed: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                _emit_minimal_failure("websocket_connect")
                raise

        for _ep in range(EPISODES):
            rewards: List[float] = []
            steps_taken = 0
            score = 0.01
            success = False
            cur: Any = None
            task_name = "unknown"

            try:
                res = await env.reset()
                obs = _as_obs_dict(res)
                task_name = str(obs.get("task_id") or "unknown")
                log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

                cur = res
                ticket = str(obs.get("ticket_text", ""))
                instruction = str(obs.get("instruction", ""))
                hint = str(obs.get("hint", ""))
                feedback = str(obs.get("last_feedback", ""))

                for step in range(1, MAX_STEPS + 1):
                    if cur is None or cur.done:
                        break
                    line = get_model_line(
                        oa, ticket, instruction, task_name, hint, feedback
                    )
                    cur = await env.step({"message": line})
                    _rw = float(getattr(cur, "reward", None) or 0.01)
                    rw = max(0.01, min(0.99, _rw))
                    dn = bool(cur.done)
                    try:
                        st = await env.state()
                        err_raw = (
                            st.get("last_action_error", "")
                            if isinstance(st, dict)
                            else ""
                        )
                    except Exception:
                        err_raw = ""
                    err: Optional[str] = err_raw if err_raw else None

                    rewards.append(rw)
                    steps_taken = step
                    log_step(step=step, action=line, reward=rw, done=dn, error=err)

                    o2 = _as_obs_dict(cur)
                    feedback = str(o2.get("last_feedback", ""))
                    if dn:
                        break

                score = max(rewards) if rewards else 0.01
                score = max(0.01, min(0.99, score))
                success = score >= 0.99
            except Exception as exc:
                print(f"[DEBUG] episode error: {exc}", file=sys.stderr, flush=True)
                score = 0.01
                success = False
                if task_name == "unknown":
                    log_start(task="unknown", env=BENCHMARK, model=MODEL_NAME)
            finally:
                log_end(
                    task=task_name,
                    success=success,
                    steps=steps_taken,
                    score=score,
                    rewards=rewards,
                )
    finally:
        if env is not None:
            try:
                await env.close()
            except Exception as exc:
                print(
                    f"[inference] env.close() ignored: {exc}",
                    file=sys.stderr,
                    flush=True,
                )


def main() -> None:
    import asyncio
    import traceback

    global _STRUCTURED_LOG_EMITTED

    try:
        asyncio.run(_run_async_inference())
    except SystemExit:
        raise
    except Exception as exc:
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        if not _STRUCTURED_LOG_EMITTED:
            _emit_minimal_failure("uncaught_exception")
        raise SystemExit(1) from exc


def run_inference() -> None:
    """Entry point for harnesses that import and call instead of executing the script."""
    main()


run = run_inference
infer = run_inference


if __name__ == "__main__":
    main()
