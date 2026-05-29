# Build context: raíz del proyecto
# Build: docker build -f deploy/Dockerfile -t oplscheduler .

# ── Stage 1: compilar el frontend ────────────────────────────
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ── Stage 2: compilar wheels de Python ───────────────────────
FROM python:3.12-slim AS python-builder

# Dependencias de compilación (solo en esta stage, no en la final)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY backend/requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ── Stage 3: imagen final ────────────────────────────────────
FROM python:3.12-slim

# libpq5 (runtime de psycopg2) + curl para healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Usuario no-root para seguridad
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

# Instalar wheels precompilados (sin compilador en imagen final)
COPY --from=python-builder /wheels /wheels
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Código backend
COPY backend/src/ src/
COPY backend/alembic/ alembic/
COPY backend/alembic.ini .

# Frontend compilado desde stage 1
COPY --from=frontend-builder /app/frontend/dist frontend/dist

RUN chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn src.api.app:app --host 0.0.0.0 --port 8000"]
