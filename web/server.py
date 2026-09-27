import os
import re
import sys
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
import youtube_uploader

# Ensure parent directory is on python path to import existing modules
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import (
    TEMP_DIR,
    OUTPUT_DIR,
    GEMINI_API_KEY,
    ANTHROPIC_API_KEY,
    DEFAULT_MIN_DURATION,
    DEFAULT_MAX_DURATION,
)
from downloader import (
    extract_video_id,
    get_video_info,
    get_transcript,
    format_transcript_for_prompt,
    download_video,
)
from models import ViralMoment, TranscriptSegment
from viral_detector import detect_viral_moments
from video_processor import render_reel

app = FastAPI(title="ViralReel AI Studio")

# Disable browser caching in development to ensure latest JS and CSS are always loaded
@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

STATIC_DIR = CURRENT_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount generated reels for direct browser streaming and download
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
# Mount static UI assets
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class AnalyzeRequest(BaseModel):
    url: str
    count: int = 3
    engine: str = "auto"
    min_duration: float = DEFAULT_MIN_DURATION
    max_duration: float = DEFAULT_MAX_DURATION

class RenderRequest(BaseModel):
    url: str
    video_id: str
    moment: ViralMoment
    with_subtitles: bool = False
    with_banner: bool = False

@app.get("/")
def get_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
    return FileResponse(index_file)

@app.get("/api/status")
def get_status():
    has_gemini = bool(GEMINI_API_KEY)
    has_anthropic = bool(ANTHROPIC_API_KEY)
    default_engine = "gemini" if has_gemini else ("anthropic" if has_anthropic else "none")
    return {
        "gemini_connected": has_gemini,
        "anthropic_connected": has_anthropic,
        "default_engine": default_engine,
    }

