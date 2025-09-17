import json
import queue
import threading
import re
import sys

import pyttsx3
import simpleaudio as sa
import sounddevice as sd
import winsound
from collections.abc import Iterable
from vosk import Model, KaldiRecognizer

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


# To play audio text-to-speech during execution
class TTSThread(threading.Thread):
    def __init__(self, queue, rate: int = 180, volume: float = 1.0, voice: str | None = None):
        threading.Thread.__init__(self)
        self.queue = queue
        self.daemon = True
        self.rate = rate
        self.volume = volume
        self.voice = voice
        self.start()

    def run(self):
        engine = pyttsx3.init()
        engine.setProperty("rate", self.rate)
        engine.setProperty("volume", self.volume)

        if self.voice is not None:
            voices = engine.getProperty("voices")
            target = self.voice.lower()
            for v in voices:
                if target in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break

        engine.startLoop(False)
        t_running = True
        while t_running or engine.isBusy():
            if self.queue.empty():
                engine.iterate()
            else:
                data = self.queue.get()
                if data == "__STOP__":
                    t_running = False
                else:
                    engine.say(data)
        engine.endLoop()


def streaming_tts(chunks: Iterable[str], rate=180, volume=1.0, voice=None):
    q = queue.Queue()
    tts_thread = TTSThread(q, rate=rate, volume=volume, voice=voice)

    buffer = ""
    try:
        for chunk in chunks:
            if not chunk:
                continue
            text = re.sub(r"\s+", " ", str(chunk))
            text = re.sub("'", "", text)
            buffer += " " + text

            # chunk where sentences end or commas are place for a good mix of streaming with natural pauses
            while True:
                match = re.search(r'(.+?[,.!?])(\s+|$)', buffer)
                if not match:
                    break
                sentence = match.group(1).strip()
                if sentence:
                    q.put(sentence)
                # remove the flushed sentence from buffer
                buffer = buffer[match.end():].lstrip()

        # Flush leftover if anything remains (in case no period at the end)
        if buffer.strip():
            q.put(buffer.strip())
    finally:
        q.put("__STOP__")
        tts_thread.join()


if __name__ == "__main__":
    query = speech_to_text(play_sounds=True)
    print("✅ Final recognized text:", query)
    text_to_speech(query)
