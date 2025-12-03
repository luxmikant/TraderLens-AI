"""
Storage Agent - Handles persistence to ChromaDB and PostgreSQL
"""
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from src.database.vector_store import get_vector_store, VectorStore
from src.database.postgres import get_database, Database, NewsArticle, ArticleEntity, StockImpact as StockImpactDB
from src.models.schemas import ProcessedNewsArticle, NewsProcessingState
from src.config import settings


logger = logging.getLogger(__name__)


class StorageAgent:
    """
    Agent responsible for:
    1. Storing embeddings in ChromaDB
    2. Storing structured data in PostgreSQL
    3. Managing data consistency across stores
    """
    
    def __init__(self, vector_store: Optional[VectorStore] = None, database: Optional[Database] = None):
        self.vector_store = vector_store or get_vector_store()
        self.database = database or get_database()
        
        logger.info("StorageAgent initialized")
    
    def store_article(self, article: ProcessedNewsArticle) -> bool:
        """
        Store a processed article in both vector and structured databases.
        
        Args:
            article: Fully processed news article
            
        Returns:
            Success status
        """
        try:
            # 1. Store in ChromaDB (if not duplicate)
            if not article.is_duplicate:
                self._store_in_vector_db(article)
            
            # 2. Store in PostgreSQL
            self._store_in_postgres(article)
            
            logger.debug(f"Stored article: {article.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing article: {e}")
            return False
    
    def _store_in_vector_db(self, article: ProcessedNewsArticle) -> bool:
        """Store article embedding in ChromaDB"""
        try:
            # Prepare content for embedding
            content = f"{article.title}\n\n{article.content}"
            
            # Prepare metadata
            metadata = {
                "source": article.source,
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "cluster_id": article.cluster_id,
                "sentiment_label": article.sentiment_label.value if article.sentiment_label else None,
                "sentiment_score": article.sentiment_score
            }
            
            # Add entity metadata
            if article.entities:
                metadata["companies"] = ",".join([e.value for e in article.entities.companies])
                metadata["sectors"] = ",".join(article.entities.sectors)
                metadata["regulators"] = ",".join([e.value for e in article.entities.regulators])
            
            # Add stock impact metadata
            if article.stock_impacts:
                high_confidence_stocks = [s.ticker_nse for s in article.stock_impacts if s.confidence >= 0.8 and s.ticker_nse]
                metadata["impacted_stocks"] = ",".join(high_confidence_stocks[:10])
            
            # Store in ChromaDB
            success = self.vector_store.add_article(
                article_id=article.id,
                content=content,
                metadata=metadata
            )
            
            if success:
                article.embedding_id = article.id
            
            return success
            
        except Exception as e:
            logger.error(f"Error storing in vector DB: {e}")
            return False
    
    def _store_in_postgres(self, article: ProcessedNewsArticle) -> bool:
        """Store article and related data in PostgreSQL"""
        session = self.database.get_session()
        
        try:
            # Create article record
            db_article = NewsArticle(
                id=article.id,
                title=article.title,
                content=article.content,
                url=article.url,
                source=article.source,
                published_at=article.published_at,
                ingested_at=article.ingested_at,
                is_duplicate=article.is_duplicate,
                cluster_id=article.cluster_id,
                sentiment_score=article.sentiment_score,
                sentiment_label=article.sentiment_label.value if article.sentiment_label else None,
                embedding_id=article.embedding_id
            )
            
            session.add(db_article)
            
            # Store entities
            if article.entities:
                for entity in article.entities.raw_entities:
                    db_entity = ArticleEntity(
                        article_id=article.id,
                        entity_type=entity.entity_type.value,
                        entity_value=entity.value,
                        confidence=entity.confidence
                    )
                    session.add(db_entity)
            
            # Store stock impacts
            for impact in article.stock_impacts:
                db_impact = StockImpactDB(
                    article_id=article.id,
                    symbol=impact.ticker_nse or impact.symbol,
                    confidence=impact.confidence,
                    impact_type=impact.impact_type.value,
                    reasoning=impact.reasoning
                )
                session.add(db_impact)
            
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing in PostgreSQL: {e}")
            return False
        finally:
            session.close()
    
    def get_article(self, article_id: str) -> Optional[ProcessedNewsArticle]:
        """Retrieve article by ID"""
        session = self.database.get_session()
        
        try:
            db_article = session.query(NewsArticle).filter_by(id=article_id).first()
            
            if not db_article:
                return None
            
            # Convert to Pydantic model
            return ProcessedNewsArticle(
                id=db_article.id,
                title=db_article.title,
                content=db_article.content,
                url=db_article.url,
                source=db_article.source,
                published_at=db_article.published_at,
                ingested_at=db_article.ingested_at,
                is_duplicate=db_article.is_duplicate,
                cluster_id=db_article.cluster_id,
                sentiment_score=db_article.sentiment_score
            )
            
        finally:
            session.close()
    
    def get_articles_by_entity(self, entity_type: str, entity_value: str, limit: int = 20) -> list:
        """Get articles mentioning a specific entity"""
        session = self.database.get_session()
        
        try:
            articles = session.query(NewsArticle).join(ArticleEntity).filter(
                ArticleEntity.entity_type == entity_type,
                ArticleEntity.entity_value.ilike(f"%{entity_value}%")
            ).order_by(NewsArticle.published_at.desc()).limit(limit).all()
            
            return [
                ProcessedNewsArticle(
                    id=a.id,
                    title=a.title,
                    content=a.content,
                    url=a.url,
                    source=a.source,
                    published_at=a.published_at,
                    is_duplicate=a.is_duplicate
                )
                for a in articles
            ]
            
        finally:
            session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        session = self.database.get_session()
        
        try:
            # PostgreSQL stats
            total_articles = session.query(NewsArticle).count()
            unique_articles = session.query(NewsArticle).filter_by(is_duplicate=False).count()
            total_entities = session.query(ArticleEntity).count()
            
            # Source breakdown
            from sqlalchemy import func
            source_counts = dict(
                session.query(NewsArticle.source, func.count(NewsArticle.id))
                .group_by(NewsArticle.source)
                .all()
            )
            
            # Vector store stats
            vector_stats = self.vector_store.get_collection_stats()
            
            return {
                "postgres": {
                    "total_articles": total_articles,
                    "unique_articles": unique_articles,
                    "duplicate_articles": total_articles - unique_articles,
                    "total_entities": total_entities,
                    "sources": source_counts
                },
                "chromadb": vector_stats
            }
            
        finally:
            session.close()
    
    # ================== LangGraph Integration ==================
    
    async def process(self, state: NewsProcessingState) -> NewsProcessingState:
        """
        Process state for LangGraph pipeline.
        Store the processed article.
        """
        if state.processed_article:
            success = self.store_article(state.processed_article)
            state.stored = success
        
        return state


# Singleton instance
_storage_agent: Optional[StorageAgent] = None


def get_storage_agent() -> StorageAgent:
    """Get or create storage agent singleton"""
    global _storage_agent
    if _storage_agent is None:
        _storage_agent = StorageAgent()
    return _storage_agent
