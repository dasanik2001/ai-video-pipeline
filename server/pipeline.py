#!/usr/bin/env python3
import os
import sys
import re
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich import print as rprint

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
from viral_detector import detect_viral_moments
from video_processor import render_reel

console = Console()

def sanitize_filename(name: str) -> str:
    """Sanitize string for file naming."""
    name = re.sub(r'[^\w\s-]', '', name).strip()
    return re.sub(r'[-\s]+', '_', name)[:40]

def format_seconds(seconds: float) -> str:
    """Convert seconds to mm:ss format."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}:{s:02d}"

def display_banner():
    banner = """
    [bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]
    [bold cyan]║[/bold cyan]  [bold yellow]⚡ YOUTUBE TO VIRAL REELS AI PIPELINE ⚡[/bold yellow]                    [bold cyan]║[/bold cyan]
    [bold cyan]║[/bold cyan]  [dim]Turn long YouTube videos into viral 9:16 Shorts & Reels[/dim]     [bold cyan]║[/bold cyan]
    [bold cyan]║[/bold cyan]  [dim]Powered by Gemini 2.5 Flash / Claude 3.7 Sonnet & FFmpeg[/dim]    [bold cyan]║[/bold cyan]
    [bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]
    """
    console.print(banner)

def check_keys(engine: str):
    """Verify appropriate API keys exist."""
    has_gemini = bool(GEMINI_API_KEY)
    has_anthropic = bool(ANTHROPIC_API_KEY)

    if engine == "gemini" and not has_gemini:
        console.print("[bold red]Error:[/bold red] GEMINI_API_KEY is not set in your .env file.")
        console.print("Please add it to .env: [green]GEMINI_API_KEY=your_key_here[/green]")
        sys.exit(1)
    elif engine == "anthropic" and not has_anthropic:
        console.print("[bold red]Error:[/bold red] ANTHROPIC_API_KEY is not set in your .env file.")
        console.print("Please add it to .env: [green]ANTHROPIC_API_KEY=your_key_here[/green]")
        sys.exit(1)
    elif engine == "auto" and not (has_gemini or has_anthropic):
        console.print("[bold red]Error:[/bold red] No API key detected!")
        console.print("Please provide at least [yellow]GEMINI_API_KEY[/yellow] or [yellow]ANTHROPIC_API_KEY[/yellow] in your .env file.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Automated pipeline to find viral moments from YouTube videos and render vertical 9:16 reels."
    )
    parser.add_argument("--url", "-u", type=str, help="YouTube video URL")
    parser.add_argument("--count", "-c", type=int, default=3, help="Number of viral reels to produce (default: 3)")
    parser.add_argument("--engine", "-e", choices=["auto", "gemini", "anthropic"], default="auto", help="AI Engine (default: auto)")
    parser.add_argument("--min-duration", type=float, default=DEFAULT_MIN_DURATION, help="Minimum reel duration in seconds (default: 20)")
    parser.add_argument("--max-duration", type=float, default=DEFAULT_MAX_DURATION, help="Maximum reel duration in seconds (default: 60)")
    parser.add_argument("--output-dir", "-o", type=str, default=str(OUTPUT_DIR), help="Output directory for generated reels")
    parser.add_argument("--with-subtitles", action="store_true", default=False, help="Burn external subtitles (disabled by default)")
    parser.add_argument("--with-banner", action="store_true", default=False, help="Add top hook headline banner (disabled by default)")
    parser.add_argument("--dry-run", action="store_true", help="Only analyze and list viral moments without rendering video")

    args = parser.parse_args()

    display_banner()
    check_keys(args.engine)

    # 1. Prompt URL if not provided
    url = args.url
    if not url:
        url = console.input("[bold yellow]Enter YouTube Video URL:[/bold yellow] ").strip()
        if not url:
            console.print("[red]No URL provided. Exiting.[/red]")
            sys.exit(1)

    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 2. Extract Video Info & Transcript
    try:
        video_id = extract_video_id(url)
    except Exception as e:
        console.print(f"[bold red]Invalid URL:[/bold red] {e}")
        sys.exit(1)

    with console.status("[bold green]Fetching video metadata & transcript...", spinner="dots"):
        try:
            info = get_video_info(url)
            title = info.get("title", "Untitled")
            uploader = info.get("uploader", "Unknown")
            duration = info.get("duration", 0)

            segments = get_transcript(video_id)
            formatted_transcript = format_transcript_for_prompt(segments)
        except Exception as e:
            console.print(f"[bold red]Failed to fetch video information or transcript:[/bold red] {e}")
            sys.exit(1)

    duration_str = format_seconds(duration)
    info_panel = f"""[bold white]{title}[/bold white]
