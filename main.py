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
from modules.pillar_tracker import get_three_pillars

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)
STATUS_FILE = "docs/status.json"

def cleanup():
    log.info("Cleaning up previous run...")
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
            "last_run": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "status":        run.get("status", "unknown"),
            "topic":         run.get("topic", ""),
            "pillar":        run.get("pillar", ""),
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

def run_single(topic, summary, pillar, video_num):
    result = {
        "status": "failed", "topic": topic,
        "pillar": pillar,
        "youtube_url": "", "instagram_url": "", "error": ""
    }
    try:
        log.info(f"{'='*60}")
        log.info(f"VIDEO {video_num}/3 | PILLAR: {pillar}")
        log.info(f"TOPIC: {topic}")
        log.info(f"{'='*60}")

        cleanup()

        log.info("STEP 2 — Generating script...")
        script = generate_script(topic, summary)
        log.info(f"Script: {len(script.split())} words")

        log.info("STEP 3 — Generating voiceover...")
        audio_path = generate_voiceover(script)

        log.info("STEP 4 — Fetching visuals...")
        image_paths = get_visuals(script, pillar)
        log.info(f"Images: {len(image_paths)}")

        log.info("STEP 5 — Assembling video...")
        video_path = assemble_video(audio_path, image_paths, topic, script=script)

        log.info("STEP 6 — Uploading to YouTube...")
        yt_url = publish_youtube(video_path, topic, script)
        result["youtube_url"] = yt_url
        log.info(f"YouTube: {yt_url}")

        log.info("STEP 7 — Uploading to Instagram...")
        ig_url = publish_instagram(video_path, topic, script)
        result["instagram_url"] = ig_url

        result["status"] = "success"
        log.info(f"Video {video_num}/3 complete! [{pillar}]")

    except Exception as e:
        result["error"] = str(e)
        result["status"] = "failed"
        log.error(f"Video {video_num}/3 failed: {e}")
        log.error(traceback.format_exc())

    return result

def run_pipeline():
    log.info("Starting daily pipeline — 3 videos across different pillars")

    # Get 3 different pillars for this run
    pillars = get_three_pillars()
    log.info(f"Today's pillars: {pillars[0]} → {pillars[1]} → {pillars[2]}")

    results = []
    for i, pillar in enumerate(pillars, 1):
        log.info(f"\nFetching news for pillar: {pillar}")

        # Fetch top news for this specific pillar
        trends = get_top_trends(niche=pillar)
        if not trends:
            log.warning(f"No trends for {pillar} — using fallback")
            trends = [(f"Latest {pillar} breakthroughs you need to know in 2025", "")]

        topic, summary = trends[0] if isinstance(trends[0], tuple) else (trends[0], "")

        # Run pipeline for this pillar
        result = run_single(topic, summary, pillar, i)
        results.append(result)

        # Delay between videos
        if i < 3:
            import time
            log.info("Waiting 15s before next video...")
            time.sleep(15)

    # Write status
    write_status(results)

    # Summary
    success = sum(1 for r in results if r["status"] == "success")
    log.info(f"\n{'='*60}")
    log.info(f"DAILY RUN COMPLETE: {success}/3 videos posted")
    for i, r in enumerate(results, 1):
        status_icon = "✅" if r["status"] == "success" else "❌"
        log.info(f"  {status_icon} Video {i} [{r['pillar']}]: {r.get('youtube_url', r.get('error', ''))[:70]}")
    log.info(f"{'='*60}")

    return success > 0

if __name__ == "__main__":
    exit(0 if run_pipeline() else 1)
