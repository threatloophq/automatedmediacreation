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

# Simple tech-focused search terms as fallback
FALLBACK_QUERIES = [
    "technology", "computer", "artificial intelligence",
    "cybersecurity", "cloud", "data", "network",
    "programming", "digital", "innovation"
]

def get_visuals(script, topic):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Clear old images
    for f in os.listdir(OUTPUT_DIR):
        if f.endswith((".jpg", ".png")):
            os.remove(os.path.join(OUTPUT_DIR, f))

    cues = extract_visual_cues(script)
    log.info(f"Visual cues found: {len(cues)}")

    # Always ensure 8 queries
    queries = cues[:8]
    while len(queries) < 8:
        queries.append(FALLBACK_QUERIES[len(queries) % len(FALLBACK_QUERIES)])

    paths = []
    used_ids = set()

    for i, query in enumerate(queries):
        path = f"{OUTPUT_DIR}/img_{i:02d}.jpg"
        log.info(f"Fetching image {i+1}/8: '{query[:40]}'")

        img = None

        # Try Pexels first
        img = fetch_pexels(query, used_ids)

        # Try Unsplash (no key needed)
        if not img:
            img = fetch_unsplash(query, i)

        # Try Picsum (always works — random tech images)
        if not img:
            img = fetch_picsum(i)

        # Last resort — generate solid color placeholder
        if not img:
            img = generate_placeholder(query, i)

        img.convert("RGB").resize((1080, 1920), Image.LANCZOS).save(path, "JPEG", quality=92)
        paths.append(path)
        log.info(f"Image {i+1} saved: {path}")

        time.sleep(0.3)  # small delay to avoid rate limits

    log.info(f"Total images: {len(paths)}")
    return paths

def extract_visual_cues(script):
    return [c.strip() for c in re.findall(r'\[VISUAL CUE:\s*(.+?)\]', script, re.IGNORECASE)]

def fetch_pexels(query, used_ids):
    if not PEXELS_API_KEY:
        return None
    try:
        # Simplify query to 1-2 words for better results
        simple_query = " ".join(query.split()[:2])
        for page in range(1, 3):
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": simple_query, "per_page": 5,
                        "page": page, "orientation": "portrait"},
                timeout=10)
            r.raise_for_status()
            for photo in r.json().get("photos", []):
                if photo["id"] not in used_ids:
                    used_ids.add(photo["id"])
                    img_data = requests.get(
                        photo["src"]["large"], timeout=15).content
                    return Image.open(BytesIO(img_data))
    except Exception as e:
        log.warning(f"Pexels failed '{query}': {e}")
    return None

def fetch_unsplash(query, seed=0):
    """Unsplash source — no API key needed."""
    try:
        simple = "+".join(query.split()[:2])
        url = f"https://source.unsplash.com/1080x1920/?{simple}&sig={seed}"
        r = requests.get(url, timeout=15, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("content-type", ""):
            return Image.open(BytesIO(r.content))
    except Exception as e:
        log.warning(f"Unsplash failed '{query}': {e}")
    return None

def fetch_picsum(seed=0):
    """Lorem Picsum — always returns a random photo, no key needed."""
    try:
        url = f"https://picsum.photos/seed/{seed * 37 + 100}/1080/1920"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content))
    except Exception as e:
        log.warning(f"Picsum failed: {e}")
    return None

def generate_placeholder(query, index):
    """Generate a colored placeholder image with text — never fails."""
    colors = [
        (15, 32, 65),   # dark blue
        (20, 60, 40),   # dark green
        (60, 15, 40),   # dark purple
        (65, 30, 10),   # dark orange
        (10, 45, 65),   # dark teal
        (50, 10, 10),   # dark red
        (30, 30, 60),   # midnight blue
        (20, 50, 50),   # dark cyan
    ]
    color = colors[index % len(colors)]
    img = Image.new("RGB", (1080, 1920), color)
    draw = ImageDraw.Draw(img)

    # Draw simple text
    text = query[:30]
    draw.rectangle([80, 860, 1000, 1060], fill=(255, 255, 255, 30))
    try:
        draw.text((540, 960), text, fill=(255, 255, 255),
                 anchor="mm", font=ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48))
    except:
        draw.text((200, 920), text, fill=(255, 255, 255))

    log.info(f"Generated placeholder for: {query}")
    return img
