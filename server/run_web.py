#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent.parent
    print("\n⚡ Starting ViralReel AI Web Studio...")
    print("📍 URL: http://localhost:8000\n")
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", "server.server:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ], cwd=str(root_dir), check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")

if __name__ == "__main__":
    main()
