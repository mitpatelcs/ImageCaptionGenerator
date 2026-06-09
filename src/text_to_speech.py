from pathlib import Path

from src.config import ARTIFACTS_DIR


DEFAULT_AUDIO_PATH = ARTIFACTS_DIR / "predicted_caption.mp3"


def clean_caption_for_speech(caption):
    """Remove model tokens and extra spaces before converting text to speech."""
    if isinstance(caption, (list, tuple)):
        caption = " ".join(caption)

    caption = str(caption)
    caption = caption.replace("startseq", "")
    caption = caption.replace("endseq", "")
    caption = " ".join(caption.split())

    return caption


def text_to_speech(caption, audio_path=DEFAULT_AUDIO_PATH, lang="en", slow=False):
    """
    Convert a caption into an MP3 audio file using gTTS.

    gTTS needs an internet connection because it calls Google's text-to-speech
    service. The generated audio path is returned so notebooks, APIs, or apps
    can play or send the file.
    """
    from gtts import gTTS

    caption = clean_caption_for_speech(caption)

    if not caption:
        raise ValueError("Caption text is empty. Cannot generate audio.")

    audio_path = Path(audio_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    tts = gTTS(text=caption, lang=lang, slow=slow)
    tts.save(str(audio_path))

    return audio_path


def play_audio(audio_path=DEFAULT_AUDIO_PATH, autoplay=True):
    """Display an audio player in a Jupyter notebook."""
    from IPython.display import Audio, display

    display(Audio(str(audio_path), autoplay=autoplay))

