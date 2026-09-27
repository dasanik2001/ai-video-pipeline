import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import BASE_DIR

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

CLIENT_SECRETS_FILE = BASE_DIR / "client_secrets.json"
TOKEN_FILE = BASE_DIR / "youtube_token.json"

def has_client_secrets() -> bool:
    """Check if client_secrets.json is configured."""
    return CLIENT_SECRETS_FILE.exists() and CLIENT_SECRETS_FILE.stat().st_size > 10

def save_client_secrets(content: str) -> None:
    """Save user-provided client_secrets.json content."""
    # Validate JSON structure
    data = json.loads(content)
    if "installed" not in data and "web" not in data:
        raise ValueError("Invalid client_secrets.json format. Must contain 'installed' or 'web' root key.")
    CLIENT_SECRETS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

def get_credentials() -> Optional[Credentials]:
    """Retrieve and refresh stored OAuth credentials."""
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception:
            return None

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        except Exception:
            return None

    if creds and creds.valid:
        return creds

    return None

def is_authenticated() -> bool:
    """Check if user is currently authenticated with YouTube."""
    return get_credentials() is not None

def disconnect_youtube() -> None:
    """Disconnect YouTube account by removing stored tokens."""
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except Exception:
            pass

def get_channel_info() -> Optional[Dict[str, Any]]:
    """Retrieve authenticated YouTube channel profile details."""
    creds = get_credentials()
    if not creds:
        return None

    try:
        youtube = build("youtube", "v3", credentials=creds)
        response = youtube.channels().list(
            part="snippet,statistics",
            mine=True
        ).execute()

        items = response.get("items", [])
        if not items:
            return None

        channel = items[0]
        snippet = channel.get("snippet", {})
        stats = channel.get("statistics", {})

        return {
            "id": channel.get("id"),
            "title": snippet.get("title", "My YouTube Channel"),
            "custom_url": snippet.get("customUrl", ""),
            "avatar": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
            "subscribers": stats.get("subscriberCount", "0"),
            "videos": stats.get("videoCount", "0"),
        }
    except Exception as e:
        print(f"Error fetching channel info: {e}")
        return None

FLOW_STATE_FILE = BASE_DIR / "temp" / "oauth_flow.json"

def get_auth_url(redirect_uri: str) -> str:
    """Generate Google OAuth 2.0 authorization URL."""
    if not has_client_secrets():
        raise FileNotFoundError("client_secrets.json not found. Please upload it first.")

    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRETS_FILE),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    # Save code_verifier and state so callback can complete exchange
    flow_state = {
        "state": state,
        "code_verifier": getattr(flow, "code_verifier", None),
        "redirect_uri": redirect_uri,
    }
    FLOW_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    FLOW_STATE_FILE.write_text(json.dumps(flow_state), encoding="utf-8")

    return auth_url

def exchange_code_for_tokens(code: str, redirect_uri: str) -> Dict[str, Any]:
    """Exchange authorization code for access and refresh tokens."""
    code_verifier = None
    if FLOW_STATE_FILE.exists():
        try:
            saved_state = json.loads(FLOW_STATE_FILE.read_text(encoding="utf-8"))
            code_verifier = saved_state.get("code_verifier")
            FLOW_STATE_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    flow = Flow.from_client_secrets_file(
        str(CLIENT_SECRETS_FILE),
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    flow.fetch_token(code=code, code_verifier=code_verifier)
    creds = flow.credentials

    # Save token
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    channel = get_channel_info()
    return {
        "success": True,
        "channel": channel
    }

def upload_short(
    file_path: Path,
    title: str,
    description: str = "",
    privacy_status: str = "public",
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Upload a 9:16 vertical video reel to YouTube as a YouTube Short.
    Ensures #Shorts tag is present in the title and description for short-form indexing.
    """
    creds = get_credentials()
    if not creds:
        raise PermissionError("Not authenticated with YouTube. Please link your YouTube account first.")

    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")

    # Ensure title contains #Shorts
    clean_title = title.strip()
    if "#Shorts" not in clean_title and "#shorts" not in clean_title:
        clean_title = f"{clean_title} #Shorts"
    # YouTube title limit is 100 chars
    clean_title = clean_title[:100]

    # Clean description
    clean_desc = description.strip()
    if "#Shorts" not in clean_desc and "#shorts" not in clean_desc:
        clean_desc = f"{clean_desc}\n\n#Shorts #Reels #Viral"

    all_tags = tags or ["Shorts", "Viral", "Trending"]
    if "Shorts" not in all_tags:
        all_tags.append("Shorts")

    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": clean_title,
            "description": clean_desc,
            "tags": all_tags,
            "categoryId": "22",  # People & Blogs / Entertainment
        },
        "status": {
            "privacyStatus": privacy_status,  # public, unlisted, private
            "selfDeclaredMadeForKids": False,
        },
    }

    # Resumable upload chunk size: 5MB
    media = MediaFileUpload(
        str(file_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=5 * 1024 * 1024
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress_pct = int(status.progress() * 100)
            print(f"Uploading to YouTube: {progress_pct}%")

    video_id = response.get("id")
    shorts_url = f"https://www.youtube.com/shorts/{video_id}"

    return {
        "success": True,
        "video_id": video_id,
        "title": clean_title,
        "url": shorts_url,
        "privacy": privacy_status
    }
