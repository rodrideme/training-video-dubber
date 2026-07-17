import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

_W, _H = 1280, 720
_BG = (17, 17, 17)          # #111111
_TEXT_COLOR = (255, 255, 255)
_BRAND_COLOR = (170, 170, 170)  # muted gray for "wxrks" watermark
_ACCENT_COLOR = (255, 255, 255)

_FONT_CANDIDATES = [
    # Docker / Linux (fonts-dejavu-core)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    # Ubuntu / Debian (fonts-liberation)
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    # macOS system fonts
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default(size=size)


def _split_words(text: str, max_per_line: int = 2) -> list[str]:
    words = text.upper().split()[:4]
    lines = []
    for i in range(0, len(words), max_per_line):
        lines.append(" ".join(words[i:i + max_per_line]))
    return lines


def generate_thumbnail(thumbnail_text: str, output_path: str) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (_W, _H), color=_BG)
    draw = ImageDraw.Draw(img)

    # Subtle gradient: slightly lighter strip at the top
    for y in range(100):
        brightness = int(17 + (30 - 17) * (1 - y / 100))
        draw.line([(0, y), (_W, y)], fill=(brightness, brightness, brightness))

    # Left accent bar
    draw.rectangle([(0, 0), (10, _H)], fill=_ACCENT_COLOR)

    # Main title text
    main_font = _load_font(110)
    lines = _split_words(thumbnail_text)

    # Measure total block height
    line_heights = []
    line_widths = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=main_font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    line_gap = 20
    total_h = sum(line_heights) + line_gap * (len(lines) - 1)
    start_y = (_H - total_h) // 2 - 20

    x_pad = 80  # leave room for the accent bar
    for i, line in enumerate(lines):
        y = start_y + sum(line_heights[:i]) + line_gap * i
        # Soft shadow for depth
        draw.text((x_pad + 3, y + 3), line, font=main_font, fill=(0, 0, 0, 160))
        draw.text((x_pad, y), line, font=main_font, fill=_TEXT_COLOR)

    # wxrks watermark — bottom right
    brand_font = _load_font(44)
    brand = "wxrks"
    bbox = draw.textbbox((0, 0), brand, font=brand_font)
    bw = bbox[2] - bbox[0]
    draw.text((_W - bw - 40, _H - 64), brand, font=brand_font, fill=_BRAND_COLOR)

    img.save(output_path, "JPEG", quality=95)
    return output_path
