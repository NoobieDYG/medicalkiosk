import io
import tempfile
import wave

from faster_whisper import WhisperModel
from piper import PiperVoice
from pathlib import Path

PIPER_MODEL_PATH = str(Path(__file__).resolve().parent.parent / "models" / "en_US-lessac-medium.onnx")
_whisper_model = None
_piper_voice = None

WHISPER_MODEL_SIZE = "base"  

def get_whisper_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _whisper_model


def get_piper_voice() -> PiperVoice:
    global _piper_voice
    if _piper_voice is None:
        _piper_voice = PiperVoice.load(PIPER_MODEL_PATH)
    return _piper_voice


def transcribe_audio(audio_bytes: bytes) -> str:

    model = get_whisper_model()

    with tempfile.NamedTemporaryFile(suffix=".webm") as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        segments, _ = model.transcribe(tmp.name, beam_size=5)
        text = " ".join(segment.text.strip() for segment in segments)

    return text.strip()


def synthesize_speech(text: str) -> bytes:

    voice = get_piper_voice()

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(voice.config.sample_rate)
        voice.synthesize(text, wav_file)

    return buffer.getvalue()