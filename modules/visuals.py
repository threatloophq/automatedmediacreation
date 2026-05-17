import os
import re
import time
import logging
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

log = logging.getLogger(__name__)
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
OUTPUT_DIR = "output/images"

# Direct mapping of common visual cue phrases to proven Pexels search terms
CUE_MAP = {
    "shocked": "person shocked laptop",
    "laptop": "person laptop working",
    "empty desk": "empty office desk",
    "office": "modern office workspace",
    "developer coding": "developer coding computer",
    "coding": "programmer coding screen",
    "software": "software developer coding",
    "business meeting": "business meeting team",
    "meeting": "professional business meeting",
    "server room": "server room data center",
    "server": "server data center rack",
    "technician": "IT technician server room",
    "hacker": "hacker dark computer",
    "cybersecurity": "cybersecurity network security",
    "cyber": "cyber security computer",
    "smartphone": "person using smartphone",
    "phone": "person smartphone technology",
    "robot": "industrial robot arm",
    "automation": "factory automation robot",
    "ai": "artificial intelligence technology",
    "artificial intelligence": "AI technology brain",
    "cloud": "cloud computing server",
    "data": "data analytics screen",
    "network": "computer network infrastructure",
    "breach": "data breach security alert",
    "malware": "computer virus malware",
    "ransomware": "ransomware cyber attack",
    "kubernetes": "software developer coding",
    "docker": "developer coding container",
    "devops": "software development team",
    "pipeline": "software deployment coding",
    "aws": "cloud computing data center",
    "azure": "cloud computing server room",
    "executive": "business executive meeting",
    "CEO": "business leader executive",
    "startup": "startup team working",
    "investment": "business investment finance",
    "revenue": "business growth chart",
    "security": "cybersecurity lock screen",
    "firewall": "network firewall security",
    "encryption": "data encryption security",
    "vulnerability": "hacker exploiting computer",
    "manufacturing": "manufacturing factory robot",
    "healthcare": "doctor using computer tablet",
    "finance": "financial analyst computer",
    "education": "student using laptop",
    "retail": "retail store technology",
    "supply chain": "warehouse logistics technology",
}

def get_visuals(script, topic):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Clear old images
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith((".jpg", ".png")):
            os.remove(os.path.join(OUTPUT_DIR, f))

    # Parse script into sections
    sections = parse_script_sections(script)
    log.info(f"Sections: {len(sections)}")

    # Build precise query for each section
    queries = []
    for section in sections:
        query = build_precise_query(section["cue"], section["text"], topic)
        queries.append({"query": query, "label": section["label"]})
        log.info(f"[{section['label']}] '{section['cue']}' → '{query}'")

    # Pad to 8
    topic_queries = get_topic_fallbacks(topic)
    while len(queries) < 8:
        queries.append({"query": topic_queries[len(queries) % len(topic_queries)], "label": "extra"})
    queries = queries[:8]

    paths = []
    used_ids = set()

    for i, item in enumerate(queries):
        path = f"{OUTPUT_DIR}/img_{i:02d}.jpg"
        query = item["query"]
        log.info(f"Fetching {i+1}/8: '{query}'")

        img = (
            fetch_pexels(query, used_ids) or
            fetch_pexels(query.split()[0] + " " + query.split()[-1] if len(query.split()) > 1 else query, used_ids) or
            fetch_unsplash(query, i) or
            fetch_picsum(i)
        )

        if img:
            img.convert("RGB").resize((1080, 1920), Image.LANCZOS).save(path, "JPEG", quality=92)
            paths.append(path)
            log.info(f"Saved img_{i:02d}.jpg")

        time.sleep(0.3)

    log.info(f"Total: {len(paths)} images")
    return paths


def build_precise_query(cue, text, topic):
    """Build a precise 2-3 word Pexels search query from visual cue."""
    cue_lower = cue.lower()

    # Check direct CUE_MAP matches first
    for keyword, mapped_query in CUE_MAP.items():
        if keyword in cue_lower:
            return mapped_query

    # Clean the cue — remove stop words and keep nouns
    stop_words = {
        "with", "and", "the", "at", "on", "in", "of", "a", "an",
        "looking", "showing", "displaying", "featuring", "using",
        "close", "shot", "view", "scene", "image", "photo",
        "animated", "animation", "overlay", "split", "screen",
        "flashing", "countdown", "logo", "icon", "button"
    }
    words = cue_lower.split()
    clean_words = [w for w in words if w not in stop_words and len(w) > 2]

    if len(clean_words) >= 2:
        return " ".join(clean_words[:3])

    # Fall back to topic-based query
    return get_topic_fallbacks(topic)[0]


