from typing import Optional
import requests
from pathlib import Path

VIMEO_BASE = "https://api.vimeo.com"
CHUNK_SIZE = 128 * 1024 * 1024  # 128 MB per chunk


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.vimeo.*+json;version=3.4",
    }


def _create_video(name: str, file_size: int, token: str, privacy: str) -> tuple:
    """POST /me/videos → (video_uri, upload_link)"""
    r = requests.post(
        f"{VIMEO_BASE}/me/videos",
        headers={**_headers(token), "Content-Type": "application/json"},
        json={
            "name": name,
            "privacy": {"view": privacy, "embed": "public"},
            "upload": {"approach": "tus", "size": file_size},
            "embed": {
                "title": {
                    "name": "hide",
                    "owner": "hide",
                    "portrait": "hide",
                },
                "buttons": {
                    "like": False,
                    "watchlater": False,
                    "share": False,
                },
                "logos": {"vimeo": False},
                "end_screen": [{"type": "empty"}],
            },
        },
    )
    r.raise_for_status()
    data = r.json()
    return data["uri"], data["upload"]["upload_link"]


def _tus_upload(upload_link: str, file_path: str) -> None:
    """Upload file in chunks using the tus resumable protocol."""
    file_size = Path(file_path).stat().st_size
    offset = 0
    with open(file_path, "rb") as fh:
        fh.seek(offset)
        while offset < file_size:
            chunk = fh.read(CHUNK_SIZE)
            r = requests.patch(
                upload_link,
                headers={
                    "Tus-Resumable": "1.0.0",
                    "Upload-Offset": str(offset),
                    "Content-Type": "application/offset+octet-stream",
                },
                data=chunk,
            )
            r.raise_for_status()
            offset = int(r.headers["Upload-Offset"])
            pct = offset / file_size * 100
            print(f"      {pct:.1f}% ({offset / 1024**2:.0f} / {file_size / 1024**2:.0f} MB)")


def _add_to_folder(video_uri: str, folder_id: str, token: str) -> None:
    video_id = video_uri.split("/")[-1]
    r = requests.put(
        f"{VIMEO_BASE}/me/folders/{folder_id}/videos/{video_id}",
        headers=_headers(token),
    )
    r.raise_for_status()


def upload_to_vimeo(
    file_path: str,
    name: str,
    token: str,
    privacy: str = "unlisted",
    folder_id: Optional[str] = None,
) -> tuple:
    """
    Upload a local file to Vimeo.

    Returns (video_uri, video_url) — e.g. ('/videos/123456', 'https://vimeo.com/videos/123456').
    """
    file_size = Path(file_path).stat().st_size
    print(f"      File size : {file_size / 1024**2:.1f} MB")

    video_uri, upload_link = _create_video(name, file_size, token, privacy)
    print(f"      Video URI : {video_uri}")

    _tus_upload(upload_link, file_path)

    if folder_id:
        _add_to_folder(video_uri, folder_id, token)
        print(f"      Added to folder {folder_id}")

    # Fetch the real shareable link (unlisted videos get a private hash appended)
    r = requests.get(
        f"{VIMEO_BASE}{video_uri}",
        headers={**_headers(token), "fields": "link"},
    )
    r.raise_for_status()
    video_url = r.json().get("link", f"https://vimeo.com{video_uri}")
    return video_uri, video_url
