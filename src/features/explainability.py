"""
Explainability Engine for News Retrieval

Provides natural language explanations for:
1. Why a news article was retrieved for a query
2. How entities were extracted
3. Why stocks were mapped to news
4. Sentiment analysis reasoning
"""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExplanationType(str, Enum):
    """Types of explanations"""
    RETRIEVAL = "retrieval"           # Why article was retrieved
    ENTITY = "entity"                 # How entity was extracted
    STOCK_MAPPING = "stock_mapping"   # Why stock was linked
    SENTIMENT = "sentiment"           # Sentiment reasoning
    IMPACT = "impact"                 # Price impact reasoning
    SUPPLY_CHAIN = "supply_chain"     # Cross-sector impact


@dataclass
class Explanation:
    """Structured explanation object"""
    explanation_type: ExplanationType
    summary: str  # One-line summary
    details: str  # Full explanation
    confidence: float
    factors: List[str]  # Contributing factors
    evidence: List[str]  # Specific text evidence
    
    def to_dict(self) -> Dict:
        return {
            "type": self.explanation_type.value,
            "summary": self.summary,
            "details": self.details,
            "confidence": round(self.confidence, 3),
            "factors": self.factors,
            "evidence": self.evidence
        }


class ExplainabilityEngine:
    """
    Generates human-readable explanations for AI decisions.
    
    Usage:
        engine = ExplainabilityEngine()
        
        # Explain retrieval
        explanation = engine.explain_retrieval(
            query="HDFC Bank news",
            article_title="HDFC Bank Q3 Results",
            match_score=0.92,
            matched_entities=["HDFC Bank"]
        )
        print(explanation.summary)
        # "This article was retrieved because it directly mentions 'HDFC Bank' 
        #  with 92% relevance to your query."
    """
    
    def __init__(self):
        logger.info("ExplainabilityEngine initialized")
    
    def explain_retrieval(
        self,
        query: str,
        article_title: str,
        article_content: str,
        match_score: float,
        matched_entities: Optional[List[str]] = None,
        matched_sectors: Optional[List[str]] = None,
        query_intent: Optional[str] = None
    ) -> Explanation:
        """
        Explain why an article was retrieved for a query.
        
        Args:
            query: User's search query
            article_title: Title of retrieved article
            article_content: Content snippet
            match_score: Similarity/relevance score
            matched_entities: Entities that matched
            matched_sectors: Sectors that matched
            query_intent: Detected query intent
            
        Returns:
            Explanation with summary and details
        """
        factors = []
        evidence = []
        
        # Build explanation based on match type
        if matched_entities:
            entity_str = ", ".join(matched_entities[:3])
            factors.append(f"Entity match: {entity_str}")
            evidence.append(f"Query mentions: {entity_str}")
        
        if matched_sectors:
            sector_str = ", ".join(matched_sectors[:2])
            factors.append(f"Sector relevance: {sector_str}")
        
        # Score interpretation
        if match_score >= 0.9:
            score_desc = "very high"
            confidence = 0.95
        elif match_score >= 0.7:
            score_desc = "high"
            confidence = 0.85
        elif match_score >= 0.5:
            score_desc = "moderate"
            confidence = 0.70
        else:
            score_desc = "partial"
            confidence = 0.55
        
        factors.append(f"Relevance score: {score_desc} ({match_score:.0%})")
        
        # Query intent
        if query_intent:
            factors.append(f"Query intent: {query_intent}")
        
        # Build summary
        if matched_entities:
            summary = f"Retrieved because it mentions '{matched_entities[0]}' with {match_score:.0%} relevance to your query."
        elif matched_sectors:
            summary = f"Retrieved for {matched_sectors[0]} sector relevance ({match_score:.0%} match)."
        else:
            summary = f"Retrieved based on semantic similarity ({match_score:.0%} relevance)."
        
        # Build detailed explanation
        details = f"""This article '{article_title}' was retrieved for query '{query}' because:

1. **Relevance Score**: {match_score:.1%} - {score_desc} semantic similarity to your query.
"""
        
        if matched_entities:
            details += f"\n2. **Entity Match**: The article mentions {', '.join(matched_entities)}, which directly relates to your search."
        
        if matched_sectors:
            details += f"\n3. **Sector Context**: Relevant to {', '.join(matched_sectors)} sector(s)."
        
        if query_intent:
            details += f"\n4. **Query Intent**: Detected as '{query_intent}' query type."
        
        return Explanation(
            explanation_type=ExplanationType.RETRIEVAL,
            summary=summary,
            details=details,
            confidence=confidence,
            factors=factors,
            evidence=evidence
        )
    
    def explain_entity_extraction(
        self,
        text: str,
        entity: str,
        entity_type: str,
        confidence: float,
        pattern_matched: Optional[str] = None,
        context: Optional[str] = None
    ) -> Explanation:
        """
        Explain how an entity was extracted from text.
        """
        factors = []
        evidence = []
        
        # Pattern type
        if pattern_matched:
            factors.append(f"Matched pattern: {pattern_matched}")
        else:
            factors.append("Dictionary/knowledge base match")
        
        # Context if available
        if context:
            evidence.append(f'Found in context: "...{context}..."')
        
        factors.append(f"Entity type: {entity_type}")
        factors.append(f"Confidence: {confidence:.0%}")
        
        summary = f"'{entity}' identified as {entity_type} with {confidence:.0%} confidence."
        
        details = f"""Entity Extraction Details:

**Entity**: {entity}
**Type**: {entity_type}
**Confidence**: {confidence:.1%}

**Extraction Method**:
- {"Pattern matching: " + pattern_matched if pattern_matched else "Dictionary lookup from financial entity database"}
- Cross-referenced with known Indian market entities

**Context**:
{context or 'N/A'}
"""
        
        return Explanation(
            explanation_type=ExplanationType.ENTITY,
            summary=summary,
            details=details,
            confidence=confidence,
            factors=factors,
            evidence=evidence
        )
    
    def explain_stock_mapping(
        self,
        entity: str,
        symbol: str,
        confidence: float,
        mapping_type: str,  # "direct", "subsidiary", "sector", "supply_chain"
        relationship: Optional[str] = None
    ) -> Explanation:
        """
        Explain why a stock was mapped to a news article.
        """
        factors = []
        evidence = []
        
        mapping_descriptions = {
            "direct": "Direct company mention",
            "subsidiary": "Subsidiary/parent company relationship",
            "sector": "Sector-level impact",
            "supply_chain": "Supply chain relationship"
        }
        
        factors.append(f"Mapping type: {mapping_descriptions.get(mapping_type, mapping_type)}")
        factors.append(f"Confidence: {confidence:.0%}")
        
        if relationship:
            factors.append(f"Relationship: {relationship}")
            evidence.append(relationship)
        
        summary = f"{symbol} linked via {mapping_type} ({confidence:.0%} confidence)."
        
        details = f"""Stock Mapping Explanation:

**Entity Mentioned**: {entity}
**Stock Symbol**: {symbol}
**Confidence**: {confidence:.1%}

**Mapping Type**: {mapping_descriptions.get(mapping_type, mapping_type)}
{f'**Relationship**: {relationship}' if relationship else ''}

**Reasoning**:
"""
        
        if mapping_type == "direct":
            details += f"The article directly mentions {entity}, which maps to stock symbol {symbol}."
        elif mapping_type == "subsidiary":
            details += f"{entity} is related to {symbol} through corporate structure (parent/subsidiary)."
        elif mapping_type == "sector":
            details += f"News affects the sector that includes {symbol}."
        elif mapping_type == "supply_chain":
            details += f"{entity} is in the supply chain of {symbol}. {relationship or ''}"
        
        return Explanation(
            explanation_type=ExplanationType.STOCK_MAPPING,
            summary=summary,
            details=details,
            confidence=confidence,
            factors=factors,
            evidence=evidence
        )
    
    def explain_sentiment(
        self,
        text: str,
        label: str,
        score: float,
        key_phrases: Optional[List[str]] = None,
        model_used: str = "FinBERT"
    ) -> Explanation:
        """
        Explain sentiment analysis result.
        """
        factors = []
        evidence = []
        
        factors.append(f"Model: {model_used}")
        factors.append(f"Sentiment: {label} ({score:.0%})")
        
        if key_phrases:
            for phrase in key_phrases[:3]:
                evidence.append(f'"{phrase}"')
            factors.append(f"Key phrases: {len(key_phrases)} detected")
        
        # Sentiment interpretation
        if label == "bullish":
            interpretation = "positive/optimistic"
            signal = "potential upward price movement"
        elif label == "bearish":
            interpretation = "negative/pessimistic"
            signal = "potential downward price movement"
        else:
            interpretation = "neutral/balanced"
            signal = "no strong directional signal"
        
        summary = f"Sentiment: {label.upper()} ({score:.0%}) - {interpretation} tone detected."
        
        details = f"""Sentiment Analysis Explanation:

**Sentiment Label**: {label.upper()}
**Confidence Score**: {score:.1%}
**Model Used**: {model_used}

**Interpretation**:
The text conveys a {interpretation} tone, suggesting {signal}.

**Key Phrases Contributing to Sentiment**:
"""
        if key_phrases:
            for phrase in key_phrases[:5]:
                details += f'\n- "{phrase}"'
        else:
            details += "\n(Phrase-level attribution not available)"
        
        return Explanation(
            explanation_type=ExplanationType.SENTIMENT,
            summary=summary,
            details=details,
            confidence=score,
            factors=factors,
            evidence=evidence
        )
    
    def explain_price_prediction(
        self,
        symbol: str,
        direction: str,
        expected_return: float,
        confidence: float,
        contributing_factors: List[str]
    ) -> Explanation:
        """
        Explain price impact prediction.
        """
        factors = contributing_factors.copy()
        evidence = []
        
        factors.append(f"Direction: {direction}")
        factors.append(f"Expected return: {expected_return:+.2f}%")
        
        if expected_return > 0:
            signal = "positive price reaction expected"
        elif expected_return < 0:
            signal = "negative price reaction expected"
        else:
            signal = "minimal price impact expected"
        
        summary = f"{symbol}: {direction.upper()} ({expected_return:+.1f}%) - {signal}"
        
        details = f"""Price Impact Prediction:

**Stock**: {symbol}
**Direction**: {direction.upper()}
**Expected Return**: {expected_return:+.2f}%
**Confidence**: {confidence:.1%}

**Contributing Factors**:
"""
        for i, factor in enumerate(contributing_factors, 1):
            details += f"\n{i}. {factor}"
        
        details += """

**Disclaimer**: This is a model prediction based on historical patterns. 
Actual market movements may differ. Not financial advice.
"""
        
        return Explanation(
            explanation_type=ExplanationType.IMPACT,
            summary=summary,
            details=details,
            confidence=confidence,
            factors=factors,
            evidence=evidence
        )
    
    def explain_supply_chain_impact(
        self,
        source_sector: str,
        target_sector: str,
        impact_direction: str,
        impact_pct: float,
        relationship: str,
        affected_stocks: List[str]
    ) -> Explanation:
        """
        Explain cross-sector supply chain impact.
        """
        factors = []
        evidence = []
        
        factors.append(f"Source: {source_sector}")
        factors.append(f"Target: {target_sector}")
        factors.append(f"Relationship: {impact_direction}")
        factors.append(f"Impact: {impact_pct:+.1f}%")
        
        evidence.append(relationship)
        if affected_stocks:
            evidence.append(f"Affected stocks: {', '.join(affected_stocks[:3])}")
        
        if impact_pct > 0:
            impact_desc = "positive spillover"
        elif impact_pct < 0:
            impact_desc = "negative spillover"
        else:
            impact_desc = "neutral impact"
        
        summary = f"{source_sector} → {target_sector}: {impact_desc} ({impact_pct:+.1f}%)"
        
        details = f"""Supply Chain Impact Analysis:

**Source Sector**: {source_sector}
**Target Sector**: {target_sector}
**Relationship**: {impact_direction}

**Impact**: {impact_pct:+.1f}%
{relationship}

**Potentially Affected Stocks**:
{', '.join(affected_stocks) if affected_stocks else 'N/A'}

**Mechanism**:
"""
        if impact_direction == "upstream":
            details += f"As {source_sector} is a supplier to {target_sector}, changes affect input costs."
        elif impact_direction == "downstream":
            details += f"As {target_sector} is a customer of {source_sector}, demand dynamics are affected."
        else:
            details += f"{source_sector} and {target_sector} are lateral peers, leading to competitive dynamics."
        
        return Explanation(
            explanation_type=ExplanationType.SUPPLY_CHAIN,
            summary=summary,
            details=details,
            confidence=0.7,  # Supply chain correlations are inherently uncertain
            factors=factors,
            evidence=evidence
        )


# Singleton
_engine: Optional[ExplainabilityEngine] = None


def get_explainability_engine() -> ExplainabilityEngine:
    """Get or create the explainability engine"""
    global _engine
    if _engine is None:
        _engine = ExplainabilityEngine()
    return _engine
