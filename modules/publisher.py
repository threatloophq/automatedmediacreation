import os
import logging
import pickle
import requests
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

log = logging.getLogger(__name__)
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID", "")

def get_youtube_client():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "client_secrets.json",
            ["https://www.googleapis.com/auth/youtube.upload"])
        creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def publish_youtube(video_path, topic, script, video_type="short"):
    youtube = get_youtube_client()
    body = {"snippet": {"title": topic[:90],
                        "description": f"{topic}\n\n{script[:300]}...\n\n#cybersecurity #ai #tech",
                        "tags": topic.split() + ["cybersecurity", "ai", "tech", "shorts"],
                        "categoryId": "28"},
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    media = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    url = f"https://www.youtube.com/shorts/{response['id']}"
    log.info(f"YouTube live: {url}")
    return url

def publish_instagram(video_path, topic, script):
    if not INSTAGRAM_ACCESS_TOKEN or not INSTAGRAM_ACCOUNT_ID:
        log.warning("Instagram credentials not set — skipping")
        return ""
    log.info("Instagram upload — set credentials in .env to enable")
    return ""