def get_topic_fallbacks(topic):
    """Get reliable fallback queries based on topic."""
    topic_lower = topic.lower()
    if any(w in topic_lower for w in ["ai", "artificial", "machine", "gpt", "llm"]):
        return [
            "artificial intelligence robot",
            "machine learning data",
            "developer coding AI",
            "technology innovation future",
            "computer neural network",
            "data scientist working",
            "tech startup team",
            "digital transformation business",
        ]
    elif any(w in topic_lower for w in ["cyber", "hack", "security", "breach", "malware"]):
        return [
            "hacker dark computer",
            "cybersecurity network",
            "data breach security",
            "network firewall protection",
            "encrypted data security",
            "IT security professional",
            "cyber attack prevention",
            "secure server room",
        ]
    elif any(w in topic_lower for w in ["cloud", "aws", "azure", "kubernetes"]):
        return [
            "cloud computing server",
            "data center infrastructure",
            "server room technology",
            "network cloud storage",
            "IT infrastructure modern",
            "developer cloud platform",
            "technology data processing",
            "computing network modern",
        ]
    elif any(w in topic_lower for w in ["devops", "docker", "pipeline", "deploy"]):
        return [
            "software developer coding",
            "development team collaboration",
            "programmer computer screen",
            "agile development team",
            "code deployment server",
            "software engineering team",
            "developer laptop coding",
            "technology startup coding",
        ]
    elif any(w in topic_lower for w in ["automat", "rpa", "workflow", "robot"]):
        return [
            "industrial robot automation",
            "factory automation modern",
            "robotic process technology",
            "workflow automation business",
            "smart manufacturing robot",
            "automated production line",
            "technology efficiency work",
            "digital automation process",
        ]
    else:
        return [
            "technology innovation",
            "business digital transformation",
            "modern tech office",
            "developer working laptop",
            "data analytics dashboard",
            "professional team technology",
            "smart technology future",
            "digital business solution",
        ]


def parse_script_sections(script):
    sections = []
    lines = script.splitlines()
    current_label = "INTRO"
    current_cue = ""
    current_text = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        label_match = re.match(
            r'^\[(HOOK|NEWS|POINT\s*\d+|CTA|INTRO|OUTRO)\]',
            line, re.IGNORECASE)
        if label_match:
            if current_text:
                sections.append({
                    "label": current_label,
                    "cue": current_cue,
                    "text": " ".join(current_text),
                })
            current_label = label_match.group(1).upper()
            current_cue = ""
            current_text = []
            continue

        cue_match = re.search(r'\[VISUAL CUE:\s*(.+?)\]', line, re.IGNORECASE)
        if cue_match:
            current_cue = cue_match.group(1).strip()
            remaining = re.sub(r'\[VISUAL CUE:[^\]]*\]', '', line).strip()
            if remaining:
                current_text.append(re.sub(r'\*+', '', remaining).strip())
            continue

        clean = re.sub(r'\[.*?\]', '', line).strip()
        clean = re.sub(r'\*+', '', clean).strip()
        if clean:
            current_text.append(clean)

    if current_text:
        sections.append({
            "label": current_label,
            "cue": current_cue,
            "text": " ".join(current_text),
        })

    return sections


def fetch_pexels(query, used_ids):
    if not PEXELS_API_KEY:
        return None
    try:
        for page in range(1, 4):
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": 5,
                        "page": page, "orientation": "portrait"},
                timeout=10)
            r.raise_for_status()
            for photo in r.json().get("photos", []):
                if photo["id"] not in used_ids:
                    used_ids.add(photo["id"])
                    img_data = requests.get(
                        photo["src"]["large2x"], timeout=15).content
                    return Image.open(BytesIO(img_data))
    except Exception as e:
        log.warning(f"Pexels failed '{query}': {e}")
    return None


def fetch_unsplash(query, seed=0):
    try:
        simple = "+".join(query.split()[:2])
        url = f"https://source.unsplash.com/1080x1920/?{simple}&sig={seed+300}"
        r = requests.get(url, timeout=15, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            return Image.open(BytesIO(r.content))
    except Exception as e:
        log.warning(f"Unsplash failed '{query}': {e}")
    return None


def fetch_picsum(seed=0):
    try:
        url = f"https://picsum.photos/seed/{seed * 53 + 400}/1080/1920"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content))
    except Exception as e:
        log.warning(f"Picsum failed: {e}")
    return None
