# Deployment Guide

## 🚀 Deployment Options

### Option 1: Docker Compose (Recommended for Demo)

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY}
      - LANGCHAIN_TRACING_V2=true
      - LANGCHAIN_PROJECT=tradl-hackathon
      - CHROMA_PERSIST_DIR=/data/chroma
      - POSTGRES_HOST=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - chroma_data:/data/chroma
    depends_on:
      - postgres
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - api

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: financial_news
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  chroma_data:
  postgres_data:
```

### Dockerfile (Backend)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY main.py .
COPY .env.example .env

# Create data directories
RUN mkdir -p /data/chroma

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile (Frontend)
```dockerfile
FROM node:20-alpine as build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

---

## Option 2: Cloud Deployment

### AWS (ECS + RDS)

```
┌─────────────────────────────────────────────────┐
│                    AWS Cloud                     │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────────────────┐ │
│  │ CloudFront  │───▶│    ALB (Load Balancer)  │ │
│  └─────────────┘    └───────────┬─────────────┘ │
│                                 │               │
│        ┌────────────────────────┼────────┐      │
│        │         ECS Cluster    │        │      │
│        │  ┌──────────┐  ┌──────────┐     │      │
│        │  │ API Task │  │ API Task │     │      │
│        │  │  (x2)    │  │  (x2)    │     │      │
│        │  └────┬─────┘  └────┬─────┘     │      │
│        └───────┼─────────────┼───────────┘      │
│                │             │                  │
│        ┌───────┴─────────────┴───────┐         │
│        │                             │         │
│  ┌─────┴─────┐  ┌──────────┐  ┌─────┴─────┐   │
│  │    RDS    │  │ ElastiC  │  │    S3     │   │
│  │ PostgreSQL│  │  (Redis) │  │  (Chroma) │   │
│  └───────────┘  └──────────┘  └───────────┘   │
└─────────────────────────────────────────────────┘
```

**Estimated Cost**: ~$150-300/month

### Vercel + Railway (Budget Option)

| Service | Purpose | Cost |
|---------|---------|------|
| Vercel | Frontend hosting | Free |
| Railway | FastAPI + PostgreSQL | ~$20/month |
| LangSmith | Observability | Free tier |

---

## Option 3: Local Development

```bash
# Terminal 1: Start PostgreSQL (optional)
docker run -d --name postgres -e POSTGRES_PASSWORD=secret -p 5432:5432 postgres:15

# Terminal 2: Start Backend
cd "e:\lux pro\Tradl AI"
venv\Scripts\activate
python -m uvicorn src.api.main:app --port 8000 --reload

# Terminal 3: Start Frontend
cd frontend
npm run dev
```

---

## 🔧 Pre-Deployment Checklist

- [ ] Set production environment variables
- [ ] Configure CORS for production domain
- [ ] Set up SSL certificates
- [ ] Configure rate limiting
- [ ] Set up monitoring (LangSmith already integrated)
- [ ] Create database backup strategy
- [ ] Test health endpoints
- [ ] Load test with sample data

---

## 📊 Environment Variables

```env
# Required
OPENAI_API_KEY=sk-...
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=tradl-hackathon

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=financial_news
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

# Optional
CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_MODEL=all-mpnet-base-v2
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 🎬 Demo Deployment Steps

### Quick Demo (5 minutes)

```bash
# 1. Start API
cd "e:\lux pro\Tradl AI"
venv\Scripts\python -m uvicorn src.api.main:app --port 8000

# 2. Start Frontend (new terminal)
cd frontend
npm run dev

# 3. Ingest sample data
python fetch_live_news.py

# 4. Open browser
# API Docs: http://localhost:8000/docs
# Dashboard: http://localhost:5173
# LangSmith: https://smith.langchain.com
```

---

## 📈 Scaling Considerations

| Load | Setup | Resources |
|------|-------|-----------|
| Demo (1-10 users) | Single instance | 2 vCPU, 4GB RAM |
| Small (10-100 users) | 2 API replicas + Redis | 4 vCPU, 8GB RAM |
| Medium (100-1000 users) | K8s cluster + CDN | 8 vCPU, 16GB RAM |
| Large (1000+ users) | Multi-region + Sharding | Custom |
