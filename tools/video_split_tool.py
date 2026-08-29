"""
Video Split Tool - Split video into segments and apply speed-up.

This tool wraps the existing process_video functionality into a 
reusable tool interface for agentic invocation.
"""

import os
import sys
import math
from datetime import datetime
from typing import Dict, Any, Optional

# Handle both direct execution and module import
try:
    from .base_tool import BaseTool, ToolResult
    from core.video_utils import (
        VideoFileClip, AudioFileClip, CompositeAudioClip,
        subclip, set_audio, apply_speed, make_vertical,
        prepare_background_audio, probe_video
    )
except ImportError:
    # When running directly (not as a module), add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.base_tool import BaseTool, ToolResult
    from core.video_utils import (
        VideoFileClip, AudioFileClip, CompositeAudioClip,
        subclip, set_audio, apply_speed, make_vertical,
        prepare_background_audio, probe_video
    )


class VideoSplitTool(BaseTool):
    """
    Split a video into segments and apply constant speed-up to fit target duration.
    
    This tool takes a long video and background audio, splits the video into
    manageable segments, applies speed-up to fit a target duration, and adds
    background music.
    """
    
    @property
    def name(self) -> str:
        return "video_split"
    
    @property
    def description(self) -> str:
        return (
            "Split a video into multiple segments and apply speed-up to fit a target duration. "
            "Each segment gets background music added. Useful for creating YouTube Shorts or "
            "Instagram Reels from longer videos."
        )
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Path to input video file"},
                "audio_path": {"type": "string", "description": "Path to background audio file"},
                "output_dir": {"type": "string", "description": "Directory to save output files"},
                "max_segment_duration_minutes": {
                    "type": "number", 
                    "description": "Maximum duration of each segment in minutes",
                    "default": 20
                },
                "target_output_duration_seconds": {
                    "type": "number",
                    "description": "Target duration for each output segment in seconds",
                    "default": 29
                },
                "vertical_mode": {
                    "type": "boolean",
                    "description": "Convert to 9:16 vertical format",
                    "default": True
                },
                "audio_volume": {
                    "type": "number",
                    "description": "Background music volume (0.0-1.0)",
                    "default": 0.4
                }
            },
            "required": ["video_path", "audio_path", "output_dir"]
        }
    
    def execute(
        self,
        video_path: str,
        audio_path: str,
        output_dir: str,
        max_segment_duration_minutes: float = 20,
        target_output_duration_seconds: float = 29,
        vertical_mode: bool = True,
        vertical_width: int = 1080,
        vertical_height: int = 1920,
        audio_volume: float = 0.4,
        keep_original_audio: bool = False,
        audio_fade_in: float = 1.0,
        audio_fade_out: float = 1.0,
        audio_start_seconds: float = 0,
        audio_random_start: bool = False,
        audio_random_seed: Optional[int] = None,
        output_fps: int = 30,
        codec: str = "libx264",
        audio_codec: str = "aac",
        threads: int = 4,
        preset: str = "fast",
        output_format: str = "mp4",
        progress_callback=None,
        **kwargs
    ) -> ToolResult:
        """
        Execute the video split and speed-up pipeline.
        
        Args:
            video_path: Path to input video
            audio_path: Path to background audio
            output_dir: Directory for output files
            max_segment_duration_minutes: Max duration per segment
            target_output_duration_seconds: Target output duration
            vertical_mode: Whether to convert to 9:16
            vertical_width: Target width for vertical mode
            vertical_height: Target height for vertical mode
            audio_volume: Background music volume
            keep_original_audio: Keep original video audio
            audio_fade_in: Fade-in duration
            audio_fade_out: Fade-out duration
            audio_start_seconds: Start position in audio track
            audio_random_start: Random start position per segment
            audio_random_seed: Seed for reproducible randomization
            output_fps: Output frame rate
            codec: Video codec
            audio_codec: Audio codec
            threads: Encoding threads
            preset: Encoding preset
            output_format: Output file format
            progress_callback: Optional callback function(progress: float, status: str)
            
        Returns:
            ToolResult with list of generated files
        """
        def report_progress(progress: float, status: str):
            """Report progress via callback and print to console."""
            if progress_callback:
                progress_callback(progress, status)
            print(f"[Progress {progress*100:5.1f}%] {status}")
        
        try:
            # Print input parameters
            print("\n" + "="*60)
            print("VIDEO SPLIT TOOL")
            print("="*60)
            print(f"Input Parameters:")
            print(f"  - video_path:             {video_path}")
            print(f"  - audio_path:             {audio_path}")
            print(f"  - output_dir:             {output_dir}")
            print(f"  - max_segment_duration:   {max_segment_duration_minutes}min")
            print(f"  - target_duration:        {target_output_duration_seconds}s")
            print(f"  - vertical_mode:          {vertical_mode}")
            print(f"  - audio_volume:           {audio_volume}")
            print("="*60 + "\n")
            
            report_progress(0.0, "Starting video split pipeline...")
            
            # Validate inputs
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
            
            report_progress(0.05, "Loading video file...")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate timestamp for output files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Load video
            video = VideoFileClip(video_path)
            total_duration = video.duration
            max_segment_duration = max_segment_duration_minutes * 60
            
            report_progress(0.10, f"Video loaded: {total_duration:.1f}s")
            
            # Calculate segments
            num_segments = math.ceil(total_duration / max_segment_duration)
            segments = []
            for i in range(num_segments):
                start = i * max_segment_duration
                end = min((i + 1) * max_segment_duration, total_duration)
                segments.append((start, end, end - start))
            
            # Calculate constant speedup
            speedup = max_segment_duration / target_output_duration_seconds
            report_progress(0.15, f"Calculated {num_segments} segments, speedup factor: {speedup:.2f}x")
            
            # Load background audio
            report_progress(0.20, "Loading background audio...")
            bg_audio = AudioFileClip(audio_path)
            
            import random
            rng = random.Random(audio_random_seed) if audio_random_seed is not None else random.Random()
            
            # FFmpeg params for clean vertical output
            ffmpeg_params = [
                "-vf", "setsar=1:1",
                "-metadata:s:v:0", "rotate=0",
                "-map_metadata", "-1",
                "-movflags", "+faststart",
            ]
            
            output_files = []
            
            for idx, (start, end, seg_dur) in enumerate(segments):
                seg_num = idx + 1
                segment_progress = 0.25 + (0.70 * idx / num_segments)
                report_progress(segment_progress, f"Processing segment {seg_num}/{num_segments}...")
                
                output_duration = seg_dur / speedup
                
                # Pick audio start position
                if audio_random_start:
                    seg_audio_start = rng.uniform(0, bg_audio.duration)
                else:
                    seg_audio_start = audio_start_seconds
                
                # Extract and process segment
                segment = subclip(video, start, end)
                sped_up = apply_speed(segment, speedup)
                
                # Apply vertical mode if enabled
                if vertical_mode:
                    sped_up = make_vertical(sped_up, vertical_width, vertical_height)
                
                # Prepare background audio
                segment_bg = prepare_background_audio(
                    bg_audio, output_duration, audio_fade_in, audio_fade_out,
                    audio_volume, start_seconds=seg_audio_start
                )
                
                # Set final audio
                if keep_original_audio and sped_up.audio is not None:
                    final_audio = CompositeAudioClip([sped_up.audio, segment_bg])
                else:
                    final_audio = segment_bg
                
                final_clip = set_audio(sped_up, final_audio)
                
                # Export with timestamp in filename - save to output_dir (not root)
                out_name = f"segment_{seg_num:03d}_{timestamp}_{int(max_segment_duration_minutes)}min_sped_{int(target_output_duration_seconds)}s.{output_format}"
                output_path = os.path.join(output_dir, out_name)
                
                report_progress(segment_progress + 0.05, f"Rendering segment {seg_num}...")
                final_clip.write_videofile(
                    output_path,
                    fps=output_fps,
                    codec=codec,
                    audio_codec=audio_codec,
                    threads=threads,
                    preset=preset,
                    ffmpeg_params=ffmpeg_params,
                    logger=None
                )
                
                output_files.append(output_path)
                
                # Cleanup
                segment.close()
                sped_up.close()
                final_clip.close()
                segment_bg.close()
            
            video.close()
            bg_audio.close()
            
            report_progress(1.0, f"Video split complete! Generated {len(output_files)} segments")
            
            # Print output summary
            print("\n" + "="*60)
            print("OUTPUT SUMMARY")
            print("="*60)
            print(f"Output Parameters:")
            print(f"  - num_segments:       {num_segments}")
            print(f"  - speedup_factor:     {speedup:.2f}x")
            print(f"  - total_input_dur:    {total_duration:.1f}s")
            print(f"  - output_files:       {len(output_files)}")
            for f in output_files:
                print(f"    - {f}")
            print("="*60 + "\n")
            
            return ToolResult(
                success=True,
                message=f"Successfully processed {len(output_files)} segments",
                output_path=output_files[0] if output_files else None,
                metadata={
                    "output_files": output_files,
                    "num_segments": num_segments,
                    "speedup_factor": speedup,
                    "total_input_duration": total_duration,
                    "timestamp": timestamp
                }
            )
            
        except Exception as e:
            report_progress(0.0, f"Error: {str(e)}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"stage": "video_split"}
            )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Split video into segments with speed-up and background music")
    parser.add_argument("--video", type=str, default="data/input/input.mkv", help="Path to input video")
    parser.add_argument("--audio", type=str, default="data/input/input_audio.mp3", help="Path to background audio")
    parser.add_argument("--output-dir", type=str, default="data/output", help="Output directory")
    parser.add_argument("--max-segment-minutes", type=float, default=20, help="Max segment duration in minutes")
    parser.add_argument("--target-duration", type=float, default=29, help="Target output duration in seconds")
    parser.add_argument("--vertical", action="store_true", default=True, help="Convert to vertical format")
    parser.add_argument("--audio-volume", type=float, default=0.4, help="Background music volume")
    
    args = parser.parse_args()
    
    tool = VideoSplitTool()
    result = tool.execute(
        video_path=args.video,
        audio_path=args.audio,
        output_dir=args.output_dir,
        max_segment_duration_minutes=args.max_segment_minutes,
        target_output_duration_seconds=args.target_duration,
        vertical_mode=args.vertical,
        audio_volume=args.audio_volume
    )
    
    if result.success:
        print(f"Success: {result.message}")
        print(f"Output files: {result.metadata.get('output_files', [])}")
    else:
        print(f"Error: {result.error}")
