"""Trending topics and Market Movers endpoint.

Surfaces top symbols and themes getting the most attention
over a short window. Designed to power the "Market Movers" tab.
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
    StockImpact as StockImpactDB,
)


@dataclass
class TrendingSymbol:
    symbol: str
    mention_count: int
    avg_sentiment: Optional[float]
    direction: str


@dataclass
class TrendingResponse:
    generated_at: datetime
    window_hours: int
    symbols: List[TrendingSymbol]


class TrendingService:
    """Computes trending symbols based on recent news flow."""

    def __init__(self, database: Optional[Database] = None):
        self.database = database or get_database()

    def get_trending(
        self, window_hours: int = 24, limit: int = 10
    ) -> TrendingResponse:
        session = self.database.get_session()
        try:
            now = datetime.utcnow()
            start = now - timedelta(hours=window_hours)

            rows = (
                session.query(
                    StockImpactDB.symbol,
                    func.count(StockImpactDB.id).label("cnt"),
                    func.avg(NewsArticle.sentiment_score).label("sentiment"),
                )
                .join(NewsArticle, StockImpactDB.article_id == NewsArticle.id)
                .filter(NewsArticle.published_at >= start)
                .group_by(StockImpactDB.symbol)
                .order_by(func.count(StockImpactDB.id).desc())
                .limit(limit)
                .all()
            )

            symbols: List[TrendingSymbol] = []
            for row in rows:
                sentiment = row.sentiment
                if sentiment is None:
                    direction = "neutral"
                elif sentiment >= 0.05:
                    direction = "bullish"
                elif sentiment <= -0.05:
                    direction = "bearish"
                else:
                    direction = "neutral"

                symbols.append(
                    TrendingSymbol(
                        symbol=row.symbol.upper(),
                        mention_count=row.cnt,
                        avg_sentiment=round(sentiment, 3) if sentiment else None,
                        direction=direction,
                    )
                )

            return TrendingResponse(
                generated_at=now,
                window_hours=window_hours,
                symbols=symbols,
            )

        finally:
            session.close()


_trending_service: Optional[TrendingService] = None


def get_trending_service() -> TrendingService:
    global _trending_service
    if _trending_service is None:
        _trending_service = TrendingService()
    return _trending_service
