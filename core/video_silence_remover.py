import whisper
from moviepy import VideoFileClip, concatenate_videoclips
import os

def extract_speech_from_video(video_path, output_audio_path="temp_audio.wav"):
    """
    Extract audio from a video file and save as WAV.

    Args:
        video_path (str): Path to the input video file.
        output_audio_path (str): Path where the extracted audio will be saved.

    Returns:
        str: Path to the extracted audio file.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    try:
        video = VideoFileClip(video_path)
        audio = video.audio
        if audio is None:
            raise ValueError("No audio stream found in the video.")
        audio.write_audiofile(output_audio_path, verbose=False, logger=None)
        video.close()
        return output_audio_path
    except Exception as e:
        raise RuntimeError(f"Failed to extract audio from video: {e}")

def speech_to_text_with_timestamps(audio_path, model_size="base", task="translate"):
    """
    Transcribe audio and return full text plus speech segments with timestamps.
    If task="translate", non-English speech is translated to English.

    Args:
        audio_path (str): Path to audio file.
        model_size (str): Whisper model size ("tiny", "base", "small", "medium", "large").
        task (str): "transcribe" or "translate".

    Returns:
        tuple: (full_text, segments_list)
            segments_list = [{"start": float, "end": float, "text": str}, ...]
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    model = whisper.load_model(model_size)
    # transcribe with segment timestamps
    result = model.transcribe(audio_path, task=task, word_timestamps=False)
    full_text = result["text"]
    segments = [
        {"start": seg["start"], "end": seg["end"], "text": seg["text"].strip()}
        for seg in result["segments"]
    ]
    return full_text, segments

def cut_video_using_transcript(video_path, transcript_segments, output_path, padding_ms=200):
    """
    Cut the video by removing silent parts, keeping only speech segments from the transcript.

    Args:
        video_path (str): Path to input video.
        transcript_segments (list): List of dicts with 'start' and 'end' keys (seconds).
        output_path (str): Where to save the output video.
        padding_ms (int): Extra milliseconds to add around each speech segment (smoothing).

    Returns:
        str: Path to the output video.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not transcript_segments:
        raise ValueError("Transcript segments list is empty – no speech found.")

    video = VideoFileClip(video_path)
    padding_sec = padding_ms / 1000.0

    speech_clips = []
    for seg in transcript_segments:
        start = max(0, seg["start"] - padding_sec)
        end = min(video.duration, seg["end"] + padding_sec)
        if end > start:
            speech_clips.append(video.subclip(start, end))

    if not speech_clips:
        raise RuntimeError("No valid speech segments to cut.")

    final_clip = concatenate_videoclips(speech_clips, method="compose")
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    video.close()
    return output_path

def process_video_remove_silence(input_video, output_video, model_size="base", padding_ms=200):
    """
    Full pipeline: extract audio -> transcribe (translate to English) -> remove silence -> save video.

    Args:
        input_video (str): Path to input video file.
        output_video (str): Path where the processed video will be saved.
        model_size (str): Whisper model size.
        padding_ms (int): Padding around speech segments (milliseconds).
    """
    temp_audio = "temp_extracted_audio.wav"

    # Step 1: Extract audio
    print("Extracting audio from video...")
    audio_path = extract_speech_from_video(input_video, temp_audio)

    # Step 2: Transcribe with timestamps (translate to English)
    print("Transcribing audio (translating to English if needed)...")
    full_text, segments = speech_to_text_with_timestamps(audio_path, model_size, task="translate")
    print("\n--- Full English Transcript ---")
    print(full_text)
    print(f"\nFound {len(segments)} speech segments.")

    # Step 3: Cut video using segments
    print("\nRemoving silent parts and saving new video...")
    cut_video_using_transcript(input_video, segments, output_video, padding_ms)

    # Cleanup temporary audio file
    if os.path.exists(temp_audio):
        os.remove(temp_audio)

    print(f"\nDone! Output video saved to: {output_video}")

# ======================
# Example usage
if __name__ == "__main__":
    # Replace with your actual video path
    input_video = "/home/zhedge/Videos/abc-3000.mp4"
    output_video = "output_no_silence.mp4"

    process_video_remove_silence(input_video, output_video, model_size="base", padding_ms=200)
