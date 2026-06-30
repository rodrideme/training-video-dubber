import subprocess
from pathlib import Path

# Use the bundled yt-dlp binary (not the pip-installed one, which is capped at Python 3.9)
_BIN = Path(__file__).parent.parent / "bin" / "yt-dlp"
YT_DLP = str(_BIN)


def download_loom(url: str, output_dir: str = "downloads") -> dict:
    """
    Download a Loom video using the bundled yt-dlp binary.

    Returns a dict with:
        path     - absolute path to the downloaded file
        filename - file name with extension
        stem     - file name without extension (used as lesson title)
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Get the filename yt-dlp would produce (without downloading)
    info_cmd = [
        YT_DLP,
        "--no-playlist",
        "--print", "filename",
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        url,
    ]
    result = subprocess.run(info_cmd, capture_output=True, text=True, check=True)
    expected_path = result.stdout.strip()

    # Download the video
    download_cmd = [
        YT_DLP,
        "--no-playlist",
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        url,
    ]
    subprocess.run(download_cmd, check=True)

    # yt-dlp may remux; find the actual file by title
    stem = Path(expected_path).stem
    parent = Path(output_dir)
    candidates = sorted(parent.glob(f"{stem}.*"))
    if not candidates:
        raise FileNotFoundError(f"Downloaded file not found in {output_dir!r} for title {stem!r}")

    actual_path = str(candidates[0].resolve())
    return {
        "path": actual_path,
        "filename": candidates[0].name,
        "stem": stem,
    }
