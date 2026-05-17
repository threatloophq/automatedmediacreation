import os
import re
import asyncio
import logging

log = logging.getLogger(__name__)

def generate_voiceover(script, output_path="output/voice.mp3"):
    os.makedirs("output", exist_ok=True)
    text = clean_text(script)
    log.info(f"Generating voiceover ({len(text)} chars)...")
    if not text.strip():
        raise RuntimeError("No text after cleaning.")

    # Try edge-tts with fast rate
    for attempt in range(3):
        try:
            asyncio.run(_tts(text, output_path))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                log.info(f"Voiceover saved: {output_path}")
                return output_path
        except Exception as e:
            log.warning(f"edge-tts attempt {attempt+1}: {e}")

    # Fallback to gTTS
    try:
        from gtts import gTTS
        gTTS(text=text, lang="en", slow=False).save(output_path)
        log.info(f"gTTS fallback saved: {output_path}")
        return output_path
    except Exception as e:
        raise RuntimeError(f"All voiceover methods failed: {e}")

async def _tts(text, path):
    import edge_tts
    communicate = edge_tts.Communicate(
        text, "en-US-GuyNeural", rate="+25%", pitch="+5Hz")
    await asyncio.wait_for(communicate.save(path), timeout=60)

def clean_text(script):
    text = re.sub(r'\[VISUAL CUE:[^\]]*\]', '', script, flags=re.IGNORECASE)
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\*+', '', text)
    return re.sub(r'\s+', ' ', text).strip()
