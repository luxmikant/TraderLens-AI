"""
Caching utilities for performance optimization.
Includes LRU cache for embeddings and query results.
"""
from functools import lru_cache
from typing import Dict, List, Tuple, Optional, Any
import hashlib
import time
import threading


class EmbeddingCache:
    """
    Thread-safe LRU cache for embeddings.
    Avoids re-computing embeddings for repeated queries.
    """
    
    def __init__(self, maxsize: int = 1000, ttl_seconds: int = 3600):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[List[float], float]] = {}
        self._lock = threading.Lock()
        self._access_order: List[str] = []
    
    def _hash_text(self, text: str) -> str:
        """Create hash key for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding if exists and not expired"""
        key = self._hash_text(text)
        
        with self._lock:
            if key in self._cache:
                embedding, timestamp = self._cache[key]
                
                # Check TTL
                if time.time() - timestamp < self.ttl_seconds:
                    # Move to end of access order (most recently used)
                    if key in self._access_order:
                        self._access_order.remove(key)
                    self._access_order.append(key)
                    return embedding
                else:
                    # Expired, remove
                    del self._cache[key]
                    if key in self._access_order:
                        self._access_order.remove(key)
        
        return None
    
    def set(self, text: str, embedding: List[float]) -> None:
        """Cache an embedding"""
        key = self._hash_text(text)
        
        with self._lock:
            # Evict oldest if at capacity
            while len(self._cache) >= self.maxsize and self._access_order:
                oldest_key = self._access_order.pop(0)
                if oldest_key in self._cache:
                    del self._cache[oldest_key]
            
            # Add new entry
            self._cache[key] = (embedding, time.time())
            self._access_order.append(key)
    
    def clear(self) -> None:
        """Clear the cache"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                "size": len(self._cache),
                "maxsize": self.maxsize,
                "ttl_seconds": self.ttl_seconds
            }


class QueryResultCache:
    """
    Cache for query results to avoid repeated searches.
    Shorter TTL since news freshness matters.
    """
    
    def __init__(self, maxsize: int = 100, ttl_seconds: int = 300):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
    
    def _make_key(self, query: str, limit: int, include_sector: bool) -> str:
        """Create cache key from query parameters"""
        key_str = f"{query.lower().strip()}|{limit}|{include_sector}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, query: str, limit: int = 10, include_sector: bool = True) -> Optional[Any]:
        """Get cached query result if exists and fresh"""
        key = self._make_key(query, limit, include_sector)
        
        with self._lock:
            if key in self._cache:
                result, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    return result
                else:
                    del self._cache[key]
        
        return None
    
    def set(self, query: str, result: Any, limit: int = 10, include_sector: bool = True) -> None:
        """Cache a query result"""
        key = self._make_key(query, limit, include_sector)
        
        with self._lock:
            # Simple eviction: remove oldest when full
            if len(self._cache) >= self.maxsize:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            
            self._cache[key] = (result, time.time())
    
    def invalidate(self) -> None:
        """Invalidate all cached results"""
        with self._lock:
            self._cache.clear()


# Global cache instances
_embedding_cache: Optional[EmbeddingCache] = None
_query_cache: Optional[QueryResultCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """Get or create embedding cache singleton"""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache(maxsize=2000, ttl_seconds=7200)  # 2 hour TTL
    return _embedding_cache


def get_query_cache() -> QueryResultCache:
    """Get or create query result cache singleton"""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryResultCache(maxsize=200, ttl_seconds=300)  # 5 min TTL
    return _query_cache
