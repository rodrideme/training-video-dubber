import json
import re
import requests

_ANTHROPIC_API = "https://api.anthropic.com/v1/messages"


def generate_video_copy(title: str, api_key: str) -> dict:
    """
    Returns {'description': '2-line YouTube description', 'thumbnail_text': 'UP TO 4 WORDS'}.
    The thumbnail_text is picked for visual impact on a dark background.
    """
    r = requests.post(
        _ANTHROPIC_API,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 200,
            "messages": [{
                "role": "user",
                "content": (
                    f'This is a training video from wxrks titled: "{title}"\n\n'
                    "Respond with a JSON object containing exactly two keys:\n"
                    '1. "description": Two short lines for the YouTube video description. '
                    "Line 1 states what the viewer will learn. "
                    "Line 2 mentions wxrks and links to community.wxrks.com. "
                    "Total under 200 characters.\n"
                    '2. "thumbnail_text": 1 to 4 words (ALL CAPS) that capture the core '
                    "topic — punchy enough to stand alone on a dark YouTube thumbnail.\n\n"
                    "Return ONLY the JSON object, no markdown or explanation."
                ),
            }],
        },
        timeout=30,
    )
    r.raise_for_status()
    raw = r.json()["content"][0]["text"].strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
    return json.loads(raw)
