# ⚡ YouTube to Viral Reels AI Pipeline

An automated AI pipeline that transforms long-form YouTube videos (podcasts, interviews, talks, tutorials) into viral 9:16 vertical Reels, Shorts, and TikToks.

Powered by **Gemini 2.5 Flash / Claude 3.7 Sonnet** for short-form retention analysis and **FFmpeg** for vertical reframing, hook overlays, and stylized burned-in captions.

---

## 🚀 Features

- **Automated Virality Detection**:
  - **The 3-Second Hook Rule**: Identifies high-curiosity opening statements, spicy questions, or counter-intuitive claims.
  - **Retention & Emotional Pacing**: Filters out introductory filler, small talk, and pleasantries.
  - **Standalone Cohesion**: Ensures the segment starts cleanly at the beginning of a sentence and ends with a complete takeaway or punchline.
  - **Viral Score (1-100)**: Evaluates hook strength, emotional engagement, and shareability.
- **Dual AI Engine Support**:
  - Use **Google Gemini** (`gemini-2.5-flash` or `gemini-1.5-pro`) or **Anthropic Claude** (`claude-3-7-sonnet` or `claude-3-5-sonnet`), with automatic fallback.
- **Vertical 9:16 Full-Width Letterboxing**:
  - Preserves 100% of the video's full width with clean black bars on the top and bottom on a 9:16 vertical canvas.
- **Direct YouTube Studio Upload**:
  - Link your YouTube channel with Google OAuth 2.0.
  - One-click publishing to **YouTube Shorts** with custom title, description, hashtags, and privacy settings (Public, Unlisted, Private).
- **TikTok/Reels Stylized Captions & Banners (Optional)**:
  - Toggleable burned-in subtitles and hook overlay headlines.

---

## 🛠️ Quick Setup

### 1. Configure API Keys
Open `.env` in the project root and add your API keys:

```bash
# In /Users/anik/Desktop/ai-pipeline/.env
GEMINI_API_KEY=your_actual_gemini_api_key
ANTHROPIC_API_KEY=your_actual_anthropic_api_key
```

> **Note**: You only need **one** API key to get started (Gemini or Anthropic), or provide both to switch between them anytime.

---

## 💻 How to Run

### 🌐 Option 1: Modern Web Studio (Recommended)
Launch the browser UI to visually analyze moments, edit timestamps, preview 9:16 vertical clips, and download reels:

```bash
.venv/bin/python run_web.py
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

---

### ⌨️ Option 2: Command-Line Interface (CLI)

#### 1. Interactive CLI Run
Run the pipeline without arguments to be prompted for a YouTube URL:
```bash
.venv/bin/python pipeline.py
```

### 2. Specify URL and Reel Count
Generate the top 3 viral reels from a YouTube video:
```bash
.venv/bin/python pipeline.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --count 3
```

### 3. Choose AI Engine
Force the pipeline to use Gemini or Anthropic Claude:
```bash
# Use Google Gemini
.venv/bin/python pipeline.py --url "https://youtu.be/VIDEO_ID" --engine gemini

# Use Anthropic Claude
.venv/bin/python pipeline.py --url "https://youtu.be/VIDEO_ID" --engine anthropic
```

### 4. Dry Run (Analyze Moments Without Rendering Video)
Inspect the detected viral moments, scores, hooks, and timestamps in seconds without downloading or rendering:
```bash
.venv/bin/python pipeline.py --url "https://youtu.be/VIDEO_ID" --dry-run
```

### 5. Custom Duration & Options
```bash
.venv/bin/python pipeline.py \
  --url "https://youtu.be/VIDEO_ID" \
  --count 5 \
  --min-duration 30 \
  --max-duration 55 \
  --output-dir ./my_reels
```

---

## 📁 Project Structure

```
ai-pipeline/
├── .env                # API keys (GEMINI_API_KEY, ANTHROPIC_API_KEY)
├── config.py           # Project settings, model choices, resolutions
├── downloader.py       # YouTube metadata & timestamped transcript extraction
├── models.py           # Pydantic data schemas for viral moments & transcripts
├── viral_detector.py   # AI virality analysis engine (Gemini & Anthropic)
├── video_processor.py  # FFmpeg 9:16 vertical crop, hook banner, & ASS subtitles
├── pipeline.py         # Rich CLI interface with tables and progress bars
├── requirements.txt    # Project dependencies
└── output_reels/       # Rendered vertical reels ready for posting
```

---

## ⚙️ Command-Line Options Reference

| Argument | Short | Default | Description |
| :--- | :--- | :--- | :--- |
| `--url` | `-u` | Prompted | YouTube video URL (standard, shortened, or shorts) |
| `--count` | `-c` | `3` | Number of top viral moments to render |
| `--engine` | `-e` | `auto` | AI engine: `auto`, `gemini`, or `anthropic` |
| `--min-duration` | | `20.0` | Minimum duration in seconds for each reel |
| `--max-duration` | | `60.0` | Maximum duration in seconds for each reel |
| `--output-dir` | `-o` | `./output_reels`| Folder where rendered reels are saved |
| `--no-subtitles` | | `False` | Disable burning stylized subtitles |
| `--no-banner` | | `False` | Disable top hook headline banner |
| `--dry-run` | | `False` | Show viral analysis table without rendering video |
