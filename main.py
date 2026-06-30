#!/usr/bin/env python3
"""
Download a Loom video (Brazilian Portuguese) and dub it to English US
using ElevenLabs for translation + Hugo voice via TTS + ffmpeg for timing,
then upload the result to Vimeo.

Usage:
    python main.py <loom_url>

Environment variables (or .env file):
    ELEVENLABS_API_KEY  — ElevenLabs API key
    VIMEO_ACCESS_TOKEN  — Vimeo API token (upload + edit scopes)
    VIMEO_FOLDER_ID     — Vimeo folder/showcase ID (optional)
    DOWNLOAD_DIR        — Where to save source videos (default: downloads)
"""

import argparse
import os
import sys
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
from src.vimeo_upload import upload_to_vimeo
from src.translate_title import translate_title


def main():
    load_dotenv()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    download_dir = os.environ.get("DOWNLOAD_DIR", "downloads")
    vimeo_token = os.environ.get("VIMEO_ACCESS_TOKEN")
    vimeo_folder_id = os.environ.get("VIMEO_FOLDER_ID") or None
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        sys.exit("Error: ELEVENLABS_API_KEY is not set.")
    if not vimeo_token:
        sys.exit("Error: VIMEO_ACCESS_TOKEN is not set.")
    if not anthropic_key:
        sys.exit("Error: ANTHROPIC_API_KEY is not set.")

    parser = argparse.ArgumentParser(description="Dub a Loom video (PT-BR → EN) with Hugo voice")
    parser.add_argument("loom_url", help="Loom share URL")
    args = parser.parse_args()

    # 1 — Download
    print("[1/5] Downloading Loom video...")
    video = download_loom(args.loom_url, output_dir=download_dir)
    print(f"      Saved : {video['path']}")
    print(f"      Title : {video['stem']}")

    # 2 — Submit to ElevenLabs for translation (auto-dub, no studio)
    print("\n[2/5] Submitting to ElevenLabs for translation (PT-BR → EN)...")
    dubbing_id = create_basic_dub(
        file_path=video["path"],
        api_key=api_key,
        target_lang="en",
        source_lang="pt",
        name=video["stem"],
    )
    print(f"      Dubbing ID: {dubbing_id}")

    # 3 — Wait for translation to finish
    print("\n[3/5] Waiting for translation to complete...")
    wait_for_dubbed(dubbing_id, api_key)
    print("      Translation complete.")

    # 4 — Fetch English SRT (timestamped transcript)
    print("\n[4/5] Fetching English transcript with timestamps...")
    srt_text = fetch_srt(dubbing_id, api_key, language_code="en")
    segments = parse_srt(srt_text)
    groups = group_segments(segments)
    print(f"      {len(groups)} speech groups found.")

    # 5 — Generate Hugo TTS per group + time-align + mux
    output_path = str(Path("dubbed") / f"{video['stem']}.mp4")
    print(f"\n[5/5] Generating Hugo voice and building dubbed video...")
    build_dubbed_video(
        source_video=video["path"],
        groups=groups,
        api_key=api_key,
        output_path=output_path,
    )

    print(f"      Saved to : {output_path}")

    # 6 — Translate title + upload to Vimeo
    print(f"\n[6/6] Uploading to Vimeo...")
    english_title = translate_title(video["stem"], anthropic_key)
    print(f"      Title     : {english_title}")
    _, video_url = upload_to_vimeo(
        file_path=output_path,
        name=english_title,
        token=vimeo_token,
        privacy="unlisted",
        folder_id=vimeo_folder_id,
    )

    print(f"\nDone!")
    print(f"  Dubbed video : {output_path}")
    print(f"  Vimeo URL   : {video_url}")


if __name__ == "__main__":
    main()
