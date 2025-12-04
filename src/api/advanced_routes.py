"""
Advanced Features API Routes

WebSocket endpoints and REST APIs for:
- Real-time alerts
- Sentiment-price predictions
- Supply chain analysis
- Explainability
- Multi-lingual support
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advanced", tags=["Advanced Features"])


# ================== Request/Response Models ==================

class PricePredictionRequest(BaseModel):
    """Request for price prediction"""
    symbol: str
    title: str
    content: str
    sentiment_score: Optional[float] = None
    sentiment_label: Optional[str] = None
    sector: Optional[str] = None


class SupplyChainRequest(BaseModel):
    """Request for supply chain analysis"""
    sector: str
    sentiment_score: float
    sentiment_label: str


class ExplainRequest(BaseModel):
    """Request for explanation"""
    explanation_type: str  # "retrieval", "sentiment", "stock_mapping", etc.
    context: Dict[str, Any]


class TranslationRequest(BaseModel):
    """Request for translation"""
    text: str
    source_lang: Optional[str] = None  # Auto-detect if None
    preserve_entities: bool = True


class AlertSubscriptionRequest(BaseModel):
    """WebSocket subscription preferences"""
    symbols: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    min_priority: str = "normal"
    alert_types: Optional[List[str]] = None


# ================== WebSocket Alerts ==================

@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time news alerts.
    
    Connect: ws://localhost:8000/advanced/ws/alerts
    
    After connecting, send subscription preferences:
    {
        "action": "subscribe",
        "symbols": ["HDFCBANK", "TCS"],
        "min_priority": "high"
    }
    
    Receive alerts:
    {
        "type": "alert",
        "data": {
            "alert_id": "ALT-20251203-0001",
            "priority": "critical",
            "title": "Breaking: RBI announces rate hike",
            ...
        }
    }
    """
    from src.features.realtime_alerts import get_alert_manager, AlertPriority
    
    manager = get_alert_manager()
    user_id = f"user_{id(websocket)}"
    
    try:
        await manager.connect(websocket, user_id)
        
        while True:
            # Receive messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action", "")
                
                if action == "subscribe":
                    # Update subscription
                    symbols = set(message.get("symbols", []))
                    sectors = set(message.get("sectors", []))
                    min_priority = AlertPriority(message.get("min_priority", "normal"))
                    
                    await manager.update_subscription(
                        user_id,
                        symbols=symbols,
                        sectors=sectors,
                        min_priority=min_priority
                    )
                    
                    await websocket.send_json({
                        "type": "subscribed",
                        "symbols": list(symbols),
                        "sectors": list(sectors),
                        "min_priority": min_priority.value
                    })
                
                elif action == "ping":
                    await websocket.send_json({"type": "pong"})
                
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected: {user_id}")


@router.get("/alerts/recent")
async def get_recent_alerts(
    limit: int = Query(50, ge=1, le=200),
    symbols: Optional[str] = None,
    priority: Optional[str] = None
):
    """
    Get recent alerts via REST API.
    
    Query params:
    - limit: Max alerts to return
    - symbols: Comma-separated stock symbols
    - priority: Minimum priority (low, normal, high, critical)
    """
    from src.features.realtime_alerts import get_alert_manager, AlertPriority
    
    manager = get_alert_manager()
    
    symbols_list = symbols.split(",") if symbols else None
    priority_enum = AlertPriority(priority) if priority else None
    
    alerts = manager.get_recent_alerts(
        limit=limit,
        symbols=symbols_list,
        priority=priority_enum
    )
    
    return {"alerts": alerts, "count": len(alerts)}


@router.get("/alerts/stats")
async def get_alert_stats():
    """Get alert system statistics"""
    from src.features.realtime_alerts import get_alert_manager
    
    manager = get_alert_manager()
    
    return {
        "active_connections": manager.active_connections,
        "total_alerts": len(manager.alert_history),
        "recent_alerts": len(manager.get_recent_alerts(limit=10))
    }


# ================== Price Prediction ==================

@router.post("/predict/price")
async def predict_price_impact(request: PricePredictionRequest):
    """
    Predict price impact from news sentiment.
    
    Uses historical sentiment-return patterns to predict
    potential price movement direction and magnitude.
    """
    from src.features.sentiment_price_predictor import get_price_predictor
    from src.agents.sentiment_agent import get_sentiment_agent
    
    predictor = get_price_predictor()
    
    # Get sentiment if not provided
    sentiment_score = request.sentiment_score
    sentiment_label = request.sentiment_label
    
    if sentiment_score is None or sentiment_label is None:
        sentiment_agent = get_sentiment_agent()
        if sentiment_agent.is_available:
            content = f"{request.title}\n{request.content}"
            result = sentiment_agent.analyze(content)
            if result:
                sentiment_score = result.score if result.label.value == "bullish" else -result.score
                sentiment_label = result.label.value
    
    # Default if still None
    sentiment_score = sentiment_score or 0.0
    sentiment_label = sentiment_label or "neutral"
    
    prediction = predictor.predict_impact(
        symbol=request.symbol,
        sentiment_score=sentiment_score,
        sentiment_label=sentiment_label,
        title=request.title,
        content=request.content,
        sector=request.sector or "general"
    )
    
    return {
        "prediction": prediction.to_dict(),
        "input": {
            "symbol": request.symbol,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label
        }
    }


