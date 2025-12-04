#!/usr/bin/env python3
"""
System Validation Script - Verify all components are working
Run this before recording demo video
"""
import sys
import time
from datetime import datetime

def print_status(message, status="info"):
    """Print colored status messages"""
    colors = {
        "success": "\033[92m✅",
        "error": "\033[91m❌",
        "warning": "\033[93m⚠️",
        "info": "\033[94mℹ️"
    }
    reset = "\033[0m"
    print(f"{colors.get(status, '')} {message}{reset}")

def main():
    print("\n" + "="*60)
    print("🚀 TRADL AI SYSTEM VALIDATION")
    print("="*60 + "\n")
    
    all_checks_passed = True
    
    # 1. Check imports
    print("1. Checking Python dependencies...")
    try:
        import fastapi
        import chromadb
        import transformers
        import torch
        import langchain
        import langgraph
        print_status("All core dependencies installed", "success")
    except ImportError as e:
        print_status(f"Missing dependency: {e}", "error")
        all_checks_passed = False
    
    # 2. Check sentiment agent
    print("\n2. Checking Sentiment Analysis (FinBERT)...")
    try:
        from src.agents.sentiment_agent import get_sentiment_agent
        agent = get_sentiment_agent()
        
        if not agent.is_available:
            print_status("Transformers not available", "error")
            all_checks_passed = False
        else:
            print_status("Sentiment agent initialized", "success")
            
            # Test sentiment analysis
            test_text = "HDFC Bank reported record quarterly profits"
            result = agent.analyze(test_text)
            
            if result:
                print_status(f"Test sentiment: {result.label.value} (score: {result.score:.3f})", "success")
            else:
                print_status("Sentiment analysis returned None", "error")
                all_checks_passed = False
    except Exception as e:
        print_status(f"Sentiment agent error: {e}", "error")
        all_checks_passed = False
    
    # 3. Check vector store
    print("\n3. Checking Vector Store (ChromaDB)...")
    try:
        from src.database.vector_store import get_vector_store
        vs = get_vector_store()
        
        # Try a test search
        results = vs.semantic_search("bank", n_results=1)
        
        if results:
            print_status(f"Vector store operational ({len(results)} results found)", "success")
            
            # Check if sentiment data exists
            if results[0].get('metadata', {}).get('sentiment_label'):
                print_status("Sentiment data present in stored articles", "success")
            else:
                print_status("No sentiment data in stored articles - need fresh ingestion", "warning")
        else:
            print_status("No articles in vector store - run RSS ingestion", "warning")
    except Exception as e:
        print_status(f"Vector store error: {e}", "error")
        all_checks_passed = False
    
    # 4. Check query agent
    print("\n4. Checking Query Agent...")
    try:
        from src.agents.query_agent import get_query_agent
        from src.models.schemas import QueryInput
        
        agent = get_query_agent()
        query_input = QueryInput(query="bank", limit=1)
        response = agent.search(query_input)
        
        if response.results:
            article = response.results[0].article
            has_sentiment = article.sentiment_label is not None
            
            print_status(f"Query agent working ({response.total_count} results)", "success")
            
            if has_sentiment:
                print_status(f"Sentiment in results: {article.sentiment_label} ({article.sentiment_score:.3f})", "success")
            else:
                print_status("No sentiment in query results - check query_agent.py fix", "warning")
        else:
            print_status("Query returned no results", "warning")
    except Exception as e:
        print_status(f"Query agent error: {e}", "error")
        all_checks_passed = False
    
    # 5. Check RAG engine (optional)
    print("\n5. Checking RAG Engine...")
    try:
        from src.utils.rag_engine import get_rag_engine
        rag = get_rag_engine()
        
        if rag.is_available:
            print_status("RAG engine available (Groq LLM configured)", "success")
        else:
            print_status("RAG engine not available - check GROQ_API_KEY", "warning")
    except Exception as e:
        print_status(f"RAG engine check skipped: {e}", "info")
    
    # 6. Check PostgreSQL (optional)
    print("\n6. Checking PostgreSQL...")
    try:
        from src.database.postgres import get_database
        db = get_database()
        session = db.get_session()
        
        # Try a simple query
        from src.database.postgres import NewsArticle
        count = session.query(NewsArticle).count()
        
        print_status(f"PostgreSQL connected ({count} articles)", "success")
    except Exception as e:
        print_status(f"PostgreSQL not available: {e}", "warning")
        print_status("This is optional - system works without it", "info")
    
    # 7. Check API health
    print("\n7. Checking API Server...")
    try:
        import httpx
        response = httpx.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_status(f"API server healthy (version {data.get('version', 'unknown')})", "success")
        else:
            print_status(f"API server returned {response.status_code}", "error")
            all_checks_passed = False
    except Exception as e:
        print_status(f"API server not running: {e}", "error")
        print_status("Start with: uvicorn src.api.main:app --host 0.0.0.0 --port 8000", "info")
        all_checks_passed = False
    
    # Summary
    print("\n" + "="*60)
    if all_checks_passed:
        print_status("ALL CRITICAL CHECKS PASSED ✅", "success")
        print_status("System is ready for demo!", "success")
    else:
        print_status("SOME CHECKS FAILED ⚠️", "warning")
        print_status("Review errors above before recording", "info")
    print("="*60 + "\n")
    
    # Demo readiness checklist
    print("📋 DEMO READINESS CHECKLIST:")
    print("   [ ] Backend running on port 8000")
    print("   [ ] Frontend running on port 5173")
    print("   [ ] Fresh RSS articles ingested (<1 hour old)")
    print("   [ ] Browser cache cleared")
    print("   [ ] Microphone tested")
    print("   [ ] Recording software ready (OBS/Loom)")
    print("   [ ] Demo script reviewed")
    print("\n💡 TIP: Run 'curl -X POST http://localhost:8000/ingest/rss' to fetch fresh news\n")
    
    return 0 if all_checks_passed else 1

if __name__ == "__main__":
    sys.exit(main())
