"""Agent-facing wrapper for the complete process_video pipeline."""

from typing import Any, Dict, Optional

from .base_tool import ToolResult
from .video_split_tool import VideoSplitTool


class ProcessVideoTool(VideoSplitTool):
    """Run split, speed-up, background music, and optional vertical output."""

    @property
    def name(self) -> str:
        return "process_video_pipeline"

    @property
    def description(self) -> str:
        return (
            "Run the complete process_video.py pipeline: split a video, speed each segment "
            "to a target duration, add background music, and optionally convert to 9:16."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        schema = super().input_schema
        schema["properties"].update({
            "keep_original_audio": {"type": "boolean", "default": False},
            "audio_fade_in": {"type": "number", "default": 1.0},
            "audio_fade_out": {"type": "number", "default": 1.0},
            "audio_start_seconds": {"type": "number", "default": 0},
            "audio_random_start": {"type": "boolean", "default": False},
            "audio_random_seed": {"type": ["integer", "null"], "default": None},
            "vertical_width": {"type": "integer", "default": 1080},
            "vertical_height": {"type": "integer", "default": 1920},
            "output_fps": {"type": "integer", "default": 30},
            "threads": {"type": "integer", "default": 4},
            "preset": {"type": "string", "default": "fast"},
            "output_format": {"type": "string", "default": "mp4"},
        })
        return schema

    def execute(self, **kwargs: Any) -> ToolResult:
        return super().execute(**kwargs)