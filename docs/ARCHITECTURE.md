# Technical Architecture Document

## AI-Powered Financial News Intelligence System

---

## 1. System Overview

This document describes the technical architecture of our multi-agent financial news intelligence system built with **LangGraph**.

### 1.1 Design Principles

1. **Agent-Based Architecture**: Each processing step is a dedicated agent
2. **RAG-First Approach**: Vector embeddings power deduplication and retrieval
3. **Hybrid NER**: Combining rule-based patterns with ML models
4. **Dual Storage**: ChromaDB (vectors) + PostgreSQL (structured data)
5. **Context Expansion**: Queries expand to related entities

---

## 2. Agent Architecture

### 2.1 LangGraph StateGraph

```python
StateGraph(AgentState)
    .add_node("ingest", ingestion_node)
    .add_node("dedup", deduplication_node)
    .add_node("extract", extraction_node)
    .add_node("impact", impact_node)
    .add_node("store", storage_node)
    
    .add_edge(START, "ingest")
    .add_edge("ingest", "dedup")
    .add_conditional_edges("dedup", should_continue)
    .add_edge("extract", "impact")
    .add_edge("impact", "store")
    .add_edge("store", END)
```

### 2.2 Agent Descriptions

| Agent | Input | Output | Purpose |
|-------|-------|--------|---------|
| **Ingestion** | RSS feeds, APIs | Raw articles | Fetch & normalize |
| **Deduplication** | Article text | is_duplicate, score | Eliminate redundancy |
| **Extraction** | Article text | Entities list | NER processing |
| **Impact** | Entities | Stock mappings | Map to impacted securities |
| **Storage** | Complete article | Storage IDs | Persist to databases |
| **Query** | User query | Results | Context-aware retrieval |

---

## 3. Data Flow

### 3.1 Ingestion Pipeline

```
┌─────────────────┐
│   Data Sources  │
├─────────────────┤
│ • Moneycontrol  │
│ • Economic Times│
│ • Business Std  │
│ • ET Markets    │
│ • NSE API       │
│ • BSE API       │
│ • RBI Notices   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Ingestion Agent │
├─────────────────┤
│ 1. Fetch RSS    │
│ 2. Parse HTML   │
│ 3. Extract text │
│ 4. Normalize    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Dedup Agent     │
├─────────────────┤
│ 1. Generate     │
│    embedding    │
│ 2. Search       │
│    similar docs │
│ 3. Check        │
│    threshold    │
│ 4. Assign       │
│    cluster ID   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
  Unique    Duplicate
    │         │
    ▼         ▼
  Continue   Skip/Link
```

### 3.2 Query Pipeline

```
┌─────────────────┐
│   User Query    │
│ "HDFC Bank news"│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Query Agent    │
├─────────────────┤
│ 1. Entity       │
│    Detection    │
│ 2. Context      │
│    Expansion    │
│ 3. Vector       │
│    Search       │
│ 4. Result       │
│    Ranking      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│      Context Expansion          │
├─────────────────────────────────┤
│ HDFC Bank → Banking Sector      │
│          → ICICI Bank, SBI      │
│          → RBI regulations      │
│          → Related subsidiaries │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────┐
│   Results       │
├─────────────────┤
│ N1: Direct      │
│ N2: Sector-wide │
│ N4: Related     │
│                 │
│ + Confidence    │
│ + Match Reason  │
└─────────────────┘
```

---

## 4. Database Schema

