"""Pydantic Action / Observation / State (OpenEnv 0.2+)."""

from __future__ import annotations

from typing import Optional

from pydantic import Field

from openenv.core.env_server.types import Action, Observation, State


class TriageAction(Action):
    """One structured line from the agent."""

    message: str = Field(default="", description="Classification / routing line")


class TriageObservation(Observation):
    """Agent-visible ticket + instructions."""

    ticket_text: str = Field(default="", description="Synthetic support ticket body")
    instruction: str = Field(default="", description="What format to output")
    task_id: str = Field(default="", description="Episode task identifier")
    hint: str = Field(default="", description="Optional hint")
    last_feedback: str = Field(default="", description="Grader hint after a step")


class TriageState(State):
    """Internal state exposed via GET /state."""

    task_id: str = Field(default="", description="Current task")
    target_response: str = Field(default="", description="Canonical answer (for debugging)")
    last_action_error: str = Field(default="", description="Last validation error if any")
