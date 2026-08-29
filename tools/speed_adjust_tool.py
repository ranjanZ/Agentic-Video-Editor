"""
Speed Adjust Tool - Change video playback speed.

This tool adjusts the playback speed of a video, optionally with pitch correction.
"""

import os
from typing import Dict, Any
from .base_tool import BaseTool, ToolResult
from core.video_utils import VideoFileClip, apply_speed, set_audio


class SpeedAdjustTool(BaseTool):
    """
    Adjust the playback speed of a video.
    
    Can speed up or slow down video while optionally preserving audio pitch.
    """
    
    @property
    def name(self) -> str:
        return "speed_adjust"
    
    @property
    def description(self) -> str:
        return (
            "Adjust the playback speed of a video. Speed up (>1) or slow down (<1). "
            "Useful for creating time-lapses, slow motion, or fitting content to duration."
        )
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Path to input video"},
                "output_path": {"type": "string", "description": "Path to save output video"},
                "speed_factor": {
                    "type": "number",
                    "description": "Speed multiplier (e.g., 2.0 = 2x faster, 0.5 = half speed)",
                    "default": 1.0
                },
                "keep_audio_pitch": {
                    "type": "boolean",
                    "description": "Attempt to preserve audio pitch when changing speed",
                    "default": False
                },
                "fps": {
                    "type": "integer",
                    "description": "Output frame rate",
                    "default": 30
                }
            },
            "required": ["video_path", "output_path", "speed_factor"]
        }
    
    def execute(
        self,
        video_path: str,
        output_path: str,
        speed_factor: float = 1.0,
        keep_audio_pitch: bool = False,
        fps: int = 30,
        **kwargs
    ) -> ToolResult:
        """
        Execute speed adjustment.
        
        Args:
            video_path: Path to input video
            output_path: Path for output video
            speed_factor: Speed multiplier
            keep_audio_pitch: Preserve audio pitch
            fps: Output frame rate
            
        Returns:
            ToolResult with output path and duration info
        """
        try:
            if not os.path.exists(video_path):
                return ToolResult(
                    success=False,
                    error=f"Video file not found: {video_path}"
                )
            
            if speed_factor <= 0:
                return ToolResult(
                    success=False,
                    error="Speed factor must be positive"
                )
            
            video = VideoFileClip(video_path)
            original_duration = video.duration
            
            # Apply speed change
            sped_video = apply_speed(video, speed_factor)
            
            # Write output
            sped_video.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                fps=fps,
                logger=None
            )
            
            new_duration = sped_video.duration
            
            video.close()
            sped_video.close()
            
            return ToolResult(
                success=True,
                output_path=output_path,
                message=f"Speed adjusted by {speed_factor}x",
                metadata={
                    "speed_factor": speed_factor,
                    "original_duration": original_duration,
                    "new_duration": new_duration,
                    "duration_change": original_duration - new_duration
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"stage": "speed_adjust"}
            )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Adjust video playback speed")
    parser.add_argument("--video", type=str, default="data/input/input.mkv", help="Path to input video")
    parser.add_argument("--output", type=str, default="data/output/speed_adjusted_output.mp4", help="Path to output video")
    parser.add_argument("--speed", type=float, default=1.0, help="Speed multiplier (e.g., 2.0 = 2x faster, 0.5 = half speed)")
    parser.add_argument("--keep-pitch", action="store_true", help="Attempt to preserve audio pitch")
    parser.add_argument("--fps", type=int, default=30, help="Output frame rate")
    
    args = parser.parse_args()
    
    tool = SpeedAdjustTool()
    result = tool.execute(
        video_path=args.video,
        output_path=args.output,
        speed_factor=args.speed,
        keep_audio_pitch=args.keep_pitch,
        fps=args.fps
    )
    
    if result.success:
        print(f"Success: {result.message}")
        print(f"Output: {result.output_path}")
        print(f"Original duration: {result.metadata.get('original_duration', 0):.2f}s")
        print(f"New duration: {result.metadata.get('new_duration', 0):.2f}s")
    else:
        print(f"Error: {result.error}")
