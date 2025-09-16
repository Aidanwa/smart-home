import queue
import threading
import sys
import sounddevice as sd
import json
from vosk import Model, KaldiRecognizer
import pyttsx3
import simpleaudio as sa
import winsound
import re

# Load the Vosk model globally so it's only initialized once
model = Model("models/vosk-model-small-en-us-0.15")


if sys.platform == "win32":
    def play_wav_async(path: str):
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
else:
    def play_wav_async(path: str):
        try:
            sa.WaveObject.from_wave_file(path).play()
        except Exception as e:
            print(f"⚠️ Could not play sound {path}: {e}")


def speech_to_text(play_sounds: bool = False):
    recognizer = KaldiRecognizer(model, 16000)
    q = queue.Queue()

    def callback(indata, frames, time, status):
        q.put(bytes(indata))

    if play_sounds:
        play_wav_async("assets/start.wav")

    print("🎙️ Speak now...")

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype="int16",
        channels=1,
        callback=callback,
    ):
        while True:
            data = q.get()
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    if play_sounds:
                        play_wav_async("assets/stop.wav")
                    return text


def text_to_speech(text: str, rate: int = 180, volume: float = 1.0, voice: str | None = None):
    """Convert text to speech using the system TTS engine."""
    engine = pyttsx3.init()

    # Configure properties
    engine.setProperty("rate", rate)     # speed (default ~200)
    engine.setProperty("volume", volume) # volume (0.0 to 1.0)

    # Pick a voice if specified
    if voice is not None:
        voices = engine.getProperty("voices")
        for v in voices:
            if voice.lower() in v.name.lower():
                engine.setProperty("voice", v.id)
                break

    # Speak
    engine.say(text)
    engine.runAndWait()


def text_to_speech(text: str, rate: int = 180, volume: float = 1.0, voice: str | None = None):
    """Convert text to speech using the system TTS engine."""
    engine = pyttsx3.init()

    # Configure properties
    engine.setProperty("rate", rate)     # speed (default ~200)
    engine.setProperty("volume", volume) # volume (0.0 to 1.0)

    # Pick a voice if specified
    if voice is not None:
        voices = engine.getProperty("voices")
        for v in voices:
            if voice.lower() in v.name.lower():
                engine.setProperty("voice", v.id)
                break

    # Speak
    engine.say(text)
    engine.runAndWait()
    

def streaming_tts(text_stream, rate=180, volume=1.0, voice=None, min_chars=40):
    engine = pyttsx3.init(driverName="sapi5")
    engine.setProperty("rate", rate)
    engine.setProperty("volume", volume)
    if voice:
        for v in engine.getProperty("voices"):
            if voice.lower() in v.name.lower():
                engine.setProperty("voice", v.id)
                break

    buffer = ""
    sentence_end = re.compile(r'[.!?]["\')\]]?\s')

    def flush_sentence_chunks():
        nonlocal buffer
        while True:
            m = sentence_end.search(buffer)
            if not m:
                break
            end = m.end()
            chunk = buffer[:end].strip()
            buffer = buffer[end:]
            if chunk:
                engine.say(chunk)
                engine.runAndWait()

    for piece in text_stream:
        buffer += piece
        flush_sentence_chunks()
        if len(buffer) >= min_chars and " " in buffer:
            cut = buffer.rfind(" ", 0, max(min_chars, buffer.find(" ") + 1))
            if cut > 0:
                engine.say(buffer[:cut].strip())
                engine.runAndWait()
                buffer = buffer[cut+1:]

    if buffer.strip():
        engine.say(buffer.strip())
        engine.runAndWait()

    engine.stop()


if __name__ == "__main__":
    query = speech_to_text(play_sounds=True)
    print("✅ Final recognized text:", query)
    text_to_speech(query)
