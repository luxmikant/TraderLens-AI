"""Impact Index scoring for news articles.

Computes a trader-friendly score based on sentiment strength, recency,
entity coverage, and source reliability. Designed to surface the
highest-actionability stories for the "daily.dev for traders" experience.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.postgres import (
    get_database,
    Database,
    NewsArticle,
    ArticleEntity,
    StockImpact as StockImpactDB,
)
from src.models.schemas import (
    ImpactScoreComponents,
    ImpactScorePayload,
    ImpactLeaderboardResponse,
)


@dataclass
class _ArticleSnapshot:
    """Lightweight representation used for scoring."""

    article: NewsArticle
    sectors: List[str]
    symbols: List[str]


class ImpactIndexService:
    """Computes impact scores and leaderboards for news articles."""

    SOURCE_RELIABILITY: Dict[str, float] = {
        # Tier-1 market sources
        "moneycontrol": 1.0,
        "economic_times": 0.95,
        "livemint": 0.9,
        "bloomberg": 0.9,
        "reuters": 0.9,
        # TV + retail outlets
        "cnbc": 0.85,
        "financial_express": 0.82,
        "business_standard": 0.82,
        # Default weight
        "default": 0.7,
    }

    RECENCY_HALF_LIFE_HRS = 12
    MAX_SENTIMENT_POINTS = 35.0
    MAX_RECENCY_POINTS = 30.0
    MAX_ENTITY_POINTS = 25.0
    MAX_SOURCE_POINTS = 10.0

    def __init__(self, database: Optional[Database] = None):
        self.database = database or get_database()

    # -------- Public API --------
    def score_article(self, article_id: str) -> Optional[ImpactScorePayload]:
        session = self.database.get_session()
        try:
            snapshot = self._build_snapshot(session, article_id)
            if not snapshot:
                return None
            components = self._calculate_components(snapshot)
            headline = snapshot.article.title[:240]
            return ImpactScorePayload(
                article_id=snapshot.article.id,
                headline=headline,
                source=snapshot.article.source,
                published_at=snapshot.article.published_at,
                impact_score=round(sum(components.dict().values()), 2),
                impact_direction=self._direction(snapshot.article.sentiment_score),
                components=components,
                impacted_symbols=snapshot.symbols,
                sector_tags=snapshot.sectors,
                summary=snapshot.article.content[:320],
            )
        finally:
            session.close()

    def top_articles(
        self, window_hours: int = 24, limit: int = 15
    ) -> ImpactLeaderboardResponse:
        session = self.database.get_session()
        try:
            window_start = datetime.utcnow() - timedelta(hours=window_hours)
            articles = (
                session.query(NewsArticle)
                .filter(NewsArticle.published_at >= window_start)
                .order_by(NewsArticle.published_at.desc())
                .limit(limit * 4)
                .all()
            )
            snapshots = self._hydrate_snapshots(session, articles)
            scored = [
                (
                    snapshot,
                    self._calculate_components(snapshot),
                )
                for snapshot in snapshots
            ]
            scored.sort(
                key=lambda pair: sum(pair[1].dict().values()),
                reverse=True,
            )
            payloads = [
                ImpactScorePayload(
                    article_id=snapshot.article.id,
                    headline=snapshot.article.title[:240],
                    source=snapshot.article.source,
                    published_at=snapshot.article.published_at,
                    impact_score=round(sum(components.dict().values()), 2),
                    impact_direction=self._direction(snapshot.article.sentiment_score),
                    components=components,
                    impacted_symbols=snapshot.symbols,
                    sector_tags=snapshot.sectors,
                    summary=snapshot.article.content[:320],
                )
                for snapshot, components in scored[:limit]
            ]
            return ImpactLeaderboardResponse(
                generated_at=datetime.utcnow(),
                window_hours=window_hours,
                articles=payloads,
            )
        finally:
            session.close()

    # -------- Internal helpers --------
    def _build_snapshot(
        self, session: Session, article_id: str
    ) -> Optional[_ArticleSnapshot]:
        article = session.query(NewsArticle).filter_by(id=article_id).first()
        if not article:
            return None
        return self._hydrate_snapshots(session, [article])[0]

    def _hydrate_snapshots(
        self, session: Session, articles: List[NewsArticle]
    ) -> List[_ArticleSnapshot]:
        if not articles:
            return []
        article_ids = [a.id for a in articles]

        # Fetch sectors/entities in one query
        sector_rows = (
            session.query(ArticleEntity.article_id, ArticleEntity.entity_value)
            .filter(
                ArticleEntity.article_id.in_(article_ids),
                ArticleEntity.entity_type == "sector",
            )
            .all()
        )
        sectors_map: Dict[str, List[str]] = {aid: [] for aid in article_ids}
        for article_id, value in sector_rows:
            sectors_map.setdefault(article_id, []).append(value)

        # Fetch impacted symbols
        impact_rows = (
            session.query(StockImpactDB.article_id, StockImpactDB.symbol, StockImpactDB.confidence)
            .filter(StockImpactDB.article_id.in_(article_ids))
            .all()
        )
        symbols_map: Dict[str, List[str]] = {aid: [] for aid in article_ids}
        for article_id, symbol, confidence in impact_rows:
            if symbol:
                formatted = symbol.upper()
                # Encode confidence as repeated weighting hint (kept simple)
                symbols_map.setdefault(article_id, []).append(formatted)

        return [
            _ArticleSnapshot(
                article=a,
                sectors=sectors_map.get(a.id, []),
                symbols=symbols_map.get(a.id, []),
            )
            for a in articles
        ]

    def _calculate_components(self, snapshot: _ArticleSnapshot) -> ImpactScoreComponents:
        article = snapshot.article
        sentiment_value = abs(article.sentiment_score or 0.0)
        sentiment_component = sentiment_value * self.MAX_SENTIMENT_POINTS

        # Recency decay (exponential)
        reference_time = article.published_at or article.ingested_at or datetime.utcnow()
        hours_old = max(
            0.0, (datetime.utcnow() - reference_time).total_seconds() / 3600.0
        )
        decay = 0.5 ** (hours_old / self.RECENCY_HALF_LIFE_HRS)
        recency_component = decay * self.MAX_RECENCY_POINTS

        # Entity importance: more impacted symbols -> higher score
        unique_symbols = set(snapshot.symbols)
        entity_component = min(
            self.MAX_ENTITY_POINTS,
            len(unique_symbols) * (self.MAX_ENTITY_POINTS / 5.0),
        )

        # Source reliability
        weight = self.SOURCE_RELIABILITY.get(
            (article.source or "").lower(), self.SOURCE_RELIABILITY["default"]
        )
        source_component = weight * self.MAX_SOURCE_POINTS

        # Surprise factor: penalize duplicates via cluster id + boost multi-sector
        surprise_factor = 0.0
        if article.cluster_id:
            surprise_factor = -5.0
        if len(set(snapshot.sectors)) >= 2:
            surprise_factor += 5.0

        return ImpactScoreComponents(
            sentiment=round(sentiment_component, 2),
            recency=round(recency_component, 2),
            entity_importance=round(entity_component, 2),
            source_reliability=round(source_component, 2),
            surprise_factor=round(surprise_factor, 2),
        )

    @staticmethod
    def _direction(sentiment_score: Optional[float]) -> str:
        if sentiment_score is None:
            return "neutral"
        if sentiment_score >= 0.05:
            return "bullish"
        if sentiment_score <= -0.05:
            return "bearish"
        return "neutral"


_service: Optional[ImpactIndexService] = None


def get_impact_index_service() -> ImpactIndexService:
    global _service
    if _service is None:
        _service = ImpactIndexService()
    return _service
