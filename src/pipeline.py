import os
from pathlib import Path

from dotenv import load_dotenv

from src.circle_lesson import create_lesson
from src.describe import generate_video_copy
from src.download_loom import download_loom
from src.elevenlabs_dub import (
    build_dubbed_video,
    create_basic_dub,
    fetch_srt,
    group_segments,
    parse_srt,
    wait_for_dubbed,
)
from src.outro import append_outro
from src.thumbnail import generate_thumbnail
from src.translate_title import translate_title
from src.vimeo_upload import upload_to_vimeo
from src.youtube_upload import upload_to_youtube


def run_pipeline(loom_url: str, log=print) -> dict:
    load_dotenv()

    api_key        = os.environ["ELEVENLABS_API_KEY"]
    vimeo_token    = os.environ["VIMEO_ACCESS_TOKEN"]
    anthropic_key  = os.environ["ANTHROPIC_API_KEY"]
    download_dir   = os.environ.get("DOWNLOAD_DIR", "downloads")
    vimeo_folder_id = os.environ.get("VIMEO_FOLDER_ID") or None
    outro_path     = os.environ.get("OUTRO_PATH", "assets/outro.mp4")
    circle_token   = os.environ.get("CIRCLE_API_TOKEN")
    yt_client_id   = os.environ.get("YOUTUBE_CLIENT_ID")
    yt_client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    yt_refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    yt_playlist_id = os.environ.get("YOUTUBE_PLAYLIST_ID") or None

    # ── 1. Download ───────────────────────────────────────────────────────────
    log(f"[1/8] Downloading {loom_url} ...")
    video = download_loom(loom_url, output_dir=download_dir)
    log(f"      Saved : {video['path']}")

    # ── 2. ElevenLabs dub submission ──────────────────────────────────────────
    log("[2/8] Submitting to ElevenLabs (PT-BR → EN) ...")
    dubbing_id = create_basic_dub(
        video["path"], api_key, target_lang="en", source_lang="pt", name=video["stem"]
    )
    log(f"      Dubbing ID: {dubbing_id}")

    # ── 3. Wait ───────────────────────────────────────────────────────────────
    log("[3/8] Waiting for ElevenLabs dubbing ...")
    wait_for_dubbed(dubbing_id, api_key)

    # ── 4. Build dubbed video with Hugo voice ─────────────────────────────────
    log("[4/8] Fetching SRT and building Hugo-voiced video ...")
    srt_text = fetch_srt(dubbing_id, api_key, language_code="en")
    segments = parse_srt(srt_text)
    groups = group_segments(segments)
    log(f"      {len(groups)} speech groups found.")
    dubbed_path = str(Path("dubbed") / f"{video['stem']}_dubbed.mp4")
    build_dubbed_video(video["path"], groups, api_key, dubbed_path)

    # ── 5. Append outro ───────────────────────────────────────────────────────
    output_path = str(Path("dubbed") / f"{video['stem']}.mp4")
    if Path(outro_path).exists():
        log("[5/8] Appending outro ...")
        append_outro(dubbed_path, outro_path, output_path)
    else:
        log(f"[5/8] No outro at {outro_path!r}, skipping.")
        output_path = dubbed_path

    # ── 6. Translate title + generate description & thumbnail text ────────────
    log("[6/8] Translating title and generating video copy ...")
    english_title = translate_title(video["stem"], anthropic_key)
    log(f"      Title : {english_title}")
    copy = generate_video_copy(english_title, anthropic_key)
    description = copy.get("description", english_title)
    thumbnail_text = copy.get("thumbnail_text", english_title)
    log(f"      Desc  : {description!r}")
    log(f"      Thumb : {thumbnail_text!r}")

    # ── 7. Upload to Vimeo ────────────────────────────────────────────────────
    log("[7/8] Uploading to Vimeo ...")
    _, vimeo_url = upload_to_vimeo(
        file_path=output_path,
        name=english_title,
        token=vimeo_token,
        privacy="unlisted",
        folder_id=vimeo_folder_id,
    )
    log(f"      Vimeo : {vimeo_url}")

    # ── 8a. Circle lesson ─────────────────────────────────────────────────────
    lesson_url = None
    if circle_token:
        log("[8/8] Creating lesson in Circle (The Essentials) ...")
        lesson = create_lesson(english_title, vimeo_url, circle_token)
        lesson_url = (
            f"https://community.wxrks.com/courses/{lesson.get('space_id')}"
            f"/lessons/{lesson.get('id')}"
        )
        log(f"      Lesson: {lesson_url}")
    else:
        log("[8/8] CIRCLE_API_TOKEN not set — skipping Circle lesson.")

    # ── 8b. YouTube upload ────────────────────────────────────────────────────
    youtube_url = None
    if yt_client_id and yt_client_secret and yt_refresh_token:
        log("[8/8] Generating thumbnail and uploading to YouTube ...")
        thumbnail_path = str(Path("dubbed") / f"{video['stem']}_thumb.jpg")
        generate_thumbnail(thumbnail_text, thumbnail_path)
        log(f"      Thumbnail: {thumbnail_path}")
        youtube_url = upload_to_youtube(
            file_path=output_path,
            title=english_title,
            description=description,
            thumbnail_path=thumbnail_path,
            client_id=yt_client_id,
            client_secret=yt_client_secret,
            refresh_token=yt_refresh_token,
            playlist_id=yt_playlist_id,
        )
        log(f"      YouTube: {youtube_url}")
    else:
        log("[8/8] YOUTUBE_* env vars not set — skipping YouTube upload.")

    return {
        "title": english_title,
        "output_path": output_path,
        "vimeo_url": vimeo_url,
        "lesson_url": lesson_url,
        "youtube_url": youtube_url,
    }
