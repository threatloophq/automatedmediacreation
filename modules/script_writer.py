import os
import logging
from groq import Groq

log = logging.getLogger(__name__)

def generate_script(topic, summary=""):
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set.")
    client = Groq(api_key=api_key)
    context = f"\nBreaking news context: {summary[:200]}" if summary else ""
    prompt = f"""You are a viral breaking news YouTube Shorts script writer for ThreatLoopHQ.
Write a STRICT 60-second script (MAX 120 WORDS) about:

Topic: {topic}{context}

FORMAT — follow exactly:

[HOOK]
[VISUAL CUE: person shocked at laptop screen]
One shocking sentence. Max 15 words.

[POINT 1]
[VISUAL CUE: relevant real photographable scene]
One punchy fact. Max 15 words.

[POINT 2]
[VISUAL CUE: relevant real photographable scene]
One punchy fact. Max 15 words.

[POINT 3]
[VISUAL CUE: relevant real photographable scene]
One punchy fact. Max 15 words.

[POINT 4]
[VISUAL CUE: relevant real photographable scene]
One punchy fact. Max 15 words.

[POINT 5]
[VISUAL CUE: relevant real photographable scene]
One punchy fact. Max 15 words.

[CTA]
[VISUAL CUE: person using smartphone]
Follow ThreatLoopHQ for daily breaking tech news. Like if this helped.

VISUAL CUE RULES:
- REAL PHOTOGRAPHABLE scenes only
- GOOD: hacker typing keyboard, server room, developer coding, business meeting
- BAD: animated graphic, logo overlay, split screen, countdown timer"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.9,
    )
    script = response.choices[0].message.content.strip()
    log.info(f"Script: {len(script.split())} words")
    return script

def extract_narrator_text(script):
    import re
    text = re.sub(r'\[VISUAL CUE:[^\]]*\]', '', script, flags=re.IGNORECASE)
    text = re.sub(r'\[(HOOK|NEWS|POINT \d+|CTA|INTRO|OUTRO)[^\]]*\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\*+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