[dim]Channel:[/dim] [cyan]{uploader}[/cyan] | [dim]Length:[/dim] [yellow]{duration_str}[/yellow] ({duration}s) | [dim]Transcript Words:[/dim] [green]{sum(len(s.text.split()) for s in segments)}[/green]"""
    console.print(Panel(info_panel, title="[bold]Video Details[/bold]", border_style="cyan"))

    # 3. Analyze for Viral Moments
    with console.status(f"[bold magenta]Analyzing viral potential using AI ({args.engine})...", spinner="bouncingBar"):
        try:
            analysis = detect_viral_moments(
                title=title,
                uploader=uploader,
                duration=duration,
                formatted_transcript=formatted_transcript,
                count=args.count,
                min_duration=args.min_duration,
                max_duration=args.max_duration,
                engine=args.engine,
            )
        except Exception as e:
            console.print(f"[bold red]AI Analysis failed:[/bold red] {e}")
            sys.exit(1)

    if not analysis.viral_moments:
        console.print("[bold red]No viral moments detected within duration constraints.[/bold red]")
        sys.exit(0)

    # 4. Display Analysis Table
    table = Table(title="[bold yellow]🔥 Detected Viral Moments[/bold yellow]", border_style="yellow")
    table.add_column("#", style="dim", width=4)
    table.add_column("Score", style="bold magenta", width=7)
    table.add_column("Timestamps", style="cyan", width=14)
    table.add_column("Duration", style="yellow", width=10)
    table.add_column("Hook / Title", style="bold white")
    table.add_column("Viral Reason", style="dim")

    for i, m in enumerate(analysis.viral_moments, start=1):
        time_range = f"{format_seconds(m.start_time)} - {format_seconds(m.end_time)}"
        dur_text = f"{m.duration:.1f}s"
        score_badge = f"{m.viral_score}/100"
        hook_display = f"[bold]{m.hook}[/bold]\n[dim]{m.title}[/dim]"
        table.add_row(str(i), score_badge, time_range, dur_text, hook_display, m.reason[:80] + "...")

    console.print(table)

    if args.dry_run:
        console.print("\n[bold green]--dry-run enabled.[/bold green] Analysis complete without rendering videos.")
        return

    # 5. Download Source Video
    source_video_path = TEMP_DIR / f"{video_id}.mp4"
    if not source_video_path.exists():
        console.print("\n[bold blue]Downloading source video (up to 1080p)...[/bold blue]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Downloading...", total=None)
            try:
                download_video(url, source_video_path)
                progress.update(task, completed=100, description="[bold green]Download Complete![/bold green]")
            except Exception as e:
                console.print(f"[bold red]Video download failed:[/bold red] {e}")
                sys.exit(1)
    else:
        console.print(f"\n[dim]Using cached source video: {source_video_path.name}[/dim]")

    # 6. Render Vertical Reels
    console.print(f"\n[bold green]🎬 Rendering {len(analysis.viral_moments)} Vertical 9:16 Reels...[/bold green]")
    rendered_files = []

    for idx, m in enumerate(analysis.viral_moments, start=1):
        clean_title = sanitize_filename(m.title)
        out_name = f"reel_{idx}_score{m.viral_score}_{clean_title}.mp4"
        out_file = output_path / out_name

        with console.status(f"[bold cyan]Rendering Reel #{idx}: {m.hook} ({m.duration:.1f}s)...", spinner="dots"):
            try:
                render_reel(
                    source_video_path=source_video_path,
                    moment=m,
                    output_file=out_file,
                    all_segments=segments,
                    with_subtitles=args.with_subtitles,
                    with_hook_banner=args.with_banner,
                )
                rendered_files.append((out_file, m))
                console.print(f"  [bold green]✓[/bold green] Reel #{idx} created: [cyan]{out_file.name}[/cyan] ({m.duration:.1f}s)")
            except Exception as e:
                console.print(f"  [bold red]✗[/bold red] Failed to render Reel #{idx}: {e}")

    # 7. Summary
    if rendered_files:
        summary_panel = f"[bold green]Successfully generated {len(rendered_files)} Reels![/bold green]\n\n"
        for f, m in rendered_files:
            summary_panel += f"• [bold white]{f.name}[/bold white]\n"
            summary_panel += f"  Location: [blue]{f.resolve()}[/blue]\n"
            summary_panel += f"  Hook: [yellow]{m.hook}[/yellow] (Score: {m.viral_score})\n\n"
        console.print(Panel(summary_panel, title="[bold]Export Complete[/bold]", border_style="green"))

if __name__ == "__main__":
    main()
