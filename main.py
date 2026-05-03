import os
import json
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv

from modules.trends import get_top_trends
from modules.script_writer import generate_script
from modules.voiceover import generate_voiceover
from modules.visuals import get_visuals
from modules.video_assembler import assemble_video
from modules.publisher import publish_youtube, publish_instagram

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

NICHE = os.getenv("NICHE", "cybersecurity")
STATUS_FILE = "docs/status.json"

def write_status(data):
    os.makedirs("docs", exist_ok=True)
    existing = []
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE) as f:
                existing = json.load(f).get("history", [])
        except:
            existing = []
    current = {
        "last_run": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "status": data.get("status", "unknown"),
        "topic": data.get("topic", ""),
        "youtube_url": data.get("youtube_url", ""),
        "instagram_url": data.get("instagram_url", ""),
        "error": data.get("error", ""),
    }
    existing.insert(0, current)
    with open(STATUS_FILE, "w") as f:
        json.dump({"last_run": current["last_run"], "status": current["status"],
                   "topic": current["topic"], "youtube_url": current["youtube_url"],
                   "instagram_url": current["instagram_url"], "history": existing[:30]}, f, indent=2)
    log.info(f"Status written to {STATUS_FILE}")

def run_pipeline():
    result = {"status": "failed", "topic": "", "youtube_url": "", "instagram_url": "", "error": ""}
    try:
        log.info("STEP 1 — Fetching trending topics...")
        trends = get_top_trends(niche=NICHE)
        topic = trends[0]
        result["topic"] = topic
        log.info(f"Topic: {topic}")

        log.info("STEP 2 — Generating script...")
        script = generate_script(topic)
        log.info(f"Script: {len(script.split())} words")

        log.info("STEP 3 — Generating voiceover...")
        audio_path = generate_voiceover(script)
        log.info(f"Audio: {audio_path}")

        log.info("STEP 4 — Fetching visuals...")
        image_paths = get_visuals(script, topic)
        log.info(f"Images: {len(image_paths)}")

        log.info("STEP 5 — Assembling video...")
        video_path = assemble_video(audio_path, image_paths, topic)
        log.info(f"Video: {video_path}")

        log.info("STEP 6 — Uploading to YouTube...")
        yt_url = publish_youtube(video_path, topic, script)
        result["youtube_url"] = yt_url

        log.info("STEP 7 — Uploading to Instagram...")
        ig_url = publish_instagram(video_path, topic, script)
        result["instagram_url"] = ig_url

        result["status"] = "success"
        log.info("Pipeline complete!")

    except Exception as e:
        result["error"] = str(e)
        log.error(f"Pipeline failed: {e}")
        log.error(traceback.format_exc())
    finally:
        write_status(result)
    return result["status"] == "success"

if __name__ == "__main__":
    exit(0 if run_pipeline() else 1)
