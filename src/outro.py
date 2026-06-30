import subprocess
from pathlib import Path


def append_outro(main_video: str, outro_video: str, output_path: str) -> str:
    """
    Concatenate main_video + outro_video into output_path.
    Normalises both clips to the outro's resolution and stereo audio
    so ffmpeg concat never fails on mismatched streams.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Detect outro resolution to use as the target
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0", outro_video],
        capture_output=True, text=True, check=True,
    )
    w, h = probe.stdout.strip().split(",")

    filter_complex = (
        # Scale main video to match outro resolution (pad with black bars)
        f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2[v0];"
        # Convert main audio to stereo
        "[0:a]aformat=channel_layouts=stereo[a0];"
        # Ensure outro video is the right size
        f"[1:v]scale={w}:{h}[v1];"
        # Ensure outro audio is stereo
        "[1:a]aformat=channel_layouts=stereo[a1];"
        # Concatenate
        "[v0][a0][v1][a1]concat=n=2:v=1:a=1[vout][aout]"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-i", main_video,
        "-i", outro_video,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "h264",
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ], check=True, capture_output=True)
    return output_path
