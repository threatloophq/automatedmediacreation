import os
import re
import subprocess
import logging
import shutil
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

def assemble_video(audio_path, image_paths, topic, script="", output_path="output/video_final.mp4"):
    os.makedirs("output", exist_ok=True)
    os.makedirs("output/slides", exist_ok=True)

    # Clear slides
    for f in os.listdir("output/slides"):
        os.remove(f"output/slides/{f}")

    duration = get_audio_duration(audio_path)
    n_images = len(image_paths)

    if n_images == 0:
        raise RuntimeError("No images provided")

    # Each image gets equal time — synced to audio duration
    per_image = round(duration / n_images, 3)
    log.info(f"Audio: {duration:.1f}s | {n_images} images | {per_image:.1f}s each")

    # Extract hook and captions from script
    hook_text = extract_hook(script, topic)
    captions = extract_captions(script)
    log.info(f"Hook: {hook_text}")
    log.info(f"Captions: {len(captions)}")

    # Build one slide per image — NO tiling, NO repeating
    for i, img_path in enumerate(image_paths):
        out = f"output/slides/img{i:04d}.png"
        img = Image.open(img_path).convert("RGB").resize((1080, 1920), Image.LANCZOS)

        # Dark gradient overlay
        overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw_overlay = ImageDraw.Draw(overlay)
        for y in range(1400, 1920):
            alpha = int(200 * (y - 1400) / 520)
            draw_overlay.rectangle([0, y, 1080, y+1], fill=(0, 0, 0, alpha))
        for y in range(0, 250):
            alpha = int(150 * (1 - y / 250))
            draw_overlay.rectangle([0, y, 1080, y+1], fill=(0, 0, 0, alpha))

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Load fonts
        try:
            font_hook    = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 54)
            font_caption = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            font_brand   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            font_badge   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
        except:
            font_hook = font_caption = font_brand = font_badge = ImageFont.load_default()

        # ── BREAKING NEWS badge (all slides) ──
        draw.rectangle([50, 50, 340, 100], fill=(220, 30, 30))
        draw_centered(draw, "⚡ BREAKING NEWS", 195, 75, font_badge, (255, 255, 255))

        # ── Channel brand ──
        draw_centered(draw, "ThreatLoopHQ", 810, 75, font_brand, (255, 220, 0))

        # ── Hook text at top (first 2 slides) ──
        if i < 2 and hook_text:
            draw_wrapped(draw, hook_text, 540, 180, font_hook, (255, 255, 255), max_width=980)

        # ── Caption at bottom — unique per slide ──
        if captions:
            caption = captions[i % len(captions)]
            draw_wrapped(draw, caption, 540, 1750, font_caption, (255, 255, 255), max_width=960)

        # ── Slide progress bar at very bottom ──
        bar_width = int((i + 1) / n_images * 1080)
        draw.rectangle([0, 1900, 1080, 1920], fill=(50, 50, 50))
        draw.rectangle([0, 1900, bar_width, 1920], fill=(255, 220, 0))

        img.save(out, "PNG")
        log.info(f"Slide {i+1}/{n_images} built: {out}")

    # Build video from image sequence
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", f"1/{int(per_image)}",
        "-i", "output/slides/img%04d.png",
        "-i", audio_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-tune", "stillimage",
        "-b:v", "6M",
        "-maxrate", "6M",
        "-bufsize", "12M",
        "-vf", "fps=30,format=yuv420p,scale=1080:1920",
        "-profile:v", "high",
        "-level", "4.2",
        "-r", "30",
        "-g", "30",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-map", "0:v",
        "-map", "1:a",
        "-shortest",
        "-movflags", "+faststart",
        output_path
    ]

    log.info("Building final video...")
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"FFmpeg error: {result.stderr[-500:]}")
        raise RuntimeError("FFmpeg failed")

    size = os.path.getsize(output_path)
    log.info(f"Video ready: {output_path} ({size:,} bytes)")

    shutil.rmtree("output/slides", ignore_errors=True)
    return output_path


def extract_hook(script, topic):
    lines = [l.strip() for l in script.splitlines() if l.strip()]
    in_hook = False
    for line in lines:
        if re.match(r'^\[HOOK\]', line, re.IGNORECASE):
            in_hook = True
            continue
        if in_hook:
            clean = re.sub(r'\[.*?\]', '', line).strip()
            clean = re.sub(r'\*+', '', clean).strip()
            if clean and len(clean) > 10:
                return clean[:80].upper()
    # Fallback: first meaningful line
    for line in lines:
        clean = re.sub(r'\[.*?\]', '', line).strip()
        clean = re.sub(r'\*+', '', clean).strip()
        if clean and len(clean) > 10:
            return clean[:80].upper()
    return topic.upper()[:80]


def extract_captions(script):
    """Extract one punchy caption per script section."""
    captions = []
    lines = [l.strip() for l in script.splitlines() if l.strip()]
    for line in lines:
        clean = re.sub(r'\[.*?\]', '', line).strip()
        clean = re.sub(r'\*+', '', clean).strip()
        if 8 < len(clean) < 120:
            captions.append(clean)
    return captions if captions else ["Follow ThreatLoopHQ for daily tech news"]


def draw_centered(draw, text, x, y, font, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    # Shadow
    draw.text((x - tw//2 + 2, y - th//2 + 2), text, font=font, fill=(0, 0, 0))
    # Text
    draw.text((x - tw//2, y - th//2), text, font=font, fill=color)


def draw_wrapped(draw, text, x, y, font, color, max_width=960):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_height = 60
    total_h = len(lines) * line_height
    start_y = y - total_h // 2

    for i, line in enumerate(lines):
        ly = start_y + i * line_height
        draw_centered(draw, line, x, ly, font, color)


def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())
