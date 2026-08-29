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


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Complete video processing pipeline: split, speed-up, background music")
    parser.add_argument("--video", type=str, default="data/input/input.mkv", help="Path to input video")
    parser.add_argument("--audio", type=str, default="data/input/input_audio.mp3", help="Path to background audio")
    parser.add_argument("--output-dir", type=str, default="data/output", help="Output directory")
    parser.add_argument("--max-segment-minutes", type=float, default=20, help="Max segment duration in minutes")
    parser.add_argument("--target-duration", type=float, default=29, help="Target output duration in seconds")
    parser.add_argument("--vertical", action="store_true", default=True, help="Convert to vertical format")
    parser.add_argument("--audio-volume", type=float, default=0.4, help="Background music volume")
    parser.add_argument("--keep-original-audio", action="store_true", help="Keep original video audio")
    parser.add_argument("--audio-fade-in", type=float, default=1.0, help="Audio fade-in duration")
    parser.add_argument("--audio-fade-out", type=float, default=1.0, help="Audio fade-out duration")
    
    args = parser.parse_args()
    
    tool = ProcessVideoTool()
    result = tool.execute(
        video_path=args.video,
        audio_path=args.audio,
        output_dir=args.output_dir,
        max_segment_duration_minutes=args.max_segment_minutes,
        target_output_duration_seconds=args.target_duration,
        vertical_mode=args.vertical,
        audio_volume=args.audio_volume,
        keep_original_audio=args.keep_original_audio,
        audio_fade_in=args.audio_fade_in,
        audio_fade_out=args.audio_fade_out
    )
    
    if result.success:
        print(f"Success: {result.message}")
        print(f"Output files: {result.metadata.get('output_files', [])}")
    else:
        print(f"Error: {result.error}")