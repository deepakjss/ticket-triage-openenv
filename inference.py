"""
Baseline inference — OpenEnv hackathon format.

Uses OpenAI client + GenericEnvClient (async) over WebSocket to the Space/server.

Env: API_BASE_URL, MODEL_NAME (defaults OK); HF_TOKEN required (no default).
Either OPENENV_BASE_URL (http://host:port) or LOCAL_IMAGE_NAME for Docker.
"""
from __future__ import annotations

import os
import textwrap
from typing import Any, Dict, List, Optional

from openai import OpenAI
from openenv.core import GenericEnvClient

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME") or os.getenv("IMAGE_NAME")
OPENENV_BASE_URL = os.getenv("OPENENV_BASE_URL")

BENCHMARK = os.getenv("OPENENV_BENCHMARK", "ticket_triage_openenv")
EPISODES = int(os.getenv("OPENENV_EPISODES", "3"))
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


def log_start(task: str, env_name: str, model: str) -> None:
    print(f"[START] task={task} env={env_name} model={model}", flush=True)


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
    print(
        f"[STEP] step={step} action={a} reward={reward:.2f} done={done_val} error={err}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rstr = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rstr}",
        flush=True,
    )


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
        print(f"[DEBUG] LLM error: {exc}", flush=True)
        return "intent:unknown"


async def _run_async_inference() -> None:
    if not HF_TOKEN:
        raise SystemExit("HF_TOKEN is required (no default).")

    oa = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    if OPENENV_BASE_URL:
        base = OPENENV_BASE_URL.rstrip("/")
        env = GenericEnvClient(base_url=base)
    elif LOCAL_IMAGE_NAME:
        env = await GenericEnvClient.from_docker_image(LOCAL_IMAGE_NAME)
    else:
        raise SystemExit("Set OPENENV_BASE_URL or LOCAL_IMAGE_NAME.")

    try:
        await env.connect()
        for _ep in range(EPISODES):
            res = await env.reset()
            obs: Dict[str, Any] = res.observation  # type: ignore[assignment]
            task_name = obs.get("task_id") or "unknown"
            log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

            rewards: List[float] = []
            steps_taken = 0
            score = 0.0
            success = False
            cur = res

            try:
                ticket = str(obs.get("ticket_text", ""))
                instruction = str(obs.get("instruction", ""))
                hint = str(obs.get("hint", ""))
                feedback = str(obs.get("last_feedback", ""))

                for step in range(1, MAX_STEPS + 1):
                    if cur.done:
                        break
                    line = get_model_line(
                        oa, ticket, instruction, task_name, hint, feedback
                    )
                    cur = await env.step({"message": line})
                    rw = float(cur.reward or 0.0)
                    dn = bool(cur.done)
                    st = await env.state()
                    err_raw = (
                        st.get("last_action_error", "") if isinstance(st, dict) else ""
                    )
                    err: Optional[str] = err_raw if err_raw else None

                    rewards.append(rw)
                    steps_taken = step
                    log_step(step=step, action=line, reward=rw, done=dn, error=err)

                    o2: Dict[str, Any] = cur.observation  # type: ignore[assignment]
                    feedback = str(o2.get("last_feedback", ""))
                    if dn:
                        break

                score = max(rewards) if rewards else 0.0
                score = max(0.0, min(1.0, score))
                success = score >= 0.99
            except Exception as exc:
                print(f"[DEBUG] episode error: {exc}", flush=True)
                score = 0.0
                success = False
            finally:
                log_end(
                    success=success,
                    steps=steps_taken,
                    score=score,
                    rewards=rewards,
                )
    finally:
        await env.close()


def main() -> None:
    import asyncio

    asyncio.run(_run_async_inference())


if __name__ == "__main__":
    main()
