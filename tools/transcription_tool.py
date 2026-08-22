"""
Transcription Tool - Convert speech to text using Whisper.

This tool extracts audio from video and transcribes it to text.
"""

import os
from typing import Dict, Any, Optional
import whisper
from moviepy import VideoFileClip

from .base_tool import BaseTool, ToolResult


class TranscriptionTool(BaseTool):
    """
    Transcribe speech from video or audio files using Whisper AI.
    
    Supports multiple languages and can translate to English.
    """
    
    @property
    def name(self) -> str:
        return "transcription"
    
    @property
    def description(self) -> str:
        return (
            "Transcribe speech from video or audio files using Whisper AI. "
            "Supports automatic language detection and optional translation to English. "
            "Returns full transcript with timestamps."
        )
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "input_path": {"type": "string", "description": "Path to video or audio file"},
                "model_size": {
                    "type": "string",
                    "description": "Whisper model size",
                    "default": "base",
                    "enum": ["tiny", "base", "small", "medium", "large"]
                },
                "language": {
                    "type": "string",
                    "description": "Language code (e.g., 'en', 'es'). Auto-detect if None",
                    "default": None
                },
                "task": {
                    "type": "string",
                    "description": "Task type",
                    "default": "transcribe",
                    "enum": ["transcribe", "translate"]
                },
                "word_timestamps": {
                    "type": "boolean",
                    "description": "Include word-level timestamps",
                    "default": False
                }
            },
            "required": ["input_path"]
        }
    
    def execute(
        self,
        input_path: str,
        model_size: str = "base",
        language: Optional[str] = None,
        task: str = "transcribe",
        word_timestamps: bool = False,
        **kwargs
    ) -> ToolResult:
        """
        Execute transcription.
        
        Args:
            input_path: Path to video or audio file
            model_size: Whisper model size
            language: Language code for forced language
            task: "transcribe" or "translate"
            word_timestamps: Include word-level timestamps
            
        Returns:
            ToolResult with transcript and metadata
        """
        try:
            if not os.path.exists(input_path):
                return ToolResult(
                    success=False,
                    error=f"Input file not found: {input_path}"
                )
            
            temp_audio = "temp_transcription_audio.wav"
            is_video = input_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))
            
            # Extract audio if video
            if is_video:
                video = VideoFileClip(input_path)
                if video.audio is None:
                    video.close()
                    return ToolResult(
                        success=False,
                        error="No audio stream found in the video"
                    )
                video.audio.write_audiofile(temp_audio, verbose=False, logger=None)
                video.close()
                audio_path = temp_audio
            else:
                audio_path = input_path
            
            # Transcribe
            model = whisper.load_model(model_size)
            result = model.transcribe(
                audio_path,
                language=language,
                task=task,
                word_timestamps=word_timestamps
            )
            
            # Cleanup temp file
            if is_video and os.path.exists(temp_audio):
                os.remove(temp_audio)
            
            segments_info = []
            if "segments" in result:
                segments_info = [
                    {
                        "start": seg["start"],
                        "end": seg["end"],
                        "text": seg["text"].strip()
                    }
                    for seg in result["segments"]
                ]
            
            return ToolResult(
                success=True,
                message=f"Transcribed {len(segments_info)} segments",
                metadata={
                    "full_text": result["text"],
                    "language": result.get("language", "unknown"),
                    "num_segments": len(segments_info),
                    "segments": segments_info,
                    "model_size": model_size,
                    "task": task
                }
            )
            
        except Exception as e:
            temp_audio = "temp_transcription_audio.wav"
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"stage": "transcription"}
            )
