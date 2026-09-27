import json
import re
from typing import List, Optional
from google import genai
from google.genai import types
import anthropic

from models import AnalysisResponse, ViralMoment, TranscriptSegment
from config import (
    GEMINI_API_KEY,
    ANTHROPIC_API_KEY,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_MIN_DURATION,
    DEFAULT_MAX_DURATION,
)

SYSTEM_PROMPT = """You are an elite short-form video producer, viral strategist, and algorithm specialist for TikTok, YouTube Shorts, and Instagram Reels.
Your objective is to analyze a timestamped transcript of a video and identify the highest potential viral segments to cut into vertical 9:16 reels.

VIRALITY CRITERIA (Score 1-100):
1. **The 3-Second Hook**: The clip must start with a captivating sentence, controversial statement, shocking counter-intuitive truth, high-stakes question, or intriguing mystery. Reject any clip that starts with slow pleasantries ("So today we...", "Thanks for having me").
2. **Pacing & High Retention**: High energy, no filler, maximum value or emotional payoff per second.
3. **Standalone Value**: The clip must make complete sense on its own. The viewer should never need context from before or after the clip.
4. **Clean Cut Boundaries**:
   - MUST start cleanly at the very beginning of a punchy sentence.
   - MUST end cleanly at the end of a sentence (a punchline, mic-drop conclusion, or intriguing takeaway). Never cut off a speaker mid-word or mid-sentence.
5. **Length Constraints**: Each segment MUST strictly be between {min_duration} and {max_duration} seconds.

Output must strictly follow the required JSON structure.
"""

USER_PROMPT_TEMPLATE = """Video Title: {title}
Video Uploader: {uploader}
Duration: {duration} seconds

Here is the timestamped transcript:
---
{formatted_transcript}
---

Find the top {count} segments that have the highest probability of going viral on Instagram Reels, TikTok, and YouTube Shorts.
CRITICAL CONSTRAINT:
- The video duration is {duration} seconds.
- Both start_time and end_time MUST be strictly within [0, {duration}] seconds. Never output a timestamp exceeding {duration} seconds.

For each segment:
- `title`: Catchy, punchy title for this reel.
- `hook`: Engaging text overlay for the top of the video (in ALL CAPS, max 7 words, e.g. "HOW MILLIONAIRES THINK DIFFERENTLY").
- `start_time`: Precise start timestamp in seconds (must align with sentence boundary and be < {duration}).
- `end_time`: Precise end timestamp in seconds (must align with sentence boundary and be <= {duration}).
- `duration`: end_time - start_time (must be between {min_duration} and {max_duration} seconds).
- `viral_score`: 1-100 rating based on hook strength, retention likelihood, and shareability.
- `reason`: Concrete breakdown of why this moment will hook the viewer and hold retention.
- `key_quote`: The most impactful quote in the segment.

Rank the moments from highest viral score to lowest.
"""

def analyze_with_gemini(
    title: str,
    uploader: str,
    duration: float,
    formatted_transcript: str,
    count: int = 3,
    min_duration: float = DEFAULT_MIN_DURATION,
    max_duration: float = DEFAULT_MAX_DURATION,
    model_name: str = DEFAULT_GEMINI_MODEL,
    api_key: Optional[str] = None,
) -> AnalysisResponse:
    """Analyze transcript for viral moments using Google Gemini."""
    key = api_key or GEMINI_API_KEY
    if not key:
        raise ValueError("GEMINI_API_KEY is not set. Please set it in .env or pass it.")

    client = genai.Client(api_key=key)

    system_instruction = SYSTEM_PROMPT.format(min_duration=min_duration, max_duration=max_duration)
    prompt = USER_PROMPT_TEMPLATE.format(
        title=title,
        uploader=uploader,
        duration=duration,
        formatted_transcript=formatted_transcript,
        count=count,
        min_duration=min_duration,
        max_duration=max_duration,
    )

    candidate_models = [model_name, "gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]
    # Deduplicate while preserving order
    seen = set()
    models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]

    last_error = None
    response = None

    for m in models_to_try:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=AnalysisResponse,
                        temperature=0.3,
                    ),
                )
                if response and response.text:
                    break
            except Exception as e:
                last_error = e
                import time
                time.sleep(1.5)
        if response and response.text:
            break

    if not response or not response.text:
        raise RuntimeError(f"Gemini API generation failed after trying models {models_to_try}: {last_error}")

    try:
        raw_text = response.text
        data = json.loads(raw_text)
        result = AnalysisResponse.model_validate(data)
        # Validate and clamp moments within video duration
        valid_moments = []
        for m in result.viral_moments:
            if m.start_time < duration:
                m.end_time = min(m.end_time, duration)
                m.duration = round(m.end_time - m.start_time, 1)
                if m.duration >= 10.0:
                    valid_moments.append(m)
        result.viral_moments = valid_moments
        return result
    except Exception as e:
        raise RuntimeError(f"Failed to parse Gemini response as AnalysisResponse: {e}\nRaw output: {response.text}")


