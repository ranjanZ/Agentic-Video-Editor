"""
Silence Removal Tool - Remove silent portions from video using Whisper and audio energy detection.

This tool analyzes audio in a video, detects speech segments using Whisper and audio energy,
and removes portions without speech.
"""

import os
import sys
from typing import Dict, Any, List, Optional
import whisper
import numpy as np
from scipy.io import wavfile

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
                },
                "use_energy_detection": {
                    "type": "boolean",
                    "description": "Use audio energy detection to find additional silent gaps",
                    "default": True
                },
                "energy_threshold_factor": {
                    "type": "number",
                    "description": "Factor for energy-based silence detection (lower = more aggressive)",
                    "default": 0.15,
                    "minimum": 0.05,
                    "maximum": 0.5
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
        use_energy_detection: bool = True,
        energy_threshold_factor: float = 0.15,
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
            threshold_db: Silence threshold in decibels
            task: "transcribe" or "translate"
            use_energy_detection: Whether to use audio energy detection for better silence detection
            energy_threshold_factor: Factor for energy-based silence detection
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
            print(f"  - video_path:             {video_path}")
            print(f"  - output_path:            {output_path or '(auto-generated)'}")
            print(f"  - model_size:             {model_size}")
            print(f"  - padding_ms:             {padding_ms}ms")
            print(f"  - threshold_db:           {threshold_db}dB")
            print(f"  - task:                   {task}")
            print(f"  - use_energy_detection:   {use_energy_detection}")
            print(f"  - energy_threshold_factor:{energy_threshold_factor}")
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
            
            # Step 2: Transcribe with timestamps AND analyze audio energy
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
            
            report_progress(0.55, f"Found {len(segments)} speech segments from Whisper")
            
            # Step 2b: Use energy detection to find additional silent gaps within Whisper segments
            if use_energy_detection:
                report_progress(0.58, "Analyzing audio energy for better silence detection...")
                
                # Read audio file
                sample_rate, audio_data = wavfile.read(temp_audio)
                
                # Convert to mono if stereo
                if len(audio_data.shape) > 1:
                    audio_data = audio_data.mean(axis=1)
                
                # Convert to float for calculations
                audio_float = audio_data.astype(np.float32)
                
                # Calculate RMS energy in small windows (50ms)
                window_size = int(0.05 * sample_rate)  # 50ms windows
                hop_size = window_size // 2
                
                energies = []
                for i in range(0, len(audio_float) - window_size, hop_size):
                    window = audio_float[i:i + window_size]
                    rms = np.sqrt(np.mean(window ** 2))
                    energies.append(rms)
                
                energies = np.array(energies)
                
                # Calculate threshold based on energy distribution
                # Use a percentage of max energy as threshold
                max_energy = np.max(energies)
                min_energy = np.min(energies[energies > 0]) if np.any(energies > 0) else 0
                energy_threshold = min_energy + energy_threshold_factor * (max_energy - min_energy)
                
                # Also consider the dB threshold
                db_threshold_linear = 10 ** (threshold_db / 20)  # Convert dB to linear scale
                energy_threshold = max(energy_threshold, db_threshold_linear)
                
                # Find silent regions within Whisper segments
                refined_segments = []
                time_per_window = hop_size / sample_rate
                
                for seg_idx, seg in enumerate(segments):
                    seg_start_window = int(seg["start"] / time_per_window)
                    seg_end_window = int(seg["end"] / time_per_window)
                    
                    # Get energies for this segment
                    seg_energies = energies[max(0, seg_start_window):min(len(energies), seg_end_window)]
                    
                    if len(seg_energies) == 0:
                        continue
                    
                    # Find continuous non-silent regions within this segment
                    is_speech = seg_energies >= energy_threshold
                    
                    # Find transitions
                    speech_regions = []
                    in_speech = False
                    region_start = None
                    
                    for i, is_sp in enumerate(is_speech):
                        if is_sp and not in_speech:
                            in_speech = True
                            region_start = seg["start"] + i * time_per_window
                        elif not is_sp and in_speech:
                            in_speech = False
                            region_end = seg["start"] + i * time_per_window
                            speech_regions.append((region_start, region_end))
                    
                    # Handle case where speech continues to end
                    if in_speech:
                        region_end = seg["end"]
                        speech_regions.append((region_start, region_end))
                    
                    # Add refined segments
                    for start, end in speech_regions:
                        if end - start > 0.1:  # Only keep segments > 100ms
                            refined_segments.append({
                                "start": start,
                                "end": end,
                                "text": seg["text"]
                            })
                
                if refined_segments:
                    segments = refined_segments
                    report_progress(0.60, f"Refined to {len(segments)} segments using energy detection")
                else:
                    report_progress(0.60, f"Keeping original {len(segments)} segments (energy detection found no refinements)")
            else:
                report_progress(0.60, f"Using {len(segments)} segments from Whisper only")
            
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
    parser.add_argument("--use-energy-detection", action="store_true", default=True, help="Use audio energy detection for better silence removal")
    parser.add_argument("--energy-threshold-factor", type=float, default=0.15, help="Energy threshold factor (lower = more aggressive)")
    
    args = parser.parse_args()
    
    tool = SilenceRemovalTool()
    result = tool.execute(
        video_path=args.video,
        output_path=args.output,
        model_size=args.model,
        padding_ms=args.padding_ms,
        threshold_db=args.threshold_db,
        task=args.task,
        use_energy_detection=args.use_energy_detection,
        energy_threshold_factor=args.energy_threshold_factor
    )
    
    if result.success:
        print(f"Success: {result.message}")
        print(f"Output: {result.output_path}")
        print(f"Original duration: {result.metadata.get('original_duration', 0):.2f}s")
        print(f"New duration: {result.metadata.get('new_duration', 0):.2f}s")
    else:
        print(f"Error: {result.error}")