### 4.1 PostgreSQL ERD

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────┐
│   Sectors    │     │    Companies     │     │ News Articles  │
├──────────────┤     ├──────────────────┤     ├────────────────┤
│ id (PK)      │◄───┐│ id (PK)          │     │ id (PK)        │
│ name         │    ││ name             │     │ title          │
│ description  │    ││ symbol           │     │ content        │
│ keywords[]   │    ││ sector_id (FK)───┘     │ source         │
└──────────────┘    ││ aliases[]        │     │ url            │
                    ││ is_nifty50       │     │ published_date │
                    │└──────────────────┘     │ is_duplicate   │
                    │                         │ cluster_id     │
                    │         ┌───────────────│ embedding_id   │
                    │         │               └────────────────┘
                    │         │                       │
                    │         ▼                       │
                    │  ┌──────────────────┐          │
                    │  │ Article_Entities │          │
                    │  ├──────────────────┤          │
                    │  │ id (PK)          │          │
                    │  │ article_id (FK)──┼──────────┘
                    │  │ entity_type      │
                    │  │ entity_value     │
                    │  │ confidence       │
                    │  │ position_start   │
                    │  │ position_end     │
                    │  └──────────────────┘
                    │
                    │  ┌──────────────────┐
                    │  │  Stock_Impacts   │
                    │  ├──────────────────┤
                    │  │ id (PK)          │
                    │  │ article_id (FK)  │
                    └──│ company_id (FK)  │
                       │ impact_type      │
                       │ confidence       │
                       │ reasoning        │
                       └──────────────────┘
```

### 4.2 ChromaDB Collection

```python
Collection: "financial_news"
{
    "ids": ["article_uuid"],
    "embeddings": [[768-dim vector]],
    "documents": ["article_content"],
    "metadatas": [{
        "title": "...",
        "source": "...",
        "published_date": "...",
        "entities": ["HDFC", "Banking"],
        "cluster_id": "..."
    }]
}
```

---

## 5. Deduplication Algorithm

### 5.1 Semantic Similarity

```python
def check_duplicate(article: NewsArticle) -> Tuple[bool, float, str]:
    """
    RAG-based deduplication using embedding similarity.
    
    Threshold: 0.85 cosine similarity
    """
    # 1. Generate embedding
    embedding = embed_model.encode(article.content)
    
    # 2. Search ChromaDB
    similar = collection.query(
        query_embeddings=[embedding],
        n_results=5
    )
    
    # 3. Check threshold
    for doc, distance in zip(similar['ids'], similar['distances']):
        similarity = 1 - distance  # Convert distance to similarity
        if similarity >= 0.85:
            return (True, similarity, existing_cluster_id)
    
    # 4. Create new cluster
    return (False, 0.0, new_cluster_id)
