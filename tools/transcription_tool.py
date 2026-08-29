"""
Transcription Tool - Convert speech to text using Whisper.

This tool extracts audio from video and transcribes it to text.
"""

import os
import sys
from typing import Dict, Any, Optional
import whisper
from moviepy import VideoFileClip

# Handle both direct execution and module import
try:
    from .base_tool import BaseTool, ToolResult
except ImportError:
    # When running directly (not as a module), add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.base_tool import BaseTool, ToolResult


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
        progress_callback=None,
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
            progress_callback: Optional callback function(progress: float, status: str)
            
        Returns:
            ToolResult with transcript and metadata
        """
        def report_progress(progress: float, status: str):
            """Report progress via callback and print to console."""
            if progress_callback:
                progress_callback(progress, status)
            print(f"[Progress {progress*100:5.1f}%] {status}")
        
        try:
            # Print input parameters
            print("\n" + "="*60)
            print("TRANSCRIPTION TOOL")
            print("="*60)
            print(f"Input Parameters:")
            print(f"  - input_path:       {input_path}")
            print(f"  - model_size:       {model_size}")
            print(f"  - language:         {language or 'auto-detect'}")
            print(f"  - task:             {task}")
            print(f"  - word_timestamps:  {word_timestamps}")
            print("="*60 + "\n")
            
            report_progress(0.0, "Starting transcription...")
            
            if not os.path.exists(input_path):
                return ToolResult(
                    success=False,
                    error=f"Input file not found: {input_path}"
                )
            
            temp_audio = "temp_transcription_audio.wav"
            is_video = input_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))
            
            # Extract audio if video
            if is_video:
                report_progress(0.10, "Extracting audio from video...")
                video = VideoFileClip(input_path)
                if video.audio is None:
                    video.close()
                    return ToolResult(
                        success=False,
                        error="No audio stream found in the video"
                    )
                video.audio.write_audiofile(temp_audio, logger=None)
                video.close()
                audio_path = temp_audio
                report_progress(0.20, "Audio extraction complete")
            else:
                audio_path = input_path
            
            # Transcribe
            report_progress(0.30, f"Loading Whisper model ({model_size})...")
            model = whisper.load_model(model_size)
            report_progress(0.50, "Transcribing audio...")
            result = model.transcribe(
                audio_path,
                language=language,
                task=task,
                word_timestamps=word_timestamps,
                fp16=False
            )
            report_progress(0.90, "Transcription complete")
            
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
            
            report_progress(1.0, "Transcription finished!")
            
            # Print output summary
            print("\n" + "="*60)
            print("OUTPUT SUMMARY")
            print("="*60)
            print(f"Output Parameters:")
            print(f"  - language:         {result.get('language', 'unknown')}")
            print(f"  - num_segments:     {len(segments_info)}")
            print(f"  - model_size:       {model_size}")
            print(f"  - task:             {task}")
            print(f"  - text_length:      {len(result['text'])} chars")
            print("="*60 + "\n")
            
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
            report_progress(0.0, f"Error: {str(e)}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"stage": "transcription"}
            )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Transcribe speech from video or audio using Whisper")
    parser.add_argument("--input", type=str, default="data/input/input.mkv", help="Path to input video or audio file")
    parser.add_argument("--model", type=str, default="base", choices=["tiny", "base", "small", "medium", "large"], help="Whisper model size")
    parser.add_argument("--language", type=str, default=None, help="Language code (e.g., 'en', 'es'). Auto-detect if None")
    parser.add_argument("--task", type=str, default="transcribe", choices=["transcribe", "translate"], help="Task type")
    parser.add_argument("--word-timestamps", action="store_true", help="Include word-level timestamps")
    
    args = parser.parse_args()
    
    tool = TranscriptionTool()
    result = tool.execute(
        input_path=args.input,
        model_size=args.model,
        language=args.language,
        task=args.task,
        word_timestamps=args.word_timestamps
    )
    
    if result.success:
        print(f"Success: {result.message}")
        print(f"Language: {result.metadata.get('language', 'unknown')}")
        print(f"\nFull Transcript:\n{result.metadata.get('full_text', '')}")
    else:
        print(f"Error: {result.error}")
