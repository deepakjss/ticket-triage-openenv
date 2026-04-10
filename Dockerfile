# Support Triage OpenEnv — HF Space / local Docker
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md requirements.txt ./
COPY server ./server
COPY ticket_triage_openenv ./ticket_triage_openenv
COPY openenv.yaml ./

RUN pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
# OpenEnv GenericEnvClient.from_docker_image() maps -p host:8000 (see LocalDockerProvider).
# HF Spaces set PORT=7860 at runtime — use $PORT so both validators and HF work.
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1'

CMD ["sh", "-c", "exec uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
