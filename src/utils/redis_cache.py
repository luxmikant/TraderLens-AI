"""
Redis-based caching for production scalability.
Falls back to in-memory cache if Redis is unavailable.
"""
import os
import json
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod
import time

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract cache backend interface"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    def clear(self, pattern: str = "*") -> int:
        pass
    
    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        pass


class RedisCache(CacheBackend):
    """
    Redis-based cache for production deployment.
    
    Features:
    - Distributed caching across instances
    - Automatic TTL expiration
    - JSON serialization for complex objects
    - Connection pooling
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        password: str = None,
        db: int = 0,
        prefix: str = "tradl:"
    ):
        self.prefix = prefix
        self.redis_client = None
        
        try:
            import redis
            
            self.redis_client = redis.Redis(
                host=host or os.getenv("REDIS_HOST", "localhost"),
                port=port or int(os.getenv("REDIS_PORT", "6379")),
                password=password or os.getenv("REDIS_PASSWORD"),
                db=db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis cache connected: {host}:{port}")
            
        except ImportError:
            logger.warning("redis package not installed. Run: pip install redis")
            self.redis_client = None
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to memory cache.")
            self.redis_client = None
    
    @property
    def is_available(self) -> bool:
        """Check if Redis is connected"""
        if self.redis_client is None:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key"""
        return f"{self.prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if not self.is_available:
            return None
        
        try:
            full_key = self._make_key(key)
            value = self.redis_client.get(full_key)
            
            if value is None:
                return None
            
            return json.loads(value)
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in Redis with TTL"""
        if not self.is_available:
            return False
        
        try:
            full_key = self._make_key(key)
            serialized = json.dumps(value)
            self.redis_client.setex(full_key, ttl, serialized)
            return True
            
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a key"""
        if not self.is_available:
            return False
        
        try:
            full_key = self._make_key(key)
            self.redis_client.delete(full_key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def clear(self, pattern: str = "*") -> int:
        """Clear keys matching pattern"""
        if not self.is_available:
            return 0
        
        try:
            full_pattern = self._make_key(pattern)
            keys = self.redis_client.keys(full_pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return 0
    
    def stats(self) -> Dict[str, Any]:
        """Get Redis stats"""
        if not self.is_available:
            return {"backend": "redis", "status": "disconnected"}
        
        try:
            info = self.redis_client.info()
            keys_count = len(self.redis_client.keys(self._make_key("*")))
            
            return {
                "backend": "redis",
                "status": "connected",
                "keys": keys_count,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "uptime_days": info.get("uptime_in_days", 0)
            }
        except Exception as e:
            return {"backend": "redis", "status": "error", "error": str(e)}


class MemoryCache(CacheBackend):
    """
    In-memory cache fallback when Redis is unavailable.
    Thread-safe with TTL support.
    """
    
    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self._cache: Dict[str, Tuple[Any, float, int]] = {}  # key -> (value, timestamp, ttl)
        import threading
        self._lock = threading.Lock()
    
    def _is_expired(self, key: str) -> bool:
        """Check if key is expired"""
        if key not in self._cache:
            return True
        _, timestamp, ttl = self._cache[key]
        return time.time() - timestamp > ttl
    
    def _evict_expired(self):
        """Remove expired entries"""
        expired = [k for k in self._cache if self._is_expired(k)]
        for k in expired:
            del self._cache[k]
    
    def _evict_lru(self):
        """Evict least recently used entries"""
        while len(self._cache) >= self.maxsize:
            # Find oldest entry
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
            del self._cache[oldest_key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        with self._lock:
            if key in self._cache and not self._is_expired(key):
                value, _, ttl = self._cache[key]
                # Update timestamp (touch)
                self._cache[key] = (value, time.time(), ttl)
                return value
            elif key in self._cache:
                del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in memory cache"""
        with self._lock:
            self._evict_expired()
            self._evict_lru()
            self._cache[key] = (value, time.time(), ttl)
            return True
    
    def delete(self, key: str) -> bool:
        """Delete a key"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self, pattern: str = "*") -> int:
        """Clear all keys (pattern ignored for memory cache)"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    def stats(self) -> Dict[str, Any]:
        """Get memory cache stats"""
        with self._lock:
            self._evict_expired()
            return {
                "backend": "memory",
                "status": "active",
                "keys": len(self._cache),
                "maxsize": self.maxsize
            }


class HybridCache:
    """
    Hybrid cache that uses Redis when available, falls back to memory.
    Provides unified interface for caching operations.
    """
    
    def __init__(self, redis_config: Optional[Dict] = None, memory_maxsize: int = 1000):
        self.redis_cache = RedisCache(**(redis_config or {}))
        self.memory_cache = MemoryCache(maxsize=memory_maxsize)
        
        # Choose backend
        if self.redis_cache.is_available:
            self.primary = self.redis_cache
            self.backend_name = "redis"
            logger.info("Using Redis as primary cache")
        else:
            self.primary = self.memory_cache
            self.backend_name = "memory"
            logger.info("Using in-memory cache (Redis unavailable)")
    
    def get(self, key: str) -> Optional[Any]:
        """Get from primary cache"""
        return self.primary.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set in primary cache"""
        return self.primary.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete from primary cache"""
        return self.primary.delete(key)
    
    def clear(self, pattern: str = "*") -> int:
        """Clear keys matching pattern"""
        return self.primary.clear(pattern)
    
    def stats(self) -> Dict[str, Any]:
        """Get cache stats"""
        return self.primary.stats()


# ================== Specialized Caches ==================

class EmbeddingCacheRedis:
    """
    Redis-backed embedding cache for production.
    """
    
    def __init__(self, ttl_seconds: int = 7200):
        self.cache = HybridCache()
        self.ttl = ttl_seconds
        self.prefix = "emb:"
    
    def _hash_text(self, text: str) -> str:
        """Create hash key for text"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding"""
        key = f"{self.prefix}{self._hash_text(text)}"
        return self.cache.get(key)
    
    def set(self, text: str, embedding: List[float]) -> None:
        """Cache an embedding"""
        key = f"{self.prefix}{self._hash_text(text)}"
        self.cache.set(key, embedding, self.ttl)
    
    def clear(self) -> None:
        """Clear all embeddings"""
        self.cache.clear(f"{self.prefix}*")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        base_stats = self.cache.stats()
        base_stats["cache_type"] = "embedding"
        base_stats["ttl_seconds"] = self.ttl
        return base_stats


class QueryCacheRedis:
    """
    Redis-backed query result cache for production.
    """
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache = HybridCache()
        self.ttl = ttl_seconds
        self.prefix = "query:"
    
    def _make_key(self, query: str, limit: int, include_sector: bool) -> str:
        """Create cache key from query parameters"""
        key_str = f"{query.lower().strip()}|{limit}|{include_sector}"
        return f"{self.prefix}{hashlib.md5(key_str.encode()).hexdigest()}"
    
    def get(self, query: str, limit: int = 10, include_sector: bool = True) -> Optional[Any]:
        """Get cached query result"""
        key = self._make_key(query, limit, include_sector)
        return self.cache.get(key)
    
    def set(self, query: str, result: Any, limit: int = 10, include_sector: bool = True) -> None:
        """Cache a query result"""
        key = self._make_key(query, limit, include_sector)
        self.cache.set(key, result, self.ttl)
    
    def invalidate(self) -> None:
        """Invalidate all cached results"""
        self.cache.clear(f"{self.prefix}*")
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        base_stats = self.cache.stats()
        base_stats["cache_type"] = "query"
        base_stats["ttl_seconds"] = self.ttl
        return base_stats


# ================== Global Instances ==================

_embedding_cache: Optional[EmbeddingCacheRedis] = None
_query_cache: Optional[QueryCacheRedis] = None


def get_embedding_cache() -> EmbeddingCacheRedis:
    """Get or create embedding cache singleton"""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCacheRedis(ttl_seconds=7200)
    return _embedding_cache


def get_query_cache() -> QueryCacheRedis:
    """Get or create query cache singleton"""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCacheRedis(ttl_seconds=300)
    return _query_cache
