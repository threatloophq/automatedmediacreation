import os
import logging
from groq import Groq

log = logging.getLogger(__name__)

def generate_script(topic):
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set.")
    client = Groq(api_key=api_key)
    prompt = f"""Write a 60-second faceless video script about: "{topic}"
Rules:
- Hook in first 5 seconds (bold claim or shocking stat)
- 3 key points in the body (40 seconds)
- Strong CTA at end (subscribe/follow)
- Include 6 [VISUAL CUE: description] markers
- No filler words, no intro like hey guys
- Write only narrator text
Format: [HOOK] [VISUAL CUE: ...] narrator text, [POINT 1] etc."""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
    )
    return response.choices[0].message.content.strip()

def extract_narrator_text(script):
    lines = []
    for line in script.splitlines():
        s = line.strip()
        if s and not any(s.startswith(x) for x in ["[VISUAL", "[HOOK", "[POINT", "[CTA"]):
            lines.append(s)
    return " ".join(lines)
