import os
from pathlib import Path
from dotenv import load_dotenv

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from project root
load_dotenv(BASE_DIR / ".env")

TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output_reels"

# Ensure working directories exist
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Default AI Models
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
DEFAULT_ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-20250219")

# Target Reel Settings
DEFAULT_MIN_DURATION = 20.0  # seconds
DEFAULT_MAX_DURATION = 60.0  # seconds
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
ASPECT_RATIO = "9:16"
