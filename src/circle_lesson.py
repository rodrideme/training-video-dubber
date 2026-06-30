import re
import requests

CIRCLE_BASE = "https://app.circle.so/api/admin/v2"
SPACE_ID = 2710272
SECTION_ID = 1077562


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _vimeo_embed_html(vimeo_url: str) -> str:
    """Build a Vimeo iframe from a URL like https://vimeo.com/VIDEO_ID/HASH."""
    match = re.search(r'vimeo\.com/(?:videos/)?(\d+)(?:/([a-f0-9]+))?', vimeo_url)
    if not match:
        raise ValueError(f"Cannot parse Vimeo URL: {vimeo_url}")
    video_id = match.group(1)
    h = match.group(2)
    src = f"https://player.vimeo.com/video/{video_id}"
    if h:
        src += f"?h={h}&"
    else:
        src += "?"
    src += "badge=0&autopause=0&player_id=0"
    return (
        f'<div style="padding:56.25% 0 0 0;position:relative;">'
        f'<iframe src="{src}" frameborder="0" allow="autoplay; fullscreen; '
        f'picture-in-picture" allowfullscreen '
        f'style="position:absolute;top:0;left:0;width:100%;height:100%;"></iframe>'
        f'</div>'
    )


def create_lesson(title: str, vimeo_url: str, token: str) -> dict:
    """
    Create a published lesson in The Essentials course with the Vimeo video embedded.
    Returns the created lesson data.
    """
    body_html = _vimeo_embed_html(vimeo_url)
    r = requests.post(
        f"{CIRCLE_BASE}/course_lessons",
        headers=_headers(token),
        json={
            "space_id": SPACE_ID,
            "section_id": SECTION_ID,
            "name": title,
            "body_html": body_html,
            "status": "published",
            "is_comments_enabled": False,
        },
    )
    r.raise_for_status()
    lesson = r.json()
    return lesson
