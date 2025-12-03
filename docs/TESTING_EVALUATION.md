# Testing & Evaluation Guide

## 📊 Evaluation Criteria Mapping

| Category | Weight | Our Coverage | Status |
|----------|--------|--------------|--------|
| **Functional Correctness** | 40% | Dedup (≥95%), NER (≥90%), Query Matrix | ✅ Implemented |
| **Technical Implementation** | 30% | LangGraph, RAG, Clean Code | ✅ Implemented |
| **Innovation & Completeness** | 20% | Groq RAG, Context Expansion | ✅ Implemented |
| **Documentation & Demo** | 10% | README, ARCHITECTURE, Demo | ✅ Complete |

---

## 🧪 How to Run Tests

### 1. Unit Tests

```bash
# Activate virtual environment
cd "e:\lux pro\Tradl AI"
venv\Scripts\activate

# Run all tests
pytest tests/ -v

# Run specific test files
pytest tests/test_dedup_agent.py -v
pytest tests/test_ner_agent.py -v
pytest tests/test_query_agent.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run integration tests only
pytest tests/test_integration.py -v
```

### 2. Performance Tests

```bash
# Test query response time (<500ms target)
python -c "
import time
from src.agents.query_agent import get_query_agent
from src.models.schemas import QueryInput

agent = get_query_agent()
start = time.time()
result = agent.search(QueryInput(query='HDFC Bank news', limit=10))
elapsed = (time.time() - start) * 1000
print(f'Query time: {elapsed:.2f}ms (target: <500ms)')
print(f'Results: {result.total_count}')
"
```

### 3. Accuracy Tests

```bash
# Test deduplication accuracy (≥95% target)
python -c "
from src.agents.dedup_agent import get_dedup_agent
from src.database.vector_store import get_vector_store

agent = get_dedup_agent()
vs = get_vector_store()

# Test duplicate detection
content1 = 'HDFC Bank announces 15% dividend for shareholders'
content2 = 'HDFC Bank declares 15% dividend in AGM'
content3 = 'TCS wins major contract from European bank'

r1 = agent.check_duplicate(content1)
r2 = agent.check_duplicate(content2)  # Should detect as duplicate
r3 = agent.check_duplicate(content3)  # Should be unique

print(f'Article 1: is_dup={r1.is_duplicate}')
print(f'Article 2: is_dup={r2.is_duplicate} (expected: True)')
print(f'Article 3: is_dup={r3.is_duplicate} (expected: False)')
"
```

### 4. NER Precision Test

```bash
python -c "
from src.agents.ner_agent import get_ner_agent

agent = get_ner_agent()

# Test with known content
test_articles = [
    {
        'content': 'HDFC Bank CEO announced Q1 results today',
        'expected': ['HDFC Bank']
    },
    {
        'content': 'RBI Governor Shaktikanta Das kept repo rate unchanged',
        'expected': ['RBI']
    },
    {
        'content': 'TCS and Infosys both reported strong earnings',
        'expected': ['TCS', 'Infosys']
    }
]

correct = 0
total = 0
for test in test_articles:
    result = agent.extract_all(test['content'])
    extracted = [e.value for e in result.companies]
    for exp in test['expected']:
        total += 1
        if any(exp in e for e in extracted):
            correct += 1

precision = correct / total if total > 0 else 0
print(f'NER Precision: {precision*100:.1f}% (target: ≥90%)')
"
```

---

## 📋 Manual Testing Checklist

### Core Functionality

- [ ] **Ingestion Pipeline**
  - [ ] Single article ingestion via API
  - [ ] Batch ingestion (10+ articles)
  - [ ] RSS feed fetching works
  - [ ] Duplicate articles are detected and clustered

- [ ] **Entity Extraction**
  - [ ] Companies correctly identified (HDFC Bank, TCS, Reliance)
  - [ ] Regulators correctly identified (RBI, SEBI)
  - [ ] Sectors correctly tagged (Banking, IT, Pharma)

- [ ] **Stock Impact Mapping**
  - [ ] Direct mentions → confidence 1.0
  - [ ] Sector news → confidence 0.6-0.8
  - [ ] Regulatory news → affects all sector stocks

- [ ] **Query Processing**
  - [ ] Company query returns relevant news
  - [ ] Sector query returns sector-wide news
  - [ ] Regulator query filters correctly
  - [ ] RAG synthesis provides AI answer (if Groq configured)

### API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Ingest article
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"HDFC Bank news","source":"test"}'

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query":"HDFC Bank news","limit":5}'

# Quick query
curl "http://localhost:8000/query/quick?q=Banking+sector"

# Stats
curl http://localhost:8000/stats

# RSS fetch
curl -X POST http://localhost:8000/ingest/rss
```

---

## 📈 Performance Benchmarks

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Query Response Time** | <500ms | `execution_time_ms` in API response |
| **Dedup Accuracy** | ≥95% | Test with labeled duplicate pairs |
| **NER Precision** | ≥90% | Test against ground truth entities |
| **Batch Ingestion** | 50 articles < 30s | Time batch API call |
| **RAG Latency** | <200ms (Groq) | `rag_metadata.llm_latency_ms` |

### Benchmark Script

```python
# benchmark.py
import time
import json
import requests

API_URL = "http://localhost:8000"

def benchmark_query():
    queries = [
        "HDFC Bank news",
        "Banking sector update", 
        "RBI policy",
        "TCS earnings",
        "IT sector"
    ]
    
    times = []
    for q in queries:
        start = time.time()
        resp = requests.post(f"{API_URL}/query", json={"query": q, "limit": 10})
        elapsed = (time.time() - start) * 1000
        times.append(elapsed)
        data = resp.json()
        print(f"Query: '{q}' | {elapsed:.0f}ms | {data.get('total_count', 0)} results")
    
    print(f"\nAverage: {sum(times)/len(times):.0f}ms")
    print(f"Max: {max(times):.0f}ms")
    print(f"Target: <500ms")

if __name__ == "__main__":
    benchmark_query()
```

---

## 🎯 Query Behavior Matrix Validation

Test that queries return expected results:

| Query | Expected Articles | Reason |
|-------|-------------------|--------|
| "HDFC Bank news" | N001, N004 | Direct mention + Banking sector |
| "Banking sector update" | N001, N002, N003, N004 | All banking articles |
| "RBI policy changes" | N002, N006, N007 | Regulator-specific |
| "Interest rate impact" | N002, N006, N007, N004 | Theme + Banking sector |
| "TCS" | N008, N010 | Direct + IT sector context |

---

## 🔬 LangSmith Tracing Verification

1. **Enable tracing** (already configured in `.env`)
2. **Run some queries**
3. **Check LangSmith dashboard**: https://smith.langchain.com
4. **Verify**:
   - Each query shows full agent pipeline
   - Trace includes: Ingestion → Dedup → NER → Impact → Storage
   - RAG synthesis appears as separate trace

---

## ✅ Final Submission Checklist

### Code Repository
- [x] LangGraph multi-agent implementation (6 agents)
- [x] Mock news dataset (35+ articles in `data/mock_news/`)
- [x] API endpoints for querying
- [ ] Test suite with unit and integration tests (needs real implementations)

### Documentation
- [x] README.md: Setup, architecture, usage
- [x] ARCHITECTURE.md: System design, agent flow
- [ ] Performance benchmarks (run and document results)

### Demo
- [x] Live demo (Web interface at `localhost:5173`)
- [ ] 5-10 minute video walkthrough