@router.post("/predict/batch")
async def predict_batch(articles: List[PricePredictionRequest]):
    """Batch price predictions for multiple articles"""
    from src.features.sentiment_price_predictor import get_price_predictor
    
    predictor = get_price_predictor()
    
    predictions = []
    for article in articles:
        prediction = predictor.predict_impact(
            symbol=article.symbol,
            sentiment_score=article.sentiment_score or 0.0,
            sentiment_label=article.sentiment_label or "neutral",
            title=article.title,
            content=article.content,
            sector=article.sector or "general"
        )
        predictions.append(prediction.to_dict())
    
    return {"predictions": predictions, "count": len(predictions)}


# ================== Supply Chain Analysis ==================

@router.post("/supply-chain/analyze")
async def analyze_supply_chain(request: SupplyChainRequest):
    """
    Analyze cross-sectoral supply chain impacts.
    
    Given news about one sector, predicts spillover effects
    to related upstream, downstream, and lateral sectors.
    """
    from src.features.supply_chain import get_supply_chain_analyzer
    
    analyzer = get_supply_chain_analyzer()
    
    impacts = analyzer.analyze_full_chain(
        sector=request.sector,
        sentiment_score=request.sentiment_score,
        sentiment_label=request.sentiment_label
    )
    
    # Convert to dict format
    result = {
        "source_sector": request.sector,
        "sentiment": {
            "score": request.sentiment_score,
            "label": request.sentiment_label
        },
        "impacts": {
            "upstream": [
                {
                    "sector": i.sector,
                    "impact_pct": i.impact_pct,
                    "strength": i.strength.value,
                    "stocks": i.stocks,
                    "reasoning": i.reasoning
                }
                for i in impacts["upstream"]
            ],
            "downstream": [
                {
                    "sector": i.sector,
                    "impact_pct": i.impact_pct,
                    "strength": i.strength.value,
                    "stocks": i.stocks,
                    "reasoning": i.reasoning
                }
                for i in impacts["downstream"]
            ],
            "lateral": [
                {
                    "sector": i.sector,
                    "impact_pct": i.impact_pct,
                    "strength": i.strength.value,
                    "stocks": i.stocks,
                    "reasoning": i.reasoning
                }
                for i in impacts["lateral"]
            ]
        }
    }
    
    return result


@router.get("/supply-chain/sectors")
async def get_supply_chain_sectors():
    """Get all sectors with supply chain mappings"""
    from src.features.supply_chain import get_supply_chain_analyzer
    
    analyzer = get_supply_chain_analyzer()
    
    return {
        "sectors": list(analyzer.SUPPLY_CHAIN.keys()),
        "total_mappings": sum(len(v) for v in analyzer.SUPPLY_CHAIN.values())
    }


@router.get("/supply-chain/related/{sector}")
async def get_related_stocks(sector: str):
    """Get stocks related to a sector via supply chain"""
    from src.features.supply_chain import get_supply_chain_analyzer
    
    analyzer = get_supply_chain_analyzer()
    related = analyzer.get_related_stocks(sector)
    
    return {
        "sector": sector,
        "related_sectors": related
    }


# ================== Explainability ==================

@router.post("/explain")
async def get_explanation(request: ExplainRequest):
    """
    Get natural language explanation for AI decisions.
    
    Types:
    - retrieval: Why an article was retrieved
    - sentiment: Sentiment analysis reasoning
    - stock_mapping: Why a stock was linked
    - supply_chain: Cross-sector impact reasoning
    """
    from src.features.explainability import get_explainability_engine
    
    engine = get_explainability_engine()
    context = request.context
    
    if request.explanation_type == "retrieval":
        explanation = engine.explain_retrieval(
            query=context.get("query", ""),
            article_title=context.get("title", ""),
            article_content=context.get("content", ""),
            match_score=context.get("score", 0.5),
            matched_entities=context.get("entities", []),
            matched_sectors=context.get("sectors", []),
            query_intent=context.get("intent")
        )
    
    elif request.explanation_type == "sentiment":
        explanation = engine.explain_sentiment(
            text=context.get("text", ""),
            label=context.get("label", "neutral"),
            score=context.get("score", 0.5),
            key_phrases=context.get("key_phrases", []),
            model_used=context.get("model", "FinBERT")
        )
    
    elif request.explanation_type == "stock_mapping":
        explanation = engine.explain_stock_mapping(
            entity=context.get("entity", ""),
            symbol=context.get("symbol", ""),
            confidence=context.get("confidence", 0.5),
            mapping_type=context.get("mapping_type", "direct"),
            relationship=context.get("relationship")
        )
    
    elif request.explanation_type == "supply_chain":
        explanation = engine.explain_supply_chain_impact(
            source_sector=context.get("source_sector", ""),
            target_sector=context.get("target_sector", ""),
            impact_direction=context.get("direction", "lateral"),
            impact_pct=context.get("impact_pct", 0.0),
            relationship=context.get("relationship", ""),
            affected_stocks=context.get("stocks", [])
        )
    
    else:
        raise HTTPException(400, f"Unknown explanation type: {request.explanation_type}")
    
    return explanation.to_dict()


