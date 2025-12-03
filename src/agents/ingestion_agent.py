"""
News Ingestion Agent - Fetches and normalizes news from RSS feeds and APIs
"""
import feedparser
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging
import asyncio
import re
import html

from src.config import RSS_FEEDS, settings
from src.models.schemas import RawNewsInput, NewsProcessingState
from src.utils.retry import retry_async, RetryConfig, CircuitBreaker, CircuitBreakerConfig, health_checker


logger = logging.getLogger(__name__)


class NewsIngestionAgent:
    """
    Agent responsible for:
    1. Fetching news from RSS feeds
    2. Fetching announcements from NSE/BSE APIs
    3. Normalizing content format
    4. Filtering out irrelevant content
    """
    
    def __init__(self):
        self.rss_feeds = RSS_FEEDS
        self.seen_urls = set()  # Track processed URLs to avoid re-processing
        self.http_client = None

        # Fault tolerance: retry config + circuit breakers per source
        self._retry_cfg = RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=30.0,
            retriable_exceptions=(httpx.HTTPError, httpx.TimeoutException, Exception)
        )
        self._circuit_breakers: dict[str, CircuitBreaker] = {}

        # Register health check
        health_checker.register("ingestion_agent", self._health_check)

    async def _health_check(self) -> bool:
        """Simple health check: ensure HTTP client can be created."""
        try:
            await self._get_client()
            return True
        except Exception:
            return False

    def _get_circuit_breaker(self, source: str) -> CircuitBreaker:
        """Get or create circuit breaker for a source."""
        if source not in self._circuit_breakers:
            self._circuit_breakers[source] = CircuitBreaker(
                name=f"ingestion-{source}",
                config=CircuitBreakerConfig(failure_threshold=3, recovery_timeout=120.0)
            )
        return self._circuit_breakers[source]
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
        return self.http_client
    
    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
    
    # ================== RSS Feed Ingestion ==================
    
    async def fetch_rss_feed(self, url: str, source: str, feed_type: str) -> List[RawNewsInput]:
        """Fetch and parse a single RSS feed with retry & circuit breaker."""
        articles = []
        cb = self._get_circuit_breaker(source)

        async def _do_fetch():
            client = await self._get_client()
            resp = await client.get(url)
            resp.raise_for_status()
            return resp

        try:
            response = await cb.call(
                retry_async, _do_fetch, config=self._retry_cfg
            )
            
            feed = feedparser.parse(response.text)
            
            for entry in feed.entries:
                # Skip if already processed
                if entry.link in self.seen_urls:
                    continue
                
                self.seen_urls.add(entry.link)
                
                # Parse the entry
                article = self._parse_rss_entry(entry, source, feed_type)
                if article:
                    articles.append(article)
            
            logger.info(f"Fetched {len(articles)} new articles from {source}/{feed_type}")
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")
        
        return articles
    
    def _parse_rss_entry(self, entry: Any, source: str, feed_type: str) -> Optional[RawNewsInput]:
        """Parse RSS entry into RawNewsInput"""
        try:
            # Extract title
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            # Extract content
            content = ""
            if hasattr(entry, 'content'):
                content = entry.content[0].get('value', '')
            elif hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description
            
            # Clean HTML from content
            content = self._clean_html(content)
            
            # If content is too short, use title as content
            if len(content) < 50:
                content = title
            
            # Parse publication date
            published_at = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published_at = datetime(*entry.published_parsed[:6])
                except:
                    pass
            
            if not published_at:
                published_at = datetime.now()
            
            return RawNewsInput(
                title=title,
                content=content,
                url=entry.link,
                source=source,
                published_at=published_at,
                metadata={
                    "feed_type": feed_type,
                    "author": entry.get('author', ''),
                    "tags": [tag.term for tag in entry.get('tags', [])] if hasattr(entry, 'tags') else []
                }
            )
            
        except Exception as e:
            logger.error(f"Error parsing RSS entry: {e}")
            return None
    
    async def fetch_all_rss_feeds(self) -> List[RawNewsInput]:
        """Fetch news from all configured RSS feeds"""
        all_articles = []
        tasks = []
        
        for source, feeds in self.rss_feeds.items():
            for feed_type, url in feeds.items():
                tasks.append(self.fetch_rss_feed(url, source, feed_type))
        
        # Fetch all feeds concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Feed fetch error: {result}")
        
        logger.info(f"Total articles fetched from RSS: {len(all_articles)}")
        return all_articles
    
    # ================== NSE Data Ingestion ==================
    
    async def fetch_nse_announcements(self, symbol: Optional[str] = None) -> List[RawNewsInput]:
        """Fetch corporate announcements from NSE"""
        articles = []
        
        try:
            client = await self._get_client()
            
            # First, visit NSE homepage to get cookies
            await client.get("https://www.nseindia.com")
            
            # Fetch announcements
            url = "https://www.nseindia.com/api/corporate-announcements"
            params = {"index": "equities"}
            if symbol:
                params["symbol"] = symbol
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data[:50]:  # Limit to recent 50
                    article = RawNewsInput(
                        title=item.get('desc', 'NSE Announcement'),
                        content=item.get('attchmntText', item.get('desc', '')),
                        url=f"https://www.nseindia.com/companies-listing/corporate-filings-announcements",
                        source="nse",
                        published_at=self._parse_nse_date(item.get('an_dt')),
                        metadata={
                            "symbol": item.get('symbol'),
                            "company": item.get('sm_name'),
                            "announcement_type": item.get('desc')
                        }
                    )
                    articles.append(article)
            
        except Exception as e:
            logger.error(f"Error fetching NSE announcements: {e}")
        
        return articles
    
    async def fetch_nse_board_meetings(self) -> List[RawNewsInput]:
        """Fetch upcoming board meetings from NSE"""
        articles = []
        
        try:
            client = await self._get_client()
            await client.get("https://www.nseindia.com")
            
            url = "https://www.nseindia.com/api/corporate-board-meetings"
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data[:30]:
                    purpose = item.get('bm_purpose', 'Board Meeting')
                    company = item.get('sm_name', '')
                    
                    article = RawNewsInput(
                        title=f"{company}: Board Meeting for {purpose}",
                        content=f"{company} has scheduled a board meeting. Purpose: {purpose}",
                        url="https://www.nseindia.com/companies-listing/corporate-filings-board-meeting",
                        source="nse",
                        published_at=self._parse_nse_date(item.get('bm_date')),
                        metadata={
                            "symbol": item.get('symbol'),
                            "company": company,
                            "meeting_purpose": purpose
                        }
                    )
                    articles.append(article)
        
        except Exception as e:
            logger.error(f"Error fetching NSE board meetings: {e}")
        
        return articles
    
    # ================== BSE Data Ingestion ==================
    
    async def fetch_bse_announcements(self) -> List[RawNewsInput]:
        """Fetch announcements from BSE"""
        articles = []
        
        try:
            client = await self._get_client()
            
            # BSE API endpoint
            url = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
            params = {
                "strCat": "-1",
                "strPrevDate": datetime.now().strftime("%Y%m%d"),
                "strScrip": "",
                "strSearch": "P",
                "strToDate": datetime.now().strftime("%Y%m%d"),
                "strType": "C"
            }
            
            response = await client.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, dict) and 'Table' in data:
                    for item in data['Table'][:50]:
                        article = RawNewsInput(
                            title=item.get('NEWSSUB', 'BSE Announcement'),
                            content=item.get('HEADLINE', item.get('NEWSSUB', '')),
                            url=f"https://www.bseindia.com/",
                            source="bse",
                            published_at=self._parse_bse_date(item.get('NEWS_DT')),
                            metadata={
                                "scrip_code": item.get('SCRIP_CD'),
                                "company": item.get('SLONGNAME')
                            }
                        )
                        articles.append(article)
        
        except Exception as e:
            logger.error(f"Error fetching BSE announcements: {e}")
        
        return articles
    
    # ================== Content Processing ==================
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags and clean text"""
        if not text:
            return ""
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Remove HTML tags
        soup = BeautifulSoup(text, 'html.parser')
        text = soup.get_text(separator=' ')
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _parse_nse_date(self, date_str: str) -> datetime:
        """Parse NSE date format"""
        if not date_str:
            return datetime.now()
        
        try:
            # NSE uses format: "01-Dec-2025" or similar
            for fmt in ["%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except:
                    continue
        except:
            pass
        
        return datetime.now()
    
    def _parse_bse_date(self, date_str: str) -> datetime:
        """Parse BSE date format"""
        if not date_str:
            return datetime.now()
        
        try:
            # BSE uses various formats
            for fmt in ["%d %b %Y", "%Y-%m-%d", "%d/%m/%Y"]:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except:
                    continue
        except:
            pass
        
        return datetime.now()
    
    def normalize_article(self, article: RawNewsInput) -> RawNewsInput:
        """Normalize article content"""
        # Clean title
        article.title = self._clean_html(article.title)
        
        # Clean content
        article.content = self._clean_html(article.content)
        
        # Ensure minimum content
        if len(article.content) < 20:
            article.content = article.title
        
        return article
    
    # ================== LangGraph Integration ==================
    
    async def process(self, state: NewsProcessingState) -> NewsProcessingState:
        """Process state for LangGraph pipeline"""
        # Normalize the raw news
        normalized = self.normalize_article(state.raw_news)
        state.normalized_content = f"{normalized.title}\n\n{normalized.content}"
        
        return state
    
    async def ingest_batch(self) -> List[RawNewsInput]:
        """
        Main ingestion method - fetch from all sources.
        Called by scheduler or manually.
        """
        all_articles = []
        
        # Fetch RSS feeds
        rss_articles = await self.fetch_all_rss_feeds()
        all_articles.extend(rss_articles)
        
        # Fetch NSE data
        try:
            nse_announcements = await self.fetch_nse_announcements()
            all_articles.extend(nse_announcements)
            
            nse_meetings = await self.fetch_nse_board_meetings()
            all_articles.extend(nse_meetings)
        except Exception as e:
            logger.warning(f"NSE fetch failed: {e}")
        
        # Fetch BSE data
        try:
            bse_announcements = await self.fetch_bse_announcements()
            all_articles.extend(bse_announcements)
        except Exception as e:
            logger.warning(f"BSE fetch failed: {e}")
        
        # Normalize all articles
        all_articles = [self.normalize_article(a) for a in all_articles]
        
        logger.info(f"Total ingested articles: {len(all_articles)}")
        return all_articles


# Singleton instance
_ingestion_agent: Optional[NewsIngestionAgent] = None


def get_ingestion_agent() -> NewsIngestionAgent:
    """Get or create ingestion agent singleton"""
    global _ingestion_agent
    if _ingestion_agent is None:
        _ingestion_agent = NewsIngestionAgent()
    return _ingestion_agent