```

### 5.2 Clustering Strategy

- **Unique Articles**: Get new cluster_id, become cluster representative
- **Duplicates**: Link to existing cluster, store as variant
- **Near-Duplicates (0.75-0.85)**: Flag for review, create sub-cluster

---

## 6. NER Pipeline

### 6.1 Hybrid Approach

```
┌────────────────────────────────────────────────────┐
│                  NER Pipeline                       │
├────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────┐   ┌─────────────────┐         │
│  │ Rule-Based      │   │ spaCy NER       │         │
│  │ Patterns        │   │ (en_core_web_sm)│         │
│  ├─────────────────┤   ├─────────────────┤         │
│  │ • NSE symbols   │   │ • ORG           │         │
│  │ • Bank names    │   │ • PERSON        │         │
│  │ • Regulator     │   │ • GPE           │         │
│  │   acronyms      │   │ • MONEY         │         │
│  │ • Sector terms  │   │ • DATE          │         │
│  └────────┬────────┘   └────────┬────────┘         │
│           │                     │                   │
│           └──────────┬──────────┘                   │
│                      ▼                              │
│           ┌─────────────────┐                       │
│           │  Entity Merger  │                       │
│           │  & Deduplication│                       │
│           └────────┬────────┘                       │
│                    ▼                                │
│           ┌─────────────────┐                       │
│           │ Confidence      │                       │
│           │ Assignment      │                       │
│           └────────┬────────┘                       │
│                    ▼                                │
│           Extracted Entities                        │
│                                                     │
└────────────────────────────────────────────────────┘
```

### 6.2 Entity Categories

| Category | Examples | Source |
|----------|----------|--------|
| COMPANY | HDFC Bank, TCS, Reliance | Rule + spaCy |
| SECTOR | Banking, IT, Pharma | Rule patterns |
| REGULATOR | RBI, SEBI, MCA | Rule patterns |
| PERSON | CEO names, Officials | spaCy |
| EVENT | Q1 Results, AGM | Rule patterns |
| METRIC | Revenue, PAT, EBITDA | Rule patterns |

---

## 7. Stock Impact Mapping

### 7.1 Confidence Scoring

```python
IMPACT_TYPES = {
    "DIRECT": {
        "confidence": 1.0,
        "reason": "Company directly mentioned"
    },
    "SECTOR": {
        "confidence": 0.7,
        "reason": "Sector-wide impact"
    },
    "REGULATORY": {
        "confidence": 0.6,
        "reason": "Regulator policy impact"
    },
    "SUPPLY_CHAIN": {
        "confidence": 0.5,
        "reason": "Supply chain connection"
    }
}
```

### 7.2 Mapping Logic

```python
def map_impact(article, entities):
    impacts = []
    
    for entity in entities:
        # Direct match
        if entity.type == "COMPANY":
            company = lookup_company(entity.value)
            impacts.append({
                "stock": company.symbol,
                "type": "DIRECT",
                "confidence": 1.0
            })
            
            # Sector peers
            peers = get_sector_peers(company.sector)
            for peer in peers:
                impacts.append({
                    "stock": peer.symbol,
                    "type": "SECTOR",
                    "confidence": 0.7
                })
        
        # Regulatory impact
        elif entity.type == "REGULATOR":
            affected = get_regulated_companies(entity.value)
            for company in affected:
                impacts.append({
                    "stock": company.symbol,
                    "type": "REGULATORY",
                    "confidence": 0.6
                })
    
    return deduplicate_and_rank(impacts)
```

---

## 8. Query Processing

### 8.1 Context Expansion

```
Query: "HDFC Bank"
        │
        ▼
┌───────────────────────────────────┐
│      Entity Detection             │
│  → Type: COMPANY                  │
│  → Normalized: "HDFC Bank"        │
└───────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────┐
│      Context Expansion            │
├───────────────────────────────────┤
│ 1. Direct: "HDFC Bank"            │
│ 2. Aliases: "HDFCBANK", "HDFC"    │
│ 3. Sector: "Banking"              │
│ 4. Peers: "ICICI", "SBI", "Axis"  │
│ 5. Regulators: "RBI"              │
│ 6. Subsidiaries: "HDFC Life"      │
└───────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────┐
│      Hybrid Search                │
├───────────────────────────────────┤
│ • Vector similarity (0.4)         │
│ • Metadata filter (0.3)           │
│ • Entity match (0.3)              │
└───────────────────────────────────┘
```

### 8.2 Result Ranking

```python
def rank_results(query, results):
    for result in results:
        score = 0.0
        
        # Semantic similarity
        score += result.vector_similarity * 0.4
        
        # Entity match bonus
        if has_direct_entity_match(query, result):
            score += 0.3
        elif has_sector_match(query, result):
            score += 0.15
        
        # Recency bonus
        days_old = (now - result.published_date).days
        score += max(0, 0.2 - (days_old * 0.02))
        
        # Freshness for duplicates (prefer original)
        if result.is_original:
            score += 0.1
        
        result.final_score = score
    
    return sorted(results, key=lambda x: x.final_score, reverse=True)
```

---

## 9. Performance Optimization

### 9.1 Embedding Cache

```python
class EmbeddingCache:
    """
    LRU cache for frequently accessed embeddings.
    Reduces ChromaDB queries for hot content.
    """
    
    cache_size = 1000
    ttl = 3600  # 1 hour
    
    def get_or_compute(self, text):
        hash_key = hashlib.md5(text.encode()).hexdigest()
        if hash_key in self.cache:
            return self.cache[hash_key]
        
        embedding = self.model.encode(text)
        self.cache[hash_key] = embedding
        return embedding
