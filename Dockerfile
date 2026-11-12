# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: build the React frontend (Vite + TypeScript + Tailwind)
# ---------------------------------------------------------------------------
FROM node:22-alpine AS frontend-build

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: install the pinned Python dependencies into a venv from pyproject
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS backend-build

WORKDIR /build

COPY pyproject.toml README.md ./
COPY backend/ ./backend/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

# ---------------------------------------------------------------------------
# Stage 3: minimal, self-contained runtime (no external services)
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv" \
    CORPUS_DIR="/app/corpus" \
    CACHE_DIR="/tmp/synapse-cache"

# Non-root user and a writable cache directory for embedding caches.
RUN groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid appuser --home-dir /home/appuser --create-home appuser \
    && mkdir -p /tmp/synapse-cache \
    && chown -R appuser:appuser /tmp/synapse-cache

WORKDIR /app

COPY --from=backend-build /opt/venv /opt/venv
COPY backend/ /app/backend/
COPY corpus/ /app/corpus/
COPY --from=frontend-build /build/dist /app/frontend/dist/

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "/app/backend"]
