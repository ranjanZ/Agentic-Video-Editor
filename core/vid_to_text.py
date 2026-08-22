import whisper
from moviepy import VideoFileClip
import os

def extract_speech_from_video(video_path, output_audio_path="temp_audio.wav"):
    """
    Extract audio (speech) from a video file and save as WAV.

    Args:
        video_path (str): Path to the input video file.
        output_audio_path (str): Path where the extracted audio will be saved.

    Returns:
        str: Path to the extracted audio file.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    try:
        # Load video and extract audio
        video = VideoFileClip(video_path)
        audio = video.audio

        if audio is None:
            raise ValueError("No audio stream found in the video.")

        # Write audio to file
        audio.write_audiofile(output_audio_path, verbose=False, logger=None)
        video.close()
        return output_audio_path
    except Exception as e:
        raise RuntimeError(f"Failed to extract audio from video: {e}")


def speech_to_text(audio_path, model_size="base", language=None, task=None):
    """
    Transcribe speech from an audio file to text using Whisper.

    Args:
        audio_path (str): Path to the audio file.
        model_size (str): Whisper model size ("tiny", "base", "small", "medium", "large").
        language (str, optional): Force language code (e.g., "en", "ur"). If None, auto-detect.
        task (str, optional): "transcribe" (original language) or "translate" (to English).

    Returns:
        str: Transcribed (or translated) text.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    try:
        model = whisper.load_model(model_size)
        options = {}
        if language:
            options["language"] = language
        if task:
            options["task"] = task

        result = model.transcribe(audio_path, **options)
        return result["text"]
    except Exception as e:
        raise RuntimeError(f"Speech-to-text conversion failed: {e}")


from pydub import AudioSegment
from pydub.effects import speedup

def make_voice_mature_pydub(input_wav, output_wav, semitones=-3):
    """
    Lower the pitch of the voice to sound more mature.
    
    Args:
        input_wav (str): Path to input WAV file.
        output_wav (str): Path to output WAV file.
        semitones (int): Negative = lower pitch (e.g., -2 to -5). -3 is natural.
    """
    audio = AudioSegment.from_wav(input_wav)
    # Change pitch by adjusting speed, then resample
    # Formula: new_sample_rate = old_sample_rate * (2^(semitones/12))
    octaves = semitones / 12.0
    new_sample_rate = int(audio.frame_rate * (2.0 ** octaves))
    # Shift pitch by changing sample rate (speeds up/slows down, but we compensate duration)
    pitched_audio = audio._spawn(audio.raw_data, overrides={"frame_rate": new_sample_rate})
    # Convert back to original sample rate (preserves duration)
    pitched_audio = pitched_audio.set_frame_rate(audio.frame_rate)
    pitched_audio.export(output_wav, format="wav")
    return output_wav



# ======================
# Example usage
if __name__ == "__main__":
    video_file = "/home/zhedge/Videos/abc-3000.mp4"
    audio_file = "extracted_speech.wav"

    # Step 1: Extract audio from video
    audio_path = extract_speech_from_video(video_file, audio_file)
    print(f"Audio extracted to: {audio_path}")
    make_voice_mature_pydub("extracted_speech.wav", "mature_voice.wav", semitones=-4)

    # Step 2: Convert speech to text
    #transcript = speech_to_text(audio_path, model_size="base")

    transcript = speech_to_text(audio_path, task="transcribe")
    print("\nTranscript:\n", transcript)

