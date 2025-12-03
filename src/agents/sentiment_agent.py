"""
FinBERT Sentiment Analysis Agent

Uses ProsusAI/finbert for financial domain-specific sentiment analysis.
Provides sentiment labels: BULLISH, BEARISH, NEUTRAL with confidence scores.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FinancialSentiment(str, Enum):
    """Financial sentiment labels from FinBERT"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class SentimentResult:
    """Result from sentiment analysis"""
    label: FinancialSentiment
    score: float  # Confidence score 0-1
    raw_scores: Dict[str, float]  # All label scores
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label.value,
            "score": self.score,
            "raw_scores": self.raw_scores
        }


class FinBERTSentimentAgent:
    """
    Financial sentiment analysis using FinBERT.
    
    FinBERT is a BERT model fine-tuned on financial text:
    - Model: ProsusAI/finbert
    - Labels: positive, negative, neutral
    - We map these to: bullish, bearish, neutral
    
    Performance targets:
    - Latency: <50ms per article (GPU) / <200ms (CPU)
    - Accuracy: ~85% on financial news
    """
    
    # Map FinBERT labels to our domain labels
    LABEL_MAP = {
        "positive": FinancialSentiment.BULLISH,
        "negative": FinancialSentiment.BEARISH,
        "neutral": FinancialSentiment.NEUTRAL
    }
    
    def __init__(self, model_name: str = "ProsusAI/finbert", device: Optional[str] = None):
        """
        Initialize the FinBERT sentiment analyzer.
        
        Args:
            model_name: HuggingFace model ID
            device: 'cuda', 'cpu', or None for auto-detect
        """
        self.model_name = model_name
        self.device: Optional[str] = device
        self.pipeline: Any = None
        self._is_loaded = False
        
        logger.info(f"FinBERTSentimentAgent initialized (lazy loading: {model_name})")
    
    def _load_model(self):
        """Lazy load the model on first use"""
        if self._is_loaded:
            return
            
        try:
            from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
            import torch
            
            # Auto-detect device if not specified
            if self.device is None:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            
            logger.info(f"Loading FinBERT model on {self.device}...")
            
            # Load tokenizer and model
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            
            # Create pipeline
            self.pipeline = pipeline(
                "sentiment-analysis",
                model=model,
                tokenizer=tokenizer,
                device=0 if self.device == "cuda" else -1,
                top_k=None  # Return all scores
            )
            
            self._is_loaded = True
            logger.info("FinBERT model loaded successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import transformers: {e}")
            logger.info("Install with: pip install transformers torch")
            raise
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            raise
    
    @property
    def is_available(self) -> bool:
        """Check if the model can be loaded"""
        try:
            import transformers
            import torch
            return True
        except ImportError:
            return False
    
    def analyze(self, text: str) -> Optional[SentimentResult]:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: Financial news text (title + content recommended)
            
        Returns:
            SentimentResult with label, score, and raw scores
        """
        if not text or not text.strip():
            return None
            
        try:
            self._load_model()
            
            # Truncate to model's max length (512 tokens ~ 2000 chars)
            truncated_text = text[:2000]
            
            # Run inference
            results = self.pipeline(truncated_text)
            
            if not results:
                return None
            
            # Parse results (format: [{'label': 'positive', 'score': 0.95}, ...])
            raw_scores: Dict[str, float] = {}
            best_label: str = "neutral"
            best_score: float = 0.0
            
            for result in results[0]:
                label = result['label'].lower()
                score = result['score']
                raw_scores[label] = score
                
                if score > best_score:
                    best_score = score
                    best_label = label
            
            # Map to our labels
            sentiment_label = self.LABEL_MAP.get(best_label, FinancialSentiment.NEUTRAL)
            
            return SentimentResult(
                label=sentiment_label,
                score=best_score,
                raw_scores=raw_scores
            )
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return None
    
    def analyze_batch(self, texts: List[str]) -> List[Optional[SentimentResult]]:
        """
        Analyze sentiment of multiple texts efficiently.
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of SentimentResult objects
        """
        if not texts:
            return []
            
        try:
            self._load_model()
            
            # Truncate all texts
            truncated_texts = [t[:2000] if t else "" for t in texts]
            
            # Batch inference
            batch_results = self.pipeline(truncated_texts)
            
            results = []
            for text_results in batch_results:
                if not text_results:
                    results.append(None)
                    continue
                    
                raw_scores: Dict[str, float] = {}
                best_label: str = "neutral"
                best_score: float = 0.0
                
                for result in text_results:
                    label = result['label'].lower()
                    score = result['score']
                    raw_scores[label] = score
                    
                    if score > best_score:
                        best_score = score
                        best_label = label
                
                sentiment_label = self.LABEL_MAP.get(best_label, FinancialSentiment.NEUTRAL)
                results.append(SentimentResult(
                    label=sentiment_label,
                    score=best_score,
                    raw_scores=raw_scores
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"Batch sentiment analysis failed: {e}")
            return [None] * len(texts)
    
    def get_aggregated_sentiment(
        self, 
        texts: List[str],
        weights: Optional[List[float]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get aggregated sentiment across multiple texts.
        
        Useful for:
        - Cluster-level sentiment (multiple articles on same topic)
        - Daily/weekly sentiment summary
        
        Args:
            texts: List of texts to analyze
            weights: Optional weights for each text (e.g., by recency or relevance)
            
        Returns:
            Aggregated sentiment with label, confidence, and distribution
        """
        results = self.analyze_batch(texts)
        valid_results = [r for r in results if r is not None]
        
        if not valid_results:
            return None
        
        if weights is None:
            weights = [1.0] * len(valid_results)
        else:
            weights = weights[:len(valid_results)]
        
        total_weight = sum(weights)
        
        # Aggregate scores
        sentiment_scores = {
            FinancialSentiment.BULLISH: 0.0,
            FinancialSentiment.BEARISH: 0.0,
            FinancialSentiment.NEUTRAL: 0.0
        }
        
        for result, weight in zip(valid_results, weights):
            normalized_weight = weight / total_weight
            sentiment_scores[result.label] += result.score * normalized_weight
        
        # Find dominant sentiment
        dominant_sentiment = max(sentiment_scores, key=lambda x: sentiment_scores.get(x, 0.0))
        confidence = sentiment_scores[dominant_sentiment]
        
        return {
            "label": dominant_sentiment.value,
            "confidence": round(confidence, 3),
            "distribution": {
                "bullish": round(sentiment_scores[FinancialSentiment.BULLISH], 3),
                "bearish": round(sentiment_scores[FinancialSentiment.BEARISH], 3),
                "neutral": round(sentiment_scores[FinancialSentiment.NEUTRAL], 3)
            },
            "sample_size": len(valid_results)
        }


