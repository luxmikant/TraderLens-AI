"""
LangGraph Orchestrator - Connects all agents in a multi-agent workflow
"""
from typing import TypedDict, Annotated, Literal, List, Optional
from datetime import datetime
import logging
import operator

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.models.schemas import (
    RawNewsInput, ProcessedNewsArticle, NewsProcessingState,
    QueryInput, QueryProcessingState, QueryResponse,
    EntityExtractionResult, StockImpact, SentimentLabel
)
from src.agents.ingestion_agent import get_ingestion_agent
from src.agents.dedup_agent import get_dedup_agent
from src.agents.ner_agent import get_ner_agent
from src.agents.impact_agent import get_impact_agent
from src.agents.storage_agent import get_storage_agent
from src.agents.query_agent import get_query_agent
from src.utils.langsmith_setup import enable_langsmith

# Import tracing decorators
try:
    from langsmith import traceable
    TRACING_ENABLED = True
except ImportError:
    TRACING_ENABLED = False
    def traceable(*args, **kwargs):
        def decorator(func):
            return func
        return decorator


logger = logging.getLogger(__name__)


# ================== State Definitions ==================

class NewsState(TypedDict):
    """State for news processing pipeline"""
    # Input
    raw_news: RawNewsInput
    
    # Processing stages
    normalized_content: str
    is_duplicate: bool
    duplicate_cluster_id: Optional[str]
    
    # Extraction
    entities: Optional[EntityExtractionResult]
    stock_impacts: Annotated[List[StockImpact], operator.add]
    
    # Sentiment (Bonus)
    sentiment_score: Optional[float]
    sentiment_label: Optional[str]
    
    # Output
    processed_article: Optional[ProcessedNewsArticle]
    stored: bool
    
    # Metadata
    errors: Annotated[List[str], operator.add]


class QueryState(TypedDict):
    """State for query processing pipeline"""
    query_input: QueryInput
    response: Optional[QueryResponse]
    errors: Annotated[List[str], operator.add]


# ================== Node Functions (News Processing) ==================

@traceable(name="1. Ingestion Agent", run_type="chain", metadata={"agent": "ingestion"})
async def ingest_node(state: NewsState) -> NewsState:
    """Ingestion node - normalize raw news"""
    try:
        agent = get_ingestion_agent()
        
        # Create processing state
        processing_state = NewsProcessingState(raw_news=state["raw_news"])
        
        # Process
        result = await agent.process(processing_state)
        
        return {
            **state,
            "normalized_content": result.normalized_content or ""
        }
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        return {
            **state,
            "errors": [f"Ingestion error: {str(e)}"]
        }


@traceable(name="2. Deduplication Agent", run_type="chain", metadata={"agent": "dedup"})
async def dedup_node(state: NewsState) -> NewsState:
    """Deduplication node - check for duplicates"""
    try:
        agent = get_dedup_agent()
        
        content = state.get("normalized_content") or f"{state['raw_news'].title}\n\n{state['raw_news'].content}"
        
        is_duplicate, cluster_id, similarity = agent.check_duplicate(content)
        
        return {
            **state,
            "is_duplicate": is_duplicate,
            "duplicate_cluster_id": cluster_id
        }
    except Exception as e:
        logger.error(f"Deduplication error: {e}")
        return {
            **state,
            "is_duplicate": False,
            "errors": [f"Deduplication error: {str(e)}"]
        }


@traceable(name="3. NER Agent", run_type="chain", metadata={"agent": "ner"})
async def ner_node(state: NewsState) -> NewsState:
    """Entity extraction node"""
    try:
        agent = get_ner_agent()
        
        content = state.get("normalized_content") or f"{state['raw_news'].title}\n\n{state['raw_news'].content}"
        
        entities = agent.extract_all(content)
        
        return {
            **state,
            "entities": entities
        }
    except Exception as e:
        logger.error(f"NER error: {e}")
        return {
            **state,
            "errors": [f"NER error: {str(e)}"]
        }


@traceable(name="4. Impact Agent", run_type="chain", metadata={"agent": "impact"})
async def impact_node(state: NewsState) -> NewsState:
    """Stock impact analysis node"""
    try:
        agent = get_impact_agent()
        
        entities = state.get("entities")
        if entities is None:
            return state
        
        result = agent.analyze_impact(entities)
        
        return {
            **state,
            "stock_impacts": result.impacted_stocks
        }
    except Exception as e:
        logger.error(f"Impact analysis error: {e}")
        return {
            **state,
            "errors": [f"Impact analysis error: {str(e)}"]
        }


