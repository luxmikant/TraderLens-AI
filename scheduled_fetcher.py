"""
Scheduled News Fetcher - Runs in background and fetches news every X minutes
Run: python scheduled_fetcher.py
"""
import asyncio
import feedparser
import httpx
from datetime import datetime
from typing import List, Dict
import json
import os
import time

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# Configuration
FETCH_INTERVAL_MINUTES = 5  # Fetch every 5 minutes
API_URL = "http://localhost:8000"

# RSS Feed Sources
RSS_FEEDS = {
    "moneycontrol": [
        "https://www.moneycontrol.com/rss/latestnews.xml",
        "https://www.moneycontrol.com/rss/marketreports.xml",
    ],
    "economic_times": [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    ],
    "business_standard": [
        "https://www.business-standard.com/rss/markets-106.rss",
    ],
    "livemint": [
        "https://www.livemint.com/rss/markets",
    ],
}

# Track seen URLs to avoid re-processing
seen_urls = set()


async def fetch_rss_feed(url: str, source: str) -> List[Dict]:
    """Fetch and parse a single RSS feed"""
    articles = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                
                for entry in feed.entries[:5]:  # Latest 5 per feed
                    url = entry.get("link", "")
                    
                    # Skip if already seen
                    if url in seen_urls:
                        continue
                    
                    seen_urls.add(url)
                    
                    import re
                    content = entry.get("summary", entry.get("description", ""))
                    content = re.sub(r'<[^>]+>', '', content)
                    
                    article = {
                        "title": entry.get("title", ""),
                        "content": content,
                        "url": url,
                        "source": source,
                    }
                    
                    if article["title"] and len(article["title"]) > 10:
                        articles.append(article)
                        
    except Exception as e:
        pass  # Silent fail for scheduled tasks
    
    return articles


async def fetch_and_ingest():
    """Fetch new articles and ingest to API"""
    all_articles = []
    
    # Fetch from all sources
    tasks = []
    for source, urls in RSS_FEEDS.items():
        for url in urls:
            tasks.append(fetch_rss_feed(url, source))
    
    results = await asyncio.gather(*tasks)
    
    for articles in results:
        all_articles.extend(articles)
    
    if not all_articles:
        return 0
    
    # Ingest to API
    success_count = 0
    async with httpx.AsyncClient(timeout=60.0) as client:
        for article in all_articles:
            try:
                response = await client.post(
                    f"{API_URL}/ingest",
                    json=article
                )
                if response.status_code == 200:
                    success_count += 1
                    result = response.json()
                    status = "DUP" if result.get("is_duplicate") else "NEW"
                    print(f"   [{status}] {article['title'][:50]}...")
            except:
                pass
    
    return success_count


async def run_scheduler():
    """Run the scheduled fetcher"""
    print("=" * 60)
    print("📡 REAL-TIME NEWS SCHEDULER")
    print(f"   Fetching every {FETCH_INTERVAL_MINUTES} minutes")
    print(f"   API: {API_URL}")
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    
    cycle = 0
    while True:
        cycle += 1
        now = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n🔄 [{now}] Fetch cycle #{cycle}")
        
        try:
            count = await fetch_and_ingest()
            print(f"   ✅ Ingested {count} new articles")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
        
        # Wait for next cycle
        print(f"   ⏰ Next fetch in {FETCH_INTERVAL_MINUTES} minutes...")
        await asyncio.sleep(FETCH_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        print("\n\n👋 Scheduler stopped")
