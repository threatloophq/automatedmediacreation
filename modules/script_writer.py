import os
import logging
from groq import Groq

log = logging.getLogger(__name__)

def generate_script(topic, summary="", video_type="short"):
    if video_type == "long_form":
        return _generate_long_simple(topic, summary)
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

def _generate_long_simple(topic, summary):
    import os
    from groq import Groq
    from datetime import datetime
    api_key = os.getenv("GROQ_API_KEY", "")
    client = Groq(api_key=api_key)
    context = f"\nLatest news: {summary[:400]}" if summary else ""
    styles = [
        "professional news anchor — authoritative and clear",
        "friendly educator — like a knowledgeable friend",
        "dramatic storyteller — cinematic and tension-building",
        "fast-paced energetic — high energy like MrBeast",
    ]
    style = styles[datetime.utcnow().weekday() % len(styles)]

    prompt = f"""Write a detailed 5-6 minute YouTube video script for ThreatLoopHQ about:
Topic: {topic}{context}
Voice style: {style}

Include ALL these sections with [SECTION_NAME] labels and [VISUAL CUE: scene] markers:

[HOOK] — 30 sec — shocking stat or claim (60-80 words)
[NEWS_EXPLAINER] — 60 sec — what happened, who is affected, impact (120-140 words)
[WHY_IT_MATTERS] — 45 sec — why every viewer should care personally (90-110 words)
[TUTORIAL] — 90 sec — 3 specific actionable steps with tool names (150-180 words)
[TOP_TOOLS] — 90 sec — exactly 5 tools: name, what it does, free/paid (150-180 words)
[EXPERT_INSIGHT] — 60 sec — surprising perspective most people get wrong (100-120 words)
[CTA] — 30 sec — subscribe, comment, share with urgency (50-60 words)

RULES:
- Total 700-800 words narrator text
- Every VISUAL CUE must be a real photographable scene
- No filler phrases
- Make every sentence teach, shock or create curiosity
- Be specific with real tool names, real stats, real examples"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000, temperature=0.85,
    )
    script = response.choices[0].message.content.strip()
    log.info(f"Long form script: {len(script.split())} words")
    return script
