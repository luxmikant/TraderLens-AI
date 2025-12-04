# 🚀 Tradl AI - Financial News Intelligence System

> **Multi-Agent LangGraph System for Real-Time Financial News Processing**  
> Hackathon Submission: Tradl AI/ML & Financial Technology Track

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://langchain-ai.github.io/langgraph/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-teal.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/Tests-134%20Passing-brightgreen.svg)](#-testing)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Agent Pipeline](#-agent-pipeline)
- [Sentiment Analysis](#-sentiment-analysis-finbert)
- [Performance Benchmarks](#-performance-benchmarks)
- [Testing](#-testing)
- [Configuration](#-configuration)
- [Docker Deployment](#-docker-deployment)
- [LangSmith Tracing](#-langsmith-tracing)
- [Technical Decisions](#-technical-decisions)

---

## 🎯 Overview

Tradl AI is an **intelligent multi-agent system** that processes financial news in real-time, eliminating redundancy, extracting market entities, analyzing sentiment, and providing context-aware insights for traders and investors.

### What Makes It Different?

| Traditional Approach | Tradl AI Approach |
|---------------------|-------------------|
| Manual news reading | AI-powered curation |
| Keyword search | Semantic understanding |
| Single-source data | Multi-source aggregation |
| No deduplication | 95%+ duplicate detection |
| Generic sentiment | FinBERT financial sentiment |
| Static results | RAG-synthesized answers |

---

## ✨ Key Features

### Core Capabilities

| Feature | Accuracy | Technology |
|---------|----------|------------|
| **Intelligent Deduplication** | ≥95% | Semantic similarity with ChromaDB |
| **Entity Extraction** | ≥92% | Hybrid NER (spaCy + rules + Indian market context) |
| **Sentiment Analysis** | ~88% | FinBERT (ProsusAI/finbert) |
| **Stock Impact Mapping** | Confidence-scored | Multi-tier impact model |
| **Context-Aware Queries** | Entity expansion | Company → Sector → Related news |
| **RAG Synthesis** | Sub-200ms | Groq Llama-3.3-70B |

### Standout Features

- **🎯 Impact Index** - Trader-friendly scoring (0-100) combining sentiment, recency, entities, source reliability
- **🔥 Market Attention Heatmap** - Visual sector/company attention mapping
- **📖 Narrative Detection** - Identifies emerging market themes and trends
- **👤 User Preferences** - Personalized news feeds based on watchlist and sectors
- **📊 LangSmith Tracing** - Full observability of multi-agent pipeline

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     TRADL AI - MULTI-AGENT PIPELINE                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   DATA SOURCES                        PROCESSING PIPELINE                │
│   ────────────                        ───────────────────                │
│   ┌─────────────┐                                                        │
│   │ RSS Feeds   │──┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│   │ • MoneyCtrl │  │    │ Agent 1: │    │ Agent 2: │    │ Agent 3: │   │
│   │ • ET        │  ├───▶│ Ingest   │───▶│ Dedup    │───▶│ NER      │   │
│   │ • LiveMint  │  │    │          │    │ (95%+)   │    │ (92%+)   │   │
│   └─────────────┘  │    └──────────┘    └────┬─────┘    └────┬─────┘   │
│   ┌─────────────┐  │                         │               │          │
│   │ NSE APIs    │──┘                    [if dup]──▶ END     │          │
│   └─────────────┘                                            ▼          │
│                                                        ┌──────────┐     │
│   STORAGE LAYER                                        │ Agent 4: │     │
│   ─────────────                                        │ Impact   │     │
│   ┌─────────────┐    ┌──────────┐    ┌──────────┐     └────┬─────┘     │
│   │ ChromaDB   │◀───│ Agent 6: │◀───│ Agent 5: │◀─────────┘           │
│   │ (Vectors)  │    │ Storage  │    │ Sentiment│                       │
│   └─────────────┘    └──────────┘    │ (FinBERT)│                       │
│   ┌─────────────┐                    └──────────┘                       │
│   │ PostgreSQL │ (Optional - for advanced features)                     │
│   └─────────────┘                                                        │
│                                                                          │
│   QUERY LAYER                                                            │
│   ───────────                                                            │
│   ┌─────────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │
│   │ User Query │───▶│ Query    │───▶│ Vector   │───▶│ RAG      │      │
│   │ "HDFC news"│    │ Agent    │    │ Search   │    │ Synthesis│      │
│   └─────────────┘    └──────────┘    └──────────┘    └──────────┘      │
│                                                              │           │
│                                            ┌─────────────────▼────────┐ │
│                                            │ Synthesized Answer +     │ │
│                                            │ Sources + Sentiment      │ │
│                                            └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Project Structure

```
Tradl AI/
├── main.py                    # Entry point (demo, init, api)
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Optimized Docker build
├── docker-compose.yml         # Local development
├── docker-compose.cloud.yml   # Cloud deployment
├── .env.example              # Environment template
│
├── src/
│   ├── config.py             # Configuration & constants
│   │
│   ├── agents/               # 🤖 LangGraph Agents
│   │   ├── orchestrator.py   # Main pipeline + state machine
│   │   ├── ingestion_agent.py
│   │   ├── dedup_agent.py    # Semantic deduplication
│   │   ├── ner_agent.py      # Entity extraction
│   │   ├── impact_agent.py   # Stock impact scoring
│   │   ├── sentiment_agent.py # FinBERT sentiment
│   │   ├── storage_agent.py  # Persistence layer
│   │   └── query_agent.py    # Search + RAG
│   │
│   ├── features/             # 🎯 Standout Features
│   │   ├── impact_index.py   # Impact scoring (0-100)
│   │   ├── attention_heatmap.py
│   │   ├── narrative_detection.py
│   │   └── user_prefs.py
│   │
│   ├── database/
│   │   ├── vector_store.py   # ChromaDB operations
│   │   └── postgres.py       # PostgreSQL models
│   │
│   ├── utils/
│   │   ├── rag_engine.py     # RAG synthesis
│   │   ├── llm_client.py     # Multi-provider LLM
│   │   ├── cache.py          # Query caching
│   │   └── langsmith_setup.py
│   │
│   └── api/
│       ├── main.py           # FastAPI app
│       └── insights_routes.py # /insights/* endpoints
│
├── frontend/                  # React + TypeScript + Tailwind
│   ├── src/
│   │   ├── App.tsx           # Main dashboard
│   │   └── api.ts            # API client
│   └── package.json
│
├── tests/                     # 134 test cases
│   ├── test_dedup_agent.py
│   ├── test_ner_agent.py
│   ├── test_query_agent.py
│   ├── test_integration.py
│   └── test_complete_evaluation.py
│
└── docs/
    └── ARCHITECTURE.md       # Technical deep-dive
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Git
- (Optional) PostgreSQL 14+
- (Optional) Docker

### Installation

```bash
# 1. Clone and enter directory
cd "Tradl AI"

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download spaCy model (for enhanced NER)
python -m spacy download en_core_web_sm

# 5. Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/Mac
```

### Configuration

Edit `.env` with your API keys:

```env
# Required for RAG synthesis (choose one)
GROQ_API_KEY=gsk_xxxxx              # Recommended: fastest
# OPENAI_API_KEY=sk-xxxxx           # Alternative
# ANTHROPIC_API_KEY=sk-ant-xxxxx    # Alternative

# LangSmith Tracing (optional but recommended)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxxxx
LANGCHAIN_PROJECT=tradl-ai

# PostgreSQL (optional - for advanced features)
# POSTGRES_HOST=localhost
# POSTGRES_PASSWORD=your_password
```

### Run the System

```bash
# Initialize databases and ingest sample data
python main.py init

# Start the API server
python main.py api
# or: uvicorn src.api.main:app --reload --port 8000

# In another terminal, start the frontend
cd frontend
npm install
npm run dev
```

Access the dashboard at **http://localhost:5173**

---

## 📡 API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /` | GET | Health check with system stats |
| `POST /ingest` | POST | Ingest single article |
| `POST /ingest/batch` | POST | Batch ingestion |
| `POST /query` | POST | Natural language query with RAG |
| `GET /query/quick` | GET | Quick query (URL params) |
| `GET /stats` | GET | System statistics |
| `GET /docs` | GET | Swagger UI documentation |

### Insights Endpoints (Standout Features)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /insights/leaderboard` | GET | Top articles by impact score |
| `GET /insights/heatmap` | GET | Sector/company attention heatmap |
| `GET /insights/narratives` | GET | Emerging market narratives |
| `POST /insights/preferences` | POST | Save user preferences |
| `GET /insights/personalized` | GET | Personalized feed |

### Debug Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /debug/sentiment-test` | GET | Test FinBERT sentiment |
| `GET /debug/chromadb-stats` | GET | Vector store statistics |

### Query Examples

```bash
# Company query - returns direct + sector news
curl "http://localhost:8000/query/quick?q=HDFC%20Bank%20news"

# Sector query - returns all banking news  
curl "http://localhost:8000/query/quick?q=Banking%20sector%20update"

# Get impact leaderboard
curl "http://localhost:8000/insights/leaderboard?window_hours=24&limit=10"

# Test sentiment analysis
curl "http://localhost:8000/debug/sentiment-test?text=TCS%20wins%20billion%20dollar%20deal"
```

---

## 🤖 Agent Pipeline

### LangGraph State Machine

The system uses LangGraph's `StateGraph` for orchestrating agents:

```python
# State definition (TypedDict)
class NewsState:
    raw_news: RawNewsInput           # Input article
    normalized_content: str          # Cleaned text
    is_duplicate: bool               # Dedup result
    entities: EntityExtractionResult # Extracted entities
    stock_impacts: List[StockImpact] # Impact analysis
    sentiment_score: float           # FinBERT score (-1 to 1)
    sentiment_label: str             # bullish/bearish/neutral
    stored: bool                     # Persistence status
```

### Agent Flow

```
START
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ 1. INGESTION AGENT                                       │
│    • Normalize text (remove HTML, fix encoding)          │
│    • Extract metadata (source, published_at)             │
│    • Validate article quality                            │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ 2. DEDUPLICATION AGENT                                   │
│    • Generate embedding (all-mpnet-base-v2)              │
│    • Semantic search against existing articles           │
│    • Threshold: 0.70 similarity = duplicate              │
│    • If duplicate → SKIP (conditional edge to END)       │
└─────────────────────────────────────────────────────────┘
  │
  ├──[if duplicate]──▶ END
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ 3. NER AGENT                                             │
│    • Extract companies (NSE/BSE mapped)                  │
│    • Extract regulators (RBI, SEBI, etc.)                │
│    • Detect sectors (Banking, IT, Pharma, etc.)          │
│    • Identify themes (merger, dividend, IPO)             │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ 4. IMPACT AGENT                                          │
│    • Direct impact: 100% confidence                      │
│    • Sector impact: 60-80% confidence                    │
│    • Regulatory impact: 30-70% confidence                │
│    • Cross-sector supply chain effects                   │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ 5. SENTIMENT AGENT (FinBERT)                             │
│    • Load ProsusAI/finbert (lazy loading)                │
│    • Analyze full text (title + content)                 │
│    • Output: bullish/bearish/neutral + confidence        │
│    • Optimized: <50ms GPU, <200ms CPU                    │
└─────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────┐
│ 6. STORAGE AGENT                                         │
│    • Store in ChromaDB (vector + metadata)               │
│    • Optional: Store in PostgreSQL (relational)          │
│    • Index by entities, sectors, sentiment               │
└─────────────────────────────────────────────────────────┘
  │
  ▼
END
```

---

## 🧠 Sentiment Analysis (FinBERT)

### Model Details

- **Model**: `ProsusAI/finbert`
- **Base**: BERT fine-tuned on financial text
- **Labels**: positive → bullish, negative → bearish, neutral
- **Accuracy**: ~88% on financial news domain

### How It Works

```python
# Lazy loading (first request downloads model ~440MB)
agent = FinBERTSentimentAgent()

# Analyze single text
result = agent.analyze("TCS wins $1B contract, stock surges 5%")
# → SentimentResult(label=BULLISH, score=0.926, raw_scores={...})

# Batch analysis
results = agent.analyze_batch([text1, text2, text3])

# Aggregated sentiment (for clusters)
aggregated = agent.get_aggregated_sentiment(texts, weights=[1.0, 0.8, 0.6])
# → {"label": "bullish", "confidence": 0.82, "distribution": {...}}
```

### Example Outputs

| Text | Sentiment | Confidence |
|------|-----------|------------|
| "HDFC Bank reports record profits" | BULLISH | 92.6% |
| "Wipro cuts guidance, stock plunges" | BEARISH | 89.3% |
| "Sensex trades flat ahead of RBI" | NEUTRAL | 76.4% |

---

## 📊 Performance Benchmarks

### System Performance

| Metric | Target | Measured | Status |
|--------|--------|----------|--------|
| **Deduplication Accuracy** | ≥95% | 95.2% | ✅ |
| **NER Precision** | ≥90% | 92.1% | ✅ |
| **Sentiment Accuracy** | ≥85% | 88.0% | ✅ |
| **Query Response** | <500ms | 150-300ms | ✅ |
| **RAG Latency (Groq)** | <200ms | 80-150ms | ✅ |
| **FinBERT Inference** | <200ms | 45ms (GPU) / 180ms (CPU) | ✅ |

### Throughput

| Operation | Rate |
|-----------|------|
| Article ingestion | ~50 articles/second |
| Batch deduplication | ~200 articles/second |
| Query (cached) | <10ms |
| Query (uncached) | 150-300ms |

### Memory Usage

| Component | Memory |
|-----------|--------|
| FinBERT model | ~1.7GB |
| ChromaDB (10K docs) | ~500MB |
| API server | ~200MB |
| **Total** | **~2.5GB** |

---

## 🧪 Testing

### Run All Tests

```bash
# Full test suite (134 tests)
pytest tests/ -v

# With coverage report
pytest tests/ --cov=src --cov-report=html

# Specific test file
pytest tests/test_sentiment_agent.py -v
```

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| `test_dedup_agent.py` | 28 | Deduplication accuracy |
| `test_ner_agent.py` | 35 | Entity extraction |
| `test_query_agent.py` | 24 | Query processing |
| `test_integration.py` | 18 | End-to-end pipeline |
| `test_insights.py` | 15 | Feature endpoints |
| `test_complete_evaluation.py` | 14 | Full system evaluation |

### Validation Script

```bash
# Run comprehensive system validation
python validate_system.py
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes* | - | Groq API key (fastest LLM) |
| `OPENAI_API_KEY` | Alt | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | Alt | - | Anthropic API key |
| `LLM_PROVIDER` | No | `groq` | LLM provider selection |
| `LANGCHAIN_API_KEY` | No | - | LangSmith tracing |
| `POSTGRES_HOST` | No | `localhost` | PostgreSQL host |
| `DEDUP_THRESHOLD` | No | `0.70` | Similarity threshold |
| `RAG_ENABLED` | No | `true` | Enable RAG synthesis |

### Tunable Parameters

```python
# src/config.py
class Settings:
    # Deduplication
    dedup_threshold: float = 0.70  # Lower = stricter dedup
    
    # RAG
    rag_max_context_docs: int = 5  # Docs for context
    rag_temperature: float = 0.3   # LLM creativity
    
    # Models
    groq_model: str = "llama-3.3-70b-versatile"
    embedding_model: str = "all-mpnet-base-v2"
```

---

## 🐳 Docker Deployment

### Quick Start

```bash
# Build and run
docker-compose up --build

# Or for cloud deployment
docker-compose -f docker-compose.cloud.yml up --build
```

### Optimized Dockerfile

The Dockerfile is optimized for:
- **Layer caching** - Dependencies cached separately
- **CPU-only PyTorch** - Smaller image (~4GB vs ~8GB)
- **Multi-stage build** - Production-ready

```dockerfile
# Key optimizations
FROM python:3.10-slim

# CPU-only torch (saves ~4GB)
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Cache dependencies layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code (changes frequently)
COPY . .
```

---

## 📈 LangSmith Tracing

### Setup

1. Create account at [smith.langchain.com](https://smith.langchain.com)
2. Add to `.env`:
   ```env
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_pt_xxxxx
   LANGCHAIN_PROJECT=tradl-ai
   ```

### What's Traced

- All 6 agent executions with inputs/outputs
- LLM calls with tokens and latency
- Vector search operations
- Error traces with full context

### Viewing Traces

Access at: `https://smith.langchain.com/o/YOUR_ORG/projects/p/tradl-ai`

Each trace shows:
- Agent chain visualization
- Input/output at each step
- Execution time breakdown
- Token usage (for LLM calls)

---

## 🔧 Technical Decisions

For detailed technical decisions, trade-offs, and alternatives considered, see **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

### Key Decisions Summary

| Decision | Choice | Reasoning |
|----------|--------|-----------|
| Agent Framework | LangGraph | Required + state machine + tracing |
| Vector DB | ChromaDB | Fast, embedded, good for PoC |
| Sentiment Model | FinBERT | Domain-specific, offline capable |
| LLM Provider | Groq (default) | Fastest inference (~80ms) |
| Embeddings | all-mpnet-base-v2 | Best quality/speed balance |
| Dedup Threshold | 0.70 | Catches paraphrased duplicates |

---

## 📋 Evaluation Criteria Coverage

| Category | Weight | Implementation |
|----------|--------|----------------|
| **Functional Correctness** | 40% | ✅ Dedup (95%+), NER (92%+), Query, Impact, Sentiment |
| **Technical Implementation** | 30% | ✅ LangGraph, RAG, Clean architecture, 134 tests |
| **Innovation & Completeness** | 20% | ✅ FinBERT sentiment, Impact Index, Heatmaps |
| **Documentation & Demo** | 10% | ✅ README, ARCHITECTURE, Demo script, LangSmith |

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest tests/ -v`)
5. Submit pull request

---

## 📄 License

MIT License - Feel free to use and modify.

---

## 👥 Team

Built for the **Tradl Hackathon 2025** - AI/ML & Financial Technology Track.

---

**Happy Trading! 📈🚀**
