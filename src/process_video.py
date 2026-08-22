#!/usr/bin/env python3
"""
process_video.py — Main pipeline: split, speed-up, background music, vertical mode.

Usage:
    python3 process_video.py [config.yaml]

Helpers live in video_utils.py (same folder).
Compatible with MoviePy 1.x and 2.x (tested on 2.2.1)
Outputs true 9:16 vertical videos for YouTube Shorts / Instagram Reels / Facebook Reels
"""

import os
import sys
import math
import random
import yaml

from video_utils import (
    MOVIEPY_V2,
    VideoFileClip, AudioFileClip, CompositeAudioClip,
    subclip, set_audio, apply_speed,
    make_vertical, prepare_background_audio,
    probe_video, verify_output_vertical,
)


def load_config(config_path):
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def process_video(config):
    video_path = config['input_video_path']
    audio_path = config['input_audio_path']
    output_dir = config['output_dir']

    max_segment_duration = config.get('max_segment_duration_minutes', 20) * 60
    target_output_duration = config.get('target_output_duration_seconds', 29)

    audio_volume = config.get('audio_volume', 0.4)
    keep_original = config.get('keep_original_audio', False)
    fade_in = config.get('audio_fade_in_seconds', 1.0)
    fade_out = config.get('audio_fade_out_seconds', 1.0)

    # ── Audio start-position settings (NEW) ──
    audio_start_seconds = config.get('audio_start_seconds', 0)
    audio_random_start = config.get('audio_random_start', False)
    audio_random_seed = config.get('audio_random_seed', None)  # null = different each run

    output_fps = config.get('output_fps', 30)
    codec = config.get('codec', 'libx264')
    audio_codec = config.get('audio_codec', 'aac')
    threads = config.get('threads', 4)
    preset = config.get('preset', 'fast')
    ext = config.get('output_format', 'mp4')
    show_progress = config.get('show_progress_bar', True)

    # Vertical mode settings
    vertical_mode = config.get('vertical_mode', False)
    vertical_width = config.get('vertical_width', 1080)
    vertical_height = config.get('vertical_height', 1920)

    # Validate paths
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print("VIDEO PROCESSING PIPELINE")
    print(f"{'='*60}")
    print(f"MoviePy     : {'v2.x' if MOVIEPY_V2 else 'v1.x'}")
    print(f"Input Video : {video_path}")
    print(f"Input Audio : {audio_path}")
    print(f"Output Dir  : {output_dir}")
    print(f"Max Segment : {max_segment_duration/60:.1f} min")
    print(f"Target Out  : {target_output_duration} sec")
    if audio_random_start:
        print(f"Audio Start : RANDOM per segment (seed: {audio_random_seed})")
    else:
        print(f"Audio Start : {audio_start_seconds}s (fixed)")
    print(f"Progress Bar: {'ON' if show_progress else 'OFF'}")
    if vertical_mode:
        print(f"Vertical    : ON ({vertical_width}x{vertical_height})")
    else:
        print(f"Vertical    : OFF (original ratio)")
    print(f"{'='*60}\n")

    # ── Inspect the input container (rotation metadata etc.) ──
    in_info = probe_video(video_path)
    if in_info:
        print(f"Input stream: {in_info['width']}x{in_info['height']} "
              f"SAR={in_info['sar']} DAR={in_info['dar']} "
              f"rotation={in_info['rotation']}\n")

    print("Loading video...")
    video = VideoFileClip(video_path)
    total_duration = video.duration
    orig_w, orig_h = video.size
    print(f"Total duration: {total_duration:.2f} sec ({total_duration/60:.2f} min)")
    print(f"Original size : {orig_w}x{orig_h}\n")

    # Calculate segments
    num_segments = math.ceil(total_duration / max_segment_duration)
    segments = []
    for i in range(num_segments):
        start = i * max_segment_duration
        end = min((i + 1) * max_segment_duration, total_duration)
        segments.append((start, end, end - start))

    print(f"Splitting into {num_segments} segment(s)")

    # CONSTANT speedup factor
    speedup = max_segment_duration / target_output_duration
    print(f"Constant speedup factor: {speedup:.4f}x")
    print(f"{'-'*60}\n")

    print("Loading background audio...")
    bg_audio = AudioFileClip(audio_path)
    print(f"Audio duration: {bg_audio.duration:.2f} sec\n")

    # Random-number generator for per-segment audio start positions
    rng = random.Random(audio_random_seed) if audio_random_seed is not None else random.Random()

    # ── FFmpeg output hardening (NEW) ──
    # Guarantees a *true* vertical file that VLC opens in a vertical window:
    #   setsar=1:1        -> square pixels (no anamorphic/wide display ratio)
    #   rotate=0          -> no rotation display-matrix in the container
    #   -map_metadata -1  -> drop any inherited global metadata
    #   +faststart        -> moov atom first (better streaming/playback)
    ffmpeg_params = [
        "-vf", "setsar=1:1",
        "-metadata:s:v:0", "rotate=0",
        "-map_metadata", "-1",
        "-movflags", "+faststart",
    ]

    processed = 0
    for idx, (start, end, seg_dur) in enumerate(segments):
        seg_num = idx + 1
        output_duration = seg_dur / speedup

        # ── Pick this segment's audio start position (NEW) ──
        if audio_random_start:
            seg_audio_start = rng.uniform(0, bg_audio.duration)
        else:
            seg_audio_start = audio_start_seconds

        print(f"[Segment {seg_num}/{num_segments}]")
        print(f"  Source: {start:.2f}s - {end:.2f}s (duration: {seg_dur:.2f}s)")
        print(f"  Output: ~{output_duration:.2f}s (speedup: {speedup:.2f}x)")
        print(f"  Audio starts at: {seg_audio_start:.2f}s of the song"
              f"{' (random)' if audio_random_start else ''}")

        # Extract segment
        segment = subclip(video, start, end)

        # Apply constant speedup
        sped_up = apply_speed(segment, speedup)

        # Convert to vertical if enabled
        if vertical_mode:
            sped_up = make_vertical(sped_up, vertical_width, vertical_height)
            print(f"  Resized to: {vertical_width}x{vertical_height} (9:16)")

        # Prepare background music for this segment (with start offset)
        segment_bg = prepare_background_audio(
            bg_audio, output_duration, fade_in, fade_out, audio_volume,
            start_seconds=seg_audio_start,
        )

        # Set final audio
        if keep_original and sped_up.audio is not None:
            final_audio = CompositeAudioClip([sped_up.audio, segment_bg])
        else:
            final_audio = segment_bg

        final_clip = set_audio(sped_up, final_audio)

        # Export
        out_name = f"segment_{seg_num:03d}_{max_segment_duration//60}min_sped_{target_output_duration}s.{ext}"
        output_path = os.path.join(output_dir, out_name)

        print(f"  Rendering: {out_name}")

        # Show progress bar if enabled
        logger = 'bar' if show_progress else None

        final_clip.write_videofile(
            output_path,
            fps=output_fps,
            codec=codec,
            audio_codec=audio_codec,
            threads=threads,
            preset=preset,
            ffmpeg_params=ffmpeg_params,
            logger=logger
        )

        # Verify the file on disk is a true vertical stream
        if vertical_mode:
            verify_output_vertical(output_path, vertical_width, vertical_height)

        # Cleanup
        segment.close()
        sped_up.close()
        final_clip.close()
        segment_bg.close()

        print(f"  Saved: {output_path}\n")
        processed += 1

    video.close()
    bg_audio.close()

    print(f"{'='*60}")
    print(f"DONE! Processed {processed} segment(s) -> {output_dir}")
    print(f"{'='*60}")
    return processed


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config/config.yaml'

    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        print("Usage: python3 process_video.py [config.yaml]")
        sys.exit(1)

    config = load_config(config_path)
    process_video(config)


if __name__ == "__main__":
    main()
