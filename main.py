import os
import json
import shutil
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

NICHE = os.getenv("NICHE", None)
STATUS_FILE = "docs/status.json"

def cleanup():
    """Remove all previous output files to ensure fresh content."""
    log.info("Cleaning up previous run files...")
    # Remove old audio
    for f in ["output/voice.mp3", "output/video_final.mp4", "output/video_only.mp4"]:
        if os.path.exists(f):
            os.remove(f)
            log.info(f"Removed: {f}")
    # Remove old images
    img_dir = "output/images"
    if os.path.exists(img_dir):
        shutil.rmtree(img_dir)
        os.makedirs(img_dir)
        log.info("Cleared output/images/")
    # Remove old slides
    slides_dir = "output/slides"
    if os.path.exists(slides_dir):
        shutil.rmtree(slides_dir)
        log.info("Cleared output/slides/")

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
        json.dump({
            "last_run": current["last_run"],
            "status": current["status"],
            "topic": current["topic"],
            "youtube_url": current["youtube_url"],
            "instagram_url": current["instagram_url"],
            "history": existing[:30]
        }, f, indent=2)
    log.info(f"Status written to {STATUS_FILE}")

def run_pipeline():
    result = {
        "status": "failed", "topic": "",
        "youtube_url": "", "instagram_url": "", "error": ""
    }
    try:
        # ── Cleanup previous run ─────────────────────────────────────
        cleanup()

        # ── Step 1: Fetch latest news ────────────────────────────────
        log.info("STEP 1 — Fetching latest news...")
        trends = get_top_trends(niche=NICHE)
        if not trends:
            raise ValueError("No trends returned.")

        if isinstance(trends[0], tuple):
            topic, summary = trends[0]
        else:
            topic, summary = trends[0], ""

        result["topic"] = topic
        log.info(f"Today's topic: {topic}")
        log.info(f"Context: {summary[:100]}")

        # ── Step 2: Generate script ──────────────────────────────────
        log.info("STEP 2 — Generating script from latest news...")
        script = generate_script(topic, summary)
        log.info(f"Script: {len(script.split())} words")

        # ── Step 3: Voiceover ────────────────────────────────────────
        log.info("STEP 3 — Generating voiceover...")
        audio_path = generate_voiceover(script)
        log.info(f"Audio: {audio_path}")

        # ── Step 4: Visuals ──────────────────────────────────────────
        log.info("STEP 4 — Fetching fresh visuals...")
        niche_tag = "technology"
        for n in ["AI", "Cloud", "Cybersecurity", "DevOps", "Automation"]:
            if n.lower() in topic.lower():
                niche_tag = n
                break
        image_paths = get_visuals(script, niche_tag)
        log.info(f"Images: {len(image_paths)}")

        # ── Step 5: Assemble video ───────────────────────────────────
        log.info("STEP 5 — Assembling video with captions...")
        video_path = assemble_video(audio_path, image_paths, topic, script=script)
        log.info(f"Video: {video_path}")

        # ── Step 6: YouTube ──────────────────────────────────────────
        log.info("STEP 6 — Uploading to YouTube...")
        yt_url = publish_youtube(video_path, topic, script)
        result["youtube_url"] = yt_url
        log.info(f"YouTube: {yt_url}")

        # ── Step 7: Instagram ────────────────────────────────────────
        log.info("STEP 7 — Uploading to Instagram...")
        ig_url = publish_instagram(video_path, topic, script)
        result["instagram_url"] = ig_url

        result["status"] = "success"
        log.info("Pipeline complete!")

    except Exception as e:
        result["error"] = str(e)
        result["status"] = "failed"
        log.error(f"Pipeline failed: {e}")
        log.error(traceback.format_exc())
    finally:
        write_status(result)

    return result["status"] == "success"

if __name__ == "__main__":
    exit(0 if run_pipeline() else 1)
