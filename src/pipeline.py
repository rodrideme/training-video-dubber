import os
from pathlib import Path

from dotenv import load_dotenv

from src.download_loom import download_loom
from src.elevenlabs_dub import (
    create_basic_dub,
    wait_for_dubbed,
    fetch_srt,
    parse_srt,
    group_segments,
    build_dubbed_video,
)
from src.translate_title import translate_title
from src.vimeo_upload import upload_to_vimeo


def run_pipeline(loom_url: str, log=print) -> dict:
    """
    Full pipeline: download → dub → Hugo TTS → mux → translate title → Vimeo upload.
    Returns {'title': str, 'output_path': str, 'vimeo_url': str}.
    """
    load_dotenv()

    api_key = os.environ["ELEVENLABS_API_KEY"]
    vimeo_token = os.environ["VIMEO_ACCESS_TOKEN"]
    anthropic_key = os.environ["ANTHROPIC_API_KEY"]
    download_dir = os.environ.get("DOWNLOAD_DIR", "downloads")
    vimeo_folder_id = os.environ.get("VIMEO_FOLDER_ID") or None

    log(f"[1/6] Downloading {loom_url} ...")
    video = download_loom(loom_url, output_dir=download_dir)
    log(f"      Saved : {video['path']}")

    log("[2/6] Submitting to ElevenLabs (PT-BR → EN) ...")
    dubbing_id = create_basic_dub(
        video["path"], api_key, target_lang="en", source_lang="pt", name=video["stem"]
    )
    log(f"      Dubbing ID: {dubbing_id}")

    log("[3/6] Waiting for translation ...")
    wait_for_dubbed(dubbing_id, api_key)

    log("[4/6] Fetching English SRT ...")
    srt_text = fetch_srt(dubbing_id, api_key, language_code="en")
    segments = parse_srt(srt_text)
    groups = group_segments(segments)
    log(f"      {len(groups)} speech groups found.")

    output_path = str(Path("dubbed") / f"{video['stem']}.mp4")
    log("[5/6] Generating Hugo voice and building video ...")
    build_dubbed_video(video["path"], groups, api_key, output_path)

    log("[6/6] Translating title and uploading to Vimeo ...")
    english_title = translate_title(video["stem"], anthropic_key)
    log(f"      Title : {english_title}")
    _, vimeo_url = upload_to_vimeo(
        file_path=output_path,
        name=english_title,
        token=vimeo_token,
        privacy="unlisted",
        folder_id=vimeo_folder_id,
    )
    log(f"      Vimeo : {vimeo_url}")

    return {"title": english_title, "output_path": output_path, "vimeo_url": vimeo_url}
