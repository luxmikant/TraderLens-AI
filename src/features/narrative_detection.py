"""Market Narrative Detection.

Clusters recent headlines into high-level story themes using embeddings +
lightweight clustering. Exposes the top narratives driving market attention
in a given window—akin to daily.dev's "trending topics" but for traders.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from src.database.postgres import get_database, Database, NewsArticle
from src.database.vector_store import get_vector_store, VectorStore

logger = logging.getLogger(__name__)


@dataclass
class NarrativeCluster:
    """A detected narrative with representative articles."""

    narrative_id: str
    label: str
    sector_tags: List[str]
    article_count: int
    avg_sentiment: Optional[float]
    representative_headlines: List[str]
    article_ids: List[str]


@dataclass
class NarrativeResponse:
    """Response wrapper for narrative list."""

    generated_at: datetime
    window_hours: int
    narratives: List[NarrativeCluster]


class NarrativeDetectionService:
    """Detects market narratives from recent news using clustering."""

    def __init__(
        self,
        database: Optional[Database] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        self.database = database or get_database()
        self.vector_store = vector_store or get_vector_store()

    def detect_narratives(
        self,
        window_hours: int = 48,
        min_cluster_size: int = 3,
        distance_threshold: float = 0.35,
        max_narratives: int = 10,
    ) -> NarrativeResponse:
        """Cluster recent headlines and return top narratives."""
        session = self.database.get_session()
        try:
            window_start = datetime.utcnow() - timedelta(hours=window_hours)
            articles = (
                session.query(NewsArticle)
                .filter(
                    NewsArticle.published_at >= window_start,
                    NewsArticle.is_duplicate == False,
                )
                .order_by(NewsArticle.published_at.desc())
                .limit(500)
                .all()
            )

            if len(articles) < min_cluster_size:
                return NarrativeResponse(
                    generated_at=datetime.utcnow(),
                    window_hours=window_hours,
                    narratives=[],
                )

            headlines = [a.title for a in articles]
            embeddings = self._batch_embed(headlines)

            labels = self._cluster(
                embeddings,
                distance_threshold=distance_threshold,
            )

            clusters = self._aggregate_clusters(articles, labels, min_cluster_size)
            clusters.sort(key=lambda c: c.article_count, reverse=True)

            return NarrativeResponse(
                generated_at=datetime.utcnow(),
                window_hours=window_hours,
                narratives=clusters[:max_narratives],
            )
        finally:
            session.close()

    # -------- Helpers --------
    def _batch_embed(self, texts: List[str]) -> np.ndarray:
        embeddings = self.vector_store.generate_embeddings(texts)
        return np.array(embeddings)

    @staticmethod
    def _cluster(
        embeddings: np.ndarray,
        distance_threshold: float,
    ) -> np.ndarray:
        """Agglomerative clustering on embeddings."""
        if len(embeddings) < 2:
            return np.array([0] * len(embeddings))
        clustering = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=distance_threshold,
        )
        return clustering.fit_predict(embeddings)

    def _aggregate_clusters(
        self,
        articles: List[NewsArticle],
        labels: np.ndarray,
        min_size: int,
    ) -> List[NarrativeCluster]:
        cluster_map: Dict[int, List[NewsArticle]] = {}
        for article, label in zip(articles, labels):
            cluster_map.setdefault(int(label), []).append(article)

        narratives: List[NarrativeCluster] = []
        for cluster_id, cluster_articles in cluster_map.items():
            if len(cluster_articles) < min_size:
                continue
            # Pick representative headlines (first 3)
            rep_headlines = [a.title for a in cluster_articles[:3]]
            sentiments = [
                a.sentiment_score for a in cluster_articles if a.sentiment_score is not None
            ]
            avg_sent = float(np.mean(sentiments)) if sentiments else None

            # Extract sector tags from content (simplistic keyword match)
            sector_tags = self._extract_sectors(cluster_articles)

            # Label = first headline truncated
            label = self._generate_label(rep_headlines)

            narratives.append(
                NarrativeCluster(
                    narrative_id=f"nar-{cluster_id}",
                    label=label,
                    sector_tags=sector_tags,
                    article_count=len(cluster_articles),
                    avg_sentiment=round(avg_sent, 3) if avg_sent is not None else None,
                    representative_headlines=rep_headlines,
                    article_ids=[a.id for a in cluster_articles],
                )
            )
        return narratives

    @staticmethod
    def _extract_sectors(articles: List[NewsArticle]) -> List[str]:
        from src.config import SECTORS

        text = " ".join(a.title + " " + (a.content or "") for a in articles).lower()
        found = set()
        for sector, keywords in SECTORS.items():
            if sector.lower() in text or any(k in text for k in keywords):
                found.add(sector)
        return list(found)[:5]

    @staticmethod
    def _generate_label(headlines: List[str]) -> str:
        if not headlines:
            return "Emerging Story"
        first = headlines[0]
        if len(first) > 60:
            return first[:57] + "..."
        return first


_narrative_service: Optional[NarrativeDetectionService] = None


def get_narrative_service() -> NarrativeDetectionService:
    global _narrative_service
    if _narrative_service is None:
        _narrative_service = NarrativeDetectionService()
    return _narrative_service
