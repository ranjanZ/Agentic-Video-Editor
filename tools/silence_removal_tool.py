"""
Silence Removal Tool - Remove silent portions from video using Whisper.

This tool analyzes audio in a video, detects speech segments using Whisper,
and removes portions without speech.
"""

import os
from typing import Dict, Any, List
import whisper
from moviepy.editor import VideoFileClip, concatenate_videoclips

from .base_tool import BaseTool, ToolResult


class SilenceRemovalTool(BaseTool):
    """
    Remove silent portions from a video by detecting speech segments.
    
    This tool uses Whisper to transcribe audio and identify speech segments,
    then cuts the video to keep only those segments with optional padding.
    """
    
    @property
    def name(self) -> str:
        return "silence_removal"
    
    @property
    def description(self) -> str:
        return (
            "Remove silent portions from a video by detecting speech using Whisper AI. "
            "Keeps only segments where someone is speaking, with configurable padding. "
            "Useful for creating concise videos from recordings with pauses."
        )
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Path to input video file"},
                "output_path": {"type": "string", "description": "Path to save output video"},
                "model_size": {
                    "type": "string",
                    "description": "Whisper model size (tiny, base, small, medium, large)",
                    "default": "base",
                    "enum": ["tiny", "base", "small", "medium", "large"]
                },
                "padding_ms": {
                    "type": "integer",
                    "description": "Padding in milliseconds around speech segments",
                    "default": 200
                },
                "task": {
                    "type": "string",
                    "description": "Transcription task",
                    "default": "translate",
                    "enum": ["transcribe", "translate"]
                }
            },
            "required": ["video_path", "output_path"]
        }
    
    def execute(
        self,
        video_path: str,
        output_path: str,
        model_size: str = "base",
        padding_ms: int = 200,
        task: str = "translate",
        **kwargs
    ) -> ToolResult:
        """
        Execute silence removal pipeline.
        
        Args:
            video_path: Path to input video
            output_path: Path for output video
            model_size: Whisper model size
            padding_ms: Padding around speech segments in milliseconds
            task: "transcribe" or "translate"
            
        Returns:
            ToolResult with output path and segment information
        """
        try:
            if not os.path.exists(video_path):
                return ToolResult(
                    success=False,
                    error=f"Video file not found: {video_path}"
                )
            
            # Create temp directory if needed
            temp_audio = "temp_extracted_audio.wav"
            
            # Step 1: Extract audio
            video = VideoFileClip(video_path)
            if video.audio is None:
                video.close()
                return ToolResult(
                    success=False,
                    error="No audio stream found in the video"
                )
            
            video.audio.write_audiofile(temp_audio, verbose=False, logger=None)
            video.close()
            
            # Step 2: Transcribe with timestamps
            model = whisper.load_model(model_size)
            result = model.transcribe(temp_audio, task=task, word_timestamps=False)
            
            segments = [
                {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
                for seg in result["segments"]
            ]
            
            if not segments:
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
                return ToolResult(
                    success=False,
                    error="No speech segments detected in the audio"
                )
            
            # Step 3: Cut video using segments
            video = VideoFileClip(video_path)
            padding_sec = padding_ms / 1000.0
            
            speech_clips = []
            for seg in segments:
                start = max(0, seg["start"] - padding_sec)
                end = min(video.duration, seg["end"] + padding_sec)
                if end > start:
                    speech_clips.append(video.subclip(start, end))
            
            if not speech_clips:
                video.close()
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
                return ToolResult(
                    success=False,
                    error="No valid speech segments to cut"
                )
            
            final_clip = concatenate_videoclips(speech_clips, method="compose")
            final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
            
            # Cleanup
            video.close()
            final_clip.close()
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            
            # Calculate statistics
            original_duration = video.duration if hasattr(video, 'duration') else 0
            new_duration = sum(seg["end"] - seg["start"] for seg in segments)
            
            return ToolResult(
                success=True,
                output_path=output_path,
                message=f"Removed silence from {len(segments)} speech segments",
                metadata={
                    "num_segments": len(segments),
                    "original_duration": original_duration,
                    "new_duration": new_duration,
                    "time_saved": original_duration - new_duration,
                    "transcript": result["text"],
                    "segments": segments
                }
            )
            
        except Exception as e:
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"stage": "silence_removal"}
            )
