import os
import re
import asyncio
import logging
import tempfile
import subprocess

log = logging.getLogger(__name__)

# Different voice styles per section
SECTION_VOICES = {
    "HOOK":    {"voice": "en-US-GuyNeural",   "rate": "+30%", "pitch": "+10Hz"},  # Fast, high energy
    "NEWS":    {"voice": "en-US-GuyNeural",   "rate": "+20%", "pitch": "+5Hz"},   # Authoritative
    "POINT":   {"voice": "en-US-GuyNeural",   "rate": "+25%", "pitch": "+0Hz"},   # Clear, crisp
    "CTA":     {"voice": "en-US-GuyNeural",   "rate": "+15%", "pitch": "+5Hz"},   # Warm, engaging
    "DEFAULT": {"voice": "en-US-GuyNeural",   "rate": "+20%", "pitch": "+5Hz"},   # Standard
}

def generate_voiceover(script, output_path="output/voice.mp3"):
    os.makedirs("output", exist_ok=True)

    # Parse script into sections
    sections = parse_sections(script)
    log.info(f"Voiceover sections: {len(sections)}")
    for s in sections:
        log.info(f"  [{s['label']}] {s['text'][:50]}...")

    if not sections:
        # Fallback — use full cleaned text
        text = clean_text(script)
        return generate_single(text, "DEFAULT", output_path)

    # Try section-by-section edge-tts for dynamic audio
    try:
        return generate_sectioned(sections, output_path)
    except Exception as e:
        log.warning(f"Sectioned TTS failed: {e} — falling back to single voice")
        full_text = " ".join([s["text"] for s in sections])
        return generate_single(full_text, "DEFAULT", output_path)


def generate_sectioned(sections, output_path):
    """Generate separate audio for each section then merge."""
    os.makedirs("output/audio_parts", exist_ok=True)

    # Clear old parts
    for f in os.listdir("output/audio_parts"):
        os.remove(f"output/audio_parts/{f}")

    part_paths = []

    for i, section in enumerate(sections):
        label = section["label"]
        text = section["text"]
        if not text.strip():
            continue

        part_path = f"output/audio_parts/part_{i:02d}.mp3"

        # Get voice style for this section
        style_key = "POINT" if label.startswith("POINT") else label
        style = SECTION_VOICES.get(style_key, SECTION_VOICES["DEFAULT"])

        log.info(f"Generating [{label}] with rate={style['rate']} pitch={style['pitch']}")

        success = False
        for attempt in range(3):
            try:
                asyncio.run(_tts(
                    text,
                    style["voice"],
                    style["rate"],
                    style["pitch"],
                    part_path
                ))
                if os.path.exists(part_path) and os.path.getsize(part_path) > 500:
                    part_paths.append(part_path)
                    success = True
                    break
            except Exception as e:
                log.warning(f"edge-tts attempt {attempt+1} failed for [{label}]: {e}")

        if not success:
            # Fallback to gTTS for this section
            try:
                from gtts import gTTS
                gTTS(text=text, lang="en", slow=False).save(part_path)
                if os.path.exists(part_path) and os.path.getsize(part_path) > 500:
                    part_paths.append(part_path)
                    log.info(f"gTTS fallback used for [{label}]")
            except Exception as e:
                log.warning(f"gTTS also failed for [{label}]: {e}")

    if not part_paths:
        raise RuntimeError("No audio parts generated")

    if len(part_paths) == 1:
        import shutil
        shutil.copy(part_paths[0], output_path)
        return output_path

    # Merge all parts using FFmpeg concat
    concat_file = "output/audio_parts/concat.txt"
    with open(concat_file, "w") as f:
        for p in part_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    result = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        output_path
    ], capture_output=True, text=True)

    if result.returncode != 0:
        log.error(f"FFmpeg merge failed: {result.stderr[-300:]}")
        raise RuntimeError("Audio merge failed")

    size = os.path.getsize(output_path)
    log.info(f"Merged audio: {output_path} ({size:,} bytes)")

    # Cleanup
    import shutil
    shutil.rmtree("output/audio_parts", ignore_errors=True)

    return output_path


def generate_single(text, style_key, output_path):
    """Single voice fallback."""
    style = SECTION_VOICES.get(style_key, SECTION_VOICES["DEFAULT"])

    for attempt in range(3):
        try:
            asyncio.run(_tts(text, style["voice"], style["rate"], style["pitch"], output_path))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                log.info(f"Single voice saved: {output_path}")
                return output_path
        except Exception as e:
            log.warning(f"edge-tts attempt {attempt+1} failed: {e}")

    # Final fallback: gTTS
    from gtts import gTTS
    gTTS(text=text, lang="en", slow=False).save(output_path)
    log.info(f"gTTS fallback: {output_path}")
    return output_path


async def _tts(text, voice, rate, pitch, path):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await asyncio.wait_for(communicate.save(path), timeout=60)


def parse_sections(script):
    """Parse script into labeled sections with narrator text only."""
    sections = []
    lines = script.splitlines()
    current_label = "DEFAULT"
    current_text = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Section label
        label_match = re.match(
            r'^\[(HOOK|NEWS|POINT\s*\d+|CTA|INTRO|OUTRO)\]',
            line, re.IGNORECASE)
        if label_match:
            if current_text:
                text = " ".join(current_text).strip()
                if text:
                    sections.append({"label": current_label, "text": text})
            current_label = label_match.group(1).upper().replace(" ", "_")
            current_text = []
            continue

        # Skip visual cues
        if re.search(r'\[VISUAL CUE:', line, re.IGNORECASE):
            remaining = re.sub(r'\[VISUAL CUE:[^\]]*\]', '', line).strip()
            if remaining:
                clean = re.sub(r'\[.*?\]', '', remaining).strip()
                clean = re.sub(r'\*+', '', clean).strip()
                if clean:
                    current_text.append(clean)
            continue

        # Narrator text
        clean = re.sub(r'\[.*?\]', '', line).strip()
        clean = re.sub(r'\*+', '', clean).strip()
        if clean:
            current_text.append(clean)

    # Save last section
    if current_text:
        text = " ".join(current_text).strip()
        if text:
            sections.append({"label": current_label, "text": text})

    return sections


def clean_text(script):
    text = re.sub(r'\[VISUAL CUE:[^\]]*\]', '', script, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
