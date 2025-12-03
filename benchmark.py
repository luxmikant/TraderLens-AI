"""
Performance Benchmark Script for Tradl AI
Run with: python benchmark.py

Measures:
- Query response times
- Deduplication accuracy
- NER precision
- RAG synthesis latency
"""

import time
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def benchmark_query_performance():
    """Benchmark query response times."""
    print("\n" + "="*60)
    print("📊 QUERY PERFORMANCE BENCHMARK")
    print("="*60)
    
    from src.agents.query_agent import get_query_agent
    from src.models.schemas import QueryInput
    
    agent = get_query_agent()
    
    queries = [
        ("HDFC Bank news", "company"),
        ("Banking sector update", "sector"),
        ("RBI policy changes", "regulator"),
        ("TCS earnings report", "company"),
        ("Interest rate impact", "theme"),
        ("Reliance quarterly results", "company"),
        ("IT sector outlook", "sector"),
        ("SEBI new regulations", "regulator"),
    ]
    
    # First test WITH RAG (slower but synthesized answer)
    print("\n  📝 WITH RAG SYNTHESIS:")
    results_with_rag = []
    for query, query_type in queries:
        start = time.time()
        result = agent.search(QueryInput(query=query, limit=10, skip_rag=False))
        elapsed = (time.time() - start) * 1000
        
        rag_time = None
        if hasattr(result, 'rag_metadata') and result.rag_metadata:
            rag_time = result.rag_metadata.get('llm_latency_ms')
        
        results_with_rag.append({
            "query": query,
            "type": query_type,
            "time_ms": elapsed,
            "results": result.total_count,
            "rag_ms": rag_time
        })
        
        rag_str = f" (RAG: {rag_time:.0f}ms)" if rag_time else ""
        print(f"    {query:30s} | {elapsed:6.0f}ms | {result.total_count:3d} results{rag_str}")
    
    times_with_rag = [r["time_ms"] for r in results_with_rag]
    avg_with_rag = sum(times_with_rag) / len(times_with_rag)
    
    # Then test WITHOUT RAG (fast retrieval only)
    print("\n  ⚡ WITHOUT RAG (skip_rag=True):")
    results_no_rag = []
    for query, query_type in queries:
        start = time.time()
        result = agent.search(QueryInput(query=query, limit=10, skip_rag=True))
        elapsed = (time.time() - start) * 1000
        
        results_no_rag.append({
            "query": query,
            "type": query_type,
            "time_ms": elapsed,
            "results": result.total_count,
        })
        
        print(f"    {query:30s} | {elapsed:6.0f}ms | {result.total_count:3d} results")
    
    times_no_rag = [r["time_ms"] for r in results_no_rag]
    avg_no_rag = sum(times_no_rag) / len(times_no_rag)
    
    print(f"\n  WITH RAG:    {avg_with_rag:.0f}ms avg | Status: {'✅ PASS' if avg_with_rag < 2000 else '⚠️ SLOW'}")
    print(f"  WITHOUT RAG: {avg_no_rag:.0f}ms avg | Status: {'✅ PASS' if avg_no_rag < 500 else '⚠️ SLOW'}")
    print(f"  Target: <500ms for retrieval, <2000ms with RAG")
    
    return results_with_rag


