# 🚀 Tradl AI - Deployment Guide

This guide covers deployment options for Tradl AI on various platforms.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Render.com Deployment](#rendercom-deployment)
5. [Railway Deployment](#railway-deployment)
6. [AWS/GCP/Azure Deployment](#cloud-deployment)
7. [Environment Variables](#environment-variables)
8. [Monitoring Setup](#monitoring-setup)

---

## Prerequisites

- Python 3.11+
- OpenAI API Key (or Groq API Key)
- PostgreSQL (optional, for persistence)
- Redis (recommended for production caching)

---

## Local Development

### Quick Start

```bash
# 1. Clone and setup
cd "Tradl AI"
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Run the application
uvicorn main:app --reload --port 8000

# 4. Access the API
# API Docs: http://localhost:8000/docs
# Health: http://localhost:8000/health
```

---

## Docker Deployment

### Option 1: Docker Compose (Recommended)

```bash
# Start all services (API + PostgreSQL + Redis + ChromaDB)
docker-compose up -d

# With monitoring (Prometheus + Grafana)
docker-compose --profile monitoring up -d

# View logs
docker-compose logs -f tradl-api

# Stop services
docker-compose down
```

### Option 2: Single Container

```bash
# Build image
docker build -t tradl-ai .

# Run container
docker run -d \
  --name tradl-ai \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your-key \
  -e LLM_PROVIDER=openai \
  tradl-ai
```

---

## Render.com Deployment

### Automatic Deployment (Recommended)

1. **Connect Repository**
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml`

2. **Set Environment Variables**
   - Navigate to your service in Render
   - Go to "Environment" tab
   - Add `OPENAI_API_KEY` (marked as secret)

3. **Deploy**
   - Click "Manual Deploy" → "Deploy latest commit"
   - Wait for build to complete (~5-10 minutes first time)

### Manual Web Service Setup

1. **Create Web Service**
   - Click "New" → "Web Service"
   - Connect GitHub repo
   - Configure:
     - Name: `tradl-api`
     - Runtime: Python 3
     - Build Command: `pip install -r requirements.txt && python -m spacy download en_core_web_sm`
     - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

2. **Add Database**
   - Click "New" → "PostgreSQL"
   - Copy connection string to `DATABASE_URL`

3. **Add Redis**
   - Click "New" → "Redis"
   - Copy connection string to `REDIS_URL`

### Render Pricing

| Resource | Free Tier | Starter | Standard |
|----------|-----------|---------|----------|
| Web Service | 750 hrs/mo | $7/mo | $25/mo |
| PostgreSQL | 1GB | $7/mo | $20/mo |
| Redis | - | $10/mo | $25/mo |

---

## Railway Deployment

### Quick Deploy

1. **Create Project**
   ```bash
   # Install Railway CLI
   npm install -g @railway/cli
   
   # Login and deploy
   railway login
   railway init
   railway up
   ```

2. **Add Services**
   - PostgreSQL: `railway add --plugin postgresql`
   - Redis: `railway add --plugin redis`

3. **Configure Environment**
   - Add `OPENAI_API_KEY` in Railway dashboard
   - Railway auto-injects `DATABASE_URL` and `REDIS_URL`

### Railway Configuration (railway.json)

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

---

## Cloud Deployment

### AWS (Elastic Beanstalk)

1. Install EB CLI: `pip install awsebcli`
2. Initialize: `eb init -p python-3.11 tradl-ai`
3. Create environment: `eb create tradl-prod`
4. Deploy: `eb deploy`

### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/tradl-ai

# Deploy
gcloud run deploy tradl-ai \
  --image gcr.io/PROJECT_ID/tradl-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=your-key
```

### Azure Container Apps

```bash
# Create container app
az containerapp create \
  --name tradl-api \
  --resource-group tradl-rg \
  --environment tradl-env \
  --image tradl-ai:latest \
  --target-port 8000 \
  --ingress external
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key |
| `GROQ_API_KEY` | Yes* | - | Groq API key (alternative) |
| `LLM_PROVIDER` | No | `openai` | `openai` or `groq` |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model name |
| `DATABASE_URL` | No | SQLite | PostgreSQL connection string |
| `REDIS_HOST` | No | `localhost` | Redis host |
| `REDIS_PORT` | No | `6379` | Redis port |
| `REDIS_PASSWORD` | No | - | Redis password |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `LOG_LEVEL` | No | `INFO` | Logging level |

*One of OPENAI_API_KEY or GROQ_API_KEY is required.

---

## Monitoring Setup

### Prometheus Metrics

The `/metrics` endpoint exposes Prometheus metrics:

```bash
# View metrics
curl http://localhost:8000/metrics
```

Available metrics:
- `tradl_http_requests_total` - HTTP request count
- `tradl_http_request_duration_seconds` - Request latency
- `tradl_llm_requests_total` - LLM API calls
- `tradl_cache_hits_total` / `tradl_cache_misses_total` - Cache performance
- `tradl_sentiment_distribution_total` - Sentiment analysis results
- `tradl_entities_extracted_total` - NER extraction counts

### Grafana Dashboard

1. Start with monitoring profile: `docker-compose --profile monitoring up -d`
2. Access Grafana: http://localhost:3000 (admin/admin)
3. Add Prometheus data source: http://prometheus:9090
4. Import dashboard or create custom panels

### Health Checks

```bash
# Health endpoint
curl http://localhost:8000/health

# Expected response
{
  "status": "healthy",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "vector_store": "healthy",
    "cache": "healthy"
  }
}
```

---

## Production Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Configure PostgreSQL database
- [ ] Enable Redis caching
- [ ] Set up Prometheus monitoring
- [ ] Configure rate limiting
- [ ] Enable HTTPS (handled by platform)
- [ ] Set up logging aggregation
- [ ] Configure backup strategy
- [ ] Set up alerting (Grafana/PagerDuty)
- [ ] Load testing completed

---

## Troubleshooting

### Common Issues

**1. Model download fails**
```bash
# Manually download spaCy model
python -m spacy download en_core_web_sm
```

**2. Redis connection refused**
```bash
# Check Redis is running
redis-cli ping
```

**3. Out of memory**
- Reduce batch sizes in config
- Use smaller embedding model
- Increase container memory

**4. API rate limits**
- Implement request queuing
- Add caching for repeated queries
- Use multiple API keys with rotation

---

## Support

For issues or questions:
- Create GitHub issue
- Check logs: `docker-compose logs -f`
- Health check: `GET /health`
