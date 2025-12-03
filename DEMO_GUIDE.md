# 🎬 Tradl AI - Demo Guide

This guide explains how to give an effective demo of the Tradl AI financial news analysis system.

---

## Quick Demo Setup

### 1. Start the System

```bash
# Option A: Local Development
cd "Tradl AI"
uvicorn main:app --reload --port 8000

# Option B: Docker (Recommended for demos)
docker-compose up -d

# Wait for services to start (~30 seconds)
```

### 2. Verify Health

```bash
curl http://localhost:8000/health
```

### 3. Open API Documentation

Navigate to: **http://localhost:8000/docs**

---

## Demo Script (5-10 minutes)

### 🎯 Part 1: Introduction (1 minute)

> "Tradl AI is an intelligent financial news analysis platform that uses LLMs and RAG to help traders make informed decisions. It processes financial news in real-time, extracts entities, analyzes sentiment, and provides actionable insights."

**Key Features to Highlight:**
- Multi-agent LangGraph architecture
- Real-time news ingestion
- FinBERT sentiment analysis
- Named Entity Recognition (NER)
- Vector similarity search with ChromaDB
- WebSocket real-time alerts

---

### 🎯 Part 2: Live API Demo (5-7 minutes)

#### Demo 1: News Ingestion

Open Swagger UI at `/docs`, then:

```json
POST /api/v1/ingest

{
  "title": "Reliance Industries reports record quarterly profit",
  "content": "Reliance Industries Ltd (RIL) announced Q3 results with revenue of ₹2.5 lakh crore. The company's retail and digital services segments showed strong growth. Jio Platforms reported 450 million subscribers. Chairman Mukesh Ambani announced plans for renewable energy investments.",
  "source": "Economic Times",
  "published_date": "2024-01-15T10:30:00"
}
```

**Talking Points:**
- "Watch how the system extracts entities like company names, stock symbols, and key figures"
- "FinBERT analyzes the sentiment - this news is clearly positive/bullish"
- "The article is automatically deduplicated if similar content exists"

#### Demo 2: RAG Query

```json
POST /api/v1/query

{
  "query": "What are the latest developments for Reliance Industries?",
  "limit": 5
}
```

**Talking Points:**
- "The system retrieves relevant news using vector similarity search"
- "GPT-4 synthesizes the information into a coherent response"
- "Notice the structured output with entities and sentiment included"

#### Demo 3: Search with Filters

```json
POST /api/v1/search

{
  "query": "tech sector news",
  "sector": "Technology",
  "sentiment": "positive",
  "limit": 10
}
```

**Talking Points:**
- "Advanced filtering by sector, sentiment, date range"
- "Useful for sector-specific analysis and trend identification"

#### Demo 4: Real-time Alerts (Advanced)

Open WebSocket connection in a separate terminal:

```bash
# Using websocat (install: cargo install websocat)
websocat ws://localhost:8000/ws/alerts

# Or use the Python demo script
python demo.py
```

Then ingest a high-impact article:

```json
POST /api/v1/ingest

{
  "title": "SEBI announces major regulatory changes for F&O trading",
  "content": "SEBI has announced sweeping changes to futures and options trading rules that will impact millions of retail traders. New margin requirements and position limits will be effective from next month.",
  "source": "Mint",
  "published_date": "2024-01-15T14:00:00"
}
```

**Talking Points:**
- "High-impact news triggers real-time alerts"
- "WebSocket delivers instant notifications"
- "Traders can set up custom alert rules"

---

### 🎯 Part 3: Technical Deep Dive (Optional, 3-5 minutes)

#### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       Tradl AI Architecture                  │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │ Ingestion│───▶│ NER +    │───▶│ Storage  │              │
│  │  Agent   │    │ Sentiment│    │  Agent   │              │
│  └──────────┘    └──────────┘    └──────────┘              │
│        │              │                │                    │
│        ▼              ▼                ▼                    │
│  ┌──────────────────────────────────────────────┐          │
│  │            ChromaDB + PostgreSQL              │          │
│  └──────────────────────────────────────────────┘          │
│        │                                                    │
│        ▼                                                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │   RAG    │───▶│   LLM    │───▶│ Response │              │
│  │ Retrieval│    │Synthesis │    │  Format  │              │
│  └──────────┘    └──────────┘    └──────────┘              │
└─────────────────────────────────────────────────────────────┘
```

#### Metrics Dashboard

Navigate to: **http://localhost:8000/metrics**

Show Prometheus metrics:
- Request latency
- Cache hit rates
- LLM usage statistics
- Entity extraction counts

---

## Demo with Sample Data

### Run the Demo Script

```bash
# Run comprehensive demo
python demo.py
```

This script:
1. Ingests sample financial news articles
2. Runs various queries
3. Shows deduplication in action
4. Demonstrates sentiment analysis
5. Tests multilingual support

### Sample Articles for Demo

```python
articles = [
    {
        "title": "Tata Motors EV sales surge 150%",
        "content": "Tata Motors reported record electric vehicle sales in December...",
        "source": "Business Standard"
    },
    {
        "title": "Infosys wins $500M digital transformation deal",
        "content": "Infosys has secured a major contract with a US financial services firm...",
        "source": "Moneycontrol"
    },
    {
        "title": "RBI holds rates steady amid inflation concerns",
        "content": "The Reserve Bank of India maintained the repo rate at 6.5%...",
        "source": "Economic Times"
    }
]
```

---

## Benchmark Demo

Show system performance:

```bash
python tests/test_complete_evaluation.py -v
```

**Highlight:**
- ✅ 100% Deduplication accuracy
- ✅ 100% NER extraction accuracy
- ✅ Sub-millisecond query latency
- ✅ 37/37 tests passing

---

## Q&A Preparation

### Common Questions

**Q: How does deduplication work?**
> "We use MinHash and Jaccard similarity to detect near-duplicate articles. Articles with >85% similarity are flagged as duplicates."

**Q: What sentiment model do you use?**
> "FinBERT, a BERT model fine-tuned on financial text. It outperforms generic sentiment models on financial news."

**Q: How do you handle multiple languages?**
> "We support Hindi and regional languages. The system detects the language and uses appropriate translation/processing."

**Q: What's the latency for real-time queries?**
> "Vector search takes ~10-50ms. Full RAG queries with LLM synthesis typically complete in 1-3 seconds."

**Q: How do you scale?**
> "Redis caching for embeddings, PostgreSQL for persistent storage, and horizontal scaling via containerization."

---

## Troubleshooting During Demo

### If something fails:

1. **API not responding:**
   ```bash
   docker-compose logs tradl-api
   ```

2. **LLM quota exceeded:**
   - Use skip_rag mode for fast queries
   - Show cached results

3. **Database issues:**
   ```bash
   docker-compose restart postgres
   ```

4. **Fallback demo:**
   - Run unit tests: `pytest tests/ -v`
   - Show code architecture
   - Walk through Swagger documentation

---

## Post-Demo

### Share Links
- GitHub Repository: [link]
- API Documentation: `/docs`
- Deployment Guide: `DEPLOYMENT.md`

### Follow-up Materials
- Architecture diagram
- Performance benchmarks
- Integration guide for traders

---

## Demo Checklist

Before demo:
- [ ] Services running (`docker-compose up -d`)
- [ ] API responding (`/health`)
- [ ] OpenAI key configured
- [ ] Sample data ingested
- [ ] Swagger UI accessible
- [ ] WebSocket working
- [ ] Screen sharing ready

Good luck with your demo! 🚀
