# ⚡ ViralReel AI — YouTube to 9:16 Shorts & Reels Studio

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-8E75C2?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)
[![Anthropic Claude](https://img.shields.io/badge/Anthropic%20Claude-D97757?style=for-the-badge&logo=anthropic&logoColor=white)](https://anthropic.com)

An automated AI pipeline that transforms long-form YouTube videos (podcasts, gaming streams, interviews, keynote talks) into high-retention 9:16 vertical Shorts, Reels, and TikToks. 

It uses **Google Gemini** or **Anthropic Claude** to detect viral hooks, **FFmpeg** to render letterboxed 9:16 vertical videos at maximum native source resolution, and includes a **Modern Web Studio** with direct **1-click YouTube Shorts publishing**.

---

## ✨ Features

- 🧠 **AI Virality Detection**:
  - Analyzes timestamped transcripts for the **3-Second Hook Rule** (curiosity gaps, controversial claims, emotional peaks).
  - Evaluates standalone value (clean sentence start, complete punchline/takeaway).
  - Computes a Virality Score (1–100) and extracts key quotes.
  - Supports **Google Gemini** (`gemini-2.5-flash` / `gemini-1.5-pro`) and **Anthropic Claude** (`claude-3-7-sonnet` / `claude-3-5-sonnet`) with automatic fallback.

- 🎬 **Vertical 9:16 Full-Width Letterboxing**:
  - Preserves **100% of the video's width** without cropping side details.
  - Automatically centers the video with sleek top and bottom black bars on a 1080x1920 vertical canvas.
  - Always downloads at the **maximum available resolution** (4K / 1440p / 1080p).
  - Clean video output with no forced external subtitles or top banners.

- 🌐 **Modern Web Studio UI**:
  - Dark glassmorphic interface with real-time analysis logs.
  - Interactive timeline adjuster to fine-tune start/end timestamps before rendering.
  - Built-in 9:16 vertical player modal with immediate preview and download.
  - Local reels library to manage past generations.

- 🚀 **Direct YouTube Studio Integration**:
  - Authenticate with your YouTube Channel via Google OAuth 2.0.
  - Built-in **AI Copywriter** generates viral titles, hashtags, and descriptions with one click.
  - Publish directly to **YouTube Shorts** with custom privacy settings (Public, Unlisted, Private).

- 💻 **Rich CLI Alternative**:
  - Full terminal interface with progress spinners, colorized tables, and dry-run mode.

---

## 📋 Prerequisites

Before installing the project, ensure you have the following installed on your system:

### 1. Python 3.10 or Higher
Check your Python version:
```bash
python3 --version
```

### 2. FFmpeg (Required for video extraction and rendering)
FFmpeg is required to cut, re-encode, and letterbox the video.

- **macOS (via Homebrew):**
  ```bash
  brew install ffmpeg
  ```

- **Ubuntu / Debian Linux:**
  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```

- **Windows:**
  ```powershell
  # Using winget
  winget install Gyan.FFmpeg

  # Or using Chocolatey
  choco install ffmpeg
  ```
  *(Verify installation by running `ffmpeg -version` in your terminal)*.

### 3. AI API Key (At least one required)
- **Google Gemini API Key** (Free tier available): [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Anthropic Claude API Key**: [Anthropic Console](https://console.anthropic.com/)

---

## 🛠️ Step-by-Step Installation

### Step 1: Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/ai-pipeline.git
cd ai-pipeline
```

### Step 2: Create and Activate a Virtual Environment
```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (Command Prompt)
python -m venv .venv
.venv\Scripts\activate

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the example environment file and add your API keys:
```bash
cp .env.example .env
```
Open `.env` in any text editor and fill in your keys:
```env
# Google Gemini API Key (https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# Anthropic Claude API Key (https://console.anthropic.com/)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Override default models
# GEMINI_MODEL=gemini-2.5-flash
# ANTHROPIC_MODEL=claude-3-7-sonnet-20250219
```

> **Note**: You only need **one** API key (Gemini or Claude) to start. If both are provided, the app will automatically fall back if one encounters rate limits.

---

## 🚀 Running the Application

### Option 1: Launch the Web Studio (Recommended)

Start the local web server:
```bash
python server/run_web.py
```
Open your browser and navigate to:
```
http://localhost:8000
```

1. Paste any YouTube video URL.
2. Select your desired number of reels (1 to 5) and click **✨ Find Viral Reels**.
3. Inspect ranked moments, preview quotes, and adjust start/end times if desired.
4. Click **Render 9:16 Reel** to generate the clip.
5. Click the generated reel in the **Library** to preview it, download the `.mp4`, or publish directly to **YouTube Shorts**.

---

### Option 2: Command-Line Interface (CLI)

#### Interactive Mode
Run without arguments to be prompted for a URL:
```bash
python server/pipeline.py
```

#### Generate Top 3 Viral Reels
```bash
python server/pipeline.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --count 3
```

#### Dry-Run Mode (Analyze Moments in Seconds Without Rendering Video)
```bash
python server/pipeline.py --url "https://youtu.be/VIDEO_ID" --dry-run
```

#### Choose Specific AI Engine
```bash
# Use Google Gemini
python server/pipeline.py --url "https://youtu.be/VIDEO_ID" --engine gemini

# Use Anthropic Claude
python server/pipeline.py --url "https://youtu.be/VIDEO_ID" --engine anthropic
```

#### CLI Options Reference
| Flag | Description | Default |
| :--- | :--- | :--- |
| `-u`, `--url` | YouTube video link (standard, shortened, or shorts) | *Prompted* |
| `-c`, `--count` | Number of top viral moments to render | `3` |
| `-e`, `--engine` | AI engine (`auto`, `gemini`, `anthropic`) | `auto` |
| `--min-duration` | Minimum duration in seconds for each reel | `20.0` |
| `--max-duration` | Maximum duration in seconds for each reel | `60.0` |
| `-o`, `--output-dir` | Folder to save rendered reels | `./output_reels` |
| `--dry-run` | Analyze transcript without downloading or rendering video | `False` |

---

## 🔴 Direct YouTube Studio Upload Setup (Optional)

If you want to link your YouTube account and publish Shorts directly from the web interface:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g. `ViralReel Studio`).
3. Enable the **YouTube Data API v3**:
   - Navigate to **APIs & Services > Library**.
   - Search for **YouTube Data API v3** and click **Enable**.
4. Configure the **OAuth Consent Screen**:
   - User Type: **External**.
   - App Name: `ViralReel Studio`.
   - Add your email under **Test Users** (important while your app is in testing status).
5. Create **OAuth 2.0 Credentials**:
   - Navigate to **APIs & Services > Credentials > Create Credentials > OAuth Client ID**.
   - Application Type: **Web application**.
   - **Authorized redirect URIs**: Add:
     ```
     http://localhost:8000/api/youtube/callback
     ```
6. Download the OAuth client JSON file and save it as **`client_secrets.json`** in the root directory of this repository:
   ```bash
   # In ai-pipeline/
   client_secrets.json
   ```
7. Click **"Connect YouTube Studio"** in the top navigation of the Web Studio (or run `python server/auth_youtube.py`) and approve Google permissions in your browser.
8. Once authorized, a green badge with your channel name will appear. You can now post any rendered reel straight to YouTube Shorts with 1 click!

---

## 📁 Project Architecture

```
ai-pipeline/
├── server/
│   ├── static/             # Web Studio UI (HTML/CSS/JS)
│   │   ├── index.html      # Responsive single-page interface
│   │   ├── style.css       # Dark-mode glassmorphic design system
│   │   └── app.js          # Client-side reactivity, player & upload drawer
│   ├── run_web.py          # Web Studio launcher script
│   ├── server.py           # FastAPI application & REST endpoints
│   ├── pipeline.py         # End-to-end viral detection & rendering pipeline
│   ├── viral_detector.py   # Gemini & Claude virality analysis engine
│   ├── video_processor.py  # FFmpeg 9:16 letterboxing & encoding
│   ├── downloader.py       # YouTube metadata & transcript extraction (yt-dlp)
│   ├── youtube_uploader.py # YouTube Data API v3 & OAuth 2.0 uploader
│   ├── auth_youtube.py     # Standalone CLI authorization helper logic
│   ├── config.py           # Environment config, directory paths & models
│   ├── models.py           # Pydantic data schemas
│   └── __init__.py         # Python package marker
├── requirements.txt        # Python package dependencies
├── .env.example            # Template for API credentials
├── .gitignore              # Excludes secrets, virtual environments, and outputs
├── LICENSE                 # MIT License
├── README.md               # GitHub setup and usage guide
└── output_reels/           # Directory where finished 9:16 vertical reels are saved
```

---

## ❓ Frequently Asked Questions & Troubleshooting

### 1. `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`
FFmpeg is not installed or not in your system's PATH.
- Verify installation with `ffmpeg -version`.
- On macOS, install with `brew install ffmpeg`.
- On Linux, install with `sudo apt install ffmpeg`.
- On Windows, install via `winget install Gyan.FFmpeg` and restart your terminal.

### 2. "Could not extract transcript for video"
Some videos disable transcripts or do not have speech audio. The pipeline will attempt to pull automatic speech recognition (ASR) captions. If no captions exist in any language, choose a video with speech or captions enabled.

### 3. Google OAuth "Access blocked: This app has not been verified"
During development in Google Cloud Console, your app is in "Testing" mode. Make sure your personal Google account email is added under **OAuth consent screen > Test users**.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