# ================== Multi-lingual Support ==================

@router.post("/translate")
async def translate_text(request: TranslationRequest):
    """
    Translate Indian language text to English.
    
    Supports: Hindi, Marathi, Tamil, Telugu, Gujarati, Bengali, Kannada, Malayalam
    
    Entity names are preserved in their English form.
    """
    from src.features.multilingual import get_multilingual_processor
    
    processor = get_multilingual_processor()
    
    # Detect language if not provided
    if request.source_lang:
        from src.features.multilingual import SupportedLanguage
        source = SupportedLanguage(request.source_lang)
    else:
        detection = processor.detect_language(request.text)
        source = detection.detected_lang
    
    result = processor.translate_to_english(
        text=request.text,
        source_lang=source,
        preserve_entities=request.preserve_entities
    )
    
    return {
        "original": result.original_text,
        "translated": result.translated_text,
        "source_language": result.source_lang.value,
        "confidence": result.confidence,
        "entities_preserved": result.entities_preserved
    }


@router.post("/detect-language")
async def detect_language(text: str):
    """Detect the language of input text"""
    from src.features.multilingual import get_multilingual_processor
    
    processor = get_multilingual_processor()
    result = processor.detect_language(text)
    
    return {
        "detected_language": result.detected_lang.value,
        "confidence": result.confidence,
        "is_mixed": result.is_mixed
    }


@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    from src.features.multilingual import get_multilingual_processor
    
    processor = get_multilingual_processor()
    return {"languages": processor.get_supported_languages()}


@router.post("/extract-entities-multilingual")
async def extract_multilingual_entities(request: TranslationRequest):
    """Extract entities from multilingual text"""
    from src.features.multilingual import get_multilingual_processor
    
    processor = get_multilingual_processor()
    
    # Detect language
    detection = processor.detect_language(request.text)
    
    # Extract entities
    entities = processor.extract_entities_multilingual(
        text=request.text,
        source_lang=detection.detected_lang
    )
    
    return {
        "text": request.text,
        "language": detection.detected_lang.value,
        "entities": entities
    }


# ================== Sentiment Analysis ==================

@router.post("/sentiment/analyze")
async def analyze_sentiment(text: str, use_finbert: bool = True):
    """
    Analyze sentiment of financial text.
    
    Uses FinBERT for financial domain-specific analysis.
    """
    from src.agents.sentiment_agent import get_sentiment_agent
    
    agent = get_sentiment_agent()
    
    if not agent.is_available:
        raise HTTPException(503, "FinBERT not available. Install: pip install transformers torch")
    
    result = agent.analyze(text)
    
    if result:
        return {
            "label": result.label.value,
            "score": result.score,
            "raw_scores": result.raw_scores
        }
    else:
        return {"label": "neutral", "score": 0.5, "error": "Analysis failed"}


@router.post("/sentiment/batch")
async def analyze_sentiment_batch(texts: List[str]):
    """Batch sentiment analysis"""
    from src.agents.sentiment_agent import get_sentiment_agent
    
    agent = get_sentiment_agent()
    
    if not agent.is_available:
        raise HTTPException(503, "FinBERT not available")
    
    results = agent.analyze_batch(texts)
    
    return {
        "results": [
            {
                "label": r.label.value if r else "neutral",
                "score": r.score if r else 0.5
            }
            for r in results
        ]
    }


@router.post("/sentiment/aggregate")
async def aggregate_sentiment(texts: List[str]):
    """Get aggregated sentiment across multiple texts"""
    from src.agents.sentiment_agent import get_sentiment_agent
    
    agent = get_sentiment_agent()
    
    if not agent.is_available:
        raise HTTPException(503, "FinBERT not available")
    
    result = agent.get_aggregated_sentiment(texts)
    
    return result or {"error": "No valid results"}


# ================== Insights (NEW) ==================

