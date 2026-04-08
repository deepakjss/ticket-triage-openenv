"""FastAPI app — POST /reset, /step, GET /state, /health, WS /ws."""

from openenv.core.env_server.http_server import create_app

from ticket_triage_openenv.models import TriageAction, TriageObservation
from ticket_triage_openenv.server.support_environment import SupportTriageEnvironment

app = create_app(
    SupportTriageEnvironment,
    TriageAction,
    TriageObservation,
    env_name="ticket_triage_openenv",
    max_concurrent_envs=1,
)


@app.get("/")
def root() -> dict:
    """HF Spaces / probes often hit `/`; OpenEnv otherwise has no root route."""
    return {
        "status": "ok",
        "service": "ticket-triage-openenv",
        "docs": "/docs",
        "health": "/health",
    }
