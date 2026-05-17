import os
import re
import asyncio
import logging
import shutil
import subprocess

log = logging.getLogger(__name__)

SECTION_VOICES = {
    "HOOK":    {"voice": "en-US-GuyNeural", "rate": "+30%", "pitch": "+10Hz"},
    "NEWS":    {"voice": "en-US-GuyNeural", "rate": "+20%", "pitch": "+5Hz"},
    "POINT":   {"voice": "en-US-GuyNeural", "rate": "+25%", "pitch": "+0Hz"},
    "CTA":     {"voice": "en-US-GuyNeural", "rate": "+15%", "pitch": "+5Hz"},
    "DEFAULT": {"voice": "en-US-GuyNeural", "rate": "+20%", "pitch": "+5Hz"},
}

def generate_voiceover(script, output_path="output/voice.mp3"):
    os.makedirs("output", exist_ok=True)
    sections = parse_sections(script)
    log.info(f"Voiceover sections: {len(sections)}")
    if not sections:
        return generate_single(clean_text(script), "DEFAULT", output_path)
    try:
        return generate_sectioned(sections, output_path)
    except Exception as e:
        log.warning(f"Sectioned TTS failed: {e} — fallback to single")
        full_text = " ".join([s["text"] for s in sections if s["text"].strip()])
        return generate_single(full_text, "DEFAULT", output_path)

def generate_sectioned(sections, output_path):
    parts_dir = "output/audio_parts"
    os.makedirs(parts_dir, exist_ok=True)
    for f in os.listdir(parts_dir):
        os.remove(f"{parts_dir}/{f}")

    part_paths = []
    for i, section in enumerate(sections):
        label = section["label"]
        text  = section["text"]
        if not text.strip(): continue

        # Save as WAV for reliable merging
        part_path = f"{parts_dir}/part_{i:02d}.wav"
        style_key = "POINT" if "POINT" in label else label
        style = SECTION_VOICES.get(style_key, SECTION_VOICES["DEFAULT"])
        log.info(f"[{label}] rate={style['rate']} → {text[:50]}")

        success = False
        for attempt in range(3):
            try:
                asyncio.run(_tts_wav(
                    text, style["voice"], style["rate"], style["pitch"], part_path))
                if os.path.exists(part_path) and os.path.getsize(part_path) > 500:
                    part_paths.append(part_path)
                    success = True
                    break
            except Exception as e:
                log.warning(f"edge-tts attempt {attempt+1} [{label}]: {e}")

        if not success:
            try:
                mp3_tmp = f"{parts_dir}/tmp_{i:02d}.mp3"
                from gtts import gTTS
                gTTS(text=text, lang="en", slow=False).save(mp3_tmp)
                subprocess.run([
                    "ffmpeg", "-y", "-i", mp3_tmp,
                    "-ar", "24000", "-ac", "1", part_path
                ], capture_output=True, check=True)
                if os.path.exists(mp3_tmp):
                    os.remove(mp3_tmp)
                if os.path.exists(part_path) and os.path.getsize(part_path) > 500:
                    part_paths.append(part_path)
                    log.info(f"gTTS fallback used for [{label}]")
            except Exception as e:
                log.warning(f"gTTS also failed for [{label}]: {e}")

    if not part_paths:
        raise RuntimeError("No audio parts generated")

    if len(part_paths) == 1:
        subprocess.run([
            "ffmpeg", "-y", "-i", part_paths[0],
            "-codec:a", "libmp3lame", "-q:a", "2", output_path
        ], capture_output=True, check=True)
        return output_path

    # Write concat file
    concat_file = f"{parts_dir}/concat.txt"
    with open(concat_file, "w") as f:
        for p in part_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    # Merge WAV files
    merged_wav = f"{parts_dir}/merged.wav"
    r1 = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file, merged_wav
    ], capture_output=True, text=True)
    if r1.returncode != 0:
        raise RuntimeError(f"WAV concat failed: {r1.stderr[-200:]}")

    # Convert to MP3
    r2 = subprocess.run([
        "ffmpeg", "-y", "-i", merged_wav,
        "-codec:a", "libmp3lame", "-q:a", "2", output_path
    ], capture_output=True, text=True)
    if r2.returncode != 0:
        raise RuntimeError(f"WAV to MP3 failed: {r2.stderr[-200:]}")

    log.info(f"Merged audio: {output_path} ({os.path.getsize(output_path):,} bytes)")
    shutil.rmtree(parts_dir, ignore_errors=True)
    return output_path

def generate_single(text, style_key, output_path):
    style = SECTION_VOICES.get(style_key, SECTION_VOICES["DEFAULT"])
    for attempt in range(3):
        try:
            asyncio.run(_tts(text, style["voice"], style["rate"],
                             style["pitch"], output_path))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                log.info(f"Single voice saved: {output_path}")
                return output_path
        except Exception as e:
            log.warning(f"edge-tts attempt {attempt+1}: {e}")
    from gtts import gTTS
    gTTS(text=text, lang="en", slow=False).save(output_path)
    log.info(f"gTTS fallback: {output_path}")
    return output_path

async def _tts(text, voice, rate, pitch, path):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await asyncio.wait_for(communicate.save(path), timeout=60)

async def _tts_wav(text, voice, rate, pitch, path):
    import edge_tts
    mp3_path = path.replace(".wav", "_tmp.mp3")
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await asyncio.wait_for(communicate.save(mp3_path), timeout=60)
    r = subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-ar", "24000", "-ac", "1", path
    ], capture_output=True, text=True)
    if os.path.exists(mp3_path):
        os.remove(mp3_path)
    if r.returncode != 0:
        raise RuntimeError(f"MP3→WAV failed: {r.stderr[-100:]}")

def parse_sections(script):
    sections, lines = [], script.splitlines()
    current_label, current_text = "DEFAULT", []
    for line in lines:
        line = line.strip()
        if not line: continue
        lm = re.match(r'^\[(HOOK|NEWS|POINT\s*\d+|CTA|INTRO|OUTRO)\]',
                      line, re.IGNORECASE)
        if lm:
            if current_text:
                sections.append({"label": current_label,
                                  "text": " ".join(current_text)})
            current_label = lm.group(1).upper()
            current_text = []
            continue
        if re.search(r'\[VISUAL CUE:', line, re.IGNORECASE):
            remaining = re.sub(r'\[VISUAL CUE:[^\]]*\]', '', line).strip()
            clean = re.sub(r'\[.*?\]|\*+', '', remaining).strip()
            if clean: current_text.append(clean)
            continue
        clean = re.sub(r'\[.*?\]|\*+', '', line).strip()
        if clean: current_text.append(clean)
    if current_text:
        sections.append({"label": current_label,
                          "text": " ".join(current_text)})
    return sections

def clean_text(script):
    text = re.sub(r'\[.*?\]', '', script)
    text = re.sub(r'\*+', '', text)
    return re.sub(r'\s+', ' ', text).strip()
