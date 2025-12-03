"""
Financial News Intelligence System - Main Entry Point
"""
import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

from src.config import settings
from src.models.schemas import RawNewsInput
from src.agents.orchestrator import get_orchestrator
from src.database.postgres import init_database


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_mock_data():
    """Load and process mock news data"""
    mock_data_path = Path("data/mock_news/sample_articles.json")
    
    if not mock_data_path.exists():
        logger.error("Mock data file not found!")
        return []
    
    with open(mock_data_path, 'r', encoding='utf-8') as f:
        articles = json.load(f)
    
    logger.info(f"Loaded {len(articles)} mock articles")
    
    # Convert to RawNewsInput
    raw_articles = []
    for article in articles:
        raw_articles.append(RawNewsInput(
            title=article['title'],
            content=article['content'],
            source=article['source'],
            published_at=datetime.fromisoformat(article['published_at'].replace('Z', '+00:00')) if article.get('published_at') else datetime.now(),
            metadata={
                "id": article.get('id'),
                "duplicate_of": article.get('duplicate_of'),
                "expected_entities": article.get('expected_entities'),
                "expected_impacts": article.get('expected_impacts')
            }
        ))
    
    return raw_articles


async def demo_system():
    """Run a complete demo of the system"""
    print("=" * 70)
    print("  FINANCIAL NEWS INTELLIGENCE SYSTEM - DEMO")
    print("  Powered by LangGraph Multi-Agent Architecture")
    print("=" * 70)
    
    # Initialize orchestrator
    print("\n[1/4] Initializing system...")
    orchestrator = get_orchestrator()
    
    # Load mock data
    print("[2/4] Loading mock news data...")
    articles = await load_mock_data()
    
    if not articles:
        print("No articles to process!")
        return
    
    # Process articles
    print(f"[3/4] Processing {len(articles)} articles through pipeline...")
    print("-" * 70)
    
    result = await orchestrator.process_news_batch(articles)
    
    print(f"\nProcessing Results:")
    print(f"  ✓ Total articles: {result['total']}")
    print(f"  ✓ Unique stories: {result['processed']}")
    print(f"  ✓ Duplicates detected: {result['duplicates']}")
    print(f"  ✓ Errors: {result['errors']}")
    print(f"  ✓ Success rate: {result['success_rate']:.1%}")
    
    # Demo queries
    print("\n[4/4] Running sample queries...")
    print("-" * 70)
    
    queries = [
        ("HDFC Bank news", "Direct company + sector news"),
        ("Banking sector update", "All banking sector news"),
        ("RBI policy changes", "Regulator-specific filter"),
        ("Interest rate impact", "Semantic theme matching"),
    ]
    
    for query, description in queries:
        print(f"\n📊 Query: \"{query}\"")
        print(f"   Purpose: {description}")
        
        response = await orchestrator.query(query, limit=5)
        
        if response:
            print(f"   Intent: {response.analysis.intent}")
            print(f"   Entities: {[e.value for e in response.analysis.entities]}")
            print(f"   Sectors: {response.analysis.sectors}")
            print(f"   Results: {response.total_count} articles ({response.execution_time_ms:.1f}ms)")
            
            for i, result in enumerate(response.results[:3], 1):
                print(f"   {i}. [{result.relevance_score:.2f}] {result.article.title[:55]}...")
                print(f"      Reason: {result.match_reason}")
        else:
            print("   No results found")
    
    print("\n" + "=" * 70)
    print("  DEMO COMPLETE!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Run API server: python -m uvicorn src.api.main:app --reload")
    print("  2. Open docs: http://localhost:8000/docs")
    print("  3. Try queries: http://localhost:8000/query/quick?q=HDFC+Bank")
    print()


async def init_system():
    """Initialize the system (database, vector store)"""
    print("Initializing Financial News Intelligence System...")
    
    try:
        # Initialize PostgreSQL
        print("  - Initializing PostgreSQL database...")
        init_database()
        print("  ✓ PostgreSQL initialized")
        
        # Initialize Vector Store (happens on first use)
        print("  - Initializing ChromaDB vector store...")
        from src.database.vector_store import get_vector_store
        get_vector_store()
        print("  ✓ ChromaDB initialized")
        
        # Initialize Orchestrator
        print("  - Initializing LangGraph orchestrator...")
        get_orchestrator()
        print("  ✓ Orchestrator initialized")
        
        print("\n✓ System initialization complete!")
        
    except Exception as e:
        print(f"\n✗ Initialization failed: {e}")
        raise


def run_api():
    """Run the FastAPI server"""
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )


def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "demo":
            asyncio.run(demo_system())
        elif command == "init":
            asyncio.run(init_system())
        elif command == "api":
            run_api()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python main.py [demo|init|api]")
    else:
        # Default: run demo
        asyncio.run(demo_system())


if __name__ == "__main__":
    main()
