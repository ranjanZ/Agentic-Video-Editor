"""
Audio Mix Tool - Mix background music with video audio.

This tool adds background music to a video with configurable volume and fade effects.
"""

import os
import math
from typing import Dict, Any
from .base_tool import BaseTool, ToolResult
from core.video_utils import (
    VideoFileClip, AudioFileClip, CompositeAudioClip,
    subclip, set_audio, prepare_background_audio
)


class AudioMixTool(BaseTool):
    """
    Mix background music with video's original audio.
    
    Adds background music to a video with control over volume levels,
    fade in/out effects, and start position.
    """
    
    @property
    def name(self) -> str:
        return "audio_mix"
    
    @property
    def description(self) -> str:
        return (
            "Add background music to a video while optionally keeping the original audio. "
            "Control volume levels, fade effects, and music start position. "
            "Perfect for adding mood music to vlogs or content videos."
        )
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Path to input video"},
                "audio_path": {"type": "string", "description": "Path to background music file"},
                "output_path": {"type": "string", "description": "Path to save output video"},
                "music_volume": {
                    "type": "number",
                    "description": "Background music volume (0.0-1.0)",
                    "default": 0.3
                },
                "original_volume": {
                    "type": "number",
                    "description": "Original audio volume (0.0-1.0), 0 to mute",
                    "default": 1.0
                },
                "fade_in": {
                    "type": "number",
                    "description": "Fade-in duration in seconds",
                    "default": 1.0
                },
                "fade_out": {
                    "type": "number",
                    "description": "Fade-out duration in seconds",
                    "default": 1.0
                },
                "start_seconds": {
                    "type": "number",
                    "description": "Start position in audio track",
                    "default": 0
                },
                "loop_audio": {
                    "type": "boolean",
                    "description": "Loop audio if shorter than video",
                    "default": True
                }
            },
            "required": ["video_path", "audio_path", "output_path"]
        }
    
    def execute(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        music_volume: float = 0.3,
        original_volume: float = 1.0,
        fade_in: float = 1.0,
        fade_out: float = 1.0,
        start_seconds: float = 0,
        loop_audio: bool = True,
        **kwargs
    ) -> ToolResult:
        """
        Execute audio mixing.
        
        Args:
            video_path: Path to input video
            audio_path: Path to background music
            output_path: Path for output video
            music_volume: Background music volume
            original_volume: Original audio volume
            fade_in: Fade-in duration
            fade_out: Fade-out duration
            start_seconds: Start position in audio track
            loop_audio: Loop audio if needed
            
        Returns:
            ToolResult with output path and audio info
        """
        try:
            if not os.path.exists(video_path):
                return ToolResult(
                    success=False,
                    error=f"Video file not found: {video_path}"
                )
            if not os.path.exists(audio_path):
                return ToolResult(
                    success=False,
                    error=f"Audio file not found: {audio_path}"
                )
            
            video = VideoFileClip(video_path)
            bg_audio = AudioFileClip(audio_path)
            
            target_duration = video.duration
            
            # Prepare background music
            segment_bg = prepare_background_audio(
                bg_audio, target_duration, fade_in, fade_out,
                music_volume, start_seconds=start_seconds
            )
            
            # Mix with original audio if desired
            if original_volume > 0 and video.audio is not None:
                from core.video_utils import set_volume
                original_audio = set_volume(video.audio, original_volume)
                final_audio = CompositeAudioClip([original_audio, segment_bg])
            else:
                final_audio = segment_bg
            
            # Set audio and export
            final_clip = set_audio(video, final_audio)
            final_clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                logger=None
            )
            
            video.close()
            bg_audio.close()
            final_clip.close()
            segment_bg.close()
            
            return ToolResult(
                success=True,
                output_path=output_path,
                message="Background music mixed successfully",
                metadata={
                    "music_volume": music_volume,
                    "original_volume": original_volume,
                    "video_duration": target_duration,
                    "audio_duration": bg_audio.duration if hasattr(bg_audio, 'duration') else 0
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"stage": "audio_mix"}
            )
