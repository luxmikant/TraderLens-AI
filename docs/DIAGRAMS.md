# Architecture Diagrams - Mermaid Code

Copy these into any Mermaid viewer (GitHub, Notion, https://mermaid.live)

---

## 1. System Overview Diagram

```mermaid
graph TB
    subgraph "Data Sources"
        RSS["📰 RSS Feeds<br/>Moneycontrol, ET, BS, Livemint"]
        NSE["📊 NSE API<br/>Corporate Announcements"]
        BSE["📊 BSE API<br/>Company Filings"]
        MANUAL["✍️ Manual Input<br/>API Ingestion"]
    end

    subgraph "Tradl AI Platform"
        subgraph "API Layer"
            FASTAPI["⚡ FastAPI Server<br/>REST API + WebSocket"]
            HEALTH["🏥 Health Check<br/>Component Monitoring"]
        end

        subgraph "LangGraph Pipeline"
            ORCH["🎭 Orchestrator<br/>State Management"]
            A1["1️⃣ Ingestion Agent<br/>Normalize & Clean"]
            A2["2️⃣ Dedup Agent<br/>Semantic Similarity"]
            A3["3️⃣ NER Agent<br/>Entity Extraction"]
            A4["4️⃣ Impact Agent<br/>Stock Mapping"]
            A5["5️⃣ Storage Agent<br/>Persist Data"]
            A6["6️⃣ Query Agent<br/>Context-Aware Search"]
        end

        subgraph "Storage Layer"
            CHROMA[("🔮 ChromaDB<br/>Vector Store")]
            PG[("🐘 PostgreSQL<br/>Structured Data")]
        end

        subgraph "Observability"
            LANGSMITH["🔍 LangSmith<br/>Tracing & Monitoring"]
        end
    end

    subgraph "Frontend"
        REACT["⚛️ React Dashboard<br/>Trader UI"]
    end

    RSS --> FASTAPI
    NSE --> FASTAPI
    BSE --> FASTAPI
    MANUAL --> FASTAPI

    FASTAPI --> ORCH
    ORCH --> A1
    A1 --> A2
    A2 -->|Unique| A3
    A2 -->|Duplicate| SKIP["⏭️ Skip"]
    A3 --> A4
    A4 --> A5
    A5 --> CHROMA
    A5 --> PG

    FASTAPI --> A6
    A6 --> CHROMA
    A6 --> PG

    ORCH -.-> LANGSMITH
    REACT --> FASTAPI
    HEALTH --> FASTAPI

    style ORCH fill:#e1f5fe
    style LANGSMITH fill:#fff3e0
    style REACT fill:#f3e5f5
```

---

## 2. High-Level Design (HLD)

```mermaid
flowchart TB
    subgraph "Tier 1: Presentation"
        UI["React Dashboard"]
        API_DOC["Swagger/OpenAPI"]
    end

    subgraph "Tier 2: Application"
        REST["REST API<br/>FastAPI"]
        WS["WebSocket<br/>Real-time Alerts"]
        SCHEDULER["APScheduler<br/>Periodic Fetch"]
    end

    subgraph "Tier 3: Business Logic"
        LANGGRAPH["LangGraph<br/>Multi-Agent Orchestration"]
        RETRY["Retry/Circuit Breaker<br/>Fault Tolerance"]
    end

    subgraph "Tier 4: Data"
        VECTOR["Vector DB<br/>Embeddings"]
        RELATIONAL["Relational DB<br/>Metadata"]
        CACHE["Redis Cache<br/>Rate Limiting"]
    end

    subgraph "Tier 5: External"
        LLM["OpenAI/Anthropic<br/>LLM APIs"]
        FEEDS["RSS/NSE/BSE<br/>Data Sources"]
        TRACE["LangSmith<br/>Observability"]
    end

    UI --> REST
    API_DOC --> REST
    REST --> LANGGRAPH
    WS --> LANGGRAPH
    SCHEDULER --> LANGGRAPH
    LANGGRAPH --> RETRY
    RETRY --> VECTOR
    RETRY --> RELATIONAL
    RETRY --> CACHE
    LANGGRAPH --> LLM
    SCHEDULER --> FEEDS
    LANGGRAPH -.-> TRACE
```

---

## 3. Low-Level Design (LLD) - News Ingestion Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Orchestrator
    participant IngestAgent
    participant DedupAgent
    participant NERAgent
    participant ImpactAgent
    participant StorageAgent
    participant ChromaDB
    participant PostgreSQL
    participant LangSmith

    Client->>FastAPI: POST /ingest {title, content, source}
    FastAPI->>Orchestrator: process_news(RawNewsInput)
    
    Note over Orchestrator,LangSmith: Trace Started
    Orchestrator->>LangSmith: log_run_start()

    Orchestrator->>IngestAgent: normalize(raw_news)
    IngestAgent-->>Orchestrator: normalized_content

    Orchestrator->>DedupAgent: check_duplicate(content)
    DedupAgent->>ChromaDB: similarity_search()
    ChromaDB-->>DedupAgent: similar_docs[]
    DedupAgent-->>Orchestrator: {is_dup, cluster_id, score}

    alt is_duplicate
        Orchestrator-->>FastAPI: {success: true, is_duplicate: true}
    else unique
        Orchestrator->>NERAgent: extract_all(content)
        NERAgent-->>Orchestrator: {companies, sectors, events}

        Orchestrator->>ImpactAgent: analyze_impact(entities)
        ImpactAgent-->>Orchestrator: {stock_impacts[]}

        Orchestrator->>StorageAgent: store(article)
        StorageAgent->>ChromaDB: add_documents()
        StorageAgent->>PostgreSQL: INSERT article
        StorageAgent-->>Orchestrator: {stored: true}
    end

    Orchestrator->>LangSmith: log_run_end()
    Orchestrator-->>FastAPI: ProcessingResult
    FastAPI-->>Client: IngestResponse
```

---

## 4. Query Flow Detail

```mermaid
sequenceDiagram
    participant User
    participant Dashboard
    participant FastAPI
    participant QueryAgent
    participant ChromaDB
    participant LangSmith

    User->>Dashboard: Search "HDFC Bank news"
    Dashboard->>FastAPI: POST /query {query, limit}
    
    FastAPI->>QueryAgent: search(QueryInput)
    QueryAgent->>LangSmith: trace_start()
    
    Note over QueryAgent: 1. Analyze Intent
    QueryAgent->>QueryAgent: detect_query_type()
    
    Note over QueryAgent: 2. Entity Expansion
    QueryAgent->>QueryAgent: expand_entities("HDFC Bank")
    Note right of QueryAgent: → HDFCBANK ticker<br/>→ Banking sector<br/>→ HDFC subsidiaries

    Note over QueryAgent: 3. Vector Search
    QueryAgent->>ChromaDB: similarity_search(query_embedding)
    ChromaDB-->>QueryAgent: relevant_docs[]

    Note over QueryAgent: 4. Re-rank & Score
    QueryAgent->>QueryAgent: calculate_relevance()
    
    QueryAgent->>LangSmith: trace_end()
    QueryAgent-->>FastAPI: QueryResponse
    FastAPI-->>Dashboard: {results, analysis}
    Dashboard-->>User: Display News Cards
```

---

## 5. Data Model (ERD)

```mermaid
erDiagram
    ARTICLE {
        uuid id PK
        string title
        text content
        string url
        string source
        datetime published_at
        boolean is_duplicate
        uuid cluster_id FK
        float sentiment_score
        string sentiment_label
        datetime created_at
    }

    ENTITY {
        uuid id PK
        uuid article_id FK
        string entity_type
        string value
        float confidence
    }

    STOCK_IMPACT {
        uuid id PK
        uuid article_id FK
        string stock_symbol
        string company_name
        string impact_type
        float confidence
        string sector
    }

    DEDUP_CLUSTER {
        uuid id PK
        uuid canonical_article_id FK
        int article_count
        datetime created_at
    }

    ARTICLE ||--o{ ENTITY : has
    ARTICLE ||--o{ STOCK_IMPACT : affects
    ARTICLE }o--|| DEDUP_CLUSTER : belongs_to
```

---

## 6. Fault Tolerance Architecture

```mermaid
graph LR
    subgraph "Fault Tolerance Layer"
        RETRY["RetryConfig<br/>max_attempts=3<br/>exponential backoff"]
        CB["CircuitBreaker<br/>failure_threshold=5<br/>recovery_timeout=60s"]
        HC["HealthChecker<br/>component monitoring"]
    end

    subgraph "Agents"
        ING["Ingestion Agent"]
        DED["Dedup Agent"]
        NER["NER Agent"]
        IMP["Impact Agent"]
        STO["Storage Agent"]
    end

    ING --> RETRY
    DED --> RETRY
    NER --> RETRY
    IMP --> RETRY
    STO --> RETRY
    RETRY --> CB
    CB --> HC
```

---

## 7. Deployment Architecture

```mermaid
graph TB
    subgraph "Production Setup"
        LB["🌐 Load Balancer<br/>nginx/traefik"]
        
        subgraph "App Containers"
            API1["FastAPI #1"]
            API2["FastAPI #2"]
            WORKER["Background Worker<br/>RSS Scheduler"]
        end

        subgraph "Data Containers"
            CHROMA_C["ChromaDB"]
            PG_C["PostgreSQL"]
            REDIS_C["Redis"]
        end

        subgraph "Monitoring"
            LS["LangSmith Cloud"]
            PROM["Prometheus"]
            GRAF["Grafana"]
        end
    end

    CLIENT["👥 Users"] --> LB
    LB --> API1
    LB --> API2
    API1 --> CHROMA_C
    API1 --> PG_C
    API2 --> CHROMA_C
    API2 --> PG_C
    WORKER --> CHROMA_C
    WORKER --> PG_C
    API1 -.-> LS
    API2 -.-> LS
    API1 -.-> PROM
    PROM --> GRAF
```

---

## 8. Agent State Machine

```mermaid
stateDiagram-v2
    [*] --> Ingestion
    Ingestion --> Deduplication
    
    Deduplication --> NER: Unique Article
    Deduplication --> [*]: Duplicate (Skip)
    
    NER --> ImpactAnalysis
    ImpactAnalysis --> Storage
    Storage --> [*]: Success
    Storage --> ErrorHandling: Failure
    ErrorHandling --> Storage: Retry
    ErrorHandling --> [*]: Max Retries
```

---

## 9. Frontend Component Hierarchy

```mermaid
graph TD
    APP["App"]
    APP --> HEADER["Header<br/>Logo + Search"]
    APP --> MAIN["Main Content"]
    APP --> FOOTER["Footer"]

    MAIN --> SIDEBAR["Sidebar<br/>Filters"]
    MAIN --> CONTENT["Content Area"]

    CONTENT --> FEED["News Feed"]
    CONTENT --> DETAIL["Article Detail"]
    CONTENT --> DASHBOARD["Dashboard"]

    FEED --> CARD["NewsCard[]"]
    CARD --> TITLE["Title"]
    CARD --> META["Source + Time"]
    CARD --> ENTITIES["Entity Tags"]
    CARD --> IMPACT["Impact Badge"]

    DASHBOARD --> CHARTS["Charts"]
    DASHBOARD --> STATS["Stats Cards"]
    DASHBOARD --> ALERTS["Alert Panel"]

    SIDEBAR --> SECTOR_FILTER["Sector Filter"]
    SIDEBAR --> SOURCE_FILTER["Source Filter"]
    SIDEBAR --> DATE_FILTER["Date Range"]
```