def benchmark_dedup_accuracy():
    """Benchmark deduplication accuracy."""
    print("\n" + "="*60)
    print("🔍 DEDUPLICATION ACCURACY BENCHMARK")
    print("="*60)
    
    from src.agents.dedup_agent import get_dedup_agent
    from src.database.vector_store import get_vector_store
    import uuid
    
    agent = get_dedup_agent()
    vector_store = get_vector_store()
    
    # Pairs that SHOULD be detected as duplicates
    duplicate_pairs = [
        (
            "HDFC Bank announces 15% dividend for shareholders in AGM",
            "HDFC Bank declares 15% dividend at annual general meeting"
        ),
        (
            "RBI raises repo rate by 25 basis points to 6.75%",
            "Reserve Bank hikes interest rate by 0.25% to 6.75%"
        ),
        (
            "TCS wins $500 million contract from European bank",
            "Tata Consultancy Services bags $500M deal from Europe"
        ),
    ]
    
    # Pairs that should NOT be detected as duplicates
    unique_pairs = [
        (
            "HDFC Bank announces 15% dividend",
            "TCS reports record quarterly profit"
        ),
        (
            "RBI raises interest rates",
            "Sensex hits all-time high today"
        ),
        (
            "Reliance Jio adds 5M subscribers",
            "Airtel launches new 5G plans in metro cities"
        ),
    ]
    
    true_positives = 0
    false_negatives = 0
    true_negatives = 0
    false_positives = 0
    
    print("\n  Testing duplicate detection:")
    for orig, dup in duplicate_pairs:
        # IMPORTANT: First STORE the original article in vector store
        article_id = f"benchmark-{uuid.uuid4().hex[:8]}"
        vector_store.add_article(
            article_id=article_id,
            content=orig,
            metadata={"source": "benchmark", "cluster_id": article_id}
        )
        
        # Now check if duplicate is detected
        is_duplicate, cluster_id, similarity_score = agent.check_duplicate(dup)
        
        if is_duplicate:
            true_positives += 1
            print(f"  ✅ Detected duplicate (score: {similarity_score:.2f})")
        else:
            false_negatives += 1
            print(f"  ❌ Missed duplicate (score: {similarity_score:.2f})")
    
    print("\n  Testing unique detection:")
    for art1, art2 in unique_pairs:
        # Store first article
        article_id = f"benchmark-{uuid.uuid4().hex[:8]}"
        vector_store.add_article(
            article_id=article_id,
            content=art1,
            metadata={"source": "benchmark", "cluster_id": article_id}
        )
        
        # Check if second (unrelated) article is wrongly flagged as duplicate
        is_duplicate, cluster_id, similarity_score = agent.check_duplicate(art2)
        
        if not is_duplicate:
            true_negatives += 1
            print(f"  ✅ Correctly identified as unique (score: {similarity_score:.2f})")
        else:
            false_positives += 1
            print(f"  ❌ False positive (score: {similarity_score:.2f})")
    
    total = true_positives + true_negatives + false_positives + false_negatives
    accuracy = (true_positives + true_negatives) / total if total > 0 else 0
    
    print(f"\n  True Positives: {true_positives} | False Negatives: {false_negatives}")
    print(f"  True Negatives: {true_negatives} | False Positives: {false_positives}")
    print(f"  Accuracy: {accuracy*100:.1f}% | Target: ≥95% | Status: {'✅ PASS' if accuracy >= 0.95 else '⚠️ NEEDS TUNING'}")
    
    return {"accuracy": accuracy, "tp": true_positives, "tn": true_negatives, "fp": false_positives, "fn": false_negatives}


def benchmark_ner_precision():
    """Benchmark NER precision."""
    print("\n" + "="*60)
    print("🏷️ NER PRECISION BENCHMARK")
    print("="*60)
    
    from src.agents.ner_agent import get_ner_agent
    
    agent = get_ner_agent()
    
    test_cases = [
        {
            "content": "HDFC Bank CEO Sashidhar Jagdishan announced Q1 results",
            "expected_companies": ["HDFC Bank"],
            "expected_people": ["Sashidhar Jagdishan"]
        },
        {
            "content": "TCS and Infosys both reported strong quarterly earnings today",
            "expected_companies": ["TCS", "Infosys"],
            "expected_people": []
        },
        {
            "content": "RBI Governor Shaktikanta Das raised repo rate by 25bps",
            "expected_companies": [],
            "expected_regulators": ["RBI"]
        },
        {
            "content": "Reliance Industries Q3 profit rises 12% on strong Jio growth",
            "expected_companies": ["Reliance Industries", "Reliance"],
            "expected_people": []
        },
        {
            "content": "SEBI issues new guidelines for FPI investments in India",
            "expected_companies": [],
            "expected_regulators": ["SEBI"]
        },
    ]
    
    company_correct = 0
    company_total = 0
    regulator_correct = 0
    regulator_total = 0
    
    for test in test_cases:
        result = agent.extract_all(test["content"])
        extracted_companies = [e.value for e in result.companies]
        extracted_regulators = [e.value for e in result.regulators]
        
        # Check companies
        for exp in test.get("expected_companies", []):
            company_total += 1
            if any(exp.lower() in e.lower() for e in extracted_companies):
                company_correct += 1
                print(f"  ✅ Found company: {exp}")
            else:
                print(f"  ❌ Missed company: {exp} (extracted: {extracted_companies})")
        
        # Check regulators
        for exp in test.get("expected_regulators", []):
            regulator_total += 1
            if any(exp.lower() in e.lower() for e in extracted_regulators):
                regulator_correct += 1
                print(f"  ✅ Found regulator: {exp}")
            else:
                print(f"  ❌ Missed regulator: {exp}")
    
    company_precision = company_correct / company_total if company_total > 0 else 1.0
    regulator_precision = regulator_correct / regulator_total if regulator_total > 0 else 1.0
    overall_precision = (company_correct + regulator_correct) / (company_total + regulator_total)
    
    print(f"\n  Company Precision: {company_precision*100:.1f}% ({company_correct}/{company_total})")
    print(f"  Regulator Precision: {regulator_precision*100:.1f}% ({regulator_correct}/{regulator_total})")
    print(f"  Overall Precision: {overall_precision*100:.1f}% | Target: ≥90% | Status: {'✅ PASS' if overall_precision >= 0.90 else '⚠️ NEEDS TUNING'}")
    
    return {"company_precision": company_precision, "regulator_precision": regulator_precision, "overall": overall_precision}


