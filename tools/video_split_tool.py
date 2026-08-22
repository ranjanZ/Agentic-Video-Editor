"""
Video Split Tool - Split video into segments and apply speed-up.

This tool wraps the existing process_video functionality into a 
reusable tool interface for agentic invocation.
"""

import os
import math
from datetime import datetime
from typing import Dict, Any, Optional

from .base_tool import BaseTool, ToolResult
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
            
        Returns:
            ToolResult with list of generated files
        """
        try:
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
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate timestamp for output files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Load video
            video = VideoFileClip(video_path)
            total_duration = video.duration
            max_segment_duration = max_segment_duration_minutes * 60
            
            # Calculate segments
            num_segments = math.ceil(total_duration / max_segment_duration)
            segments = []
            for i in range(num_segments):
                start = i * max_segment_duration
                end = min((i + 1) * max_segment_duration, total_duration)
                segments.append((start, end, end - start))
            
            # Calculate constant speedup
            speedup = max_segment_duration / target_output_duration_seconds
            
            # Load background audio
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
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"stage": "video_split"}
            )
