"""
Silence Removal Tool - Remove silent portions from video using Whisper.

This tool analyzes audio in a video, detects speech segments using Whisper,
and removes portions without speech.
"""

import os
import sys
from typing import Dict, Any, List, Optional
import whisper

# Handle both direct execution and module import
try:
    from .base_tool import BaseTool, ToolResult
except ImportError:
    # When running directly (not as a module), add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.base_tool import BaseTool, ToolResult

from moviepy import VideoFileClip, concatenate_videoclips


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
                "threshold_db": {
                    "type": "number",
                    "description": "Treat audio below this level as silence in decibels",
                    "default": -32,
                    "minimum": -60,
                    "maximum": 0
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
        output_path: Optional[str] = None,
        output_dir: Optional[str] = None,
        model_size: str = "base",
        padding_ms: int = 200,
        threshold_db: float = -32,
        task: str = "translate",
        progress_callback=None,
        **kwargs
    ) -> ToolResult:
        """
        Execute silence removal pipeline.
        
        Args:
            video_path: Path to input video
            output_path: Path for output video (optional, will generate if not provided)
            output_dir: Directory for output (used if output_path not provided)
            model_size: Whisper model size
            padding_ms: Padding around speech segments in milliseconds
            task: "transcribe" or "translate"
            progress_callback: Optional callback function(progress: float, status: str)
            
        Returns:
            ToolResult with output path and segment information
        """
        def report_progress(progress: float, status: str):
            """Report progress via callback and print to console."""
            if progress_callback:
                progress_callback(progress, status)
            # Print progress to console
            print(f"[Progress {progress*100:5.1f}%] {status}")
        
        try:
            from datetime import datetime
            
            if not os.path.exists(video_path):
                return ToolResult(
                    success=False,
                    error=f"Video file not found: {video_path}"
                )
            
            # Print input parameters
            print("\n" + "="*60)
            print("SILENCE REMOVAL TOOL")
            print("="*60)
            print(f"Input Parameters:")
            print(f"  - video_path:     {video_path}")
            print(f"  - output_path:    {output_path or '(auto-generated)'}")
            print(f"  - model_size:     {model_size}")
            print(f"  - padding_ms:     {padding_ms}ms")
            print(f"  - threshold_db:   {threshold_db}dB")
            print(f"  - task:           {task}")
            print("="*60 + "\n")
            
            report_progress(0.0, "Starting silence removal...")
            
            # Generate output path with timestamp if not provided
            if not output_path:
                if not output_dir:
                    output_dir = "data/output"
                os.makedirs(output_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                base_name = os.path.basename(video_path)
                name_without_ext = os.path.splitext(base_name)[0]
                output_path = os.path.join(output_dir, f"{name_without_ext}_no_silence_{timestamp}.mp4")
            
            # Create temp directory if needed
            temp_dir = "data/temp"
            os.makedirs(temp_dir, exist_ok=True)
            temp_audio = os.path.join(temp_dir, f"temp_extracted_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
            
            # Step 1: Extract audio
            report_progress(0.05, "Extracting audio from video...")
            video = VideoFileClip(video_path)
            if video.audio is None:
                video.close()
                return ToolResult(
                    success=False,
                    error="No audio stream found in the video"
                )
            
            video.audio.write_audiofile(temp_audio, logger=None)
            video.close()
            report_progress(0.15, "Audio extraction complete")
            
            # Step 2: Transcribe with timestamps
            report_progress(0.20, f"Loading Whisper model ({model_size})...")
            model = whisper.load_model(model_size)
            report_progress(0.30, "Transcribing audio with Whisper...")
            result = model.transcribe(temp_audio, task=task, word_timestamps=False, fp16=False)
            report_progress(0.50, "Transcription complete")
            
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
            
            report_progress(0.55, f"Found {len(segments)} speech segments")
            
            # Step 3: Cut video using segments
            report_progress(0.60, "Processing video segments...")
            video = VideoFileClip(video_path)
            padding_sec = padding_ms / 1000.0
            
            speech_clips = []
            kept_segments = []
            for i, seg in enumerate(segments):
                start = max(0, seg["start"] - padding_sec)
                end = min(video.duration, seg["end"] + padding_sec)
                if end > start:
                    # Use subclipped for newer moviepy versions, fallback to subclip for older versions
                    clip_method = getattr(video, "subclipped", None)
                    if clip_method is None:
                        clip_method = video.subclip
                    speech_clips.append(clip_method(start, end))
                    kept_segments.append({"start": start, "end": end})
                    report_progress(0.60 + (0.25 * (i+1) / len(segments)), f"Processing segment {i+1}/{len(segments)}")
            
            if not speech_clips:
                video.close()
                if os.path.exists(temp_audio):
                    os.remove(temp_audio)
                return ToolResult(
                    success=False,
                    error="No valid speech segments to cut"
                )
            
            report_progress(0.88, "Concatenating video segments...")
            # Use 'chain' method for much faster concatenation (no re-encoding during concat)
            final_clip = concatenate_videoclips(speech_clips, method="chain")
            original_duration = video.duration or 0
            
            # Determine number of CPU cores to use for encoding
            import multiprocessing
            n_cores = multiprocessing.cpu_count()
            # Use ffmpeg threads for faster encoding (leave 1 core free for system)
            ffmpeg_threads = max(1, n_cores - 1)
            
            report_progress(0.92, f"Writing output video to {output_path} (using {ffmpeg_threads} threads, fast preset)...")
            final_clip.write_videofile(
                output_path, 
                codec="libx264", 
                audio_codec="aac", 
                logger=None,
                threads=ffmpeg_threads,  # Enable multi-threading
                preset="fast",  # Fast encoding preset (much faster than medium)
                bitrate="2000k",  # Reasonable bitrate to balance quality/speed
                audio_bitrate="128k"
            )
            
            # Cleanup
            video.close()
            final_clip.close()
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            
            # Calculate statistics
            new_duration = sum(clip.duration or 0 for clip in speech_clips)
            
            report_progress(1.0, "Silence removal complete!")
            
            # Print output summary
            print("\n" + "="*60)
            print("OUTPUT SUMMARY")
            print("="*60)
            print(f"Output Parameters:")
            print(f"  - output_path:        {output_path}")
            print(f"  - num_segments:       {len(segments)}")
            print(f"  - original_duration:  {original_duration:.2f}s")
            print(f"  - new_duration:       {new_duration:.2f}s")
            print(f"  - time_saved:         {original_duration - new_duration:.2f}s")
            print(f"  - compression_ratio:  {(1 - new_duration/original_duration)*100:.1f}%")
            print("="*60 + "\n")
            
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
                    "segments": segments,
                    "kept_segments": kept_segments,
                    "padding_ms": padding_ms,
                    "threshold_db": threshold_db,
                }
            )
            
        except Exception as e:
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            report_progress(0.0, f"Error: {str(e)}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"stage": "silence_removal"}
            )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Remove silent portions from video using Whisper")
    parser.add_argument("--video", type=str, default="data/input/input.mkv", help="Path to input video")
    parser.add_argument("--output", type=str, default="data/output/no_silence_output.mp4", help="Path to output video")
    parser.add_argument("--model", type=str, default="base", choices=["tiny", "base", "small", "medium", "large"], help="Whisper model size")
    parser.add_argument("--padding-ms", type=int, default=200, help="Padding in milliseconds around speech segments")
    parser.add_argument("--threshold-db", type=float, default=-32, help="Silence threshold in decibels")
    parser.add_argument("--task", type=str, default="translate", choices=["transcribe", "translate"], help="Transcription task")
    
    args = parser.parse_args()
    
    tool = SilenceRemovalTool()
    result = tool.execute(
        video_path=args.video,
        output_path=args.output,
        model_size=args.model,
        padding_ms=args.padding_ms,
        threshold_db=args.threshold_db,
        task=args.task
    )
    
    if result.success:
        print(f"Success: {result.message}")
        print(f"Output: {result.output_path}")
        print(f"Original duration: {result.metadata.get('original_duration', 0):.2f}s")
        print(f"New duration: {result.metadata.get('new_duration', 0):.2f}s")
    else:
        print(f"Error: {result.error}")

