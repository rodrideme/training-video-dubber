#!/usr/bin/env python3
"""
Check the status of an ElevenLabs dubbing job.

Usage:
    python check_status.py <dubbing_id>
"""

import os
import sys

from dotenv import load_dotenv
from elevenlabs import ElevenLabs


def main():
    load_dotenv()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        sys.exit("Error: ELEVENLABS_API_KEY is not set.")
    if len(sys.argv) < 2:
        sys.exit("Usage: python check_status.py <dubbing_id>")

    client = ElevenLabs(api_key=api_key)
    info = client.dubbing.get(sys.argv[1])
    print(f"Status : {info.status}")
    print(f"Name   : {info.name}")


if __name__ == "__main__":
    main()
