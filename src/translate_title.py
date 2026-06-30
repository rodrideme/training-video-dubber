import re
import requests

_ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
_COMPANY_NAME = "wxrks"


def translate_title(title: str, api_key: str) -> str:
    """
    Translate a Portuguese video title to English.
    Always replaces 'Works' with 'Wxrks' (company name).
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
            "max_tokens": 100,
            "messages": [{
                "role": "user",
                "content": (
                    'Translate this Portuguese video title to English. '
                    'The word "Works" is a company name always written in lowercase as "wxrks" — use that exact spelling. '
                    'Return only the translated title, nothing else.\n\n'
                    f'Title: {title}'
                ),
            }],
        },
    )
    r.raise_for_status()
    translated = r.json()["content"][0]["text"].strip()
    # Safety net: enforce Works → Wxrks regardless of what the model returned
    translated = re.sub(r'\bworks\b', _COMPANY_NAME, translated, flags=re.IGNORECASE)
    return translated
