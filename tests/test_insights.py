"""Unit tests for new standout features."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# ---- Impact Score ----
def test_impact_score_direction():
    from src.features.impact_index import ImpactIndexService

    assert ImpactIndexService._direction(0.2) == "bullish"
    assert ImpactIndexService._direction(-0.3) == "bearish"
    assert ImpactIndexService._direction(0.0) == "neutral"
    assert ImpactIndexService._direction(None) == "neutral"


def test_impact_score_recency_decay():
    from src.features.impact_index import ImpactIndexService, _ArticleSnapshot

    service = ImpactIndexService.__new__(ImpactIndexService)

    mock_article_recent = MagicMock()
    mock_article_recent.sentiment_score = 0.5
    mock_article_recent.published_at = datetime.utcnow()
    mock_article_recent.ingested_at = datetime.utcnow()
    mock_article_recent.source = "moneycontrol"
    mock_article_recent.cluster_id = None

    mock_article_old = MagicMock()
    mock_article_old.sentiment_score = 0.5
    mock_article_old.published_at = datetime.utcnow() - timedelta(hours=24)
    mock_article_old.ingested_at = datetime.utcnow() - timedelta(hours=24)
    mock_article_old.source = "moneycontrol"
    mock_article_old.cluster_id = None

    snap_recent = _ArticleSnapshot(article=mock_article_recent, sectors=[], symbols=[])
    snap_old = _ArticleSnapshot(article=mock_article_old, sectors=[], symbols=[])

    comp_recent = service._calculate_components(snap_recent)
    comp_old = service._calculate_components(snap_old)

    assert comp_recent.recency > comp_old.recency


# ---- Attention Heatmap ----
def test_attention_score_static():
    from src.features.attention_heatmap import MarketAttentionService

    score = MarketAttentionService._attention_score(10, 5)
    assert 50 < score <= 100

    score_low = MarketAttentionService._attention_score(2, 10)
    assert score_low < 50

    score_zero = MarketAttentionService._attention_score(10, 0)
    assert score_zero == 100.0


# ---- Narrative Detection ----
def test_narrative_label_truncation():
    from src.features.narrative_detection import NarrativeDetectionService

    long_headline = "A" * 100
    label = NarrativeDetectionService._generate_label([long_headline])
    assert len(label) <= 60


def test_narrative_label_empty():
    from src.features.narrative_detection import NarrativeDetectionService

    label = NarrativeDetectionService._generate_label([])
    assert label == "Emerging Story"


def test_narrative_extract_sectors():
    from src.features.narrative_detection import NarrativeDetectionService

    mock_article = MagicMock()
    mock_article.title = "HDFC Bank sees surge in deposits"
    mock_article.content = "Banking sector growth continues as credit demand picks up"

    sectors = NarrativeDetectionService._extract_sectors([mock_article])
    assert "Banking" in sectors


# ---- User Preferences ----
def test_user_prefs_follow_sector():
    from src.features.user_prefs import UserPreferencesService
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        service = UserPreferencesService(Path(tmpdir) / "prefs.json")
        service.follow_sector("test_user", "Banking")
        prefs = service.get("test_user")
        assert "Banking" in prefs.followed_sectors

        service.unfollow_sector("test_user", "Banking")
        prefs = service.get("test_user")
        assert "Banking" not in prefs.followed_sectors


def test_user_prefs_bookmarks():
    from src.features.user_prefs import UserPreferencesService
    from pathlib import Path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        service = UserPreferencesService(Path(tmpdir) / "prefs.json")
        service.add_bookmark("test_user", "art123", "Test Headline", "moneycontrol")
        prefs = service.get("test_user")
        assert len(prefs.bookmarks) == 1
        assert prefs.bookmarks[0].article_id == "art123"

        service.remove_bookmark("test_user", "art123")
        prefs = service.get("test_user")
        assert len(prefs.bookmarks) == 0
