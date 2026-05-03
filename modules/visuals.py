import os
import re
import logging
import requests
from PIL import Image
from io import BytesIO

log = logging.getLogger(__name__)
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

def get_visuals(script, topic):
    os.makedirs("output/images", exist_ok=True)
    cues = re.findall(r'\[VISUAL CUE:\s*(.+?)\]', script, re.IGNORECASE) or [topic] * 6
    paths = []
    for i, cue in enumerate(cues):
        path = f"output/images/img_{i:02d}.jpg"
        img = _pexels(cue) or _pollinations(cue)
        if img:
            img.convert("RGB").resize((1080, 1920), Image.LANCZOS).save(path, "JPEG", quality=90)
            paths.append(path)
            log.info(f"Image {i+1}: {path}")
    return paths

def _pexels(query):
    if not PEXELS_API_KEY:
        return None
    try:
        r = requests.get("https://api.pexels.com/v1/search",
                         headers={"Authorization": PEXELS_API_KEY},
                         params={"query": query, "per_page": 1, "orientation": "portrait"},
                         timeout=10)
        photos = r.json().get("photos", [])
        if photos:
            return Image.open(BytesIO(requests.get(photos[0]["src"]["large"], timeout=15).content))
    except Exception as e:
        log.warning(f"Pexels failed: {e}")
    return None

def _pollinations(query):
    try:
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(query)}?width=1080&height=1920&nologo=true"
        return Image.open(BytesIO(requests.get(url, timeout=30).content))
    except Exception as e:
        log.warning(f"Pollinations failed: {e}")
    return None
