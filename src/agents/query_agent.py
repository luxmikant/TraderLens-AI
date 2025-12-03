"""
Query Processing Agent - Handles context-aware natural language queries
Now with RAG (Retrieval-Augmented Generation) for synthesized answers
"""
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime
import time

from src.database.vector_store import get_vector_store, VectorStore
from src.agents.ner_agent import get_ner_agent, EntityExtractionAgent
from src.config import COMPANIES, SECTORS, settings
from src.models.schemas import (
    QueryInput, QueryAnalysis, QueryEntity, QueryResult, QueryResponse,
    ProcessedNewsArticle, EntityType, QueryProcessingState
)
from src.utils.cache import get_query_cache

# RAG integration
try:
    from src.utils.rag_engine import get_rag_engine, RAGEngine
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


logger = logging.getLogger(__name__)


class QueryProcessingAgent:
    """
    Agent responsible for:
    1. Understanding query intent
    2. Extracting entities from queries
    3. Expanding context (company → sector, etc.)
    4. Semantic search with metadata filtering
    5. Ranking and explaining results
    
    Query Patterns Supported:
    - "HDFC Bank news" → Direct + Sector news
    - "Banking sector update" → All banking news
    - "RBI policy changes" → Regulator-specific
    - "Interest rate impact" → Semantic theme matching
    """
    
    def __init__(self, vector_store: Optional[VectorStore] = None, ner_agent: Optional[EntityExtractionAgent] = None):
        self.vector_store = vector_store or get_vector_store()
        self.ner_agent = ner_agent or get_ner_agent()
        
        # RAG engine for synthesized answers
        self.rag_engine = None
        if RAG_AVAILABLE:
            try:
                self.rag_engine = get_rag_engine()
                if self.rag_engine.is_available:
                    logger.info("RAG engine enabled for query synthesis")
                else:
                    logger.warning("RAG engine not available (no LLM configured)")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG engine: {e}")
        
        # Build knowledge graph for context expansion
        self._build_knowledge_graph()
        
        logger.info("QueryProcessingAgent initialized")
    
    def _build_knowledge_graph(self):
        """Build knowledge graph for entity relationships"""
        # Company to sector mapping
        self.company_to_sector: Dict[str, str] = {}
        for company, info in COMPANIES.items():
            self.company_to_sector[company.lower()] = info.get('sector', '')
            if info.get('ticker_nse'):
                self.company_to_sector[info['ticker_nse'].lower()] = info.get('sector', '')
        
        # Sector to companies mapping
        self.sector_to_companies: Dict[str, List[str]] = {}
        for company, info in COMPANIES.items():
            sector = info.get('sector')
            if sector:
                if sector not in self.sector_to_companies:
                    self.sector_to_companies[sector] = []
                self.sector_to_companies[sector].append(company)
        
        # Regulator to sector mapping
        self.regulator_to_sectors = {
            "RBI": ["Banking", "Financial Services"],
            "SEBI": ["Financial Services"],
            "Ministry of Finance": ["Banking", "Financial Services"]
        }
    
    # ================== Query Analysis ==================
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """
        Analyze user query to understand intent and extract entities.
        
        Args:
            query: User's natural language query
            
        Returns:
            QueryAnalysis with entities, intent, and expanded query
        """
        # Extract entities from query
        entities_result = self.ner_agent.extract_from_query(query)
        
        # Build query entities with expansion
        query_entities = []
        detected_sectors = set()
        
        # Process companies
        for company_entity in entities_result.companies:
            expanded = self._expand_company(company_entity.value)
            query_entities.append(QueryEntity(
                entity_type=EntityType.COMPANY,
                value=company_entity.value,
                expanded_values=expanded
            ))
            # Add sector for context expansion
            sector = self.company_to_sector.get(company_entity.value.lower())
            if sector:
                detected_sectors.add(sector)
        
        # Process regulators
        for reg_entity in entities_result.regulators:
            expanded = self._expand_regulator(reg_entity.value)
            query_entities.append(QueryEntity(
                entity_type=EntityType.REGULATOR,
                value=reg_entity.value,
                expanded_values=expanded
            ))
        
        # Detect sectors from query or entities
        for sector in entities_result.sectors:
            detected_sectors.add(sector)
        
        # Also check query text for sector keywords
        query_lower = query.lower()
        for sector, keywords in SECTORS.items():
            if sector.lower() in query_lower or any(kw in query_lower for kw in keywords):
                detected_sectors.add(sector)
        
        # Determine intent
        intent = self._determine_intent(query, query_entities, list(detected_sectors))
        
        # Build expanded query
        expanded_query = self._build_expanded_query(query, query_entities, list(detected_sectors))
        
        return QueryAnalysis(
            original_query=query,
            entities=query_entities,
            sectors=list(detected_sectors),
            intent=intent,
            expanded_query=expanded_query
        )
    
    def _expand_company(self, company: str) -> List[str]:
        """Expand company to related terms"""
        expanded = [company]
        
        # Add ticker
        company_info = COMPANIES.get(company, {})
        if company_info.get('ticker_nse'):
            expanded.append(company_info['ticker_nse'])
        
        # Add sector companies for context
        sector = company_info.get('sector')
        if sector:
            expanded.append(sector)
        
        return expanded
    
    def _expand_regulator(self, regulator: str) -> List[str]:
        """Expand regulator to affected sectors"""
        expanded = [regulator]
        
        # Add affected sectors
        affected_sectors = self.regulator_to_sectors.get(regulator, [])
        expanded.extend(affected_sectors)
        
        return expanded
    
    def _determine_intent(self, query: str, entities: List[QueryEntity], sectors: List[str]) -> str:
        """Determine query intent"""
        query_lower = query.lower()
        
        # Check for specific patterns
        if any(e.entity_type == EntityType.REGULATOR for e in entities):
            return "regulator_action"
        
        if any(e.entity_type == EntityType.COMPANY for e in entities):
            if "sector" in query_lower or sectors:
                return "company_with_sector"
            return "company_news"
        
        if sectors or "sector" in query_lower:
            return "sector_update"
        
        # Theme-based queries
        themes = ["interest rate", "inflation", "earnings", "dividend", "merger", "ipo"]
        for theme in themes:
            if theme in query_lower:
                return "theme_search"
        
        return "general_search"
    
    def _build_expanded_query(self, query: str, entities: List[QueryEntity], sectors: List[str]) -> str:
        """Build expanded query for better semantic matching"""
        parts = [query]
        
        # Add entity values
        for entity in entities:
            parts.extend(entity.expanded_values)
        
        # Add sectors
        parts.extend(sectors)
        
        return " ".join(set(parts))
    
    # ================== Search Methods ==================
    
    def search(self, query_input: QueryInput) -> QueryResponse:
        """
        Execute search based on query input.
        Now includes RAG synthesis for AI-generated answers.
        Uses caching for faster repeat queries.
        
        Args:
            query_input: Query input with filters
            
        Returns:
            QueryResponse with ranked results and optional RAG synthesis
        """
        start_time = time.time()
        
        # Check query cache first (skip RAG for cached results)
        query_cache = get_query_cache()
        cache_key_result = query_cache.get(
            query_input.query, 
            query_input.limit, 
            query_input.include_sector_news
        )
        
        if cache_key_result is not None:
            # Return cached response with updated execution time
            cached_response = cache_key_result
            cached_response.execution_time_ms = round((time.time() - start_time) * 1000, 2)
            logger.debug(f"Cache hit for query: {query_input.query}")
            return cached_response
        
        # Analyze query
        analysis = self.analyze_query(query_input.query)
        
        # Execute search based on intent
        results = self._execute_search(query_input, analysis)
        
        # Rank and format results
        ranked_results = self._rank_results(results, analysis)
        
        # Limit results
        ranked_results = ranked_results[:query_input.limit]
        
        # === RAG SYNTHESIS (skip if requested for speed) ===
        rag_answer = None
        rag_metadata = None
        
        if not query_input.skip_rag and self.rag_engine and self.rag_engine.is_available and results:
            try:
                rag_response = self.rag_engine.synthesize_answer(
                    query=query_input.query,
                    retrieved_docs=results[:5]  # Use top 5 docs for context
                )
                if rag_response:
                    rag_answer = rag_response.answer
                    rag_metadata = {
                        "sources_used": rag_response.sources_used,
                        "llm_latency_ms": rag_response.latency_ms,
                        "model": rag_response.model,
                        "provider": rag_response.provider
                    }
                    logger.info(f"RAG synthesis completed in {rag_response.latency_ms:.0f}ms")
            except Exception as e:
                logger.warning(f"RAG synthesis failed: {e}")
        
        execution_time = (time.time() - start_time) * 1000
        
        response = QueryResponse(
            query=query_input.query,
            analysis=analysis,
            results=ranked_results,
            total_count=len(ranked_results),
            execution_time_ms=round(execution_time, 2)
        )
        
        # Add RAG fields if available
        if rag_answer:
            response.synthesized_answer = rag_answer
            response.rag_metadata = rag_metadata
        
        # Cache the response (before returning)
        query_cache.set(
            query_input.query,
            response,
            query_input.limit,
            query_input.include_sector_news
        )
        
        return response
    
    def _execute_search(self, query_input: QueryInput, analysis: QueryAnalysis) -> List[Dict]:
        """Execute search based on analysis"""
        all_results = []
        
        # 1. Semantic search on original query
        semantic_results = self.vector_store.semantic_search(
            query=query_input.query,
            n_results=query_input.limit * 2
        )
        for result in semantic_results:
            result['source_type'] = 'semantic'
        all_results.extend(semantic_results)
        
        # 2. Entity-based search
        for entity in analysis.entities:
            if entity.entity_type == EntityType.COMPANY:
                company_results = self.vector_store.get_by_entity(
                    entity_type="company",
                    entity_value=entity.value,
                    n_results=query_input.limit
                )
                for result in company_results:
                    result['source_type'] = 'entity_match'
                    result['matched_entity'] = entity.value
                all_results.extend(company_results)
            
            elif entity.entity_type == EntityType.REGULATOR:
                reg_results = self.vector_store.get_by_entity(
                    entity_type="regulator",
                    entity_value=entity.value,
                    n_results=query_input.limit
                )
                for result in reg_results:
                    result['source_type'] = 'regulator_match'
                    result['matched_entity'] = entity.value
                all_results.extend(reg_results)
        
        # 3. Sector-based search (if include_sector_news is True)
        if query_input.include_sector_news and analysis.sectors:
            for sector in analysis.sectors:
                sector_results = self.vector_store.hybrid_search(
                    query=query_input.query,
                    sector_filter=[sector],
                    n_results=query_input.limit
                )
                for result in sector_results:
                    result['source_type'] = 'sector_match'
                    result['matched_sector'] = sector
                all_results.extend(sector_results)
        
        return all_results
    
    def _rank_results(self, results: List[Dict], analysis: QueryAnalysis) -> List[QueryResult]:
        """Rank and deduplicate results"""
        # Deduplicate by article ID
        seen_ids = set()
        unique_results = []
        
        for result in results:
            article_id = result.get('id')
            if article_id in seen_ids:
                continue
            seen_ids.add(article_id)
            unique_results.append(result)
        
        # Calculate final scores
        scored_results = []
        for result in unique_results:
            base_score = result.get('score', 0.5)
            source_type = result.get('source_type', 'semantic')
            
            # Boost based on match type
            if source_type == 'entity_match':
                score = base_score * 1.2
                reason = f"Direct mention of {result.get('matched_entity', 'entity')}"
            elif source_type == 'regulator_match':
                score = base_score * 1.1
                reason = f"Mentions {result.get('matched_entity', 'regulator')}"
            elif source_type == 'sector_match':
                score = base_score * 1.0
                reason = f"Related to {result.get('matched_sector', 'sector')} sector"
            else:
                score = base_score
                reason = "Semantically similar to query"
            
            # Create article from result
            metadata = result.get('metadata', {})
            article = ProcessedNewsArticle(
                id=result.get('id', ''),
                title=metadata.get('title', result.get('content', '')[:100]),
                content=result.get('content', ''),
                source=metadata.get('source', 'unknown'),
                published_at=None,
                is_duplicate=False
            )
            
            scored_results.append(QueryResult(
                article=article,
                relevance_score=min(score, 1.0),
                match_reason=reason,
                highlights=self._extract_highlights(result.get('content', ''), analysis)
            ))
        
        # Sort by score
        scored_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return scored_results
    
    def _extract_highlights(self, content: str, analysis: QueryAnalysis) -> List[str]:
        """Extract relevant highlights from content"""
        highlights = []
        
        # Find sentences containing entities
        sentences = content.split('.')
        for entity in analysis.entities:
            for sentence in sentences:
                if entity.value.lower() in sentence.lower():
                    highlights.append(sentence.strip() + '.')
                    break
        
        return highlights[:3]  # Limit to 3 highlights
    
    # ================== Convenience Methods ==================
    
    def quick_search(self, query: str, limit: int = 10) -> List[QueryResult]:
        """Quick search with default settings"""
        query_input = QueryInput(query=query, limit=limit)
        response = self.search(query_input)
        return response.results
    
    def search_by_company(self, company: str, limit: int = 10) -> List[QueryResult]:
        """Search for news about a specific company"""
        return self.quick_search(f"{company} news", limit)
    
    def search_by_sector(self, sector: str, limit: int = 10) -> List[QueryResult]:
        """Search for news about a specific sector"""
        return self.quick_search(f"{sector} sector update", limit)
    
    # ================== LangGraph Integration ==================
    
    async def process(self, state: QueryProcessingState) -> QueryProcessingState:
        """
        Process state for LangGraph pipeline.
        """
        response = self.search(state.query_input)
        state.query_analysis = response.analysis
        state.response = response
        
        return state


# ================== Example Usage ==================

def demonstrate_query():
    """Demonstrate query processing"""
    agent = QueryProcessingAgent()
    
    queries = [
        "HDFC Bank news",
        "Banking sector update",
        "RBI policy changes",
        "Interest rate impact on markets"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        
        response = agent.search(QueryInput(query=query, limit=5))
        
        print(f"\nAnalysis:")
        print(f"  Intent: {response.analysis.intent}")
        print(f"  Entities: {[e.value for e in response.analysis.entities]}")
        print(f"  Sectors: {response.analysis.sectors}")
        
        print(f"\nResults ({response.total_count} found, {response.execution_time_ms:.1f}ms):")
        for i, result in enumerate(response.results[:3], 1):
            print(f"  {i}. [{result.relevance_score:.2f}] {result.article.title[:60]}...")
            print(f"     Reason: {result.match_reason}")


# Singleton instance
_query_agent: Optional[QueryProcessingAgent] = None


def get_query_agent() -> QueryProcessingAgent:
    """Get or create query agent singleton"""
    global _query_agent
    if _query_agent is None:
        _query_agent = QueryProcessingAgent()
    return _query_agent