```

### 9.2 Batch Processing

```python
async def ingest_batch(articles: List[Article]):
    """
    Process articles in batches for efficiency.
    """
    BATCH_SIZE = 50
    
    for i in range(0, len(articles), BATCH_SIZE):
        batch = articles[i:i+BATCH_SIZE]
        
        # Parallel embedding generation
        embeddings = await asyncio.gather(*[
            generate_embedding(a.content) for a in batch
        ])
        
        # Batch ChromaDB insert
        collection.add(
            ids=[a.id for a in batch],
            embeddings=embeddings,
            documents=[a.content for a in batch]
        )
```

---

## 10. API Design

### 10.1 RESTful Endpoints

```yaml
openapi: 3.0.0
paths:
  /ingest:
    post:
      summary: Ingest single article
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Article'
      responses:
        200:
          description: Ingestion result
          
  /query:
    post:
      summary: Natural language query
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                query:
                  type: string
                limit:
                  type: integer
                  default: 10
      responses:
        200:
          description: Query results
          
  /stocks/{symbol}:
    get:
      summary: Get news affecting stock
      parameters:
        - name: symbol
          in: path
          required: true
          schema:
            type: string
      responses:
        200:
          description: Impacted news list
```

### 10.2 WebSocket (Bonus)

```python
@app.websocket("/ws/alerts/{symbol}")
async def alert_websocket(websocket: WebSocket, symbol: str):
    """
    Real-time alerts for stock-impacting news.
    """
    await websocket.accept()
    
    while True:
        # Check for new impacting articles
        new_articles = await check_new_impacts(symbol)
        
        if new_articles:
            await websocket.send_json({
                "type": "alert",
                "symbol": symbol,
                "articles": new_articles
            })
        
        await asyncio.sleep(30)  # Poll interval
```

---

## 11. Testing Strategy

### 11.1 Unit Tests

```python
# tests/test_dedup.py
def test_duplicate_detection():
    article1 = Article(content="HDFC Bank reports Q1 profit...")
    article2 = Article(content="HDFC Bank reports Q1 profit rise...")  # Similar
    article3 = Article(content="TCS announces new partnership...")  # Different
    
    # Ingest first article
    result1 = dedup_agent.process(article1)
    assert result1.is_duplicate == False
    
    # Second should be duplicate
    result2 = dedup_agent.process(article2)
    assert result2.is_duplicate == True
    assert result2.similarity >= 0.85
    
    # Third should be unique
    result3 = dedup_agent.process(article3)
    assert result3.is_duplicate == False
```

### 11.2 Integration Tests

```python
# tests/test_pipeline.py
async def test_full_pipeline():
    # 1. Ingest articles
    articles = load_mock_articles()
    await orchestrator.ingest_batch(articles)
    
    # 2. Query and verify
    results = await query_agent.query("HDFC Bank news")
    
    assert len(results) > 0
    assert any("HDFC" in r.title for r in results)
    assert all(r.confidence >= 0.5 for r in results)
```

---

## 12. Deployment

### 12.1 Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - chromadb
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/tradl
      - CHROMA_HOST=chromadb
      
  postgres:
    image: postgres:15
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=secret
      
  chromadb:
    image: chromadb/chroma
    ports:
      - "8001:8000"
    volumes:
      - chromadata:/chroma/chroma

volumes:
  pgdata:
  chromadata:
```

---

## 13. Future Enhancements

### 13.1 Bonus Features Roadmap

1. **Sentiment Analysis**: FinBERT model for financial sentiment
2. **Real-time Alerts**: WebSocket push notifications
3. **Supply Chain Impact**: Cross-sector effect modeling
4. **Explainability**: Detailed match reasoning

### 13.2 Scalability Path

- **Horizontal Scaling**: Kubernetes deployment
- **Caching Layer**: Redis for hot queries
- **Event Streaming**: Kafka for real-time ingestion
- **Model Serving**: TensorRT optimization

---

*Document Version: 1.0*  
*Last Updated: December 2025*
