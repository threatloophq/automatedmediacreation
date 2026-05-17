import os
import logging
import requests
import feedparser
from datetime import datetime, timedelta

log = logging.getLogger(__name__)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

NEWS_FEEDS = {
    "AI": [
        "https://feeds.feedburner.com/venturebeat/SZYF",
        "https://techcrunch.com/feed/",
        "https://www.artificialintelligence-news.com/feed/",
    ],
    "Cloud": [
        "https://techcrunch.com/feed/",
        "https://www.theregister.com/cloud/feed/",
        "https://thenewstack.io/feed/",
    ],
    "Cybersecurity": [
        "https://feeds.feedburner.com/TheHackersNews",
        "https://www.bleepingcomputer.com/feed/",
        "https://krebsonsecurity.com/feed/",
    ],
    "DevOps": [
        "https://devops.com/feed/",
        "https://thenewstack.io/feed/",
        "https://feeds.feedburner.com/dzone/devops",
    ],
    "Automation": [
        "https://feeds.feedburner.com/venturebeat/SZYF",
        "https://thenewstack.io/feed/",
        "https://techcrunch.com/feed/",
    ],
}

NICHE_KEYWORDS = {
    "AI":            ["ai", "artificial intelligence", "machine learning", "gpt", "llm", "openai", "gemini", "claude"],
    "Cloud":         ["cloud", "aws", "azure", "google cloud", "kubernetes", "serverless"],
    "Cybersecurity": ["hack", "cyber", "security", "breach", "malware", "ransomware", "vulnerability"],
    "DevOps":        ["devops", "docker", "kubernetes", "ci/cd", "terraform", "pipeline"],
    "Automation":    ["automat", "rpa", "workflow", "no-code", "n8n", "zapier", "agent"],
}

YOUTUBE_KEYWORDS = {
    "AI":            ["AI news 2025", "artificial intelligence latest"],
    "Cloud":         ["cloud computing news 2025", "AWS Google Cloud news"],
    "Cybersecurity": ["cybersecurity news 2025", "latest cyber attack"],
    "DevOps":        ["DevOps news 2025", "Kubernetes Docker latest"],
    "Automation":    ["automation news 2025", "AI automation tools"],
}

def fetch_rss_news(niche):
    articles = []
    feeds = NEWS_FEEDS.get(niche, [])
    keywords = NICHE_KEYWORDS.get(niche, [niche.lower()])

    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:8]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", "")[:300]
                link    = entry.get("link", "")
                text    = (title + " " + summary).lower()
                if any(kw in text for kw in keywords):
                    articles.append({
                        "title":   title,
                        "summary": summary,
                        "link":    link,
                        "niche":   niche,
                        "source":  feed.feed.get("title", "RSS"),
                    })
            log.info(f"[{niche}] RSS {feed_url}: {len(feed.entries)} entries")
        except Exception as e:
            log.warning(f"RSS failed [{niche}] {feed_url}: {e}")
    return articles

def fetch_youtube_news(niche):
    if not YOUTUBE_API_KEY:
        log.warning(f"YOUTUBE_API_KEY not set — skipping YouTube for [{niche}]")
        return []
    results = []
    for keyword in YOUTUBE_KEYWORDS.get(niche, [])[:2]:
        try:
            params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "date",
                "publishedAfter": (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "maxResults": 5,
                "relevanceLanguage": "en",
                "key": YOUTUBE_API_KEY,
            }
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params, timeout=10)
            r.raise_for_status()
            for item in r.json().get("items", []):
                results.append({
                    "title":   item["snippet"]["title"],
                    "summary": item["snippet"]["description"][:200],
                    "niche":   niche,
                    "source":  "YouTube",
                })
            log.info(f"[{niche}] YouTube '{keyword}': {len(results)} results")
        except Exception as e:
            log.warning(f"YouTube failed [{niche}] '{keyword}': {e}")
    return results

def get_top_trends(niche=None):
    pillars = ["AI", "Cloud", "Cybersecurity", "DevOps", "Automation"]
    targets = [niche] if niche else pillars

    all_articles = []
    for pillar in targets:
        log.info(f"Fetching latest news: [{pillar}]")
        rss = fetch_rss_news(pillar)
        yt  = fetch_youtube_news(pillar)
        combined = rss + yt
        all_articles += combined
        log.info(f"[{pillar}]: {len(combined)} articles found")

    if not all_articles:
        log.warning("No news found — using fallback topics")
        return [
            ("Top AI tools revolutionising work in 2025", ""),
            ("Biggest cybersecurity breach you missed this week", ""),
            ("DevOps tools that are changing software delivery in 2025", ""),
        ]

    # Pick top 3 — one per pillar for variety
    seen = set()
    top = []
    for article in all_articles:
        if article["niche"] not in seen:
            top.append((article["title"], article.get("summary", "")))
            seen.add(article["niche"])
        if len(top) == 3:
            break

    # Fill remaining slots if needed
    for article in all_articles:
        if len(top) >= 3:
            break
        entry = (article["title"], article.get("summary", ""))
        if entry not in top:
            top.append(entry)

    log.info(f"Selected topics: {[t[0] for t in top]}")
    return top
