# AgriSaathi AI Backend — Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements.txt ./
COPY mlbackend/requirements.txt ./mlbackend-requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r mlbackend-requirements.txt

# Copy application code
COPY mlbackend ./mlbackend
COPY models ./models
COPY datasets/manifests ./datasets/manifests
COPY datasets/splits ./datasets/splits
COPY datasets/test_fixtures ./datasets/test_fixtures

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV ENFORCE_JWT_AUTH=false

# Expose API port
EXPOSE 8000

# Health check using canonical health probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start Uvicorn (reads $PORT from cloud provider, fallback to 8000)
CMD sh -c "uvicorn mlbackend.main:app --host 0.0.0.0 --port ${PORT:-8000}"