def benchmark_rag_performance():
    """Benchmark RAG synthesis performance (if enabled)."""
    print("\n" + "="*60)
    print("🤖 RAG SYNTHESIS BENCHMARK")
    print("="*60)
    
    try:
        from src.utils.rag_engine import get_rag_engine
        
        engine = get_rag_engine()
        
        if not engine.is_available:
            print("  ⚠️ RAG not available (no LLM configured)")
            print("  Set GROQ_API_KEY in .env to enable RAG synthesis")
            return None
        
        print(f"  Provider: {engine.llm.provider}")
        print(f"  Model: {engine.llm.model}")
        
        # Test with sample docs
        sample_docs = [
            {
                "content": "HDFC Bank reported a 20% increase in Q3 net profit to Rs 15,000 crore.",
                "metadata": {"title": "HDFC Q3 Results", "source": "Moneycontrol"}
            },
            {
                "content": "The bank's asset quality improved with NPAs declining to 1.2%.",
                "metadata": {"title": "Banking Sector Update", "source": "ET"}
            }
        ]
        
        queries = [
            "What happened with HDFC Bank?",
            "How is the banking sector performing?",
        ]
        
        times = []
        for query in queries:
            start = time.time()
            result = engine.synthesize_answer(query, sample_docs)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            
            if result:
                print(f"\n  Query: '{query}'")
                print(f"  Time: {elapsed:.0f}ms")
                print(f"  Answer preview: {result.answer[:100]}...")
        
        avg = sum(times) / len(times) if times else 0
        print(f"\n  Average RAG latency: {avg:.0f}ms")
        print(f"  Target: <200ms (Groq) | Status: {'✅ FAST' if avg < 200 else '⚠️ OK' if avg < 500 else '❌ SLOW'}")
        
        return {"avg_latency_ms": avg, "provider": engine.llm.provider}
        
    except ImportError:
        print("  ⚠️ RAG engine not available")
        return None


def run_all_benchmarks():
    """Run all benchmarks and generate report."""
    print("\n" + "="*60)
    print("🚀 TRADL AI PERFORMANCE BENCHMARKS")
    print("="*60)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run benchmarks
    results["query"] = benchmark_query_performance()
    results["dedup"] = benchmark_dedup_accuracy()
    results["ner"] = benchmark_ner_precision()
    results["rag"] = benchmark_rag_performance()
    
    # Summary
    print("\n" + "="*60)
    print("📋 SUMMARY")
    print("="*60)
    
    query_times = [r["time_ms"] for r in results["query"]]
    avg_query = sum(query_times) / len(query_times)
    
    print(f"  Query Performance:   {avg_query:.0f}ms avg (target: <500ms)")
    print(f"  Dedup Accuracy:      {results['dedup']['accuracy']*100:.1f}% (target: ≥95%)")
    print(f"  NER Precision:       {results['ner']['overall']*100:.1f}% (target: ≥90%)")
    
    if results["rag"]:
        print(f"  RAG Latency:         {results['rag']['avg_latency_ms']:.0f}ms ({results['rag']['provider']})")
    else:
        print(f"  RAG:                 Not configured")
    
    print("\n" + "="*60)
    
    return results


if __name__ == "__main__":
    run_all_benchmarks()
