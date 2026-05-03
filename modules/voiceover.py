import os
import asyncio
import logging
import edge_tts

log = logging.getLogger(__name__)

def generate_voiceover(script, output_path="output/voice.mp3"):
    os.makedirs("output", exist_ok=True)
    text = _clean(script)
    try:
        asyncio.run(_tts(text, output_path))
        return output_path
    except Exception as e:
        log.warning(f"edge-tts failed: {e}, using gTTS...")
        from gtts import gTTS
        gTTS(text=text, lang="en").save(output_path)
        return output_path

async def _tts(text, path):
    await edge_tts.Communicate(text, "en-US-GuyNeural", rate="+5%").save(path)

def _clean(script):
    lines = []
    for line in script.splitlines():
        s = line.strip()
        if s and not any(s.startswith(x) for x in ["[VISUAL", "[HOOK", "[POINT", "[CTA"]):
            lines.append(s)
    return " ".join(lines)
