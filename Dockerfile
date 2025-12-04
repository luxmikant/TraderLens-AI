# Tradl AI - Optimized Dockerfile for FAST builds
# Uses layer caching + pre-built wheels for rapid development

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (cached layer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip (cached layer)
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install heavy ML packages FIRST (rarely change - cached!)
RUN pip install --no-cache-dir \
    torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir \
    transformers==4.36.0 \
    sentence-transformers==2.2.2 \
    spacy==3.7.2

# Download spaCy model (cached layer)
RUN python -m spacy download en_core_web_sm

# Copy and install remaining requirements (changes more often)
COPY requirements-core.txt .
RUN pip install --no-cache-dir -r requirements-core.txt

# Copy application code LAST (changes most often)
COPY . .

# Environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production
ENV TOKENIZERS_PARALLELISM=false

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
