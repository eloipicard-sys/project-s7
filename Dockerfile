# ============================================================
# Dockerfile — Projet S7-1500 | Thermal Process Monitor
# ============================================================

FROM python:3.11-slim

LABEL maintainer="Thesis S7-1500"
LABEL description="Flask supervision app — Siemens S7-1500 thermal process"

WORKDIR /app

# Install Python dependencies (cached layer)
# Note: python-snap7 >= 1.0 bundles the snap7 shared library — no apt install needed
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create persistent log directory
RUN mkdir -p /app/logs

# Copy application source
COPY app/ .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOG_DIR=/app/logs

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

CMD ["python", "main.py"]
