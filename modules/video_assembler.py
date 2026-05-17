import os
import re
import subprocess
import logging
import shutil
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

def assemble_video(audio_path, image_paths, topic, script="", video_type="short", output_path="output/video_final.mp4"):
    os.makedirs("output", exist_ok=True)
    os.makedirs("output/slides", exist_ok=True)
    for f in os.listdir("output/slides"):
        os.remove(f"output/slides/{f}")

    if len(image_paths) == 0:
        raise RuntimeError("No images provided")
    if len(image_paths) < 3:
        image_paths = (image_paths * 8)[:8]

    duration  = get_audio_duration(audio_path)
    n_images  = len(image_paths)
    per_image = round(duration / n_images, 3) if video_type == "short" else max(5.0, round(duration / n_images, 3))
    log.info(f"Audio: {duration:.1f}s | {n_images} images | {per_image:.1f}s each")

    hook_text = extract_hook(script, topic)
    captions  = extract_captions(script)
    log.info(f"Hook: {hook_text}")
    log.info(f"Captions: {len(captions)}")

    for i, img_path in enumerate(image_paths):
        out = f"output/slides/img{i:04d}.png"
        img = Image.open(img_path).convert("RGB").resize((1080, 1920), Image.LANCZOS)

        overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        ov_draw = ImageDraw.Draw(overlay)
        for y in range(1400, 1920):
            alpha = int(210 * (y - 1400) / 520)
            ov_draw.rectangle([0, y, 1080, y+1], fill=(0, 0, 0, alpha))
        for y in range(0, 280):
            alpha = int(160 * (1 - y / 280))
            ov_draw.rectangle([0, y, 1080, y+1], fill=(0, 0, 0, alpha))

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Load fonts - try Linux first then Mac
        try:
            font_hook    = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
            font_caption = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 46)
            font_brand   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
            font_badge   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
        except:
            try:
                font_hook    = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 52)
                font_caption = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 46)
                font_brand   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
                font_badge   = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 30)
            except:
                font_hook = font_caption = font_brand = font_badge = ImageFont.load_default()

        draw.rectangle([40, 44, 310, 96], fill=(220, 30, 30))
        draw_centered(draw, "BREAKING NEWS", 175, 70, font_badge, (255, 255, 255))
        draw_centered(draw, "ThreatLoopHQ", 830, 70, font_brand, (255, 220, 0))

        if i < 2 and hook_text:
            draw_wrapped(draw, hook_text, 540, 190, font_hook, (255, 255, 255), max_width=980)

        if captions:
            caption = captions[i % len(captions)]
            draw_wrapped(draw, caption, 540, 1760, font_caption, (255, 255, 255), max_width=960)

        bar_w = int((i + 1) / n_images * 1080)
        draw.rectangle([0, 1905, 1080, 1920], fill=(40, 40, 40))
        draw.rectangle([0, 1905, bar_w, 1920], fill=(255, 220, 0))

        img.save(out, "PNG")

    log.info(f"Built {n_images} slides")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", f"1/{int(per_image)}",
        "-i", "output/slides/img%04d.png",
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-tune", "stillimage",
        "-b:v", "6M", "-maxrate", "6M", "-bufsize", "12M",
        "-vf", "fps=30,format=yuv420p,scale=1080:1920",
        "-profile:v", "high", "-level", "4.2",
        "-r", "30", "-g", "30",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-map", "0:v", "-map", "1:a",
        "-shortest", "-movflags", "+faststart",
        output_path
    ]

    log.info("Building final video...")
    result = subprocess.run(cmd, capture_output=True, text=True)
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
            in_hook = True; continue
        if in_hook:
            clean = re.sub(r'\[.*?\]|\*+', '', line).strip()
            if clean and len(clean) > 10:
                return clean[:80].upper()
    for line in lines:
        clean = re.sub(r'\[.*?\]|\*+', '', line).strip()
        if clean and len(clean) > 10:
            return clean[:80].upper()
    return topic.upper()[:80]

def extract_captions(script):
    captions = []
    for line in script.splitlines():
        clean = re.sub(r'\[.*?\]|\*+', '', line).strip()
        if 8 < len(clean) < 120:
            captions.append(clean)
    return captions if captions else ["Follow ThreatLoopHQ for daily tech news"]

def draw_centered(draw, text, x, y, font, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text((x-tw//2+2, y-th//2+2), text, font=font, fill=(0, 0, 0))
    draw.text((x-tw//2,   y-th//2),   text, font=font, fill=color)

def draw_wrapped(draw, text, x, y, font, color, max_width=960):
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    lh = 62
    sy = y - (len(lines) * lh) // 2
    for i, line in enumerate(lines):
        draw_centered(draw, line, x, sy + i*lh, font, color)

def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True, check=True)
    return float(result.stdout.strip())
