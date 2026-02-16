# ── Stage 1: Builder ──────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY api/pyproject.toml ./

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e "."

# ── Stage 2: Runtime ──────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl unzip && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY api/ ./

# Copy ALS model files
COPY models/ ./models/

# Copy data (tags.csv needed for embedding index)
COPY data/ ./data/

# Copy scripts for seeding
COPY scripts/ ./scripts/

# Download MovieLens small dataset if not already present
RUN if [ ! -f "data/raw/ml-latest-small/movies.csv" ]; then \
      mkdir -p data/raw && \
      curl -L -o /tmp/ml-latest-small.zip \
        https://files.grouplens.org/datasets/movielens/ml-latest-small.zip && \
      unzip -o /tmp/ml-latest-small.zip -d data/raw/ && \
      rm /tmp/ml-latest-small.zip; \
    fi

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health')" || exit 1

CMD ["bash", "scripts/start.sh"]
