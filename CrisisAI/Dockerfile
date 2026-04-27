# =============================================================================
# CrisisAI Backend — Dockerfile
# Google Solution Challenge 2026
#
# Deploys the FastAPI backend to Google Cloud Run.
#
# Key notes:
#   - Cloud Run injects environment variables and secrets at runtime.
#     Do NOT bake .env or service-account JSON files into this image.
#   - Cloud Run requires the container to listen on 0.0.0.0:8080.
#   - FAISS and ChromaDB depend on OpenMP (libgomp1) for SIMD / parallel ops.
# =============================================================================

# ---------------------------------------------------------------------------
# 1. Base image
# ---------------------------------------------------------------------------
FROM python:3.11-slim

# ---------------------------------------------------------------------------
# 2. Environment variables
# ---------------------------------------------------------------------------
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# ---------------------------------------------------------------------------
# 3. Working directory
# ---------------------------------------------------------------------------
WORKDIR /app

# ---------------------------------------------------------------------------
# 4. System dependencies
#    - build-essential : C compiler toolchain for native Python packages
#    - curl / git      : useful during pip installs and health-checks
#    - libgomp1        : OpenMP runtime required by FAISS and NumPy BLAS
# ---------------------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# 5. Copy dependency file first (maximises Docker layer caching)
# ---------------------------------------------------------------------------
COPY backend/requirements.txt ./backend/requirements.txt

# ---------------------------------------------------------------------------
# 6. Install Python dependencies
# ---------------------------------------------------------------------------
RUN pip install --upgrade pip && \
    pip install -r backend/requirements.txt

# ---------------------------------------------------------------------------
# 7. Copy application code
#    Only the folders needed at runtime are copied.
#    Secrets (.env, service-account JSON) are NOT included —
#    they are injected by Cloud Run / Secret Manager.
# ---------------------------------------------------------------------------
COPY backend ./backend
COPY data    ./data
COPY shared  ./shared

# ---------------------------------------------------------------------------
# 9. Expose the port Cloud Run expects
# ---------------------------------------------------------------------------
EXPOSE 8080

# ---------------------------------------------------------------------------
# 10. Start the FastAPI server
#     Cloud Run sets the PORT env var to 8080; uvicorn binds to 0.0.0.0
#     so the container is reachable from the Cloud Run proxy.
# ---------------------------------------------------------------------------
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
