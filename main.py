#!/usr/bin/env python3
"""
Download a Loom video (Brazilian Portuguese) and dub it to English US
using ElevenLabs for translation + Hugo voice via TTS + ffmpeg for timing.

Usage:
    python main.py <loom_url>

Environment variables (or .env file):
    ELEVENLABS_API_KEY  — ElevenLabs API key
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


def main():
    load_dotenv()

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    download_dir = os.environ.get("DOWNLOAD_DIR", "downloads")

    if not api_key:
        sys.exit("Error: ELEVENLABS_API_KEY is not set.")

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

    print(f"\nDone! Dubbed video saved to: {output_path}")


if __name__ == "__main__":
    main()
