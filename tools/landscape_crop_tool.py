"""Convert a video to a browser-compatible 16:9 landscape output."""

import os
from typing import Any, Dict

from .base_tool import BaseTool, ToolResult
from core.video_utils import VideoFileClip


class LandscapeCropTool(BaseTool):
    @property
    def name(self) -> str:
        return "landscape_crop"

    @property
    def description(self) -> str:
        return "Center-crop or pad a video to a 16:9 landscape MP4 output."

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_path": {"type": "string"},
                "output_path": {"type": "string"},
                "width": {"type": "integer", "default": 1920},
                "height": {"type": "integer", "default": 1080},
                "fps": {"type": "integer", "default": 30},
            },
            "required": ["video_path", "output_path"],
        }

    def execute(self, video_path: str, output_path: str, width: int = 1920, height: int = 1080, fps: int = 30, **kwargs) -> ToolResult:
        try:
            if not os.path.exists(video_path):
                return ToolResult(success=False, error=f"Video file not found: {video_path}")
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            video = VideoFileClip(video_path)
            ratio = width / height
            source_ratio = video.w / video.h
            if source_ratio > ratio:
                crop_h = int(video.h)
                crop_w = int(crop_h * ratio)
                converted = video.cropped(x_center=video.w / 2, y_center=video.h / 2, width=crop_w, height=crop_h) if hasattr(video, "cropped") else video.crop(x_center=video.w / 2, y_center=video.h / 2, width=crop_w, height=crop_h)
            else:
                crop_w = int(video.w)
                crop_h = int(crop_w / ratio)
                converted = video.cropped(x_center=video.w / 2, y_center=video.h / 2, width=crop_w, height=crop_h) if hasattr(video, "cropped") else video.crop(x_center=video.w / 2, y_center=video.h / 2, width=crop_w, height=crop_h)
            converted = converted.resized(new_size=(width, height)) if hasattr(converted, "resized") else converted.resize(newsize=(width, height))
            converted.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=fps, logger=None)
            video.close()
            converted.close()
            return ToolResult(success=True, output_path=output_path, message=f"Converted to {width}x{height} landscape format", metadata={"aspect_ratio": "16:9"})
        except Exception as error:
            return ToolResult(success=False, error=str(error), metadata={"stage": "landscape_crop"})


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert video to 16:9 landscape format")
    parser.add_argument("--video", type=str, default="data/input/input.mkv", help="Path to input video")
    parser.add_argument("--output", type=str, default="data/output/landscape_output.mp4", help="Path to output video")
    parser.add_argument("--width", type=int, default=1920, help="Output width in pixels")
    parser.add_argument("--height", type=int, default=1080, help="Output height in pixels")
    parser.add_argument("--fps", type=int, default=30, help="Output frame rate")
    
    args = parser.parse_args()
    
    tool = LandscapeCropTool()
    result = tool.execute(
        video_path=args.video,
        output_path=args.output,
        width=args.width,
        height=args.height,
        fps=args.fps
    )
    
    if result.success:
        print(f"Success: {result.message}")
        print(f"Output: {result.output_path}")
    else:
        print(f"Error: {result.error}")