import re
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from models import TranscriptSegment
from config import TEMP_DIR

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various YouTube URL formats."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/|v\/|shorts\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract YouTube video ID from URL: {url}")

def get_video_info(url: str) -> Dict[str, Any]:
    """Retrieve video metadata without downloading the full video."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            'id': info.get('id'),
            'title': info.get('title'),
            'uploader': info.get('uploader'),
            'duration': info.get('duration', 0),
            'description': info.get('description', ''),
            'thumbnail': info.get('thumbnail', ''),
            'webpage_url': info.get('webpage_url', url),
        }

def get_transcript(video_id: str) -> List[TranscriptSegment]:
    """
    Fetch timestamped transcript snippets using youtube_transcript_api.
    Tries user-specified languages or automatic fallbacks.
    """
    api = YouTubeTranscriptApi()
    snippets = None

    # Try fetching English or native transcript directly
    try:
        fetched = api.fetch(video_id, languages=['en', 'en-US', 'en-GB'])
        snippets = fetched.snippets
    except Exception:
        pass

    # If direct fetch fails, inspect available transcripts
    if not snippets:
        try:
            transcript_list = api.list(video_id)
            # Try manual transcript first, then generated transcript
            t = None
            try:
                t = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
            except Exception:
                pass

            if not t:
                try:
                    t = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB'])
                except Exception:
                    pass

            if not t:
                # Pick the first available transcript
                available = list(transcript_list)
                if available:
                    t = available[0]

            if t:
                snippets = t.fetch().snippets
        except Exception as e:
            raise RuntimeError(f"Could not retrieve captions/transcript for video {video_id}: {e}")

    if not snippets:
        raise RuntimeError(f"No transcripts found for video {video_id}.")

    segments: List[TranscriptSegment] = []
    for s in snippets:
        text = s.text.replace('\n', ' ').strip()
        if text:
            segments.append(TranscriptSegment(
                text=text,
                start=float(s.start),
                duration=float(s.duration)
            ))

    return segments

def format_transcript_for_prompt(segments: List[TranscriptSegment]) -> str:
    """Format segments into clean timestamped text blocks for LLM reasoning."""
    lines = []
    for s in segments:
        m, sec = divmod(int(s.start), 60)
        lines.append(f"[{m:02d}:{sec:02d}] {s.text}")
    return "\n".join(lines)

def download_video(url: str, output_path: Path) -> Path:
    """
    Download video up to 1080p with audio merged into an MP4 file.
    If the file already exists, returns it directly.
    """
    if output_path.exists():
        return output_path

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': str(output_path),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return output_path

def download_audio_for_transcription(url: str, output_path: Path) -> Path:
    """Download low-bitrate audio for LLM transcription fallback."""
    if output_path.exists():
        return output_path

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio',
        'outtmpl': str(output_path),
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return output_path
