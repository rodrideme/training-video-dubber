import os
import requests


HEYGEN_BASE = "https://api.heygen.com"


def _headers(api_key: str) -> dict:
    return {"x-api-key": api_key, "Accept": "application/json"}


def upload_video(file_path: str, api_key: str) -> str:
    """
    Upload a local video file to HeyGen and return the asset_id
    that can be used in subsequent API calls.
    """
    with open(file_path, "rb") as f:
        response = requests.post(
            f"{HEYGEN_BASE}/v3/assets",
            headers=_headers(api_key),
            files={"file": (os.path.basename(file_path), f, "video/mp4")},
        )

    response.raise_for_status()
    data = response.json()

    try:
        return data["data"]["asset_id"]
    except (KeyError, TypeError):
        raise RuntimeError(f"Unexpected upload response: {data}")


def submit_dubbing_job(
    asset_id: str,
    voice_id: str,
    api_key: str,
    title: str = "",
    source_language: str = None,
    target_language: str = "Portuguese (Brazil)",
) -> str:
    """
    Submit a video translation (dubbing) job to HeyGen using the
    account's imported voice as the stock voice pool.

    Returns the video_translation_id that can be polled for completion.
    """
    payload = {
        "video": {"type": "asset_id", "asset_id": asset_id},
        "output_languages": [target_language],
        "title": title or "Dubbed video",
        "enable_caption": True,
        "stock_voice_config": {
            "use_stock_voice": True,
            "preferred_stock_voice_ids": [voice_id],
        },
    }
    if source_language:
        payload["input_language"] = source_language

    response = requests.post(
        f"{HEYGEN_BASE}/v3/video-translations",
        headers={**_headers(api_key), "Content-Type": "application/json"},
        json=payload,
    )

    response.raise_for_status()
    data = response.json()

    try:
        return data["data"]["video_translation_ids"][0]
    except (KeyError, TypeError, IndexError):
        raise RuntimeError(f"Unexpected dubbing response: {data}")


def get_job_status(job_id: str, api_key: str) -> dict:
    """
    Fetch the current status of a HeyGen translation job.

    Returns the full 'data' dict from the API, which includes:
        status     - "pending" | "running" | "completed" | "failed"
        video_url  - download URL once status is "completed"
    """
    response = requests.get(
        f"{HEYGEN_BASE}/v3/video-translations/{job_id}",
        headers=_headers(api_key),
    )
    response.raise_for_status()
    data = response.json()

    try:
        return data["data"]
    except (KeyError, TypeError):
        raise RuntimeError(f"Unexpected status response: {data}")
