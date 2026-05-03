import os
import logging
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

log = logging.getLogger(__name__)

def assemble_video(audio_path, image_paths, topic, output_path="output/video_final.mp4"):
    os.makedirs("output", exist_ok=True)
    audio = AudioFileClip(audio_path)
    duration = audio.duration
    per_image = duration / len(image_paths)
    log.info(f"Assembling {len(image_paths)} images over {duration:.1f}s")
    clips = [ImageClip(p).with_duration(per_image) for p in image_paths]
    final = concatenate_videoclips(clips, method="compose").with_audio(audio)
    final.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")
    log.info(f"Video ready: {output_path}")
    return output_path
