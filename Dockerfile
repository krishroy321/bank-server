# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# ── Metadata ──────────────────────────────────────────────────────────────────
LABEL maintainer="Krish Bank"
LABEL description="Krish Bank HTTP Banking API Server"
LABEL version="1.0"

# ── Environment ───────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BANK_PORT=8080 \
    BANK_DATA=/data/bank_data.json

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Copy source ───────────────────────────────────────────────────────────────
COPY bank_server.py .

# ── Create data volume directory ──────────────────────────────────────────────
RUN mkdir -p /data

# ── Expose port ───────────────────────────────────────────────────────────────
EXPOSE 8080

# ── Health check ──────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/')" || exit 1

# ── Run ───────────────────────────────────────────────────────────────────────
CMD ["python3", "bank_server.py"]