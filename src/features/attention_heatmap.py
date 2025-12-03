"""Market attention heatmap across sectors.

This module inspects recent article volume and sentiment to surface
which sectors are receiving abnormal attention versus their baseline.
Borrowed UX inspiration from daily.dev's trending feeds, adapted for traders.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.postgres import (
    get_database,
    Database,
    NewsArticle,
    ArticleEntity,
)
from src.models.schemas import AttentionHeatmapCell, AttentionHeatmapResponse


class MarketAttentionService:
    """Computes attention levels per sector based on news flow."""

    def __init__(self, database: Optional[Database] = None):
        self.database = database or get_database()

    def get_heatmap(
        self,
        window_hours: int = 24,
        baseline_days: int = 7,
        min_mentions: int = 2,
    ) -> AttentionHeatmapResponse:
        session = self.database.get_session()
        try:
            now = datetime.utcnow()
            window_start = now - timedelta(hours=window_hours)
            baseline_start = now - timedelta(days=baseline_days)

            recent = self._sector_stats(session, window_start, now)
            baseline = self._sector_stats(session, baseline_start, now)

            baseline_hours = max(window_hours, baseline_days * 24)
            normalization_factor = baseline_hours / window_hours

            cells: List[AttentionHeatmapCell] = []
            for sector, stats in recent.items():
                if stats["count"] < min_mentions:
                    continue
                baseline_count = baseline.get(sector, {}).get("count", 0)
                baseline_avg = baseline_count / normalization_factor if normalization_factor else baseline_count
                attention = self._attention_score(stats["count"], baseline_avg)
                cells.append(
                    AttentionHeatmapCell(
                        sector=sector,
                        attention_score=round(attention, 2),
                        sentiment_score=round(stats["sentiment"], 3)
                        if stats["sentiment"] is not None
                        else None,
                        recent_mentions=int(stats["count"]),
                        baseline_mentions=round(baseline_avg, 2),
                    )
                )

            cells.sort(key=lambda c: c.attention_score, reverse=True)
            return AttentionHeatmapResponse(
                generated_at=now,
                window_hours=window_hours,
                sectors=cells,
            )
        finally:
            session.close()

    def _sector_stats(
        self, session: Session, start: datetime, end: datetime
    ) -> Dict[str, Dict[str, float]]:
        rows = (
            session.query(
                ArticleEntity.entity_value.label("sector"),
                func.count(ArticleEntity.id).label("cnt"),
                func.avg(NewsArticle.sentiment_score).label("sentiment"),
            )
            .join(NewsArticle, ArticleEntity.article_id == NewsArticle.id)
            .filter(
                ArticleEntity.entity_type == "sector",
                NewsArticle.published_at >= start,
                NewsArticle.published_at <= end,
            )
            .group_by(ArticleEntity.entity_value)
            .all()
        )
        stats: Dict[str, Dict[str, float]] = {}
        for row in rows:
            stats[row.sector] = {
                "count": row.cnt,
                "sentiment": row.sentiment,
            }
        return stats

    @staticmethod
    def _attention_score(recent: float, baseline_avg: float) -> float:
        if baseline_avg <= 0:
            return 100.0
        deviation = (recent - baseline_avg) / baseline_avg
        return max(0.0, min(100.0, 50 + deviation * 50))


_heatmap_service: Optional[MarketAttentionService] = None


def get_attention_service() -> MarketAttentionService:
    global _heatmap_service
    if _heatmap_service is None:
        _heatmap_service = MarketAttentionService()
    return _heatmap_service
