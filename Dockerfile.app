FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY .dockerignore Makefile alembic.ini compose.yaml pyproject.toml ./
COPY config/hermes-managed-config.yaml ./config/hermes-managed-config.yaml
COPY docs/runbooks ./docs/runbooks
COPY migrations ./migrations
COPY scripts ./scripts
COPY src ./src
COPY tests ./tests

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "menu_planner.bootstrap.http:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]