@router.get("/insights/impact/{article_id}")
async def get_article_impact(article_id: str):
    """Get impact score breakdown for a single article."""
    from src.features.impact_index import get_impact_index_service

    service = get_impact_index_service()
    payload = service.score_article(article_id)
    if not payload:
        raise HTTPException(404, "Article not found")
    return payload.dict()


@router.get("/insights/leaderboard")
async def get_impact_leaderboard(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(15, ge=1, le=50),
):
    """Top impact articles (Market Movers) within a time window."""
    from src.features.impact_index import get_impact_index_service

    service = get_impact_index_service()
    return service.top_articles(window_hours=hours, limit=limit).dict()


@router.get("/insights/heatmap")
async def get_attention_heatmap(
    hours: int = Query(24, ge=1, le=168),
    baseline_days: int = Query(7, ge=1, le=30),
):
    """Attention heatmap across sectors."""
    from src.features.attention_heatmap import get_attention_service

    service = get_attention_service()
    return service.get_heatmap(window_hours=hours, baseline_days=baseline_days).dict()


@router.get("/insights/narratives")
async def get_narratives(
    hours: int = Query(48, ge=12, le=168),
    min_size: int = Query(3, ge=2, le=10),
    max_results: int = Query(8, ge=1, le=20),
):
    """Detect narrative clusters from recent news."""
    from src.features.narrative_detector import get_narrative_detector

    detector = get_narrative_detector()
    narratives = detector.detect_narratives(
        window_hours=hours, min_cluster_size=min_size, max_narratives=max_results
    )
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "narratives": [
            {
                "cluster_id": n.cluster_id,
                "label": n.label,
                "summary": n.summary,
                "article_count": n.article_count,
                "avg_sentiment": n.avg_sentiment,
                "sectors": n.sectors,
                "top_articles": n.top_articles,
                "first_seen": n.first_seen.isoformat(),
                "last_seen": n.last_seen.isoformat(),
            }
            for n in narratives
        ],
    }


@router.get("/insights/trending")
async def get_trending_symbols(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=30),
):
    """Trending symbols in the current news cycle."""
    from src.features.trending import get_trending_service

    service = get_trending_service()
    response = service.get_trending(window_hours=hours, limit=limit)
    return {
        "generated_at": response.generated_at.isoformat(),
        "window_hours": response.window_hours,
        "symbols": [
            {
                "symbol": s.symbol,
                "mention_count": s.mention_count,
                "avg_sentiment": s.avg_sentiment,
                "direction": s.direction,
            }
            for s in response.symbols
        ],
    }


# ================== Bookmarks & Watchlist ==================

@router.post("/bookmarks/{user_id}/add")
async def add_bookmark(user_id: str, article_id: str):
    """Add an article to user's bookmarks."""
    from src.features.bookmarks import get_bookmark_service

    service = get_bookmark_service()
    service.add_bookmark(user_id, article_id)
    return {"status": "bookmarked", "article_id": article_id}


@router.delete("/bookmarks/{user_id}/remove")
async def remove_bookmark(user_id: str, article_id: str):
    """Remove article from user's bookmarks."""
    from src.features.bookmarks import get_bookmark_service

    service = get_bookmark_service()
    removed = service.remove_bookmark(user_id, article_id)
    return {"status": "removed" if removed else "not_found", "article_id": article_id}


@router.get("/bookmarks/{user_id}")
async def list_bookmarks(user_id: str):
    """List all bookmarked article IDs for a user."""
    from src.features.bookmarks import get_bookmark_service

    service = get_bookmark_service()
    return {"user_id": user_id, "bookmarks": service.get_bookmarks(user_id)}


@router.post("/watchlist/{user_id}/add")
async def add_to_watchlist(user_id: str, item_type: str, value: str):
    """Add a symbol or sector to watchlist."""
    from src.features.bookmarks import get_bookmark_service

    if item_type not in ("symbol", "sector"):
        raise HTTPException(400, "item_type must be 'symbol' or 'sector'")

    service = get_bookmark_service()
    item = service.add_to_watchlist(user_id, item_type, value)
    return {"status": "added", "item_type": item.item_type, "value": item.value}


@router.delete("/watchlist/{user_id}/remove")
async def remove_from_watchlist(user_id: str, item_type: str, value: str):
    """Remove a symbol or sector from watchlist."""
    from src.features.bookmarks import get_bookmark_service

    service = get_bookmark_service()
    removed = service.remove_from_watchlist(user_id, item_type, value)
    return {"status": "removed" if removed else "not_found"}


@router.get("/watchlist/{user_id}")
async def list_watchlist(user_id: str):
    """List watchlist items for a user."""
    from src.features.bookmarks import get_bookmark_service

    service = get_bookmark_service()
    items = service.get_watchlist(user_id)
    return {
        "user_id": user_id,
        "watchlist": [
            {"type": i.item_type, "value": i.value, "created_at": i.created_at.isoformat()}
            for i in items
        ],
    }
