#!/usr/bin/env python3
"""
CLI Helper to authenticate your YouTube channel with Google OAuth.
Run:
    .venv/bin/python auth_youtube.py
"""
import sys
import webbrowser
from pathlib import Path
from google_auth_oauthlib.flow import Flow
from config import BASE_DIR
import youtube_uploader

def main():
    print("\n⚡ YouTube Studio Authorization Helper ⚡\n")

    if not youtube_uploader.has_client_secrets():
        print("❌ Error: client_secrets.json not found in the project root.")
        print("Please ensure your Google OAuth client JSON is saved as 'client_secrets.json'.")
        sys.exit(1)

    print("🔑 Loaded client_secrets.json")
    print("🌐 Generating Google authorization link...\n")

    redirect_uri = "http://localhost:8000/api/youtube/callback"
    try:
        auth_url = youtube_uploader.get_auth_url(redirect_uri)
    except Exception as e:
        print(f"❌ Error generating auth URL: {e}")
        sys.exit(1)

    print("👉 Please open this URL in your browser to sign in with your YouTube account:\n")
    print(f"\033[94m{auth_url}\033[0m\n")

    # Try opening automatically in browser
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    print("After approving permissions in your browser, Google will redirect to http://localhost:8000/api/youtube/callback.")
    print("Once complete, your YouTube Studio account will be fully linked!\n")

if __name__ == "__main__":
    main()
