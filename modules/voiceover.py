import os
import re
import asyncio
import logging

log = logging.getLogger(__name__)

def generate_voiceover(script, output_path="output/voice.mp3"):
    os.makedirs("output", exist_ok=True)
    text = _clean(script)
    log.info(f"Cleaned text ({len(text)} chars): {text[:80]}...")

    if not text.strip():
        raise RuntimeError("No text after cleaning script.")

    # Try gTTS first (most reliable)
    try:
        from gtts import gTTS
        gTTS(text=text, lang="en", slow=False).save(output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            log.info(f"gTTS voiceover saved: {output_path}")
            return output_path
    except Exception as e:
        log.warning(f"gTTS failed: {e}, trying edge-tts...")

    # Fallback to edge-tts
    for attempt in range(3):
        try:
            asyncio.run(_tts(text, output_path))
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                log.info(f"edge-tts voiceover saved: {output_path}")
                return output_path
        except Exception as e:
            log.warning(f"edge-tts attempt {attempt+1} failed: {e}")

    raise RuntimeError("All voiceover methods failed.")

async def _tts(text, path):
    import edge_tts
    communicate = edge_tts.Communicate(text, "en-US-GuyNeural", rate="+5%")
    await asyncio.wait_for(communicate.save(path), timeout=60)

def _clean(script):
    text = re.sub(r'\[VISUAL CUE:[^\]]*\]', '', script, flags=re.IGNORECASE)
    text = re.sub(r'\[(HOOK|POINT \d+|CTA|INTRO|OUTRO)[^\]]*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
