import os
import json
import shutil
import logging
import traceback
import time
from datetime import datetime
from dotenv import load_dotenv

from modules.trends import get_top_trends
from modules.script_writer import generate_script
from modules.voiceover import generate_voiceover
from modules.visuals import get_visuals
from modules.video_assembler import assemble_video
from modules.publisher import publish_youtube, publish_instagram
from modules.pillar_tracker import get_three_pillars

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)
STATUS_FILE = "docs/status.json"

# Daily plan: 2 shorts + 2 long form
DAILY_PLAN = [
    {"type": "short",     "label": "Short 1"},
    {"type": "short",     "label": "Short 2"},
    {"type": "long_form", "label": "Long Form 1"},
    {"type": "long_form", "label": "Long Form 2"},
]

def cleanup():
    log.info("Cleaning up...")
    for f in ["output/voice.mp3", "output/video_final.mp4"]:
        if os.path.exists(f): os.remove(f)
    for d in ["output/images", "output/slides", "output/audio_parts"]:
        if os.path.exists(d): shutil.rmtree(d)
        os.makedirs(d)

def write_status(runs):
    os.makedirs("docs", exist_ok=True)
    existing = []
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE) as f:
                existing = json.load(f).get("history", [])
        except: existing = []
    for run in runs:
        existing.insert(0, {
            "last_run":      datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "status":        run.get("status", "unknown"),
            "topic":         run.get("topic", ""),
            "pillar":        run.get("pillar", ""),
            "video_type":    run.get("video_type", "short"),
            "youtube_url":   run.get("youtube_url", ""),
            "instagram_url": run.get("instagram_url", ""),
            "error":         run.get("error", ""),
        })
    last = runs[-1] if runs else {}
    with open(STATUS_FILE, "w") as f:
        json.dump({
            "last_run":      datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "status":        last.get("status", "unknown"),
            "topic":         last.get("topic", ""),
            "youtube_url":   last.get("youtube_url", ""),
            "instagram_url": last.get("instagram_url", ""),
            "history":       existing[:30],
        }, f, indent=2)
    log.info(f"Status written → {STATUS_FILE}")

def run_single(topic, summary, pillar, video_type, label, num, total):
    result = {
        "status": "failed", "topic": topic,
        "pillar": pillar, "video_type": video_type,
        "youtube_url": "", "instagram_url": "", "error": ""
    }
    try:
        log.info(f"{'='*60}")
        log.info(f"{label} ({num}/{total}) | {video_type.upper()} | PILLAR: {pillar}")
        log.info(f"TOPIC: {topic}")
        log.info(f"{'='*60}")

        cleanup()

        log.info("STEP 2 — Generating script...")
        script = generate_script(topic, summary, video_type=video_type)
        log.info(f"Script: {len(script.split())} words")

        log.info("STEP 3 — Generating voiceover...")
        audio_path = generate_voiceover(script)

        log.info("STEP 4 — Fetching visuals...")
        image_paths = get_visuals(script, pillar)
        log.info(f"Images: {len(image_paths)}")

        log.info("STEP 5 — Assembling video...")
        video_path = assemble_video(
            audio_path, image_paths, topic,
            script=script, video_type=video_type)

        log.info("STEP 6 — Uploading to YouTube...")
        yt_url = publish_youtube(video_path, topic, script, video_type=video_type)
        result["youtube_url"] = yt_url
        log.info(f"YouTube: {yt_url}")

        log.info("STEP 7 — Instagram...")
        ig_url = publish_instagram(video_path, topic, script)
        result["instagram_url"] = ig_url

        result["status"] = "success"
        log.info(f"{label} complete! ✅")

    except Exception as e:
        result["error"] = str(e)
        result["status"] = "failed"
        log.error(f"{label} failed: {e}")
        log.error(traceback.format_exc())

    return result

def run_pipeline():
    log.info("Starting daily pipeline — 2 Shorts + 2 Long Form")

    # Get 4 different pillars
    pillars = get_three_pillars()
    # Add one more pillar
    from modules.pillar_tracker import PILLARS
    extra = [p for p in PILLARS if p not in pillars]
    pillars.append(extra[0] if extra else pillars[0])
    log.info(f"Today's pillars: {pillars}")

    results = []
    for i, plan in enumerate(DAILY_PLAN):
        pillar = pillars[i % len(pillars)]
        video_type = plan["type"]
        label = plan["label"]

        log.info(f"\nFetching news for [{pillar}] — {video_type}")
        trends = get_top_trends(niche=pillar)
        if not trends:
            trends = [(f"Latest {pillar} breakthroughs in 2025", "")]

        topic, summary = trends[0] if isinstance(trends[0], tuple) else (trends[0], "")

        result = run_single(topic, summary, pillar, video_type, label, i+1, len(DAILY_PLAN))
        results.append(result)

        if i < len(DAILY_PLAN) - 1:
            wait = 20 if video_type == "long_form" else 10
            log.info(f"Waiting {wait}s before next video...")
            time.sleep(wait)

    write_status(results)

    success = sum(1 for r in results if r["status"] == "success")
    log.info(f"\n{'='*60}")
    log.info(f"DAILY RUN COMPLETE: {success}/{len(DAILY_PLAN)} videos posted")
    for i, r in enumerate(results, 1):
        icon = "✅" if r["status"] == "success" else "❌"
        vtype = "📱SHORT" if r["video_type"] == "short" else "🎬LONG"
        log.info(f"  {icon} {vtype} [{r['pillar']}]: {r.get('youtube_url', r.get('error',''))[:60]}")
    log.info(f"{'='*60}")

    return success > 0

if __name__ == "__main__":
    exit(0 if run_pipeline() else 1)
