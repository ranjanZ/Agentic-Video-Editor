"""
Tools module for Antigenic Video Editor.

This module contains reusable video processing tools that can be invoked
by agents or directly through the API. Each tool is a self-contained
unit of functionality with a clear interface.
"""

from .base_tool import BaseTool, ToolResult, ToolRegistry
from .video_split_tool import VideoSplitTool
from .silence_removal_tool import SilenceRemovalTool
from .transcription_tool import TranscriptionTool
from .speed_adjust_tool import SpeedAdjustTool
from .vertical_crop_tool import VerticalCropTool
from .audio_mix_tool import AudioMixTool

__version__ = "1.0.0"
__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolRegistry",
    "VideoSplitTool",
    "SilenceRemovalTool",
    "TranscriptionTool",
    "SpeedAdjustTool",
    "VerticalCropTool",
    "AudioMixTool",
]
