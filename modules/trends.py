import os
import random
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
        "https://thenewstack.io/feed/",
        "https://techcrunch.com/feed/",
        "https://www.theregister.com/cloud/feed/",
    ],
    "Cybersecurity": [
        "https://feeds.feedburner.com/TheHackersNews",
        "https://www.bleepingcomputer.com/feed/",
        "https://krebsonsecurity.com/feed/",
    ],
    "DevOps": [
        "https://devops.com/feed/",
        "https://thenewstack.io/feed/",
        "https://techcrunch.com/feed/",
    ],
    "Automation": [
        "https://feeds.feedburner.com/venturebeat/SZYF",
        "https://thenewstack.io/feed/",
        "https://techcrunch.com/feed/",
    ],
}

NICHE_KEYWORDS = {
    "AI":            ["ai", "artificial intelligence", "machine learning",
                      "gpt", "llm", "openai", "gemini", "claude", "chatgpt"],
    "Cloud":         ["cloud", "aws", "azure", "google cloud",
                      "kubernetes", "serverless", "saas", "infrastructure"],
    "Cybersecurity": ["hack", "cyber", "security", "breach",
                      "malware", "ransomware", "vulnerability", "exploit"],
    "DevOps":        ["devops", "docker", "kubernetes", "ci/cd",
                      "terraform", "pipeline", "deployment", "gitops"],
    "Automation":    ["automat", "rpa", "workflow", "no-code",
                      "n8n", "zapier", "agent", "agentic"],
}

# Strict YouTube keywords that won't return music/entertainment videos
YOUTUBE_KEYWORDS = {
    "AI":            ["AI enterprise tools 2025", "OpenAI GPT news"],
    "Cloud":         ["AWS cloud infrastructure 2025", "Kubernetes enterprise"],
    "Cybersecurity": ["cybersecurity breach 2025", "ransomware attack news"],
    "DevOps":        ["DevOps platform engineering 2025", "CI CD pipeline tools"],
    "Automation":    ["enterprise automation RPA 2025", "AI workflow automation"],
}

def fetch_rss_news(niche):
    articles = []
    keywords = NICHE_KEYWORDS.get(niche, [niche.lower()])
    for feed_url in NEWS_FEEDS.get(niche, []):
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", "")[:300]
                text    = (title + " " + summary).lower()
                if any(kw in text for kw in keywords):
                    articles.append({
                        "title":   title,
                        "summary": summary,
                        "niche":   niche,
                        "source":  "RSS",
                    })
        except Exception as e:
            log.warning(f"RSS failed [{niche}] {feed_url}: {e}")
    return articles

def fetch_youtube_news(niche):
    """Only use YouTube for niches where it gives good tech results."""
    if not YOUTUBE_API_KEY:
        return []
    # Skip YouTube search for niches that return irrelevant results
    if niche in ["Cloud", "DevOps"]:
        return []
    results = []
    keywords = NICHE_KEYWORDS.get(niche, [])
    for keyword in YOUTUBE_KEYWORDS.get(niche, [])[:2]:
        try:
            params = {
                "part": "snippet",
                "q": keyword,
                "type": "video",
                "order": "date",
                "publishedAfter": (datetime.utcnow() - timedelta(days=7)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"),
                "maxResults": 10,
                "relevanceLanguage": "en",
                "key": YOUTUBE_API_KEY,
            }
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params, timeout=10)
            r.raise_for_status()
            for item in r.json().get("items", []):
                title   = item["snippet"]["title"]
                summary = item["snippet"]["description"][:200]
                # Filter out non-tech results
                if any(kw in (title + summary).lower() for kw in keywords):
                    results.append({
                        "title":   title,
                        "summary": summary,
                        "niche":   niche,
                        "source":  "YouTube",
                    })
        except Exception as e:
            log.warning(f"YouTube failed [{niche}]: {e}")
    return results

def get_top_trends(niche=None):
    pillars = ["AI", "Cloud", "Cybersecurity", "DevOps", "Automation"]
    targets = [niche] if niche else pillars

    all_articles = []
    for pillar in targets:
        log.info(f"Fetching news: [{pillar}]")
        rss = fetch_rss_news(pillar)
        yt  = fetch_youtube_news(pillar)
        combined = rss + yt
        all_articles += combined
        log.info(f"[{pillar}]: {len(combined)} articles")

    if not all_articles:
        fallbacks = {
            "AI":            "OpenAI releases new model that changes everything",
            "Cloud":         "AWS outage hits major enterprises worldwide",
            "Cybersecurity": "Critical zero-day vulnerability found in major software",
            "DevOps":        "Kubernetes 2.0 changes how teams deploy software",
            "Automation":    "AI agents are replacing entire workflows in 2025",
        }
        target = niche or "AI"
        return [(fallbacks.get(target, f"Latest {target} news 2025"), "")]

    # Shuffle for variety on repeated runs
    random.shuffle(all_articles)

    # Pick top 3 — one per pillar
    seen, top = set(), []
    for a in all_articles:
        if a["niche"] not in seen:
            top.append((a["title"], a.get("summary", "")))
            seen.add(a["niche"])
        if len(top) == 3:
            break

    # Fill remaining
    for a in all_articles:
        if len(top) >= 3: break
        entry = (a["title"], a.get("summary", ""))
        if entry not in top:
            top.append(entry)

    log.info(f"Topics: {[t[0][:50] for t in top]}")
    return top
