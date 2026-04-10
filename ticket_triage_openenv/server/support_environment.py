"""Support ticket triage — 3 graded tasks, deterministic scores strictly in (0, 1)."""

from __future__ import annotations

import re
import uuid
from typing import Any, List, Optional, Tuple

from openenv.core.env_server.interfaces import Environment

from ticket_triage_openenv.models import TriageAction, TriageObservation, TriageState

MAX_STEPS_PER_EPISODE = 8

# Task validation: each score must be strictly between 0 and 1 (not 0.0, not 1.0).
_MIN_TASK_SCORE = 0.01
_MAX_TASK_SCORE = 0.99


def _task_score_strict(x: float) -> float:
    """Clamp to open interval (0, 1) for validator / task checks."""
    v = float(x)
    v = max(_MIN_TASK_SCORE, min(_MAX_TASK_SCORE, v))
    return round(v, 2)

TASK_SPECS: List[Tuple[str, str, str, str, str]] = [
    (
        "triage_intent_easy",
        "easy",
        "I was charged twice on my credit card for the same monthly subscription.",
        (
            "Reply with exactly one line of the form intent:<label> where <label> is "
            "either billing or technical. This ticket is about payment or charges."
        ),
        "intent:billing",
    ),
    (
        "triage_priority_medium",
        "medium",
        "Production API is down; all enterprise customers are affected right now.",
        (
            "Reply with exactly one line: priority:<level> where <level> is one of "
            "low, normal, high, urgent. Assess operational severity."
        ),
        "priority:urgent",
    ),
    (
        "triage_route_hard",
        "hard",
        (
            "Customer insists on a full refund for a duplicate charge but also reports "
            "a bug that blocked checkout; legal asked for a written paper trail."
        ),
        (
            "Reply with exactly one line: route:<name> where <name> is one of "
            "billing_review, bug_triage, refund_queue, legal_review. "
            "Choose the single best primary queue for the first action."
        ),
        "route:refund_queue",
    ),
]


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def grade_response(agent_line: str, target: str) -> float:
    a = _normalize(agent_line)
    t = _normalize(target)
    if not a:
        raw = 0.0
    elif a == t:
        raw = 1.0
    elif t in a and len(t) >= 6:
        raw = 0.85
    else:
        ta = set(a.replace(":", " ").split())
        tt = set(t.replace(":", " ").split())
        if not tt:
            raw = 0.0
        else:
            inter = len(ta & tt)
            union = len(ta | tt) or 1
            jacc = inter / union
            raw = min(1.0, 0.2 + 0.6 * jacc)
    return _task_score_strict(raw)


class SupportTriageEnvironment(Environment[TriageAction, TriageObservation, TriageState]):
    """reset / step / state — OpenEnv Environment."""

    def __init__(self) -> None:
        super().__init__()
        self._state = TriageState()
        self._task_order = 0
        self._step_in_episode = 0
        self._current_spec: Optional[Tuple[str, str, str, str, str]] = None

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> TriageObservation:
        _ = seed, episode_id, kwargs
        spec = TASK_SPECS[self._task_order % len(TASK_SPECS)]
        self._task_order += 1
        self._current_spec = spec
        task_id, _diff, ticket, instruction, target = spec
        self._step_in_episode = 0
        self._state = TriageState(
            episode_id=str(uuid.uuid4()),
            step_count=0,
            task_id=task_id,
            target_response=target,
            last_action_error="",
        )
        return TriageObservation(
            ticket_text=ticket,
            instruction=instruction,
            task_id=task_id,
            hint="Format matters: follow the one-line pattern in the instruction.",
            last_feedback="",
            done=False,
            reward=_task_score_strict(0.0),
        )

    def step(
        self,
        action: TriageAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> TriageObservation:
        _ = timeout_s, kwargs
        if self._current_spec is None:
            self._state.last_action_error = "environment not reset"
            return TriageObservation(
                ticket_text="",
                instruction="Call reset() first.",
                task_id="",
                hint="",
                last_feedback="invalid",
                done=True,
                reward=_task_score_strict(0.0),
            )

        task_id, _diff, ticket, instruction, target = self._current_spec
        self._step_in_episode += 1
        self._state.step_count = self._step_in_episode

        msg = (action.message or "").strip()
        if not msg:
            self._state.last_action_error = "empty_message"
            reward = _task_score_strict(0.05)
        else:
            self._state.last_action_error = ""
            reward = grade_response(msg, target)

        done = reward >= _MAX_TASK_SCORE or self._step_in_episode >= MAX_STEPS_PER_EPISODE
        feedback = (
            "correct"
            if reward >= _MAX_TASK_SCORE
            else ("close" if reward >= 0.5 else "keep_trying")
        )

        return TriageObservation(
            ticket_text=ticket,
            instruction=instruction,
            task_id=task_id,
            hint="",
            last_feedback=feedback,
            done=done,
            reward=float(reward),
        )

    @property
    def state(self) -> TriageState:
        return self._state
