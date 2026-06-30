import requests

CIRCLE_BASE = "https://app.circle.so/api/admin/v2"
SPACE_ID = 2710272
SECTION_ID = 1077562


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _create_embed_sgid(vimeo_url: str, token: str) -> str:
    """
    Circle's rich text editor embeds video via a signed sgid token, not a raw
    iframe (raw <iframe> tags in body_html are stripped by Circle's sanitizer).
    POST /embeds resolves the URL via Circle's oEmbed provider and returns a
    signed token referencing that embed, which can be placed in an `embed`
    node inside rich_text_body.
    """
    r = requests.post(
        f"{CIRCLE_BASE}/embeds",
        headers=_headers(token),
        json={"url": vimeo_url},
    )
    r.raise_for_status()
    return r.json()["sgid"]


def create_lesson(title: str, vimeo_url: str, token: str) -> dict:
    """
    Create a published lesson in The Essentials course with the Vimeo video embedded.
    Returns the created lesson data.
    """
    sgid = _create_embed_sgid(vimeo_url, token)
    r = requests.post(
        f"{CIRCLE_BASE}/course_lessons",
        headers=_headers(token),
        json={
            "space_id": SPACE_ID,
            "section_id": SECTION_ID,
            "name": title,
            "rich_text_body": {
                "body": {
                    "type": "doc",
                    "content": [
                        {"type": "embed", "attrs": {"sgid": sgid}},
                    ],
                },
            },
            "status": "published",
            "is_comments_enabled": False,
        },
    )
    r.raise_for_status()
    lesson = r.json()
    return lesson
