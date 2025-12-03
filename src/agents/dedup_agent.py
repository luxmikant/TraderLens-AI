"""
Deduplication Agent - Detects and consolidates duplicate news articles
"""
from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime
import uuid

from src.database.vector_store import get_vector_store, VectorStore
from src.models.schemas import (
    RawNewsInput, ProcessedNewsArticle, NewsCluster, 
    NewsProcessingState
)
from src.config import settings


logger = logging.getLogger(__name__)


class DeduplicationAgent:
    """
    Agent responsible for:
    1. Detecting semantic duplicates using vector similarity
    2. Managing duplicate clusters
    3. Consolidating duplicate articles into single stories
    
    Target: ≥95% accuracy on duplicate detection
    """
    
    def __init__(self, vector_store: Optional[VectorStore] = None, threshold: Optional[float] = None):
        self.vector_store = vector_store or get_vector_store()
        self.threshold = threshold or settings.dedup_threshold
        
        # In-memory cluster tracking (for fast lookups)
        self.clusters: Dict[str, NewsCluster] = {}
        
        logger.info(f"DeduplicationAgent initialized with threshold: {self.threshold}")
    
    def check_duplicate(self, content: str) -> Tuple[bool, Optional[str], float]:
        """
        Check if content is a duplicate of existing article.
        
        Args:
            content: Article content (title + text)
            
        Returns:
            (is_duplicate, cluster_id, similarity_score)
        """
        return self.vector_store.check_duplicate(content, self.threshold)
    
    def find_similar(self, content: str, n_results: int = 5) -> List[Dict]:
        """
        Find articles similar to given content.
        
        Args:
            content: Article content
            n_results: Number of similar articles to return
            
        Returns:
            List of similar articles with similarity scores
        """
        return self.vector_store.find_similar_articles(content, n_results, self.threshold * 0.7)
    
    def create_cluster(self, article: ProcessedNewsArticle) -> str:
        """
        Create a new cluster for a unique article.
        
        Args:
            article: The first/primary article in the cluster
            
        Returns:
            cluster_id
        """
        cluster_id = str(uuid.uuid4())
        
        cluster = NewsCluster(
            cluster_id=cluster_id,
            primary_article=article,
            duplicate_articles=[],
            sources=[article.source],
            first_seen=article.ingested_at,
            last_updated=article.ingested_at
        )
        
        self.clusters[cluster_id] = cluster
        
        logger.debug(f"Created new cluster: {cluster_id}")
        return cluster_id
    
    def add_to_cluster(self, cluster_id: str, article: ProcessedNewsArticle) -> bool:
        """
        Add a duplicate article to an existing cluster.
        
        Args:
            cluster_id: ID of the cluster
            article: Duplicate article to add
            
        Returns:
            Success status
        """
        if cluster_id not in self.clusters:
            logger.warning(f"Cluster {cluster_id} not found")
            return False
        
        cluster = self.clusters[cluster_id]
        cluster.duplicate_articles.append(article)
        cluster.sources.append(article.source)
        cluster.sources = list(set(cluster.sources))  # Dedupe sources
        cluster.last_updated = datetime.now()
        
        logger.debug(f"Added article to cluster {cluster_id}, total: {len(cluster.duplicate_articles) + 1}")
        return True
    
    def get_cluster(self, cluster_id: str) -> Optional[NewsCluster]:
        """Get cluster by ID"""
        return self.clusters.get(cluster_id)
    
    def consolidate_cluster(self, cluster_id: str) -> Optional[ProcessedNewsArticle]:
        """
        Consolidate all articles in a cluster into a single representative article.
        
        Uses the most comprehensive article as the base and merges metadata.
        
        Args:
            cluster_id: ID of the cluster to consolidate
            
        Returns:
            Consolidated article
        """
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return None
        
        all_articles = [cluster.primary_article] + cluster.duplicate_articles
        
        # Select the article with most content as primary
        primary = max(all_articles, key=lambda a: len(a.content))
        
        # Merge information from all articles
        all_sources = list(set(a.source for a in all_articles))
        all_urls = [a.url for a in all_articles if a.url]
        
        # Merge entities from all articles
        all_companies = []
        all_sectors = set()
        
        for article in all_articles:
            if article.entities:
                all_companies.extend([e.value for e in article.entities.companies])
                all_sectors.update(article.entities.sectors)
        
        # Create consolidated article
        consolidated = ProcessedNewsArticle(
            id=primary.id,
            title=primary.title,
            content=primary.content,
            url=primary.url,
            source=primary.source,
            published_at=min(a.published_at or a.ingested_at for a in all_articles),
            ingested_at=cluster.first_seen,
            is_duplicate=False,
            cluster_id=cluster_id,
            duplicate_sources=all_sources,
            entities=primary.entities,
            stock_impacts=primary.stock_impacts
        )
        
        return consolidated
    
    def get_cluster_stats(self) -> Dict:
        """Get statistics about current clusters"""
        total_clusters = len(self.clusters)
        total_duplicates = sum(len(c.duplicate_articles) for c in self.clusters.values())
        
        source_counts = {}
        for cluster in self.clusters.values():
            for source in cluster.sources:
                source_counts[source] = source_counts.get(source, 0) + 1
        
        return {
            "total_clusters": total_clusters,
            "total_duplicates": total_duplicates,
            "unique_stories": total_clusters,
            "total_articles": total_clusters + total_duplicates,
            "dedup_rate": total_duplicates / (total_clusters + total_duplicates) if total_clusters > 0 else 0,
            "sources": source_counts
        }
    
    # ================== LangGraph Integration ==================
    
    async def process(self, state: NewsProcessingState) -> NewsProcessingState:
        """
        Process state for LangGraph pipeline.
        
        This is the main entry point when used in the LangGraph workflow.
        """
        content = state.normalized_content or f"{state.raw_news.title}\n\n{state.raw_news.content}"
        
        # Check for duplicate
        is_duplicate, cluster_id, similarity = self.check_duplicate(content)
        
        state.is_duplicate = is_duplicate
        state.duplicate_cluster_id = cluster_id
        
        if is_duplicate:
            logger.info(f"Duplicate detected (similarity: {similarity:.3f}), cluster: {cluster_id}")
        else:
            logger.debug(f"Unique article (max similarity: {similarity:.3f})")
        
        return state
    
    def process_article(self, article: RawNewsInput) -> Tuple[bool, Optional[str], ProcessedNewsArticle]:
        """
        Full processing of a single article.
        
        Args:
            article: Raw news article
            
        Returns:
            (is_duplicate, cluster_id, processed_article)
        """
        content = f"{article.title}\n\n{article.content}"
        
        # Check for duplicate
        is_duplicate, cluster_id, similarity = self.check_duplicate(content)
        
        # Create processed article
        processed = ProcessedNewsArticle(
            title=article.title,
            content=article.content,
            url=article.url,
            source=article.source,
            published_at=article.published_at,
            is_duplicate=is_duplicate,
            cluster_id=cluster_id
        )
        
        if is_duplicate and cluster_id:
            # Add to existing cluster
            self.add_to_cluster(cluster_id, processed)
        else:
            # Create new cluster
            new_cluster_id = self.create_cluster(processed)
            processed.cluster_id = new_cluster_id
            cluster_id = new_cluster_id
        
        return is_duplicate, cluster_id, processed
    
    def batch_process(self, articles: List[RawNewsInput]) -> Dict:
        """
        Process a batch of articles.
        
        Args:
            articles: List of raw news articles
            
        Returns:
            Processing statistics
        """
        unique_count = 0
        duplicate_count = 0
        processed_articles = []
        
        for article in articles:
            is_dup, cluster_id, processed = self.process_article(article)
            
            if is_dup:
                duplicate_count += 1
            else:
                unique_count += 1
            
            processed_articles.append(processed)
        
        return {
            "total_processed": len(articles),
            "unique": unique_count,
            "duplicates": duplicate_count,
            "dedup_rate": duplicate_count / len(articles) if articles else 0,
            "articles": processed_articles
        }


