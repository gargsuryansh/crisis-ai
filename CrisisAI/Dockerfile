# =============================================================================
# CrisisAI Backend — Production Dockerfile
# Google Solution Challenge 2026
#
# Targets: Google Cloud Run (production) + Docker Compose (local dev)
#
# Security:
#   - Non-root runtime user
#   - No .env / service-account JSON baked in (Cloud Run injects at runtime)
#   - Multi-stage build keeps final image lean
#
# Volumes (mounted at runtime, never baked in):
#   /app/chroma_db           — ChromaDB persistence
#   /app/data/embeddings     — FAISS *.bin indexes
# =============================================================================

# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — Builder: install Python deps into a virtual-env
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# System deps needed to compile native wheels (numpy, faiss-cpu, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install -r requirements.txt

# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — Runtime: slim image with only what's needed
# ──────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="CrisisAI Team — Google Solution Challenge 2026" \
      description="FastAPI backend for CrisisAI dual-sided crisis platform"

# ── Environment ──────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # ChromaDB persistence — matches docker-compose volume mount
    CHROMA_PERSIST_DIR=/app/chroma_db \
    # Cloud Run expects port 8080
    PORT=8080

WORKDIR /app

# ── System runtime deps ─────────────────────────────────────────────────────
# libgomp1 : OpenMP runtime for FAISS / NumPy BLAS
# curl     : used by Docker HEALTHCHECK and debugging
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Copy virtual-env from builder ───────────────────────────────────────────
COPY --from=builder /opt/venv /opt/venv

# ── Copy application code ───────────────────────────────────────────────────
# Only the folders needed at runtime. Secrets are NEVER copied.
COPY backend/ ./backend/
COPY data/    ./data/
COPY shared/  ./shared/

# ── Create volume mount-points & non-root user ──────────────────────────────
RUN mkdir -p /app/chroma_db /app/data/embeddings && \
    addgroup --system crisisai && \
    adduser  --system --ingroup crisisai crisisai && \
    chown -R crisisai:crisisai /app

USER crisisai

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ── Expose + Start ──────────────────────────────────────────────────────────
EXPOSE ${PORT}

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
