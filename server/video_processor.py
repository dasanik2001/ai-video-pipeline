import subprocess
import re
from pathlib import Path
from typing import List, Optional
from models import ViralMoment, TranscriptSegment
from config import TARGET_WIDTH, TARGET_HEIGHT, OUTPUT_DIR, TEMP_DIR

def format_ass_timestamp(seconds: float) -> str:
    """Format seconds into ASS timestamp format: H:MM:SS.cs"""
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def split_text_into_chunks(text: str, max_words: int = 5) -> List[str]:
    """Break long sentences into short dynamic subtitle bursts (TikTok style)."""
    words = text.split()
    if not words:
        return []
    chunks = []
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i:i + max_words]))
    return chunks

def generate_ass_subtitles(
    moment: ViralMoment,
    all_segments: List[TranscriptSegment],
    output_ass_path: Path,
    include_hook_banner: bool = True,
    hook_duration: float = 6.0,
) -> Path:
    """
    Generate styled ASS subtitle file for the specific clip segment.
    Features:
    - Bold, high-contrast captions placed in the vertical video safe zone.
    - Optional eye-catching Hook Banner at top.
    """
    start_offset = moment.start_time
    end_offset = moment.end_time

    # Filter segments that fall within this reel
    relevant_segments: List[TranscriptSegment] = []
    for seg in all_segments:
        # Check overlap
        if seg.end > start_offset and seg.start < end_offset:
            # Clip bounds
            c_start = max(seg.start, start_offset) - start_offset
            c_end = min(seg.end, end_offset) - start_offset
            if c_end > c_start:
                relevant_segments.append(TranscriptSegment(
                    text=seg.text,
                    start=c_start,
                    duration=c_end - c_start
                ))

    # ASS Header with high-readability TikTok styles
    # Colors in ASS are &HAABBGGRR:
    # &H0000FFFF = Bright Yellow
    # &H00FFFFFF = Pure White
    # &H80000000 = Semi-transparent Black Box/Shadow
    ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {TARGET_WIDTH}
PlayResY: {TARGET_HEIGHT}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HookBanner,Arial,52,&H0000FFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,1,0,1,5,3,8,60,60,200,1
Style: Captions,Arial,66,&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogues = []

    # 1. Top Hook Banner
    if include_hook_banner and moment.hook:
        clean_hook = moment.hook.upper().strip()
        banner_end = min(hook_duration, moment.duration)
        dialogues.append(
            f"Dialogue: 1,{format_ass_timestamp(0)},{format_ass_timestamp(banner_end)},HookBanner,,0,0,0,,{clean_hook}"
        )

    # 2. Synchronized Captions
    for seg in relevant_segments:
        # Split segment into smaller chunks for fast-paced reading
        chunks = split_text_into_chunks(seg.text, max_words=5)
        if not chunks:
            continue
        chunk_duration = seg.duration / len(chunks)

        for i, chunk in enumerate(chunks):
            chunk_start = seg.start + (i * chunk_duration)
            chunk_end = chunk_start + chunk_duration
            dialogues.append(
                f"Dialogue: 0,{format_ass_timestamp(chunk_start)},{format_ass_timestamp(chunk_end)},Captions,,0,0,0,,{chunk.upper()}"
            )

    full_ass = ass_header + "\n".join(dialogues) + "\n"
    output_ass_path.write_text(full_ass, encoding='utf-8')
    return output_ass_path


def get_video_duration(video_path: Path) -> float:
    """Retrieve total duration of video in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0

def get_video_dimensions(video_path: Path) -> tuple[int, int]:
    """Retrieve width and height of video using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            str(video_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        w, h = res.stdout.strip().split("x")
        return int(w), int(h)
    except Exception:
        return 1920, 1080

def render_reel(
    source_video_path: Path,
    moment: ViralMoment,
    output_file: Path,
    all_segments: Optional[List[TranscriptSegment]] = None,
    with_subtitles: bool = False,
    with_hook_banner: bool = False,
) -> Path:
    """
    Render a 9:16 vertical video reel keeping the FULL WIDTH of the video
    with clean black bars on top and bottom.
    External subtitles and banners are disabled by default.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Validate timestamps against source video duration
    source_dur = get_video_duration(source_video_path)
    if source_dur > 0:
        if moment.start_time >= source_dur:
            raise ValueError(
                f"Requested start time ({moment.start_time:.1f}s) exceeds total video length ({source_dur:.1f}s). "
                f"Please choose a timestamp before {source_dur:.1f}s."
            )
        if moment.end_time > source_dur:
            moment.end_time = source_dur
            moment.duration = moment.end_time - moment.start_time

    # Generate ASS subtitles only if explicitly requested
    ass_path = None
    if with_subtitles and all_segments:
        ass_path = TEMP_DIR / f"sub_{output_file.stem}.ass"
        generate_ass_subtitles(
            moment=moment,
            all_segments=all_segments,
            output_ass_path=ass_path,
            include_hook_banner=with_hook_banner,
        )

    # Preserve FULL WIDTH: scale to fit 9:16 canvas and pad with black bars on top and bottom
    w, h = get_video_dimensions(source_video_path)
    if w >= 3840 or h >= 2160:
        canvas_w, canvas_h = 2160, 3840  # 4K Vertical
    elif w >= 2560 or h >= 1440:
        canvas_w, canvas_h = 1440, 2560  # 2K Vertical
    else:
        canvas_w, canvas_h = 1080, 1920  # Full HD Vertical

    filter_parts = [
        f"scale={canvas_w}:{canvas_h}:force_original_aspect_ratio=decrease:flags=lanczos",
        f"pad={canvas_w}:{canvas_h}:(ow-iw)/2:(oh-ih)/2:black"
    ]

    # Add ASS subtitles only if explicitly enabled
    if ass_path and ass_path.exists():
        escaped_ass = ass_path.as_posix().replace(":", "\\:").replace("'", "\\'")
        filter_parts.append(f"ass='{escaped_ass}'")

    vf_chain = ",".join(filter_parts)

    temp_render_path = output_file.with_suffix(".rendering.mp4")

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(moment.start_time),
        "-to", str(moment.end_time),
        "-i", str(source_video_path),
        "-vf", vf_chain,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "320k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(temp_render_path),
    ]

    process = subprocess.run(cmd, capture_output=True, text=True)
    if process.returncode != 0:
        if temp_render_path.exists():
            temp_render_path.unlink()
        raise RuntimeError(f"FFmpeg failed while rendering {output_file.name}:\n{process.stderr}")

    if temp_render_path.exists():
        temp_render_path.replace(output_file)

    # Clean up temp ass
    if ass_path and ass_path.exists():
        try:
            ass_path.unlink()
        except Exception:
            pass

    return output_file