def analyze_with_anthropic(
    title: str,
    uploader: str,
    duration: float,
    formatted_transcript: str,
    count: int = 3,
    min_duration: float = DEFAULT_MIN_DURATION,
    max_duration: float = DEFAULT_MAX_DURATION,
    model_name: str = DEFAULT_ANTHROPIC_MODEL,
    api_key: Optional[str] = None,
) -> AnalysisResponse:
    """Analyze transcript for viral moments using Anthropic Claude."""
    key = api_key or ANTHROPIC_API_KEY
    if not key:
        raise ValueError("ANTHROPIC_API_KEY is not set. Please set it in .env or pass it.")

    client = anthropic.Anthropic(api_key=key)

    system_instruction = SYSTEM_PROMPT.format(min_duration=min_duration, max_duration=max_duration)
    prompt = USER_PROMPT_TEMPLATE.format(
        title=title,
        uploader=uploader,
        duration=duration,
        formatted_transcript=formatted_transcript,
        count=count,
        min_duration=min_duration,
        max_duration=max_duration,
    )

    prompt += "\nIMPORTANT: Return ONLY a raw JSON object matching the requested schema. Do not wrap in markdown or include any explanations."

    response = client.messages.create(
        model=model_name,
        max_tokens=4000,
        temperature=0.3,
        system=system_instruction,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    # Clean json formatting if wrapped in codeblocks
    cleaned_json = re.sub(r'^```json\s*', '', raw_text.strip(), flags=re.MULTILINE)
    cleaned_json = re.sub(r'```$', '', cleaned_json.strip(), flags=re.MULTILINE)

    try:
        data = json.loads(cleaned_json)
        result = AnalysisResponse.model_validate(data)
        # Validate and clamp moments within video duration
        valid_moments = []
        for m in result.viral_moments:
            if m.start_time < duration:
                m.end_time = min(m.end_time, duration)
                m.duration = round(m.end_time - m.start_time, 1)
                if m.duration >= 10.0:
                    valid_moments.append(m)
        result.viral_moments = valid_moments
        return result
    except Exception as e:
        raise RuntimeError(f"Failed to parse Anthropic response as AnalysisResponse: {e}\nRaw output: {raw_text}")


def detect_viral_moments(
    title: str,
    uploader: str,
    duration: float,
    formatted_transcript: str,
    count: int = 3,
    min_duration: float = DEFAULT_MIN_DURATION,
    max_duration: float = DEFAULT_MAX_DURATION,
    engine: str = "auto",
) -> AnalysisResponse:
    """
    Selects the appropriate AI engine (Gemini or Anthropic) and runs viral moment detection.
    """
    chosen_engine = engine.lower()

    if chosen_engine == "auto":
        if GEMINI_API_KEY:
            chosen_engine = "gemini"
        elif ANTHROPIC_API_KEY:
            chosen_engine = "anthropic"
        else:
            raise ValueError("Neither GEMINI_API_KEY nor ANTHROPIC_API_KEY found in environment or .env file.")

    if chosen_engine == "gemini":
        return analyze_with_gemini(
            title=title,
            uploader=uploader,
            duration=duration,
            formatted_transcript=formatted_transcript,
            count=count,
            min_duration=min_duration,
            max_duration=max_duration,
        )
    elif chosen_engine == "anthropic":
        return analyze_with_anthropic(
            title=title,
            uploader=uploader,
            duration=duration,
            formatted_transcript=formatted_transcript,
            count=count,
            min_duration=min_duration,
            max_duration=max_duration,
        )
    else:
        raise ValueError(f"Unknown engine '{engine}'. Choose 'gemini', 'anthropic', or 'auto'.")