@app.post("/api/analyze")
def analyze_video(req: AnalyzeRequest):
    try:
        video_id = extract_video_id(req.url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid YouTube URL: {str(e)}")

    try:
        info = get_video_info(req.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch video information: {str(e)}")

    try:
        segments = get_transcript(video_id)
        formatted_transcript = format_transcript_for_prompt(segments)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not extract transcript for video: {str(e)}")

    try:
        analysis = detect_viral_moments(
            title=info.get("title", "Untitled"),
            uploader=info.get("uploader", "Unknown"),
            duration=info.get("duration", 0),
            formatted_transcript=formatted_transcript,
            count=req.count,
            min_duration=req.min_duration,
            max_duration=req.max_duration,
            engine=req.engine,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI virality analysis failed: {str(e)}")

    return {
        "video_info": info,
        "viral_moments": analysis.viral_moments,
        "summary": analysis.video_summary,
        "transcript_segment_count": len(segments),
    }

@app.post("/api/render")
def render_reel_endpoint(req: RenderRequest):
    try:
        video_id = extract_video_id(req.url)
    except Exception:
        video_id = req.video_id

    source_video_path = TEMP_DIR / f"{video_id}.mp4"
    if not source_video_path.exists():
        try:
            download_video(req.url, source_video_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Video download failed: {str(e)}")

    # Fetch transcript segments for subtitles if requested
    all_segments = None
    if req.with_subtitles:
        try:
            all_segments = get_transcript(video_id)
        except Exception:
            all_segments = None

    clean_title = re.sub(r'[^\w\s-]', '', req.moment.title).strip()
    clean_title = re.sub(r'[-\s]+', '_', clean_title)[:35]
    out_filename = f"reel_{video_id}_s{int(req.moment.start_time)}_e{int(req.moment.end_time)}_{clean_title}.mp4"
    output_file = OUTPUT_DIR / out_filename

    try:
        render_reel(
            source_video_path=source_video_path,
            moment=req.moment,
            output_file=output_file,
            all_segments=all_segments,
            with_subtitles=req.with_subtitles,
            with_hook_banner=req.with_banner,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rendering failed: {str(e)}")

    file_size_mb = round(output_file.stat().st_size / (1024 * 1024), 2)
    return {
        "success": True,
        "filename": out_filename,
        "url": f"/output/{out_filename}",
        "size_mb": file_size_mb,
        "duration": req.moment.duration,
    }

@app.get("/api/reels")
def list_reels():
    reels = []
    for f in OUTPUT_DIR.glob("*.mp4"):
        if f.name.endswith(".rendering.mp4"):
            continue
        stat = f.stat()
        if stat.st_size < 10000:
            try:
                f.unlink()
            except Exception:
                pass
            continue
        reels.append({
            "filename": f.name,
            "url": f"/output/{f.name}",
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": stat.st_mtime,
        })
    reels.sort(key=lambda r: r["created_at"], reverse=True)
    return {"reels": reels}

# ===================================================
# YOUTUBE STUDIO DIRECT UPLOAD ENDPOINTS
# ===================================================

class UploadShortRequest(BaseModel):
    filename: str
    title: str
    description: Optional[str] = ""
    privacy: str = "public"

class ClientSecretsRequest(BaseModel):
    content: str

@app.get("/api/youtube/status")
def get_youtube_status():
    is_auth = youtube_uploader.is_authenticated()
    channel = youtube_uploader.get_channel_info() if is_auth else None
    return {
        "has_client_secrets": youtube_uploader.has_client_secrets(),
        "is_authenticated": is_auth,
        "channel": channel,
    }

@app.post("/api/youtube/secrets")
def upload_client_secrets(req: ClientSecretsRequest):
    try:
        youtube_uploader.save_client_secrets(req.content)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/youtube/auth-url")
def get_auth_url():
    try:
        redirect_uri = "http://localhost:8000/api/youtube/callback"
        url = youtube_uploader.get_auth_url(redirect_uri)
        return {"auth_url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/youtube/callback")
def youtube_callback(code: str):
    try:
        redirect_uri = "http://localhost:8000/api/youtube/callback"
        youtube_uploader.exchange_code_for_tokens(code, redirect_uri)
        return RedirectResponse(url="/?youtube=connected")
    except Exception as e:
        return RedirectResponse(url=f"/?youtube=error&detail={str(e)}")

@app.post("/api/youtube/disconnect")
def disconnect_youtube():
    youtube_uploader.disconnect_youtube()
    return {"success": True}

@app.post("/api/youtube/upload")
def upload_to_youtube(req: UploadShortRequest):
    video_path = OUTPUT_DIR / req.filename
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"Reel file {req.filename} not found.")

    try:
        result = youtube_uploader.upload_short(
            file_path=video_path,
            title=req.title,
            description=req.description,
            privacy_status=req.privacy,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube upload failed: {str(e)}")

class SuggestCopyRequest(BaseModel):
    raw_title: str
    hook: Optional[str] = ""
    quote: Optional[str] = ""

@app.post("/api/youtube/suggest-copy")
def suggest_copy(req: SuggestCopyRequest):
    """Generate high-CTR viral titles and descriptions using Gemini."""
    clean_title = re.sub(r"^reel_[^_]+_", "", req.raw_title)
    clean_title = re.sub(r"^s\d+_e\d+_", "", clean_title)
    clean_title = re.sub(r"^score\d+_", "", clean_title)
    clean_title = re.sub(r"\.mp4$", "", clean_title).replace("_", " ").strip()

    prompt = f"""You are a master YouTube Shorts viral strategist and copywriter.
Generate high-CTR, scroll-stopping title and description for a YouTube Short.

Context:
Topic/Moment: {clean_title}
Hook: {req.hook or clean_title}
Key Quote: {req.quote or ""}

Requirements:
1. `catchy_title`: Irresistible curiosity gap, emotional hook, under 70 chars, ending with #Shorts. Use 1 or 2 relevant emojis (🤯, 💀, 🔥, 👀).
2. `alternative_titles`: 2 alternative punchy viral titles under 70 chars ending with #Shorts.
3. `catchy_description`: Engaging 3-line hook, controversial or intriguing question to spark comments (e.g. "Drop your thoughts below 👇"), and 5-7 targeted trending hashtags.

Return ONLY a JSON object:
{{
  "catchy_title": "...",
  "alternative_titles": ["...", "..."],
  "catchy_description": "..."
}}"""

    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        resp = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt,
        )
        text = resp.text
        text = re.sub(r'^```json\s*', '', text.strip(), flags=re.MULTILINE)
        text = re.sub(r'```$', '', text.strip(), flags=re.MULTILINE)
        return json.loads(text)
    except Exception:
        base = clean_title.title()
        return {
            "catchy_title": f"{base} 🤯 #Shorts",
            "alternative_titles": [
                f"The Moment Everything Changed... 💀 #Shorts",
                f"You Won't Believe This Happened! 🔥 #Shorts"
            ],
            "catchy_description": f"Watch closely till the end... 👀\n\nWhat do you think about this? Drop your thoughts below! 👇\n\n#Shorts #Viral #Trending #EpicMoments #Clips"
        }
