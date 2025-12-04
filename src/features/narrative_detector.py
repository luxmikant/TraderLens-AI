"""Narrative detection via headline clustering.

Groups recent news into coherent narratives (themes) such as "Rate Cut Hopes",
"Banking NPA Fears", etc. This lets traders see the big story driving many
small items, similar to daily.dev's curated macro radar.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import hashlib

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.postgres import (
    get_database,
    Database,
    NewsArticle,
    ArticleEntity,
)
from src.database.vector_store import get_vector_store
from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NarrativeCluster:
    """Single narrative cluster."""

    cluster_id: str
    label: str
    summary: str
    article_count: int
    avg_sentiment: Optional[float]
    sectors: List[str]
    top_articles: List[Dict]
    first_seen: datetime
    last_seen: datetime


class NarrativeDetector:
    """Detects thematic narratives from recent news using simple clustering."""

    SIMILARITY_THRESHOLD = 0.72

    def __init__(
        self,
        database: Optional[Database] = None,
    ):
        self.database = database or get_database()
        self.vector_store = get_vector_store()

    def detect_narratives(
        self,
        window_hours: int = 48,
        min_cluster_size: int = 3,
        max_narratives: int = 8,
    ) -> List[NarrativeCluster]:
        """Detect narratives from recent articles via greedy clustering."""
        session = self.database.get_session()
        try:
            now = datetime.utcnow()
            start = now - timedelta(hours=window_hours)

            articles = (
                session.query(NewsArticle)
                .filter(
                    NewsArticle.published_at >= start,
                    NewsArticle.is_duplicate == False,
                )
                .order_by(NewsArticle.published_at.desc())
                .limit(200)
                .all()
            )

            if not articles:
                return []

            texts = [f"{a.title} {a.content[:300]}" for a in articles]
            embeddings = self.vector_store.generate_embeddings(texts)

            clusters = self._greedy_cluster(embeddings)

            narratives: List[NarrativeCluster] = []
            for member_indices in clusters:
                if len(member_indices) < min_cluster_size:
                    continue

                cluster_articles = [articles[i] for i in member_indices]
                label, summary = self._generate_label(cluster_articles)
                article_ids = [a.id for a in cluster_articles]

                sector_rows = (
                    session.query(ArticleEntity.entity_value)
                    .filter(
                        ArticleEntity.article_id.in_(article_ids),
                        ArticleEntity.entity_type == "sector",
                    )
                    .distinct()
                    .all()
                )
                sectors = [row[0] for row in sector_rows]

                sentiments = [
                    a.sentiment_score for a in cluster_articles if a.sentiment_score is not None
                ]
                avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else None

                top_articles = [
                    {
                        "id": a.id,
                        "title": a.title,
                        "source": a.source,
                        "published_at": a.published_at.isoformat() if a.published_at else None,
                    }
                    for a in cluster_articles[:5]
                ]

                first_seen = min(a.published_at or a.ingested_at for a in cluster_articles)
                last_seen = max(a.published_at or a.ingested_at for a in cluster_articles)

                cluster_id = hashlib.md5(label.encode()).hexdigest()[:12]

                narratives.append(
                    NarrativeCluster(
                        cluster_id=cluster_id,
                        label=label,
                        summary=summary,
                        article_count=len(cluster_articles),
                        avg_sentiment=round(avg_sentiment, 3) if avg_sentiment is not None else None,
                        sectors=sectors,
                        top_articles=top_articles,
                        first_seen=first_seen,
                        last_seen=last_seen,
                    )
                )

            narratives.sort(key=lambda n: n.article_count, reverse=True)
            return narratives[:max_narratives]

        finally:
            session.close()

    def _greedy_cluster(
        self, embeddings: List[List[float]]
    ) -> List[List[int]]:
        """Simple greedy clustering for headline embeddings."""
        import numpy as np

        if not embeddings:
            return []

        emb_matrix = np.array(embeddings)
        norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        normalized = emb_matrix / norms

        n = len(embeddings)
        assigned = [False] * n
        clusters: List[List[int]] = []

        for i in range(n):
            if assigned[i]:
                continue
            cluster = [i]
            assigned[i] = True
            centroid = normalized[i]

            for j in range(i + 1, n):
                if assigned[j]:
                    continue
                sim = float(np.dot(centroid, normalized[j]))
                if sim >= self.SIMILARITY_THRESHOLD:
                    cluster.append(j)
                    assigned[j] = True
                    centroid = np.mean(normalized[cluster], axis=0)
                    centroid /= np.linalg.norm(centroid) or 1

            clusters.append(cluster)

        return clusters

    def _generate_label(self, articles: List[NewsArticle]) -> Tuple[str, str]:
        """Generate cluster label and summary from top headlines."""
        titles = [a.title for a in articles[:5]]
        combined = " | ".join(titles)

        keywords: Dict[str, int] = {}
        for title in titles:
            for word in title.split():
                word_clean = word.strip(".,!?\"'()").lower()
                if len(word_clean) > 3:
                    keywords[word_clean] = keywords.get(word_clean, 0) + 1

        top_words = sorted(keywords.items(), key=lambda kv: kv[1], reverse=True)[:4]
        label = " ".join(w.capitalize() for w, _ in top_words) if top_words else "Market Update"

        summary = combined[:280]

        return label, summary


_detector: Optional[NarrativeDetector] = None


def get_narrative_detector() -> NarrativeDetector:
    global _detector
    if _detector is None:
        _detector = NarrativeDetector()
    return _detector