@traceable(name="5. Sentiment Agent (FinBERT)", run_type="chain", metadata={"agent": "sentiment"})
async def sentiment_node(state: NewsState) -> NewsState:
    """FinBERT sentiment analysis node"""
    try:
        from src.agents.sentiment_agent import get_sentiment_agent
        
        agent = get_sentiment_agent()
        
        # Check if FinBERT is available
        if not agent.is_available:
            logger.warning("FinBERT not available, skipping sentiment analysis")
            return state
        
        # Analyze sentiment on full content
        content = state.get("normalized_content") or f"{state['raw_news'].title}\n\n{state['raw_news'].content}"
        
        result = agent.analyze(content)
        
        if result:
            # Map FinBERT labels to schema SentimentLabel
            label_map = {
                "bullish": SentimentLabel.BULLISH,
                "bearish": SentimentLabel.BEARISH,
                "neutral": SentimentLabel.NEUTRAL
            }
            
            return {
                **state,
                "sentiment_score": result.score,
                "sentiment_label": label_map.get(result.label.value, SentimentLabel.NEUTRAL).value
            }
        
        return state
        
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        return {
            **state,
            "errors": [f"Sentiment analysis error: {str(e)}"]
        }


@traceable(name="6. Storage Agent", run_type="chain", metadata={"agent": "storage"})
async def storage_node(state: NewsState) -> NewsState:
    """Storage node - persist to databases"""
    try:
        agent = get_storage_agent()
        
        # Build processed article
        raw = state["raw_news"]
        
        # Convert sentiment_label string to enum if needed
        sentiment_label_str = state.get("sentiment_label")
        sentiment_label_enum: Optional[SentimentLabel] = None
        if sentiment_label_str:
            try:
                sentiment_label_enum = SentimentLabel(sentiment_label_str)
            except ValueError:
                sentiment_label_enum = None
        
        article = ProcessedNewsArticle(
            title=raw.title,
            content=raw.content,
            url=raw.url,
            source=raw.source,
            published_at=raw.published_at,
            is_duplicate=state.get("is_duplicate", False),
            cluster_id=state.get("duplicate_cluster_id"),
            entities=state.get("entities"),
            stock_impacts=state.get("stock_impacts", []),
            sentiment_score=state.get("sentiment_score"),
            sentiment_label=sentiment_label_enum
        )
        
        success = agent.store_article(article)
        
        return {
            **state,
            "processed_article": article,
            "stored": success
        }
    except Exception as e:
        logger.error(f"Storage error: {e}")
        return {
            **state,
            "stored": False,
            "errors": [f"Storage error: {str(e)}"]
        }


# ================== Routing Functions ==================

def should_skip_duplicate(state: NewsState) -> Literal["skip", "continue"]:
    """Route based on duplicate status"""
    if state.get("is_duplicate", False):
        logger.info(f"Skipping duplicate article: {state['raw_news'].title[:50]}...")
        return "skip"
    return "continue"


# ================== Query Processing Nodes ==================

@traceable(name="Query Agent", run_type="chain", metadata={"agent": "query"})
async def query_node(state: QueryState) -> QueryState:
    """Query processing node"""
    try:
        agent = get_query_agent()
        
        response = agent.search(state["query_input"])
        
        return {
            **state,
            "response": response
        }
    except Exception as e:
        logger.error(f"Query error: {e}")
        return {
            **state,
            "errors": [f"Query error: {str(e)}"]
        }


# ================== Graph Builders ==================

def build_news_processing_graph() -> StateGraph:
    """
    Build the news processing pipeline graph.
    
    Flow:
    START → Ingest → Dedup → (if unique) → NER → Impact → Sentiment → Storage → END
                          ↘ (if duplicate) → END
    """
    graph = StateGraph(NewsState)
    
    # Add nodes
    graph.add_node("ingest", ingest_node)
    graph.add_node("dedup", dedup_node)
    graph.add_node("ner", ner_node)
    graph.add_node("impact", impact_node)
    graph.add_node("sentiment", sentiment_node)
    graph.add_node("storage", storage_node)
    
    # Add edges
    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "dedup")
    
    # Conditional edge after dedup
    graph.add_conditional_edges(
        "dedup",
        should_skip_duplicate,
        {
            "skip": END,  # Skip duplicate articles
            "continue": "ner"  # Process unique articles
        }
    )
    
    graph.add_edge("ner", "impact")
    graph.add_edge("impact", "sentiment")
    graph.add_edge("sentiment", "storage")
    graph.add_edge("storage", END)
    
    return graph


def build_query_graph() -> StateGraph:
    """
    Build the query processing graph.
    
    Flow:
    START → Query → END
    """
    graph = StateGraph(QueryState)
    
    graph.add_node("query", query_node)
    
    graph.add_edge(START, "query")
    graph.add_edge("query", END)
    
    return graph


# ================== Compiled Graphs ==================

