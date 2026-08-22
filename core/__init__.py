"""
Core video processing module for Antigenic Video Editor.

This module contains the fundamental video processing utilities and pipelines:
- video_utils: Core video manipulation utilities (MoviePy wrappers, vertical mode, etc.)
- process_video: Main pipeline for splitting videos into segments with speed-up
- video_silence_remover: Remove silence from videos using Whisper transcription
- vid_to_text: Speech-to-text conversion utilities
"""

from .video_utils import (
    MOVIEPY_V2,
    VideoFileClip, AudioFileClip, CompositeAudioClip,
    subclip, set_audio, apply_speed,
    make_vertical, prepare_background_audio,
    probe_video, verify_output_vertical,
)

__version__ = "1.0.0"
__all__ = [
    "MOVIEPY_V2",
    "VideoFileClip",
    "AudioFileClip", 
    "CompositeAudioClip",
    "subclip",
    "set_audio",
    "apply_speed",
    "make_vertical",
    "prepare_background_audio",
    "probe_video",
    "verify_output_vertical",
]
