"""Insights API routes.

Surfaces trader-focused analytics: Impact Score leaderboard, Market Heatmap,
Narratives, user preferences and bookmarks. This is the backend powering a
"daily.dev for traders" experience.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.features.impact_index import get_impact_index_service
from src.features.attention_heatmap import get_attention_service
from src.features.narrative_detection import get_narrative_service, NarrativeCluster
from src.features.user_prefs import get_user_prefs_service, UserBookmark
from src.models.schemas import (
    ImpactScorePayload,
    ImpactLeaderboardResponse,
    AttentionHeatmapResponse,
)


router = APIRouter(prefix="/insights", tags=["Insights"])


# ================== Impact Score ==================


@router.get("/impact/article/{article_id}", response_model=ImpactScorePayload)
async def get_article_impact(article_id: str):
    """Get impact score breakdown for a single article."""
    service = get_impact_index_service()
    payload = service.score_article(article_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Article not found")
    return payload


@router.get("/impact/leaderboard", response_model=ImpactLeaderboardResponse)
async def get_impact_leaderboard(
    window_hours: int = Query(24, ge=1, le=168),
    limit: int = Query(15, ge=1, le=50),
):
    """Get top impact stories within the specified time window."""
    service = get_impact_index_service()
    return service.top_articles(window_hours=window_hours, limit=limit)


# ================== Attention Heatmap ==================


@router.get("/heatmap", response_model=AttentionHeatmapResponse)
async def get_attention_heatmap(
    window_hours: int = Query(24, ge=1, le=168),
    baseline_days: int = Query(7, ge=1, le=30),
):
    """Get sector attention heatmap comparing recent vs baseline activity."""
    service = get_attention_service()
    return service.get_heatmap(window_hours=window_hours, baseline_days=baseline_days)


# ================== Narratives ==================


class NarrativeItem(BaseModel):
    narrative_id: str
    label: str
    sector_tags: List[str]
    article_count: int
    avg_sentiment: Optional[float]
    representative_headlines: List[str]
    article_ids: List[str]


class NarrativesResponse(BaseModel):
    generated_at: datetime
    window_hours: int
    narratives: List[NarrativeItem]


@router.get("/narratives", response_model=NarrativesResponse)
async def get_narratives(
    window_hours: int = Query(48, ge=6, le=168),
    max_narratives: int = Query(10, ge=1, le=25),
):
    """Detect top market narratives driving news flow."""
    service = get_narrative_service()
    result = service.detect_narratives(
        window_hours=window_hours, max_narratives=max_narratives
    )
    # Convert dataclasses to Pydantic
    items = [
        NarrativeItem(
            narrative_id=n.narrative_id,
            label=n.label,
            sector_tags=n.sector_tags,
            article_count=n.article_count,
            avg_sentiment=n.avg_sentiment,
            representative_headlines=n.representative_headlines,
            article_ids=n.article_ids,
        )
        for n in result.narratives
    ]
    return NarrativesResponse(
        generated_at=result.generated_at,
        window_hours=result.window_hours,
        narratives=items,
    )


# ================== User Preferences ==================


class FollowRequest(BaseModel):
    value: str


class BookmarkRequest(BaseModel):
    article_id: str
    headline: str
    source: str
    notes: Optional[str] = None


class UserPrefsResponse(BaseModel):
    user_id: str
    followed_sectors: List[str]
    followed_symbols: List[str]
    bookmarks: List[dict]
    hidden_sources: List[str]


@router.get("/user/prefs", response_model=UserPrefsResponse)
async def get_user_prefs(user_id: str = Query("default")):
    """Get current user preferences and bookmarks."""
    service = get_user_prefs_service()
    prefs = service.get(user_id)
    return UserPrefsResponse(
        user_id=prefs.user_id,
        followed_sectors=prefs.followed_sectors,
        followed_symbols=prefs.followed_symbols,
        bookmarks=[
            {
                "article_id": b.article_id,
                "headline": b.headline,
                "source": b.source,
                "saved_at": b.saved_at,
                "notes": b.notes,
            }
            for b in prefs.bookmarks
        ],
        hidden_sources=prefs.hidden_sources,
    )


@router.post("/user/follow/sector")
async def follow_sector(req: FollowRequest, user_id: str = Query("default")):
    """Follow a sector to personalize your feed."""
    service = get_user_prefs_service()
    service.follow_sector(user_id, req.value)
    return {"status": "ok", "followed": req.value}


@router.delete("/user/follow/sector")
async def unfollow_sector(sector: str, user_id: str = Query("default")):
    """Unfollow a sector."""
    service = get_user_prefs_service()
    service.unfollow_sector(user_id, sector)
    return {"status": "ok", "unfollowed": sector}


@router.post("/user/follow/symbol")
async def follow_symbol(req: FollowRequest, user_id: str = Query("default")):
    """Follow a stock symbol."""
    service = get_user_prefs_service()
    service.follow_symbol(user_id, req.value)
    return {"status": "ok", "followed": req.value.upper()}


@router.delete("/user/follow/symbol")
async def unfollow_symbol(symbol: str, user_id: str = Query("default")):
    """Unfollow a stock symbol."""
    service = get_user_prefs_service()
    service.unfollow_symbol(user_id, symbol)
    return {"status": "ok", "unfollowed": symbol.upper()}


@router.post("/user/bookmark")
async def add_bookmark(req: BookmarkRequest, user_id: str = Query("default")):
    """Bookmark an article for later."""
    service = get_user_prefs_service()
    service.add_bookmark(
        user_id, req.article_id, req.headline, req.source, req.notes
    )
    return {"status": "ok", "bookmarked": req.article_id}


@router.delete("/user/bookmark/{article_id}")
async def remove_bookmark(article_id: str, user_id: str = Query("default")):
    """Remove a bookmarked article."""
    service = get_user_prefs_service()
    service.remove_bookmark(user_id, article_id)
    return {"status": "ok", "removed": article_id}


@router.post("/user/hide-source")
async def hide_source(req: FollowRequest, user_id: str = Query("default")):
    """Hide articles from a specific source."""
    service = get_user_prefs_service()
    service.hide_source(user_id, req.value)
    return {"status": "ok", "hidden": req.value}


@router.delete("/user/hide-source")
async def unhide_source(source: str, user_id: str = Query("default")):
    """Unhide a previously hidden source."""
    service = get_user_prefs_service()
    service.unhide_source(user_id, source)
    return {"status": "ok", "unhidden": source}
