"""
OpenEnv HTTP entrypoint (expected at server/app.py by `openenv validate`).

Re-exports the FastAPI app from the environment package.
"""
from __future__ import annotations

from ticket_triage_openenv.server.app import app


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
