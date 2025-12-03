# LangSmith Testing & Observability Guide

## 🚀 Quick Start Testing

### 1. Verify LangSmith Connection
```bash
cd "e:\lux pro\Tradl AI"
venv\Scripts\python -c "from src.utils.langsmith_setup import enable_langsmith; print('Connected:', enable_langsmith())"
```

### 2. Start the API Server
```bash
venv\Scripts\python -m uvicorn src.api.main:app --port 8000
```

### 3. Trigger a Traced Run
```bash
# Ingest a sample article (this creates a trace)
curl -X POST http://localhost:8000/ingest -H "Content-Type: application/json" -d "{\"title\":\"RBI raises repo rate by 25bps\",\"content\":\"The Reserve Bank of India raised the repo rate to 6.75% citing inflation concerns.\",\"source\":\"test\"}"

# Or run a query
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d "{\"query\":\"HDFC Bank news\",\"limit\":5}"
```

### 4. View Traces in LangSmith
Open: **https://smith.langchain.com** → Project: `tradl-hackathon`

---

## 🔍 What LangSmith Shows You

| Feature | What You See | Why It Matters |
|---------|-------------|----------------|
| **Run Timeline** | Visual flow through Ingest → Dedup → NER → Impact → Storage | Debug pipeline bottlenecks |
| **Latency Breakdown** | Time spent in each agent node (ms) | Optimize slow agents |
| **Input/Output Payloads** | Full state at each step | Verify entity extraction accuracy |
| **Token Usage** | LLM tokens consumed per call | Control costs |
| **Error Traces** | Stack traces with context | Quick debugging |
| **Run Filtering** | Filter by status, latency, date | Find problematic runs |

---

## 🎯 Amazing Things You Can Do

### 1. **Debug Entity Extraction**
- Click any run → expand NER node → see extracted companies/sectors
- Compare expected vs actual to tune entity rules

### 2. **Monitor Deduplication Accuracy**
- Filter runs where `is_duplicate=True`
- Inspect similarity scores to tune threshold

### 3. **Track Stock Impact Confidence**
- View impact agent output → see confidence scores per stock
- Identify low-confidence predictions to improve

### 4. **Performance Optimization**
- Sort runs by latency → find slowest pipelines
- Drill into which agent is the bottleneck

### 5. **A/B Testing**
- Create different projects for different model versions
- Compare accuracy and latency side-by-side

### 6. **Dataset Creation**
- Export traced runs as datasets
- Use for fine-tuning or evaluation

### 7. **Alerts & Monitoring**
- Set up alerts for high error rates
- Monitor daily throughput

---

## 📊 Sample LangSmith Dashboard View

```
┌─────────────────────────────────────────────────────────────────┐
│  tradl-hackathon                                    Last 24h ▼  │
├─────────────────────────────────────────────────────────────────┤
│  Runs: 156    Success: 98.7%    Avg Latency: 1.2s    Errors: 2 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Recent Runs                                                    │
│  ────────────────────────────────────────────────────────────  │
│  ✓ news_processing  "RBI raises repo..."     1.1s   2 min ago  │
│  ✓ news_processing  "HDFC Bank dividend..."  0.9s   5 min ago  │
│  ✓ query            "Banking sector news"    0.3s   8 min ago  │
│  ✗ news_processing  "Connection timeout"     --     12 min ago │
│                                                                 │
│  [Click any run to see full trace →]                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Advanced Usage

### Custom Metadata Tagging
Add custom tags to runs for filtering:
```python
from langsmith import traceable

@traceable(tags=["high-priority", "banking-sector"])
async def process_priority_news(article):
    ...
```

### Evaluation Datasets
Export successful runs as golden datasets:
1. LangSmith → Datasets → Create
2. Add runs with correct outputs
3. Use for regression testing

### Cost Tracking
- View token usage per run
- Aggregate by day/week for budgeting
- Set alerts when usage exceeds threshold
