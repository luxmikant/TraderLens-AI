"""
FastAPI Application - REST API for Financial News Intelligence System
"""
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import asyncio

from src.config import settings
from src.models.schemas import (
    RawNewsInput, QueryInput, QueryResponse, ProcessedNewsArticle,
    IngestResponse, StatsResponse, HealthResponse
)
from src.agents.orchestrator import get_orchestrator, FinancialNewsOrchestrator
from src.agents.ingestion_agent import get_ingestion_agent
from src.agents.storage_agent import get_storage_agent
from src.utils.retry import health_checker
from src.api.advanced_routes import router as advanced_router
from src.api.insights_routes import router as insights_router
from src.monitoring.metrics import get_metrics, set_app_info, PROMETHEUS_AVAILABLE


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ================== FastAPI App ==================

app = FastAPI(
    title="Financial News Intelligence API",
    description="""
    AI-Powered Financial News Intelligence System for the Tradl Hackathon.
    
    ## Features
    - **News Ingestion**: Process news from RSS feeds and APIs
    - **Intelligent Deduplication**: 95%+ accuracy duplicate detection
    - **Entity Extraction**: Companies, Sectors, Regulators, Events
    - **Stock Impact Mapping**: Confidence-scored impact analysis
    - **Context-Aware Queries**: Natural language search with entity expansion
    
    ## Architecture
    Multi-agent LangGraph system with 6 specialized agents.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include advanced features router
app.include_router(advanced_router)

# Include insights router (Impact Score, Heatmap, Narratives, User Prefs)
app.include_router(insights_router)


# ================== Prometheus Metrics Endpoint ==================

@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint for observability.
    Exposes HTTP, LLM, cache, and business metrics.
    """
    content, content_type = get_metrics()
    return Response(content=content, media_type=content_type)


# ================== Request/Response Models ==================

class NewsArticleInput(BaseModel):
    """Input for manual news ingestion"""
    title: str
    content: str
    source: str = "manual"
    url: Optional[str] = None
    published_at: Optional[datetime] = None


class QueryRequest(BaseModel):
    """Query request"""
    query: str
    limit: int = 10
    include_sector_news: bool = True
    filters: Optional[Dict[str, Any]] = None


class BatchIngestRequest(BaseModel):
    """Batch ingestion request"""
    articles: List[NewsArticleInput]


class BatchIngestResponse(BaseModel):
    """Batch ingestion response"""
    total: int
    processed: int
    duplicates: int
    errors: int
    success_rate: float


# ================== Global State ==================

orchestrator: Optional[FinancialNewsOrchestrator] = None
ingestion_task: Optional[asyncio.Task] = None


@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    global orchestrator
    logger.info("Starting Financial News Intelligence API...")
    
    try:
        orchestrator = get_orchestrator()
        logger.info("Orchestrator initialized successfully")
        
        # Set app info for Prometheus
        set_app_info(version="1.0.0")
        
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global ingestion_task
    
    if ingestion_task:
        ingestion_task.cancel()
    
    # Close ingestion agent HTTP client
    agent = get_ingestion_agent()
    await agent.close()
    
    logger.info("Shutdown complete")


# ================== Health Check ==================

@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.now()
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Detailed health check with component statuses."""
    statuses = await health_checker.run_all()
    components = {s.name: {"healthy": s.healthy, "latency_ms": round(s.latency_ms, 2), "message": s.message} for s in statuses}
    overall_healthy = all(s.healthy for s in statuses) if statuses else True

    return HealthResponse(
        status="healthy" if overall_healthy else "degraded",
        version="1.0.0",
        timestamp=datetime.now(),
        components=components
    )


# ================== News Ingestion Endpoints ==================

@app.post("/ingest", response_model=IngestResponse)
async def ingest_article(article: NewsArticleInput):
    """
    Ingest a single news article.
    
    The article will be processed through the full pipeline:
    1. Normalization
    2. Deduplication
    3. Entity Extraction
    4. Stock Impact Analysis
    5. Storage
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        raw_news = RawNewsInput(
            title=article.title,
            content=article.content,
            source=article.source,
            url=article.url,
            published_at=article.published_at or datetime.now()
        )
        
        result = await orchestrator.process_news(raw_news)
        
        is_duplicate = result.get("is_duplicate", False)
        processed_article = result.get("processed_article")
        
        return IngestResponse(
            success=result.get("stored", False) or is_duplicate,
            article_id=processed_article.id if processed_article else None,
            is_duplicate=is_duplicate,
            message="Duplicate detected - consolidated with existing story" if is_duplicate 
                   else "Article processed and stored successfully"
        )
        
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/batch", response_model=BatchIngestResponse)
async def ingest_batch(request: BatchIngestRequest):
    """
    Ingest multiple news articles in batch.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        raw_articles = [
            RawNewsInput(
                title=a.title,
                content=a.content,
                source=a.source,
                url=a.url,
                published_at=a.published_at or datetime.now()
            )
            for a in request.articles
        ]
        
        result = await orchestrator.process_news_batch(raw_articles)
        
        return BatchIngestResponse(**result)
        
    except Exception as e:
        logger.error(f"Batch ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest/rss")
async def trigger_rss_ingestion(background_tasks: BackgroundTasks):
    """
    Trigger RSS feed ingestion.
    Fetches news from all configured RSS feeds.
    """
    async def fetch_and_process():
        agent = get_ingestion_agent()
        articles = await agent.ingest_batch()
        
        if articles and orchestrator:
            result = await orchestrator.process_news_batch(articles)
            logger.info(f"RSS ingestion complete: {result}")
    
    background_tasks.add_task(fetch_and_process)
    
    return {"message": "RSS ingestion started in background"}


# ================== Query Endpoints ==================

@app.post("/query", response_model=QueryResponse)
async def query_news(request: QueryRequest):
    """
    Query the news knowledge base.
    
    Supports:
    - Company queries: "HDFC Bank news"
    - Sector queries: "Banking sector update"
    - Regulator queries: "RBI policy changes"
    - Theme queries: "Interest rate impact"
    
    Returns context-expanded results with relevance scores.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        response = await orchestrator.query(
            query=request.query,
            limit=request.limit
        )
        
        if not response:
            raise HTTPException(status_code=404, detail="No results found")
        
        return response
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query/quick")
async def quick_query(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Quick query endpoint with GET method.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        response = await orchestrator.query(query=q, limit=limit)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/query/company/{company}")
async def query_by_company(company: str, limit: int = 10):
    """
    Get news about a specific company.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await orchestrator.query(f"{company} news", limit)


@app.get("/query/sector/{sector}")
async def query_by_sector(sector: str, limit: int = 10):
    """
    Get news about a specific sector.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return await orchestrator.query(f"{sector} sector update", limit)


# ================== Stats & Admin Endpoints ==================

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get system statistics.
    """
    try:
        storage_agent = get_storage_agent()
        stats = storage_agent.get_stats()
        
        postgres_stats = stats.get("postgres", {})
        
        return StatsResponse(
            total_articles=postgres_stats.get("total_articles", 0),
            unique_articles=postgres_stats.get("unique_articles", 0),
            duplicate_clusters=postgres_stats.get("total_articles", 0) - postgres_stats.get("unique_articles", 0),
            total_entities=postgres_stats.get("total_entities", 0),
            sources=postgres_stats.get("sources", {}),
            sectors=stats.get("chromadb", {}).get("sectors", {})
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/architecture")
async def get_architecture():
    """
    Get system architecture diagram (Mermaid format).
    """
    return {
        "diagram": """
graph TD
    subgraph "Data Sources"
        RSS[RSS Feeds]
        NSE[NSE API]
        BSE[BSE API]
        RBI[RBI Portal]
    end
    
    subgraph "LangGraph Pipeline"
        A1[1. Ingestion Agent]
        A2[2. Deduplication Agent]
        A3[3. Entity Extraction Agent]
        A4[4. Stock Impact Agent]
        A5[5. Storage Agent]
        A6[6. Query Agent]
    end
    
    subgraph "Storage"
        CHROMA[(ChromaDB Vector Store)]
        PG[(PostgreSQL)]
    end
    
    RSS --> A1
    NSE --> A1
    BSE --> A1
    RBI --> A1
    
    A1 --> A2
    A2 -->|Unique| A3
    A2 -->|Duplicate| SKIP[Skip]
    A3 --> A4
    A4 --> A5
    A5 --> CHROMA
    A5 --> PG
    
    USER[User Query] --> A6
    A6 --> CHROMA
    A6 --> PG
    A6 --> RESPONSE[Query Response]
""",
        "agents": [
            {"id": 1, "name": "News Ingestion Agent", "purpose": "Fetch and normalize news"},
            {"id": 2, "name": "Deduplication Agent", "purpose": "Detect semantic duplicates"},
            {"id": 3, "name": "Entity Extraction Agent", "purpose": "Extract companies, sectors, events"},
            {"id": 4, "name": "Stock Impact Agent", "purpose": "Map to affected stocks"},
            {"id": 5, "name": "Storage Agent", "purpose": "Persist to databases"},
            {"id": 6, "name": "Query Agent", "purpose": "Context-aware search"}
        ]
    }


# ================== Demo Endpoints ==================

@app.get("/demo/sample-articles")
async def get_sample_articles():
    """
    Get sample articles for testing.
    """
    return {
        "articles": [
            {
                "title": "HDFC Bank announces 15% dividend, board approves stock buyback",
                "content": "HDFC Bank declared a 15% dividend for shareholders. The board also approved a buyback program worth Rs 2,500 crore. CEO expressed confidence in growth.",
                "source": "moneycontrol"
            },
            {
                "title": "RBI raises repo rate by 25bps to 6.75%, citing inflation concerns",
                "content": "The Reserve Bank of India raised the repo rate by 25 basis points to 6.75% in its latest monetary policy review. The MPC cited persistent inflation pressures.",
                "source": "economic_times"
            },
            {
                "title": "ICICI Bank opens 500 new branches across Tier-2 cities",
                "content": "ICICI Bank announced expansion plans with 500 new branches in tier-2 and tier-3 cities. The move aims to increase rural penetration.",
                "source": "business_standard"
            },
            {
                "title": "Banking sector NPAs decline to 5-year low, credit growth at 16%",
                "content": "Non-performing assets in the banking sector have declined to a 5-year low of 3.9%. Credit growth remains robust at 16% year-on-year.",
                "source": "livemint"
            },
            {
                "title": "Reliance Industries Q3 profit up 12% to Rs 18,000 crore",
                "content": "Reliance Industries reported Q3 net profit of Rs 18,000 crore, up 12% YoY. Jio and retail segments drove growth.",
                "source": "financial_express"
            }
        ]
    }


@app.get("/demo/sample-queries")
async def get_sample_queries():
    """
    Get sample queries for testing.
    """
    return {
        "queries": [
            {
                "query": "HDFC Bank news",
                "description": "Get direct mentions + sector-wide banking news",
                "expected_behavior": "Returns HDFC Bank specific news AND general banking sector news"
            },
            {
                "query": "Banking sector update",
                "description": "Get all banking sector news",
                "expected_behavior": "Returns news about all banks and banking industry"
            },
            {
                "query": "RBI policy changes",
                "description": "Get regulator-specific news",
                "expected_behavior": "Returns only RBI related news"
            },
            {
                "query": "Interest rate impact",
                "description": "Semantic theme matching",
                "expected_behavior": "Returns news about interest rates across sectors"
            },
            {
                "query": "Reliance quarterly results",
                "description": "Company + event query",
                "expected_behavior": "Returns Reliance earnings/results news"
            }
        ]
    }


# ================== Run Server ==================

def run_server():
    """Run the FastAPI server"""
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )


if __name__ == "__main__":
    run_server()
