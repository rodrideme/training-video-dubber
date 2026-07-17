import os
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

_SCOPES = ["https://www.googleapis.com/auth/youtube"]
_TOKEN_URI = "https://oauth2.googleapis.com/token"
_CHUNK = 10 * 1024 * 1024  # 10 MB resumable chunks


def _service(client_id: str, client_secret: str, refresh_token: str):
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=_TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=_SCOPES,
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_to_youtube(
    file_path: str,
    title: str,
    description: str,
    thumbnail_path: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    playlist_id: str = None,
) -> str:
    yt = _service(client_id, client_secret, refresh_token)

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "27",  # Education
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        file_path,
        mimetype="video/mp4",
        chunksize=_CHUNK,
        resumable=True,
    )
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    video_id = None
    while video_id is None:
        status, response = request.next_chunk()
        if response:
            video_id = response["id"]
        elif status:
            print(f"      Upload progress: {int(status.progress() * 100)}%")

    print(f"      Video ID: {video_id}")

    # Set custom thumbnail (requires verified channel; silently skips on unverified)
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            yt.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
            ).execute()
            print("      Thumbnail set.")
        except Exception as e:
            print(f"      Thumbnail skipped ({e})")

    # Add to playlist
    if playlist_id:
        yt.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()
        print(f"      Added to playlist {playlist_id}")

    return f"https://www.youtube.com/watch?v={video_id}"
