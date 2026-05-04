import os
import subprocess
import logging
import shutil
from PIL import Image

log = logging.getLogger(__name__)

def assemble_video(audio_path, image_paths, topic, output_path="output/video_final.mp4"):
    os.makedirs("output", exist_ok=True)
    os.makedirs("output/slides", exist_ok=True)

    # Clear slides folder
    for f in os.listdir("output/slides"):
        os.remove(f"output/slides/{f}")

    if len(image_paths) < 3:
        image_paths = (image_paths * 8)[:8]

    duration = get_audio_duration(audio_path)
    per_image = 3.0  # 3 seconds per image — fast pace
    num_images = int(duration / per_image) + 1

    # Tile images to fill duration
    tiled = []
    while len(tiled) < num_images:
        tiled += image_paths
    tiled = tiled[:num_images]

    log.info(f"Audio: {duration:.1f}s | {len(tiled)} images at {per_image}s each")

    # Copy and number images sequentially as PNG for FFmpeg
    for i, img_path in enumerate(tiled):
        out = f"output/slides/img{i:04d}.png"
        img = Image.open(img_path).convert("RGB").resize((1080, 1920), Image.LANCZOS)
        img.save(out, "PNG")
        log.info(f"Slide {i+1}: {out}")

    # Use FFmpeg image sequence — most reliable method
    # -framerate 1/3 means each image shows for 3 seconds
    cmd = [
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

    log.info("Running FFmpeg image sequence...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log.error(f"FFmpeg error:\n{result.stderr[-500:]}")
        raise RuntimeError("FFmpeg failed")

    size = os.path.getsize(output_path)
    frames = get_frame_count(output_path)
    log.info(f"Video ready: {output_path} | {size:,} bytes | {frames} frames")

    # Cleanup slides
    shutil.rmtree("output/slides", ignore_errors=True)

    return output_path

def get_frame_count(video_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-count_frames", "-show_entries", "stream=nb_read_frames",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True)
    try:
        return int(result.stdout.strip())
    except:
        return -1

def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())