# ================== Example Usage ==================

def demonstrate_deduplication():
    """
    Demonstrate the deduplication capability with example articles.
    """
    agent = DeduplicationAgent()
    
    # Example articles (same event, different wording)
    articles = [
        RawNewsInput(
            title="RBI increases repo rate by 25 basis points to combat inflation",
            content="The Reserve Bank of India raised the key policy rate by 25 basis points...",
            source="moneycontrol",
            published_at=datetime.now()
        ),
        RawNewsInput(
            title="Reserve Bank hikes interest rates by 0.25% in surprise move",
            content="In a surprise decision, RBI Governor announced a 25 bps increase...",
            source="economic_times",
            published_at=datetime.now()
        ),
        RawNewsInput(
            title="Central bank raises policy rate 25bps, signals hawkish stance",
            content="The central bank increased the repo rate by 25 basis points...",
            source="business_standard",
            published_at=datetime.now()
        ),
        RawNewsInput(
            title="HDFC Bank announces 15% dividend, board approves buyback",
            content="HDFC Bank declared a 15% dividend for shareholders...",
            source="livemint",
            published_at=datetime.now()
        )
    ]
    
    result = agent.batch_process(articles)
    
    print(f"Processed {result['total_processed']} articles:")
    print(f"  - Unique stories: {result['unique']}")
    print(f"  - Duplicates detected: {result['duplicates']}")
    print(f"  - Deduplication rate: {result['dedup_rate']:.1%}")
    
    return result


# Singleton instance
_dedup_agent: Optional[DeduplicationAgent] = None


def get_dedup_agent() -> DeduplicationAgent:
    """Get or create deduplication agent singleton"""
    global _dedup_agent
    if _dedup_agent is None:
        _dedup_agent = DeduplicationAgent()
    return _dedup_agent
