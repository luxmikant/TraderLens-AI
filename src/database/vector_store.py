"""
ChromaDB Vector Store for semantic similarity and RAG
"""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Optional, Tuple, Any
import logging
from datetime import datetime
import json
import os

# Disable TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

from src.config import settings
from src.utils.cache import get_embedding_cache


logger = logging.getLogger(__name__)


def get_embedding_model():
    """Lazy load embedding model to avoid TF import issues"""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(settings.embedding_model)


class VectorStore:
    """
    ChromaDB-based vector store for financial news embeddings.
    
    Supports:
    - Semantic similarity search for deduplication
    - RAG-based retrieval for queries
    - Metadata filtering (source, sector, timestamp)
    - Hybrid search (vector + metadata)
    """
    
    def __init__(self, persist_dir: Optional[str] = None):
        """Initialize ChromaDB and embedding model"""
        self.persist_dir = persist_dir if persist_dir is not None else settings.chroma_persist_dir
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Initialize embedding model (lazy load)
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        self.embedding_model = get_embedding_model()
        self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
        
        # Create/get collections
        self._init_collections()
        
        logger.info(f"VectorStore initialized with {self.embedding_dimension}-dim embeddings")
    
    def _init_collections(self):
        """Initialize ChromaDB collections"""
        # Main news collection
        self.news_collection = self.client.get_or_create_collection(
            name="financial_news",
            metadata={
                "hnsw:space": "cosine",  # Use cosine similarity
                "description": "Financial news articles for RAG"
            }
        )
        
        # Query cache collection (optional optimization)
        self.query_cache = self.client.get_or_create_collection(
            name="query_cache",
            metadata={"hnsw:space": "cosine"}
        )
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text with caching"""
        # Check cache first
        cache = get_embedding_cache()
        cached = cache.get(text)
        if cached is not None:
            return cached
        
        # Generate and cache
        embedding = self.embedding_model.encode(text, convert_to_numpy=True).tolist()
        cache.set(text, embedding)
        return embedding
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts with caching"""
        cache = get_embedding_cache()
        results = []
        texts_to_compute = []
        indices_to_compute = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            cached = cache.get(text)
            if cached is not None:
                results.append(cached)
            else:
                results.append(None)  # Placeholder
                texts_to_compute.append(text)
                indices_to_compute.append(i)
        
        # Batch compute missing embeddings
        if texts_to_compute:
            computed = self.embedding_model.encode(texts_to_compute, convert_to_numpy=True).tolist()
            for idx, text, embedding in zip(indices_to_compute, texts_to_compute, computed):
                results[idx] = embedding
                cache.set(text, embedding)
        
        return results
    
    # ================== Deduplication Methods ==================
    
    def check_duplicate(
        self, 
        text: str, 
        threshold: Optional[float] = None
    ) -> Tuple[bool, Optional[str], float]:
        """
        Check if text is duplicate of existing article.
        
        Args:
            text: Article text to check
            threshold: Similarity threshold (default from settings)
            
        Returns:
            (is_duplicate, cluster_id, similarity_score)
        """
        effective_threshold = threshold if threshold is not None else settings.dedup_threshold
        
        # Generate embedding
        embedding = self.generate_embedding(text)
        
        # Search for similar articles
        results = self.news_collection.query(
            query_embeddings=[embedding],
            n_results=5,
            include=["metadatas", "distances", "documents"]
        )
        
        if not results['ids'][0]:
            return False, None, 0.0
        
        # ChromaDB with cosine returns distance = 1 - similarity
        # So similarity = 1 - distance
        min_distance = min(results['distances'][0])
        similarity = 1 - min_distance
        
        if similarity >= effective_threshold:
            # It's a duplicate
            cluster_id = results['metadatas'][0][0].get('cluster_id')
            return True, cluster_id, similarity
        
        return False, None, similarity
    
    def find_similar_articles(
        self, 
        text: str, 
        n_results: int = 10,
        threshold: float = 0.5
    ) -> List[Dict]:
        """Find articles similar to given text"""
        embedding = self.generate_embedding(text)
        
        results = self.news_collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["metadatas", "distances", "documents"]
        )
        
        similar = []
        for i, (id_, dist, meta, doc) in enumerate(zip(
            results['ids'][0],
            results['distances'][0],
            results['metadatas'][0],
            results['documents'][0]
        )):
            similarity = 1 - dist
            if similarity >= threshold:
                similar.append({
                    "id": id_,
                    "similarity": similarity,
                    "metadata": meta,
                    "content": doc
                })
        
        return similar
    
    # ================== Storage Methods ==================
    
    def add_article(
        self,
        article_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Add article to vector store.
        
        Args:
            article_id: Unique article ID
            content: Article text (title + content)
            metadata: Article metadata (source, sector, entities, etc.)
            
        Returns:
            Success status
        """
        try:
            # Clean metadata - ChromaDB only accepts str, int, float, bool
            clean_metadata = self._clean_metadata(metadata)
            
            # Generate embedding
            embedding = self.generate_embedding(content)
            
            # Add to collection
            self.news_collection.add(
                ids=[article_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[clean_metadata]
            )
            
            logger.debug(f"Added article {article_id} to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error adding article to vector store: {e}")
            return False
    
    def update_article(
        self,
        article_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update existing article in vector store"""
        try:
            update_kwargs: Dict[str, Any] = {"ids": [article_id]}
            
            if content:
                embedding = self.generate_embedding(content)
                update_kwargs["embeddings"] = [embedding]
                update_kwargs["documents"] = [content]
            
            if metadata:
                update_kwargs["metadatas"] = [self._clean_metadata(metadata)]
            
            self.news_collection.update(**update_kwargs)
            return True
            
        except Exception as e:
            logger.error(f"Error updating article: {e}")
            return False
    
    def delete_article(self, article_id: str) -> bool:
        """Delete article from vector store"""
        try:
            self.news_collection.delete(ids=[article_id])
            return True
        except Exception as e:
            logger.error(f"Error deleting article: {e}")
            return False
    
    # ================== Query Methods ==================
    
    def semantic_search(
        self,
        query: str,
        n_results: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict]:
        """
        Semantic search for articles matching query.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filters: Metadata filters (e.g., {"source": "moneycontrol"})
            
        Returns:
            List of matching articles with scores
        """
        embedding = self.generate_embedding(query)
        
        query_kwargs = {
            "query_embeddings": [embedding],
            "n_results": n_results,
            "include": ["metadatas", "distances", "documents"]
        }
        
        # Add metadata filters if provided
        if filters:
            where_clause = self._build_where_clause(filters)
            if where_clause:
                query_kwargs["where"] = where_clause
        
        results = self.news_collection.query(**query_kwargs)
        
        search_results = []
        for i, (id_, dist, meta, doc) in enumerate(zip(
            results['ids'][0],
            results['distances'][0],
            results['metadatas'][0],
            results['documents'][0]
        )):
            search_results.append({
                "id": id_,
                "score": 1 - dist,  # Convert distance to similarity
                "metadata": meta,
                "content": doc
            })
        
        return search_results
    
    def hybrid_search(
        self,
        query: str,
        entity_filter: Optional[List[str]] = None,
        sector_filter: Optional[List[str]] = None,
        source_filter: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        n_results: int = 10
    ) -> List[Dict]:
        """
        Hybrid search combining semantic similarity with metadata filters.
        
        This is the main query method that supports context-aware retrieval.
        """
        filters = {}
        
        # Note: ChromaDB doesn't support $contains, so we use semantic search
        # for entity matching and only use exact filters for sector/source
        
        if sector_filter:
            if len(sector_filter) == 1:
                filters["sector"] = {"$eq": sector_filter[0]}
            else:
                filters["sector"] = {"$in": sector_filter}
        
        if source_filter:
            if len(source_filter) == 1:
                filters["source"] = {"$eq": source_filter[0]}
            else:
                filters["source"] = {"$in": source_filter}
        
        # Get semantic search results
        results = self.semantic_search(query, n_results * 2, filters if filters else None)
        
        # Post-filter by entity if specified (since ChromaDB doesn't support $contains)
        if entity_filter:
            filtered_results = []
            for r in results:
                companies_str = r.get("metadata", {}).get("companies", "")
                # Check if any entity filter matches
                if any(entity.lower() in companies_str.lower() for entity in entity_filter):
                    filtered_results.append(r)
            return filtered_results[:n_results]
        
        return results[:n_results]
    
    def get_by_entity(
        self,
        entity_type: str,
        entity_value: str,
        n_results: int = 20
    ) -> List[Dict]:
        """Get all articles mentioning a specific entity"""
        # Use semantic search with entity value as query
        # Then post-filter by metadata since ChromaDB doesn't support $contains
        embedding = self.generate_embedding(entity_value)
        
        results = self.news_collection.query(
            query_embeddings=[embedding],
            n_results=n_results * 2,  # Get more to filter
            include=["metadatas", "documents", "distances"]
        )
        
        if not results['ids'][0]:
            return []
        
        # Post-filter by entity type
        filtered = []
        for id_, dist, meta, doc in zip(
            results['ids'][0],
            results['distances'][0],
            results['metadatas'][0],
            results['documents'][0]
        ):
            match = False
            if entity_type == "company":
                companies_str = meta.get("companies", "")
                match = entity_value.lower() in companies_str.lower()
            elif entity_type == "sector":
                match = meta.get("sector", "").lower() == entity_value.lower()
            elif entity_type == "regulator":
                regulators_str = meta.get("regulators", "")
                match = entity_value.lower() in regulators_str.lower()
            else:
                # For unknown types, include all semantic matches
                match = True
            
            if match:
                filtered.append({
                    "id": id_,
                    "score": 1 - dist,
                    "metadata": meta,
                    "content": doc
                })
        
        return filtered[:n_results]
    
    # ================== Utility Methods ==================
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Clean metadata for ChromaDB compatibility"""
        clean = {}
        for key, value in metadata.items():
            if value is None:
                continue
            elif isinstance(value, (str, int, float, bool)):
                clean[key] = value
            elif isinstance(value, list):
                # Convert list to comma-separated string
                clean[key] = ",".join(str(v) for v in value)
            elif isinstance(value, datetime):
                clean[key] = value.isoformat()
            elif isinstance(value, dict):
                clean[key] = json.dumps(value)
            else:
                clean[key] = str(value)
        return clean
    
    def _build_where_clause(self, filters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build ChromaDB where clause from filters"""
        if not filters:
            return None
        
        conditions = []
        for key, value in filters.items():
            if isinstance(value, dict):
                conditions.append({key: value})
            else:
                conditions.append({key: {"$eq": value}})
        
        if len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}
    
    def get_collection_stats(self) -> Dict:
        """Get statistics about the vector store"""
        count = self.news_collection.count()
        
        # Get sample to analyze sources
        sample = self.news_collection.get(limit=min(count, 1000), include=["metadatas"])
        
        sources = {}
        sectors = {}
        
        for meta in sample['metadatas']:
            source = meta.get('source', 'unknown')
            sources[source] = sources.get(source, 0) + 1
            
            sector = meta.get('sector', 'unknown')
            sectors[sector] = sectors.get(sector, 0) + 1
        
        return {
            "total_articles": count,
            "embedding_dimension": self.embedding_dimension,
            "sources": sources,
            "sectors": sectors
        }
    
    def reset(self):
        """Reset all collections (use with caution!)"""
        self.client.delete_collection("financial_news")
        self.client.delete_collection("query_cache")
        self._init_collections()
        logger.warning("Vector store reset complete")


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create vector store singleton"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
