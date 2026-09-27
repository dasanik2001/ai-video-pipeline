"""
ViralReel AI - Server Package
"""
import sys
from pathlib import Path

# Ensure server package directory and project root are on sys.path
SERVER_DIR = Path(__file__).resolve().parent
ROOT_DIR = SERVER_DIR.parent

for path in [str(SERVER_DIR), str(ROOT_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)
