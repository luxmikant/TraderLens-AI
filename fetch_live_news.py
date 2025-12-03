"""
Real-Time News Fetcher - Fetches LIVE financial news from RSS feeds
Run: python fetch_live_news.py
"""
import asyncio
import feedparser
import httpx
from datetime import datetime
from typing import List, Dict
import json
import os

# Suppress warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# RSS Feed Sources - REAL Indian Financial News
RSS_FEEDS = {
    "moneycontrol": [
        "https://www.moneycontrol.com/rss/latestnews.xml",
        "https://www.moneycontrol.com/rss/marketreports.xml",
        "https://www.moneycontrol.com/rss/buzzingstocks.xml"
    ],
    "economic_times": [
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    ],
    "business_standard": [
        "https://www.business-standard.com/rss/markets-106.rss",
        "https://www.business-standard.com/rss/companies-101.rss"
    ],
    "livemint": [
        "https://www.livemint.com/rss/markets",
    ],
    "ndtv_profit": [
        "https://feeds.feedburner.com/ndtvprofit-latest"
    ]
}


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
                
                for entry in feed.entries[:10]:  # Get latest 10 per feed
                    article = {
                        "title": entry.get("title", ""),
                        "content": entry.get("summary", entry.get("description", "")),
                        "url": entry.get("link", ""),
                        "source": source,
                        "published_at": entry.get("published", str(datetime.now())),
                        "fetched_at": str(datetime.now())
                    }
                    
                    # Clean HTML from content
                    import re
                    article["content"] = re.sub(r'<[^>]+>', '', article["content"])
                    
                    if article["title"] and len(article["title"]) > 10:
                        articles.append(article)
                        
    except Exception as e:
        print(f"   ⚠️  Error fetching {url}: {str(e)[:50]}")
    
    return articles


async def fetch_all_live_news() -> List[Dict]:
    """Fetch news from all RSS sources"""
    all_articles = []
    
    print("\n" + "=" * 60)
    print("📡 FETCHING LIVE FINANCIAL NEWS")
    print("=" * 60)
    
    tasks = []
    for source, urls in RSS_FEEDS.items():
        for url in urls:
            tasks.append(fetch_rss_feed(url, source))
    
    results = await asyncio.gather(*tasks)
    
    for articles in results:
        all_articles.extend(articles)
    
    # Remove duplicates by URL
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        if article["url"] not in seen_urls:
            seen_urls.add(article["url"])
            unique_articles.append(article)
    
    return unique_articles


async def ingest_to_api(articles: List[Dict]):
    """Send articles to the running API for processing"""
    print("\n📤 INGESTING TO API...")
    
    success_count = 0
    async with httpx.AsyncClient(timeout=60.0) as client:
        for article in articles[:20]:  # Limit to 20 for demo
            try:
                response = await client.post(
                    "http://localhost:8000/ingest",
                    json={
                        "title": article["title"],
                        "content": article["content"],
                        "source": article["source"],
                        "url": article["url"]
                    }
                )
                if response.status_code == 200:
                    success_count += 1
                    result = response.json()
                    dup_status = "🔄 DUPLICATE" if result.get("is_duplicate") else "✅ NEW"
                    print(f"   {dup_status} | {article['title'][:50]}...")
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:30]}")
    
    print(f"\n✅ Successfully ingested {success_count}/{min(20, len(articles))} articles")


async def main():
    print("🚀 Real-Time Financial News Fetcher")
    print("   Fetching from: Moneycontrol, ET, Business Standard, Livemint, NDTV")
    
    # Fetch live news
    articles = await fetch_all_live_news()
    
    print(f"\n📊 FETCHED {len(articles)} UNIQUE ARTICLES")
    print("-" * 60)
    
    # Show sample articles
    print("\n📰 SAMPLE LIVE ARTICLES:")
    for i, article in enumerate(articles[:5]):
        print(f"\n{i+1}. [{article['source'].upper()}]")
        print(f"   Title: {article['title'][:70]}...")
        print(f"   URL: {article['url'][:60]}...")
    
    # Save to file
    output_file = "data/live_news/latest_articles.json"
    os.makedirs("data/live_news", exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved to: {output_file}")
    
    # Ask to ingest to API
    print("\n" + "=" * 60)
    print("Would you like to ingest these to the running API?")
    print("Make sure the API is running: python -m uvicorn src.api.main:app --port 8000")
    print("=" * 60)
    
    try:
        choice = input("\nIngest to API? (y/n): ").strip().lower()
        if choice == 'y':
            await ingest_to_api(articles)
    except:
        print("\n📝 To ingest later, run: python -c \"import asyncio; from fetch_live_news import ingest_to_api; ...\"")
    
    print("\n✅ DONE!")


if __name__ == "__main__":
    asyncio.run(main())
