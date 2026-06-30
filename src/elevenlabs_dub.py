import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import requests
from elevenlabs import ElevenLabs

HUGO_VOICE_ID = "tJu31FjHaD1XTE4OXpYT"
ELEVEN_BASE = "https://api.elevenlabs.io/v1"


def _client(api_key: str) -> ElevenLabs:
    return ElevenLabs(api_key=api_key)


# ── Step 1: Create basic dub (no studio) to get transcript + translation ──────

def create_basic_dub(
    file_path: str,
    api_key: str,
    target_lang: str = "en",
    source_lang: str = "pt",
    name: str = "",
) -> str:
    """Submit video to ElevenLabs for dubbing (no studio). Returns dubbing_id."""
    client = _client(api_key)
    with open(file_path, "rb") as f:
        result = client.dubbing.create(
            file=f,
            name=name or Path(file_path).stem,
            source_lang=source_lang,
            target_lang=target_lang,
            num_speakers=0,
            highest_resolution=True,
            dubbing_studio=False,
        )
    return result.dubbing_id


def wait_for_dubbed(dubbing_id: str, api_key: str, poll_secs: int = 10) -> None:
    """Block until ElevenLabs dubbing is complete (status == 'dubbed')."""
    client = _client(api_key)
    while True:
        status = client.dubbing.get(dubbing_id).status
        print(f"      status: {status}")
        if status == "dubbed":
            return
        if status == "failed":
            raise RuntimeError(f"ElevenLabs dubbing failed: {dubbing_id}")
        time.sleep(poll_secs)


# ── Step 2: Fetch SRT transcript ──────────────────────────────────────────────

def fetch_srt(dubbing_id: str, api_key: str, language_code: str = "en") -> str:
    """
    Download the SRT transcript for the dubbed language.
    Uses requests directly because the ElevenLabs SDK mis-handles text/plain.
    """
    r = requests.get(
        f"{ELEVEN_BASE}/dubbing/{dubbing_id}/transcript/{language_code}",
        headers={"xi-api-key": api_key},
        params={"format_type": "srt"},
    )
    r.raise_for_status()
    return r.text


# ── Step 3: Parse + group SRT segments ───────────────────────────────────────

def _srt_time_to_sec(t: str) -> float:
    """Convert 'HH:MM:SS,mmm' to float seconds."""
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(srt_text: str) -> list:
    """Return list of (start_sec, end_sec, text) from SRT."""
    segments = []
    for block in srt_text.strip().split("\n\n"):
        lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
        if len(lines) < 3:
            continue
        # line 0 = index number, line 1 = timestamps, lines 2+ = text
        time_match = re.match(r"(.+) --> (.+)", lines[1])
        if not time_match:
            continue
        start = _srt_time_to_sec(time_match.group(1))
        end = _srt_time_to_sec(time_match.group(2))
        text = " ".join(lines[2:])
        segments.append((start, end, text))
    return segments


def group_segments(segments: list, gap_threshold: float = 0.15) -> list:
    """
    Merge consecutive subtitle blocks that have no audible gap between them.
    Returns list of (start_sec, end_sec, full_text).
    """
    if not segments:
        return []
    groups = []
    g_start, g_end, g_texts = segments[0][0], segments[0][1], [segments[0][2]]
    for start, end, text in segments[1:]:
        if start - g_end < gap_threshold:
            g_end = end
            g_texts.append(text)
        else:
            groups.append((g_start, g_end, " ".join(g_texts)))
            g_start, g_end, g_texts = start, end, [text]
    groups.append((g_start, g_end, " ".join(g_texts)))
    return groups


# ── Step 4: Generate Hugo TTS per segment ────────────────────────────────────

def generate_hugo_tts(text: str, api_key: str) -> bytes:
    """Generate MP3 audio for text using the Hugo voice."""
    client = _client(api_key)
    chunks = client.text_to_speech.convert(
        text=text,
        voice_id=HUGO_VOICE_ID,
        model_id="eleven_multilingual_v2",
        voice_settings={"stability": 0.5, "similarity_boost": 0.75},
    )
    return b"".join(chunks)


# ── Step 5: Build final dubbed video with ffmpeg ──────────────────────────────

def _get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def _atempo_chain(ratio: float) -> str:
    """Build atempo filter chain for ratios outside the [0.5, 2.0] range."""
    filters = []
    while ratio > 2.0:
        filters.append("atempo=2.0")
        ratio /= 2.0
    while ratio < 0.5:
        filters.append("atempo=0.5")
        ratio /= 0.5
    filters.append(f"atempo={ratio:.6f}")
    return ",".join(filters)


def build_dubbed_video(
    source_video: str,
    groups: list,
    api_key: str,
    output_path: str,
) -> str:
    """
    For each segment group:
      1. Generate Hugo TTS
      2. Time-stretch to fit the original segment window
      3. Mix all segments at their correct timestamps
      4. Mux onto the original video (replacing its audio)
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        positioned = []  # list of (start_ms, wav_path)

        for i, (start, end, text) in enumerate(groups):
            duration = end - start
            if duration <= 0 or not text.strip():
                continue

            print(f"      [{i+1}/{len(groups)}] {start:.1f}s — {text[:60]}...")

            # Generate Hugo TTS
            tts_bytes = generate_hugo_tts(text, api_key)
            mp3_path = os.path.join(tmp, f"tts_{i:04d}.mp3")
            with open(mp3_path, "wb") as f:
                f.write(tts_bytes)

            # Measure TTS duration
            tts_dur = _get_duration(mp3_path)

            # Only speed up Hugo if TTS overflows the window.
            # If TTS is shorter, let it play at natural speed and pad with silence —
            # slowing Hugo down to fill the Portuguese speaker's window sounds unnatural.
            if tts_dur > duration:
                ratio = min(4.0, tts_dur / duration)
                tempo_filter = f"{_atempo_chain(ratio)},"
            else:
                tempo_filter = ""

            # Pad to exact segment duration (silence fills any remaining time)
            wav_path = os.path.join(tmp, f"seg_{i:04d}.wav")
            subprocess.run([
                "ffmpeg", "-y", "-i", mp3_path,
                "-filter_complex",
                f"[0:a]{tempo_filter}apad,atrim=end={duration:.6f}[out]",
                "-map", "[out]", "-ar", "44100", "-ac", "1", wav_path,
            ], capture_output=True, check=True)

            positioned.append((int(start * 1000), wav_path))

        if not positioned:
            raise RuntimeError("No audio segments were generated.")

        # Build filter_complex: adelay each segment, then amix everything
        video_dur = _get_duration(source_video)

        # Input list: source video + all segment wavs
        inputs = ["-i", source_video]
        for _, seg in positioned:
            inputs += ["-i", seg]

        filters = []
        mix_labels = []

        # Silence base matching video length (from source video audio track silenced)
        filters.append(f"[0:a]volume=0,atrim=end={video_dur:.3f}[sil]")
        mix_labels.append("[sil]")

        for idx, (delay_ms, _) in enumerate(positioned):
            label = f"[s{idx}]"
            filters.append(f"[{idx+1}:a]adelay={delay_ms}|{delay_ms}[s{idx}]")
            mix_labels.append(label)

        n = len(mix_labels)
        filters.append(
            f"{''.join(mix_labels)}amix=inputs={n}:normalize=0:dropout_transition=0[aout]"
        )

        filter_complex = ";".join(filters)

        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_path,
        ]
        subprocess.run(cmd, check=True)

    return output_path
