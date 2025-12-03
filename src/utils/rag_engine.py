"""
RAG (Retrieval-Augmented Generation) Engine
Combines vector search with LLM synthesis for intelligent responses
"""
import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import time

from src.utils.llm_client import get_llm_client, LLMClient
from src.config import settings

logger = logging.getLogger(__name__)


# ================== RAG Prompts ==================

FINANCIAL_NEWS_SYSTEM_PROMPT = """You are an AI financial news analyst for Indian markets.
Your role is to synthesize news articles and provide actionable insights for traders.

Guidelines:
- Be concise and factual
- Highlight key entities (companies, regulators, sectors)
- Note potential market impact (bullish/bearish/neutral)
- Mention relevant stock symbols when applicable
- Use Indian market context (NSE/BSE, RBI, SEBI)
- If sentiment is mixed, explain the nuance

Format your response as:
**Summary:** [1-2 sentence overview]
**Key Points:**
- [Point 1]
- [Point 2]
**Market Impact:** [Bullish/Bearish/Neutral] - [Brief explanation]
**Stocks to Watch:** [Relevant tickers if any]"""

QUERY_SYNTHESIS_PROMPT = """Based on the following news articles, answer this query: "{query}"

Retrieved Articles:
{context}

Provide a synthesized answer that:
1. Directly addresses the query
2. Cites specific articles when relevant
3. Notes any conflicting information
4. Highlights actionable insights for traders"""

SUMMARIZATION_PROMPT = """Summarize the following financial news article for a trader:

Title: {title}
Content: {content}

Provide:
1. One-line summary
2. Key entities mentioned
3. Potential market impact (bullish/bearish/neutral)
4. Relevant stock symbols"""


# ================== RAG Response Types ==================

@dataclass
class RAGResponse:
    """Response from RAG synthesis"""
    answer: str
    sources_used: int
    latency_ms: float
    model: str
    provider: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "answer": self.answer,
            "sources_used": self.sources_used,
            "latency_ms": self.latency_ms,
            "model": self.model,
            "provider": self.provider
        }


# ================== RAG Engine ==================

class RAGEngine:
    """
    Retrieval-Augmented Generation engine for financial news.
    
    Flow:
    1. Receive retrieved documents from vector search
    2. Format context from documents
    3. Generate synthesized response using LLM
    4. Return structured response with metadata
    
    Supports:
    - Query answering with context
    - Article summarization
    - Multi-document synthesis
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or get_llm_client()
        self.max_context_docs = settings.rag_max_context_docs
        self.temperature = settings.rag_temperature
        
        logger.info(f"RAGEngine initialized (LLM available: {self.llm.is_available})")
    
    @property
    def is_available(self) -> bool:
        """Check if RAG is available (requires LLM)"""
        return settings.rag_enabled and self.llm.is_available
    
    def synthesize_answer(
        self,
        query: str,
        retrieved_docs: List[Dict],
        include_sources: bool = True
    ) -> Optional[RAGResponse]:
        """
        Synthesize answer from retrieved documents.
        
        Args:
            query: User's question
            retrieved_docs: Documents from vector search
            include_sources: Whether to cite sources
            
        Returns:
            RAGResponse with synthesized answer
        """
        if not self.is_available:
            logger.warning("RAG not available - returning None")
            return None
        
        if not retrieved_docs:
            return RAGResponse(
                answer="No relevant articles found for your query.",
                sources_used=0,
                latency_ms=0,
                model=self.llm.model or "none",
                provider=self.llm.provider or "none"
            )
        
        start_time = time.time()
        
        # Format context from top documents
        context = self._format_context(retrieved_docs[:self.max_context_docs])
        
        # Build prompt
        prompt = QUERY_SYNTHESIS_PROMPT.format(
            query=query,
            context=context
        )
        
        # Generate response
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=FINANCIAL_NEWS_SYSTEM_PROMPT,
            temperature=self.temperature,
            max_tokens=1024
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        if answer is None:
            return None
        
        return RAGResponse(
            answer=answer,
            sources_used=min(len(retrieved_docs), self.max_context_docs),
            latency_ms=round(latency_ms, 2),
            model=self.llm.model or "unknown",
            provider=self.llm.provider or "unknown"
        )
    
    def summarize_article(
        self,
        title: str,
        content: str
    ) -> Optional[str]:
        """
        Summarize a single article.
        
        Args:
            title: Article title
            content: Article content
            
        Returns:
            Summary string
        """
        if not self.is_available:
            return None
        
        prompt = SUMMARIZATION_PROMPT.format(
            title=title,
            content=content[:2000]  # Limit context
        )
        
        return self.llm.generate(
            prompt=prompt,
            system_prompt=FINANCIAL_NEWS_SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=512
        )
    
    def analyze_sentiment(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Analyze sentiment of news content.
        
        Args:
            content: News text
            
        Returns:
            Dict with sentiment label and score
        """
        if not self.is_available:
            return None
        
        prompt = f"""Analyze the sentiment of this financial news:

"{content[:1000]}"

Respond in JSON format:
{{"sentiment": "bullish/bearish/neutral", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""
        
        response = self.llm.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=256
        )
        
        if response:
            try:
                import json
                # Try to extract JSON from response
                if "{" in response and "}" in response:
                    json_str = response[response.find("{"):response.rfind("}")+1]
                    return json.loads(json_str)
            except:
                pass
        
        return None
    
    def _format_context(self, docs: List[Dict]) -> str:
        """Format documents into context string"""
        context_parts = []
        
        for i, doc in enumerate(docs, 1):
            metadata = doc.get('metadata', {})
            title = metadata.get('title', 'Untitled')
            source = metadata.get('source', 'Unknown')
            content = doc.get('content', '')[:500]  # Limit per-doc content
            
            context_parts.append(f"""
Article {i}: "{title}"
Source: {source}
Content: {content}
---""")
        
        return "\n".join(context_parts)


# ================== Singleton ==================

_rag_engine: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Get or create RAG engine singleton"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine
