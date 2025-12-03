"""User bookmarks and watchlists (localStorage-backed via API).

Provides endpoints for bookmarking articles and tracking "watched"
symbols or sectors. Initial version uses an in-memory store; swap for
Redis or PostgreSQL for persistence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
import threading


@dataclass
class Bookmark:
    article_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WatchlistItem:
    item_type: str  # "symbol" or "sector"
    value: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)


class BookmarkService:
    """In-memory bookmark and watchlist service."""

    def __init__(self):
        self._lock = threading.Lock()
        self._bookmarks: Dict[str, Set[str]] = {}  # user_id -> article_ids
        self._watchlists: Dict[str, List[WatchlistItem]] = {}  # user_id -> items

    # Bookmarks
    def add_bookmark(self, user_id: str, article_id: str) -> bool:
        with self._lock:
            if user_id not in self._bookmarks:
                self._bookmarks[user_id] = set()
            self._bookmarks[user_id].add(article_id)
            return True

    def remove_bookmark(self, user_id: str, article_id: str) -> bool:
        with self._lock:
            if user_id in self._bookmarks:
                self._bookmarks[user_id].discard(article_id)
                return True
            return False

    def get_bookmarks(self, user_id: str) -> List[str]:
        with self._lock:
            return list(self._bookmarks.get(user_id, set()))

    def is_bookmarked(self, user_id: str, article_id: str) -> bool:
        with self._lock:
            return article_id in self._bookmarks.get(user_id, set())

    # Watchlist
    def add_to_watchlist(
        self, user_id: str, item_type: str, value: str
    ) -> WatchlistItem:
        item = WatchlistItem(item_type=item_type, value=value, user_id=user_id)
        with self._lock:
            if user_id not in self._watchlists:
                self._watchlists[user_id] = []
            exists = any(
                w.item_type == item_type and w.value == value
                for w in self._watchlists[user_id]
            )
            if not exists:
                self._watchlists[user_id].append(item)
        return item

    def remove_from_watchlist(
        self, user_id: str, item_type: str, value: str
    ) -> bool:
        with self._lock:
            if user_id not in self._watchlists:
                return False
            initial = len(self._watchlists[user_id])
            self._watchlists[user_id] = [
                w
                for w in self._watchlists[user_id]
                if not (w.item_type == item_type and w.value == value)
            ]
            return len(self._watchlists[user_id]) < initial

    def get_watchlist(self, user_id: str) -> List[WatchlistItem]:
        with self._lock:
            return list(self._watchlists.get(user_id, []))


_bookmark_service: Optional[BookmarkService] = None


def get_bookmark_service() -> BookmarkService:
    global _bookmark_service
    if _bookmark_service is None:
        _bookmark_service = BookmarkService()
    return _bookmark_service
