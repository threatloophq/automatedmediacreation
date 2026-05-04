import os
import logging
import requests
from datetime import datetime, timedelta

log = logging.getLogger(__name__)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

NICHES = ["AI", "Cloud Computing", "Cybersecurity", "DevOps", "Automation"]

NICHE_KEYWORDS = {
    "AI":             ["artificial intelligence", "AI tools 2025", "ChatGPT", "AI agents", "generative AI"],
    "Cloud Computing":["cloud computing", "AWS 2025", "Google Cloud", "Azure", "Kubernetes"],
    "Cybersecurity":  ["cybersecurity", "ethical hacking", "cyber attack 2025", "ransomware", "zero day"],
    "DevOps":         ["DevOps", "CI CD pipeline", "Docker", "Terraform", "platform engineering"],
    "Automation":     ["automation tools", "Python automation", "n8n", "workflow automation", "RPA 2025"],
}

def search_youtube(keyword, max_results=10):
    """Search YouTube by keyword, sorted by view count. Returns list of (title, views, video_id)."""
    if not YOUTUBE_API_KEY:
        log.warning("YOUTUBE_API_KEY not set")
        return []
    try:
        # Step 1: Search for videos
        search_params = {
            "part": "snippet",
            "q": keyword,
            "type": "video",
            "order": "viewCount",
            "publishedAfter": (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "maxResults": max_results,
            "relevanceLanguage": "en",
            "key": YOUTUBE_API_KEY,
        }
        search_r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params=search_params, timeout=10)
        search_r.raise_for_status()
        items = search_r.json().get("items", [])
        if not items:
            return []

        # Step 2: Get view counts for those videos
        video_ids = ",".join([i["id"]["videoId"] for i in items if "videoId" in i.get("id", {})])
        if not video_ids:
            return []

        stats_r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "statistics,snippet", "id": video_ids, "key": YOUTUBE_API_KEY},
            timeout=10)
        stats_r.raise_for_status()
        stats_items = stats_r.json().get("items", [])

        results = []
        for item in stats_items:
            title = item["snippet"]["title"]
            views = int(item["statistics"].get("viewCount", 0))
            vid_id = item["id"]
            results.append((title, views, vid_id))

        # Sort by views descending
        results.sort(key=lambda x: x[1], reverse=True)
        log.info(f"'{keyword}': top result = '{results[0][0]}' ({results[0][1]:,} views)" if results else f"'{keyword}': no results")
        return results

    except Exception as e:
        log.warning(f"YouTube search failed for '{keyword}': {e}")
        return []

def get_top_trends(niche=None):
    """
    Search YouTube across all 5 niches.
    Score each topic by view count.
    Return top 3 hottest topics as video script subjects.
    """
    log.info("Scanning YouTube trends across: AI, Cloud, Cybersecurity, DevOps, Automation")
    all_scored = []

    target = NICHE_KEYWORDS if niche is None else {niche: NICHE_KEYWORDS.get(niche, [niche])}

    for niche_name, keywords in target.items():
        log.info(f"Searching YouTube: [{niche_name}]")
        for kw in keywords[:2]:  # 2 keywords per niche to save quota
            results = search_youtube(kw, max_results=5)
            for title, views, vid_id in results:
                all_scored.append({
                    "title": title,
                    "views": views,
                    "niche": niche_name,
                    "keyword": kw,
                    "url": f"https://youtube.com/watch?v={vid_id}"
                })

    if not all_scored:
        log.warning("No YouTube results — using fallback topics")
        return [
            "Top AI tools you need in 2025",
            "Biggest cybersecurity threats of 2025",
            "DevOps automation tools that save hours"
        ]

    # Sort all results by view count
    all_scored.sort(key=lambda x: x["views"], reverse=True)

    # Log top 5 trending topics
    log.info("Top YouTube trending topics found:")
    for i, item in enumerate(all_scored[:5], 1):
        log.info(f"  {i}. [{item['niche']}] {item['title']} — {item['views']:,} views")

    # Return top 3 titles as script topics
    top_topics = []
    seen_niches = set()
    for item in all_scored:
        # Pick one topic per niche for variety
        if item["niche"] not in seen_niches:
            top_topics.append(f"[{item['niche']}] {item['title']}")
            seen_niches.add(item["niche"])
        if len(top_topics) == 3:
            break

    log.info(f"Selected topics: {top_topics}")
    return top_topics
