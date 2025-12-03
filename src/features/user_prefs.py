"""User preferences and bookmarks storage.

Provides lightweight local-first state for user watchlists and saved articles.
Data persists in a JSON file so no auth/db needed during hackathon demo.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

PREFS_FILE = Path("data/user_prefs.json")


@dataclass
class UserBookmark:
    article_id: str
    headline: str
    source: str
    saved_at: str
    notes: Optional[str] = None


@dataclass
class UserPreferences:
    user_id: str = "default"
    followed_sectors: List[str] = field(default_factory=list)
    followed_symbols: List[str] = field(default_factory=list)
    bookmarks: List[UserBookmark] = field(default_factory=list)
    hidden_sources: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class UserPreferencesService:
    """Manages user preferences and bookmarks in a JSON file."""

    def __init__(self, path: Path = PREFS_FILE):
        self.path = path
        self._cache: Dict[str, UserPreferences] = {}
        self._ensure_dir()
        self._load()

    def _ensure_dir(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self):
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text())
                for uid, data in raw.items():
                    bookmarks = [UserBookmark(**b) for b in data.get("bookmarks", [])]
                    data["bookmarks"] = bookmarks
                    self._cache[uid] = UserPreferences(**data)
            except Exception:
                self._cache = {}

    def _save(self):
        raw: Dict[str, dict] = {}
        for uid, prefs in self._cache.items():
            d = asdict(prefs)
            d["bookmarks"] = [asdict(b) for b in prefs.bookmarks]
            raw[uid] = d
        self.path.write_text(json.dumps(raw, indent=2))

    def get(self, user_id: str = "default") -> UserPreferences:
        if user_id not in self._cache:
            self._cache[user_id] = UserPreferences(user_id=user_id)
        return self._cache[user_id]

    def update(self, prefs: UserPreferences):
        prefs.updated_at = datetime.utcnow().isoformat()
        self._cache[prefs.user_id] = prefs
        self._save()

    # -------- Convenience methods --------
    def follow_sector(self, user_id: str, sector: str):
        prefs = self.get(user_id)
        if sector not in prefs.followed_sectors:
            prefs.followed_sectors.append(sector)
            self.update(prefs)

    def unfollow_sector(self, user_id: str, sector: str):
        prefs = self.get(user_id)
        if sector in prefs.followed_sectors:
            prefs.followed_sectors.remove(sector)
            self.update(prefs)

    def follow_symbol(self, user_id: str, symbol: str):
        prefs = self.get(user_id)
        symbol = symbol.upper()
        if symbol not in prefs.followed_symbols:
            prefs.followed_symbols.append(symbol)
            self.update(prefs)

    def unfollow_symbol(self, user_id: str, symbol: str):
        prefs = self.get(user_id)
        symbol = symbol.upper()
        if symbol in prefs.followed_symbols:
            prefs.followed_symbols.remove(symbol)
            self.update(prefs)

    def add_bookmark(
        self,
        user_id: str,
        article_id: str,
        headline: str,
        source: str,
        notes: Optional[str] = None,
    ):
        prefs = self.get(user_id)
        existing_ids = {b.article_id for b in prefs.bookmarks}
        if article_id not in existing_ids:
            prefs.bookmarks.append(
                UserBookmark(
                    article_id=article_id,
                    headline=headline,
                    source=source,
                    saved_at=datetime.utcnow().isoformat(),
                    notes=notes,
                )
            )
            self.update(prefs)

    def remove_bookmark(self, user_id: str, article_id: str):
        prefs = self.get(user_id)
        prefs.bookmarks = [b for b in prefs.bookmarks if b.article_id != article_id]
        self.update(prefs)

    def hide_source(self, user_id: str, source: str):
        prefs = self.get(user_id)
        if source not in prefs.hidden_sources:
            prefs.hidden_sources.append(source)
            self.update(prefs)

    def unhide_source(self, user_id: str, source: str):
        prefs = self.get(user_id)
        if source in prefs.hidden_sources:
            prefs.hidden_sources.remove(source)
            self.update(prefs)


_prefs_service: Optional[UserPreferencesService] = None


def get_user_prefs_service() -> UserPreferencesService:
    global _prefs_service
    if _prefs_service is None:
        _prefs_service = UserPreferencesService()
    return _prefs_service