# Singleton instance
_sentiment_agent: Optional[FinBERTSentimentAgent] = None


def get_sentiment_agent() -> FinBERTSentimentAgent:
    """Get or create the sentiment agent singleton"""
    global _sentiment_agent
    if _sentiment_agent is None:
        _sentiment_agent = FinBERTSentimentAgent()
    return _sentiment_agent


# Convenience function for quick sentiment check
def quick_sentiment(text: str) -> Tuple[str, float]:
    """
    Quick sentiment analysis for a single text.
    
    Returns:
        (label, score) tuple, e.g., ("bullish", 0.92)
    """
    agent = get_sentiment_agent()
    result = agent.analyze(text)
    
    if result:
        return (result.label.value, result.score)
    return ("neutral", 0.5)


if __name__ == "__main__":
    # Test the sentiment agent
    import sys
    
    print("=" * 60)
    print("FinBERT Sentiment Agent Test")
    print("=" * 60)
    
    agent = get_sentiment_agent()
    
    if not agent.is_available:
        print("❌ Transformers not installed. Run:")
        print("   pip install transformers torch")
        sys.exit(1)
    
    test_cases = [
        # Bullish examples
        "HDFC Bank reported record quarterly profits, beating analyst estimates",
        "TCS wins massive $1 billion contract, stock surges 5%",
        "Reliance Industries announces special dividend, shares hit all-time high",
        
        # Bearish examples
        "Wipro cuts guidance amid weak IT spending, stock plunges",
        "RBI raises concerns over rising NPAs in banking sector",
        "Infosys faces client exits, revenue growth slows sharply",
        
        # Neutral examples
        "Sensex closes flat as markets await RBI policy decision",
        "Nifty trades in narrow range ahead of quarterly results",
        "FIIs remain net buyers in Indian equities this week"
    ]
    
    print("\nAnalyzing test cases...\n")
    
    for text in test_cases:
        result = agent.analyze(text)
        if result:
            emoji = "📈" if result.label == FinancialSentiment.BULLISH else "📉" if result.label == FinancialSentiment.BEARISH else "➡️"
            print(f"{emoji} [{result.label.value.upper():8s}] ({result.score:.2f}): {text[:60]}...")
        else:
            print(f"❓ Analysis failed: {text[:40]}...")
    
    print("\n" + "=" * 60)
    print("Aggregated Sentiment Test")
    print("=" * 60)
    
    # Test aggregation on mixed sentiment
    mixed_news = [
        "Bank sector rallies on strong earnings",
        "IT stocks under pressure after weak guidance",
        "Markets consolidate near highs"
    ]
    
    aggregated = agent.get_aggregated_sentiment(mixed_news)
    if aggregated:
        print(f"\nOverall: {aggregated['label'].upper()} ({aggregated['confidence']:.2f})")
        print(f"Distribution: {aggregated['distribution']}")
