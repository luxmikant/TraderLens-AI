"""
Pydantic models for data validation and serialization
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class EntityType(str, Enum):
    """Types of entities extracted from news"""
    COMPANY = "company"
    PERSON = "person"
    REGULATOR = "regulator"
    SECTOR = "sector"
    EVENT = "event"
    LOCATION = "location"


class ImpactType(str, Enum):
    """Types of stock impact"""
    DIRECT = "direct"  # Company directly mentioned
    SECTOR = "sector"  # Sector-wide news
    REGULATORY = "regulatory"  # Regulatory action
    SUPPLY_CHAIN = "supply_chain"  # Cross-sector impact


class SentimentLabel(str, Enum):
    """Sentiment classifications"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    BEARISH = "bearish"


# ================== Input Models ==================

class RawNewsInput(BaseModel):
    """Raw news article input from sources"""
    title: str
    content: str
    url: Optional[str] = None
    source: str
    published_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class QueryInput(BaseModel):
    """User query input"""
    query: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=10, ge=1, le=100)
    include_sector_news: bool = True
    skip_rag: bool = Field(default=False, description="Skip RAG synthesis for faster response (<100ms)")


# ================== Entity Models ==================

class ExtractedEntity(BaseModel):
    """Single extracted entity"""
    entity_type: EntityType
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    start_pos: Optional[int] = None
    end_pos: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class EntityExtractionResult(BaseModel):
    """Result of entity extraction"""
    companies: List[ExtractedEntity] = []
    people: List[ExtractedEntity] = []
    regulators: List[ExtractedEntity] = []
    sectors: List[str] = []
    events: List[ExtractedEntity] = []
    raw_entities: List[ExtractedEntity] = []


# ================== Stock Impact Models ==================

class StockImpact(BaseModel):
    """Single stock impact mapping"""
    symbol: str
    ticker_nse: Optional[str] = None
    ticker_bse: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    impact_type: ImpactType
    reasoning: Optional[str] = None


class ImpactAnalysisResult(BaseModel):
    """Result of stock impact analysis"""
    impacted_stocks: List[StockImpact] = []
    primary_sectors: List[str] = []
    impact_summary: Optional[str] = None


# ================== News Article Models ==================

class ProcessedNewsArticle(BaseModel):
    """Fully processed news article"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    url: Optional[str] = None
    source: str
    published_at: Optional[datetime] = None
    ingested_at: datetime = Field(default_factory=datetime.now)
    
    # Deduplication
    is_duplicate: bool = False
    cluster_id: Optional[str] = None
    duplicate_sources: List[str] = []
    
    # Entities
    entities: Optional[EntityExtractionResult] = Field(default_factory=EntityExtractionResult)
    
    # Impact
    stock_impacts: List[StockImpact] = []
    
    # Sentiment (Bonus)
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[SentimentLabel] = None
    
    # Embedding reference
    embedding_id: Optional[str] = None


class NewsCluster(BaseModel):
    """Cluster of duplicate/related news articles"""
    cluster_id: str
    primary_article: ProcessedNewsArticle
    duplicate_articles: List[ProcessedNewsArticle] = []
    sources: List[str] = []
    first_seen: datetime
    last_updated: datetime


# ================== Query Models ==================

class QueryEntity(BaseModel):
    """Entity extracted from user query"""
    entity_type: EntityType
    value: str
    expanded_values: List[str] = []  # Related entities for context expansion


class QueryAnalysis(BaseModel):
    """Analysis of user query"""
    original_query: str
    entities: List[QueryEntity] = []
    sectors: List[str] = []
    intent: str  # "company_news", "sector_update", "regulator_action", "theme_search"
    expanded_query: Optional[str] = None


class QueryResult(BaseModel):
    """Single query result"""
    article: ProcessedNewsArticle
    relevance_score: float
    match_reason: str  # Why this article was retrieved
    highlights: List[str] = []  # Key matching phrases


class QueryResponse(BaseModel):
    """Complete query response"""
    query: str
    analysis: QueryAnalysis
    results: List[QueryResult] = []
    total_count: int = 0
    execution_time_ms: float = 0
    
    # RAG synthesis (AI-generated answer)
    synthesized_answer: Optional[str] = None
    rag_metadata: Optional[Dict[str, Any]] = None  # {model, provider, latency_ms}


# ================== LangGraph State Models ==================

class NewsProcessingState(BaseModel):
    """State for news processing pipeline"""
    # Input
    raw_news: RawNewsInput
    
    # Processing stages
    normalized_content: Optional[str] = None
    is_duplicate: bool = False
    duplicate_cluster_id: Optional[str] = None
    
    # Extraction results
    entities: Optional[EntityExtractionResult] = None
    stock_impacts: List[StockImpact] = []
    
    # Sentiment
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[SentimentLabel] = None
    
    # Final output
    processed_article: Optional[ProcessedNewsArticle] = None
    stored: bool = False
    
    # Error handling
    errors: List[str] = []
    
    class Config:
        arbitrary_types_allowed = True


class QueryProcessingState(BaseModel):
    """State for query processing pipeline"""
    # Input
    query_input: QueryInput
    
    # Analysis
    query_analysis: Optional[QueryAnalysis] = None
    
    # Retrieval
    candidate_articles: List[ProcessedNewsArticle] = []
    
    # Final output
    response: Optional[QueryResponse] = None
    
    # Error handling
    errors: List[str] = []
    
    class Config:
        arbitrary_types_allowed = True


# ================== API Response Models ==================

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    components: Optional[Dict[str, Any]] = None


class IngestResponse(BaseModel):
    """News ingestion response"""
    success: bool
    article_id: Optional[str] = None
    is_duplicate: bool = False
    message: str


class StatsResponse(BaseModel):
    """System statistics response"""
    total_articles: int
    unique_articles: int
    duplicate_clusters: int
    total_entities: int
    sources: Dict[str, int]
    sectors: Dict[str, int]


# ================== Alert Models (Bonus) ==================

class AlertSubscription(BaseModel):
    """User alert subscription"""
    user_id: str
    subscription_type: str  # "company", "sector", "keyword"
    subscription_value: str
    created_at: datetime = Field(default_factory=datetime.now)


class Alert(BaseModel):
    """Real-time alert notification"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    article: ProcessedNewsArticle
    match_reason: str
    triggered_at: datetime = Field(default_factory=datetime.now)
