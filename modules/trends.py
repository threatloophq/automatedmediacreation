import os
import logging
import feedparser
import requests
from pytrends.request import TrendReq

log = logging.getLogger(__name__)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

def fetch_google_trends(niche):
    try:
        pt = TrendReq(hl="en-US", tz=330)
        pt.build_payload([niche], timeframe="now 1-d", geo="US")
        related = pt.related_queries()
        top = related.get(niche, {}).get("top")
        if top is not None and not top.empty:
            return top["query"].head(5).tolist()
    except Exception as e:
        log.warning(f"Google Trends failed: {e}")
    return []

def fetch_youtube_trending(niche):
    if not YOUTUBE_API_KEY:
        return []
    try:
        url = (f"https://www.googleapis.com/youtube/v3/videos"
               f"?part=snippet&chart=mostPopular&regionCode=US"
               f"&videoCategoryId=28&maxResults=10&key={YOUTUBE_API_KEY}")
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return [i["snippet"]["title"] for i in resp.json().get("items", [])[:5]]
    except Exception as e:
        log.warning(f"YouTube trending failed: {e}")
    return []

def fetch_reddit_trends(niche):
    subs = {"cybersecurity": ["cybersecurity", "netsec"],
            "ai": ["artificial", "MachineLearning"],
            "tech": ["technology", "programming"]}.get(niche, ["technology"])
    titles = []
    for sub in subs:
        try:
            feed = feedparser.parse(f"https://www.reddit.com/r/{sub}/hot.rss",
                                    request_headers={"User-Agent": "AIContentBot/1.0"})
            titles += [e.title for e in feed.entries[:5]]
        except Exception as e:
            log.warning(f"Reddit failed for r/{sub}: {e}")
    return titles

def get_top_trends(niche="cybersecurity"):
    log.info(f"Fetching trends for: {niche}")
    all_topics = fetch_google_trends(niche) + fetch_youtube_trending(niche) + fetch_reddit_trends(niche)
    if not all_topics:
        return [f"Top {niche} threats you need to know in 2025"]
    from collections import Counter
    scores = Counter()
    for t in all_topics:
        scores[" ".join(t.lower().split()[:4])] += 1
    return [t for t, _ in scores.most_common(3)]
