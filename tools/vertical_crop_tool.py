"""
Vertical Crop Tool - Convert video to 9:16 vertical format.

This tool crops and resizes videos to vertical format for Shorts/Reels.
"""

import os
from typing import Dict, Any
from .base_tool import BaseTool, ToolResult
from core.video_utils import VideoFileClip, make_vertical


class VerticalCropTool(BaseTool):
    """
    Convert video to vertical 9:16 aspect ratio.
    
    Crops the center of the video and resizes to standard vertical formats
    used by YouTube Shorts, Instagram Reels, and TikTok.
    """
    
    @property
    def name(self) -> str:
        return "vertical_crop"
    
    @property
    def description(self) -> str:
        return (
            "Convert landscape or square video to vertical 9:16 format. "
            "Crops the center portion and resizes to standard vertical resolutions. "
            "Ideal for creating Shorts, Reels, or TikToks from horizontal footage."
        )
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Path to input video"},
                "output_path": {"type": "string", "description": "Path to save output video"},
                "width": {
                    "type": "integer",
                    "description": "Output width in pixels",
                    "default": 1080
                },
                "height": {
                    "type": "integer",
                    "description": "Output height in pixels",
                    "default": 1920
                },
                "fps": {
                    "type": "integer",
                    "description": "Output frame rate",
                    "default": 30
                }
            },
            "required": ["video_path", "output_path"]
        }
    
    def execute(
        self,
        video_path: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        **kwargs
    ) -> ToolResult:
        """
        Execute vertical crop conversion.
        
        Args:
            video_path: Path to input video
            output_path: Path for output video
            width: Output width (default 1080)
            height: Output height (default 1920)
            fps: Output frame rate
            
        Returns:
            ToolResult with output path and resolution info
        """
        try:
            if not os.path.exists(video_path):
                return ToolResult(
                    success=False,
                    error=f"Video file not found: {video_path}"
                )
            
            video = VideoFileClip(video_path)
            original_size = video.size
            
            # Apply vertical crop
            vertical_video = make_vertical(video, width, height)
            
            # Write output
            vertical_video.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                fps=fps,
                logger=None
            )
            
            video.close()
            vertical_video.close()
            
            return ToolResult(
                success=True,
                output_path=output_path,
                message=f"Converted to {width}x{height} vertical format",
                metadata={
                    "original_resolution": f"{original_size[0]}x{original_size[1]}",
                    "new_resolution": f"{width}x{height}",
                    "aspect_ratio": "9:16"
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"stage": "vertical_crop"}
            )
