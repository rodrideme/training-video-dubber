#!/usr/bin/env python3
"""
Download a Loom video (Brazilian Portuguese) and dub it to English US,
then upload the result to Vimeo.

Usage:
    python main.py <loom_url>

Environment variables (or .env file):
    ELEVENLABS_API_KEY  — ElevenLabs API key
    VIMEO_ACCESS_TOKEN  — Vimeo API token (upload + edit scopes)
    ANTHROPIC_API_KEY   — Anthropic API key (title translation)
    VIMEO_FOLDER_ID     — Vimeo folder/showcase ID (optional)
    DOWNLOAD_DIR        — Where to save source videos (default: downloads)
"""

import argparse
import sys

from src.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Dub a Loom video (PT-BR → EN) with Hugo voice")
    parser.add_argument("loom_url", help="Loom share URL")
    args = parser.parse_args()

    result = run_pipeline(args.loom_url)
    print(f"\nDone!")
    print(f"  Title        : {result['title']}")
    print(f"  Dubbed video : {result['output_path']}")
    print(f"  Vimeo URL    : {result['vimeo_url']}")


if __name__ == "__main__":
    main()
