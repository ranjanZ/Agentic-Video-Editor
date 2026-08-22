"""
video_utils.py — Helper functions for the video processing pipeline.

Contains:
  - MoviePy 1.x / 2.x compatibility wrappers
  - Vertical (9:16) transform
  - Background-audio preparation (start offset / looping / fades / volume)
  - ffprobe helpers (input rotation detection + output verification)

Compatible with MoviePy 1.x and 2.x (tested on 2.2.1)
"""

import math
import json
import subprocess

# ── Detect MoviePy version and set API wrappers ──────────────────────────
try:
    # MoviePy 2.x imports
    from moviepy import (
        VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips
    )
    from moviepy.audio.fx import AudioFadeIn, AudioFadeOut
    MOVIEPY_V2 = True
except ImportError:
    # MoviePy 1.x imports
    from moviepy import (
        VideoFileClip, AudioFileClip, CompositeAudioClip, concatenate_audioclips
    )
    AudioFadeIn = None
    AudioFadeOut = None
    MOVIEPY_V2 = False


# ── Small helpers ─────────────────────────────────────────────────────────

def _even(n):
    """Round to int and force an even number (required by libx264/yuv420p)."""
    n = int(round(n))
    return n if n % 2 == 0 else n - 1


# ── Version-agnostic wrappers ─────────────────────────────────────────────

def subclip(clip, start, end):
    """Version-agnostic subclip."""
    if MOVIEPY_V2:
        return clip.subclipped(start, end)
    return clip.subclip(start, end)


def set_audio(clip, audio):
    """Version-agnostic set audio."""
    if MOVIEPY_V2:
        return clip.with_audio(audio)
    return clip.set_audio(audio)


def apply_speed(clip, factor):
    """Version-agnostic speedup."""
    if MOVIEPY_V2:
        return clip.with_speed_scaled(factor)
    try:
        from moviepy import vfx
        return clip.fx(vfx.speedx, factor)
    except Exception:
        return clip.speedx(factor)


def set_volume(audio, volume):
    """Version-agnostic volume."""
    if MOVIEPY_V2:
        return audio.with_volume_scaled(volume)
    return audio.volumex(volume)


def apply_audio_fadein(audio, duration):
    """Version-agnostic audio fade-in."""
    if duration <= 0:
        return audio
    if MOVIEPY_V2 and AudioFadeIn is not None:
        return audio.with_effects([AudioFadeIn(duration)])
    return audio.audio_fadein(duration)


def apply_audio_fadeout(audio, duration):
    """Version-agnostic audio fade-out."""
    if duration <= 0:
        return audio
    if MOVIEPY_V2 and AudioFadeOut is not None:
        return audio.with_effects([AudioFadeOut(duration)])
    return audio.audio_fadeout(duration)


# ── Vertical transform ────────────────────────────────────────────────────

def make_vertical(clip, target_w, target_h):
    """
    Center-crop clip to the target aspect ratio, then resize to the exact
    target resolution. All dimensions are forced to even numbers so the
    encoder stores a true 1080x1920 stream (no odd-size / SAR surprises).
    Works for both MoviePy v1 and v2.
    """
    target_w = _even(target_w)
    target_h = _even(target_h)

    orig_w, orig_h = clip.size
    target_ratio = target_w / target_h
    orig_ratio = orig_w / orig_h

    if orig_ratio > target_ratio:
        # Video is wider than target ratio — crop left & right sides
        new_w = _even(orig_h * target_ratio)
        x1 = (orig_w - new_w) // 2
        y1 = 0
        x2 = x1 + new_w
        y2 = orig_h
    else:
        # Video is taller/narrower than target ratio — crop top & bottom
        new_h = _even(orig_w / target_ratio)
        x1 = 0
        y1 = (orig_h - new_h) // 2
        x2 = orig_w
        y2 = y1 + new_h

    # Crop + resize
    if MOVIEPY_V2:
        cropped = clip.cropped(x1=x1, y1=y1, x2=x2, y2=y2)
        resized = cropped.resized(new_size=(target_w, target_h))
    else:
        cropped = clip.crop(x1=x1, y1=y1, x2=x2, y2=y2)
        resized = cropped.resize(newsize=(target_w, target_h))

    return resized


# ── Background audio ──────────────────────────────────────────────────────

def prepare_background_audio(bg_audio, target_duration, fade_in, fade_out,
                             volume, start_seconds=0.0):
    """
    Cut background audio to exactly `target_duration`, starting at
    `start_seconds` inside the source song.

    - If the requested window runs past the end of the song, the song is
      looped and the window wraps around seamlessly.
    - `start_seconds` is taken modulo the song duration, so any value is safe.
    - Applies fade-in / fade-out and volume afterwards.
    """
    song_dur = bg_audio.duration
    start = float(start_seconds) % song_dur
    end = start + target_duration

    if end <= song_dur:
        segment = subclip(bg_audio, start, end)
    else:
        # Need to wrap around -> loop the song enough times, then cut
        loops = math.ceil(end / song_dur)
        looped = concatenate_audioclips([bg_audio] * loops)
        segment = subclip(looped, start, end)

    # Apply fades
    segment = apply_audio_fadein(segment, fade_in)
    segment = apply_audio_fadeout(segment, fade_out)

    # Set volume
    segment = set_volume(segment, volume)

    return segment


# ── ffprobe helpers ───────────────────────────────────────────────────────

def probe_video(path):
    """
    Return dict with width / height / SAR / DAR / rotation for the first
    video stream of `path`, or None if ffprobe is unavailable.
    """
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries",
                "stream=width,height,sample_aspect_ratio,display_aspect_ratio"
                ":stream_side_data=rotation",
                "-of", "json", path,
            ],
            capture_output=True, text=True, check=True,
        ).stdout
        stream = json.loads(out).get("streams", [{}])[0]

        rotation = 0
        for sd in stream.get("side_data_list", []) or []:
            if "rotation" in sd:
                rotation = int(float(sd["rotation"]))

        return {
            "width": stream.get("width"),
            "height": stream.get("height"),
            "sar": stream.get("sample_aspect_ratio"),
            "dar": stream.get("display_aspect_ratio"),
            "rotation": rotation,
        }
    except Exception:
        return None


def verify_output_vertical(output_path, expected_w, expected_h):
    """
    Check the rendered file on disk. Returns True if the stored stream is
    exactly expected_w x expected_h with square pixels and no rotation
    metadata (i.e. players like VLC will open a true vertical window).
    Prints a warning otherwise.
    """
    info = probe_video(output_path)
    if info is None:
        print("  (ffprobe not found - skipped output verification)")
        return True

    ok = (
        info["width"] == _even(expected_w)
        and info["height"] == _even(expected_h)
        and info["rotation"] == 0
        and info["sar"] in ("1:1", "N/A", None)
    )

    print(
        f"  Verified stream: {info['width']}x{info['height']} "
        f"SAR={info['sar']} DAR={info['dar']} rotation={info['rotation']}"
    )
    if not ok:
        print(
            "  WARNING: output does NOT look like a clean vertical stream! "
            f"Expected {_even(expected_w)}x{_even(expected_h)}, SAR 1:1, rotation 0."
        )
    return ok