class FinancialNewsOrchestrator:
    """
    Main orchestrator for the Financial News Intelligence System.
    
    Provides unified interface for:
    - Processing news articles
    - Querying the knowledge base
    - Batch processing
    """
    
    def __init__(self):
        # Build and compile graphs
        self.news_graph = build_news_processing_graph().compile()
        self.query_graph = build_query_graph().compile()
        
        # Optional: Add memory for conversation history
        self.memory = MemorySaver()

        # Enable LangSmith tracing if configured
        self.tracing_enabled = enable_langsmith()
        if self.tracing_enabled:
            logger.info("LangSmith tracing connected")
        
        logger.info("FinancialNewsOrchestrator initialized")
    
    async def process_news(self, raw_news: RawNewsInput) -> dict:
        """
        Process a single news article through the pipeline.
        
        Args:
            raw_news: Raw news article
            
        Returns:
            Final state with processed article
        """
        initial_state: NewsState = {
            "raw_news": raw_news,
            "normalized_content": "",
            "is_duplicate": False,
            "duplicate_cluster_id": None,
            "entities": None,
            "stock_impacts": [],
            "sentiment_score": None,
            "sentiment_label": None,
            "processed_article": None,
            "stored": False,
            "errors": []
        }
        
        result = await self.news_graph.ainvoke(initial_state)
        
        return result
    
    async def process_news_batch(self, articles: List[RawNewsInput]) -> dict:
        """
        Process a batch of news articles.
        
        Args:
            articles: List of raw news articles
            
        Returns:
            Processing statistics
        """
        processed = 0
        duplicates = 0
        errors = 0
        
        for article in articles:
            try:
                result = await self.process_news(article)
                
                if result.get("is_duplicate"):
                    duplicates += 1
                elif result.get("stored"):
                    processed += 1
                else:
                    errors += 1
                    
            except Exception as e:
                logger.error(f"Error processing article: {e}")
                errors += 1
        
        return {
            "total": len(articles),
            "processed": processed,
            "duplicates": duplicates,
            "errors": errors,
            "success_rate": processed / len(articles) if articles else 0
        }
    
    async def query(self, query: str, limit: int = 10) -> QueryResponse:
        """
        Execute a query against the knowledge base.
        
        Args:
            query: Natural language query
            limit: Maximum results to return
            
        Returns:
            QueryResponse with results
        """
        initial_state: QueryState = {
            "query_input": QueryInput(query=query, limit=limit),
            "response": None,
            "errors": []
        }
        
        result = await self.query_graph.ainvoke(initial_state)
        
        return result.get("response")
    
    def get_graph_visualization(self) -> str:
        """Get Mermaid diagram of the news processing graph"""
        return """
        ```mermaid
        graph TD
            A[START] --> B[Ingest Agent]
            B --> C[Dedup Agent]
            C -->|Unique| D[NER Agent]
            C -->|Duplicate| G[END]
            D --> E[Impact Agent]
            E --> F[Storage Agent]
            F --> G[END]
        ```
        """


# Singleton orchestrator
_orchestrator: Optional[FinancialNewsOrchestrator] = None


def get_orchestrator() -> FinancialNewsOrchestrator:
    """Get or create orchestrator singleton"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = FinancialNewsOrchestrator()
    return _orchestrator


# ================== CLI Demo ==================

async def demo():
    """Demo the orchestrator"""
    orchestrator = get_orchestrator()
    
    # Sample articles
    articles = [
        RawNewsInput(
            title="HDFC Bank announces 15% dividend, board approves stock buyback",
            content="HDFC Bank declared a 15% dividend for shareholders. The board also approved a buyback program worth Rs 2,500 crore.",
            source="moneycontrol",
            published_at=datetime.now()
        ),
        RawNewsInput(
            title="RBI raises repo rate by 25bps to 6.75%, citing inflation concerns",
            content="The Reserve Bank of India raised the repo rate by 25 basis points to 6.75% in its latest monetary policy review.",
            source="economic_times",
            published_at=datetime.now()
        ),
        RawNewsInput(
            title="Banking sector NPAs decline to 5-year low, credit growth at 16%",
            content="Non-performing assets in the banking sector have declined to a 5-year low. Credit growth remains strong at 16%.",
            source="business_standard",
            published_at=datetime.now()
        )
    ]
    
    print("=" * 60)
    print("Processing News Articles")
    print("=" * 60)
    
    # Process articles
    result = await orchestrator.process_news_batch(articles)
    print(f"\nBatch Processing Results:")
    print(f"  Total: {result['total']}")
    print(f"  Processed: {result['processed']}")
    print(f"  Duplicates: {result['duplicates']}")
    print(f"  Errors: {result['errors']}")
    
    print("\n" + "=" * 60)
    print("Querying Knowledge Base")
    print("=" * 60)
    
    # Test queries
    queries = [
        "HDFC Bank news",
        "Banking sector update",
        "RBI policy changes"
    ]
    
    for query in queries:
        print(f"\nQuery: '{query}'")
        response = await orchestrator.query(query, limit=3)
        
        if response:
            print(f"  Intent: {response.analysis.intent}")
            print(f"  Results: {response.total_count}")
            for i, result in enumerate(response.results[:2], 1):
                print(f"  {i}. [{result.relevance_score:.2f}] {result.article.title[:50]}...")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
