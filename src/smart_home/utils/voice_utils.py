import json
import queue
import threading
import re
import sys
import time
import queue
import os, platform, glob
import logging

import pyttsx3
import simpleaudio as sa
import sounddevice as sd
import winsound
from collections.abc import Iterable
from vosk import Model, KaldiRecognizer
from openwakeword.model import Model as WakeWordModel
from openwakeword.utils import download_models as oww_download_models
import numpy as np
from smart_home.config.paths import MODELS_DIR

logger = logging.getLogger(__name__)

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
            logger.error(f"Could not play sound {path}: {e}", exc_info=True)


def speech_to_text(play_sounds: bool = False):
    recognizer = KaldiRecognizer(model, 16000)
    q = queue.Queue()

    def callback(indata, frames, time, status):
        q.put(bytes(indata))

    if play_sounds:
        play_wav_async("assets/start.wav")

    try:
        print("🎙️ Speak now...")
    except UnicodeEncodeError:
        print("Speak now...")

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


# --- Wake word helper -------------------------------------------------
def _pick_inference_framework():
    # Windows + Py3.13 → ONNX
    if platform.system() == "Windows":
        return "onnx"
    try:
        import tflite_runtime.interpreter as _  # noqa: F401
        return "tflite"
    except Exception:
        return "onnx"

def _normalize_models_for_framework(paths: list[str], framework: str) -> list[str]:
    if not paths:
        return []
    ext = ".onnx" if framework == "onnx" else ".tflite"
    return [p for p in paths if p.lower().endswith(ext) and os.path.exists(p)]


def _discover_downloaded_models(target_dir: str, framework: str) -> list[str]:
    pattern = "*.onnx" if framework == "onnx" else "*.tflite"
    return sorted(glob.glob(os.path.join(target_dir, pattern)))


def _download_oww_models_if_needed(framework: str, target_dir: str) -> list[str]:
    os.makedirs(target_dir, exist_ok=True)
    try:
        # One-time download of all pre-trained models into your repo
        oww_download_models(target_directory=target_dir)
    except Exception as e:
        logger.error(f"Wake model download failed: {e}", exc_info=True)
        return []
    return _discover_downloaded_models(target_dir, framework)


def _load_wake_model(model_paths: list[str] | None):
    framework = _pick_inference_framework()

    # Filter any user-provided paths to match the framework
    chosen = _normalize_models_for_framework(model_paths or [], framework)

    kwargs = {"inference_framework": framework}
    if chosen:
        kwargs["wakeword_models"] = chosen

    # Always provide preprocessing model paths from our downloaded models directory
    # This fixes the issue where AudioFeatures looks for melspectrogram.onnx and embedding_model.onnx
    # in the package's resources/models/ directory (which doesn't exist after pip install)
    target_dir = os.path.abspath(MODELS_DIR / "openwakeword")
    ext = ".onnx" if framework == "onnx" else ".tflite"
    melspec_path = os.path.join(target_dir, f"melspectrogram{ext}")
    embedding_path = os.path.join(target_dir, f"embedding_model{ext}")

    # Pass preprocessing model paths if they exist
    if os.path.exists(melspec_path):
        kwargs["melspec_model_path"] = melspec_path
    if os.path.exists(embedding_path):
        kwargs["embedding_model_path"] = embedding_path

    logger.debug(
        f"Loading wake model with framework={framework}",
        extra={"framework": framework, "custom_models": [os.path.basename(p) for p in chosen] if chosen else None}
    )

    try:
        return WakeWordModel(**kwargs)
    except Exception as e:
        msg = str(e)
        missing_builtin = (
            "NO_SUCHFILE" in msg
            or "File doesn't exist" in msg
            or "resources/models" in msg
        )

        # If we tried to use built-ins (no custom models) and they aren't on disk, download and retry.
        if framework == "onnx" and missing_builtin:
            logger.info("Required ONNX models not found locally. Downloading once…")
            # Keep models alongside your project (not inside site-packages)
            downloaded = _download_oww_models_if_needed(framework, target_dir)

            if downloaded:
                logger.info(
                    f"Using downloaded wake models",
                    extra={"model_count": len(downloaded), "models": [os.path.basename(p) for p in downloaded]}
                )
                # Retry with proper paths after download
                if os.path.exists(melspec_path):
                    kwargs["melspec_model_path"] = melspec_path
                if os.path.exists(embedding_path):
                    kwargs["embedding_model_path"] = embedding_path
                if not chosen:
                    # Use all downloaded wake word models if none were specified
                    kwargs["wakeword_models"] = [p for p in downloaded if "melspectrogram" not in p and "embedding_model" not in p and "silero_vad" not in p]
                return WakeWordModel(**kwargs)

        # Otherwise, surface the original error
        raise

def wait_for_wake_word(
    model_paths: list[str] | None = None,
    threshold: float = 0.5,
    sample_rate: int = 16000,
    block_size: int = 512,
    channel_count: int = 1,
    idle_print_secs: float = 10.0,
    play_sounds: bool = False,
) -> None:
    """
    Blocks until a wake word score crosses `threshold`.
    Then returns (so caller can start STT for the command).
    """
    # If no model paths provided, let OWW load its default bundled models.
    # You can also pass multiple .tflite paths: ["./models/hey_jarvis.tflite", "./models/ok_computer.tflite"]
    if isinstance(model_paths, str):
        model_paths = _parse_wake_models(model_paths)

    model = _load_wake_model(model_paths)  # <-- None passed for wakeword_models

    q: queue.Queue[np.ndarray] = queue.Queue()
    def audio_cb(indata, frames, time_info, status):
        if status:
            logger.error(f"Audio stream error: {status}")
        q.put(indata.copy())

    last_ping = time.time()

    if play_sounds:
        play_wav_async("assets/start.wav")

    # Log audio device info
    try:
        device = sd.query_devices(kind='input')
        logger.debug(f"Using microphone: {device['name']}")
    except:
        logger.debug("Using default microphone")

    try:
        print("🟡 Listening for wake word…")
    except UnicodeEncodeError:
        print("Listening for wake word...")

    with sd.InputStream(
        channels=channel_count,
        samplerate=sample_rate,
        blocksize=block_size,
        dtype="float32",
        callback=audio_cb,
        latency="low",
    ):
        chunks_processed = 0
        while True:
            audio = q.get()  # (frames, 1)
            chunks_processed += 1

            # Flatten to mono float32 @ 16k for OWW
            mono = audio[:, 0].astype(np.float32, copy=False)

            # AUTOMATIC GAIN CONTROL: Amplify quiet microphones
            # Target RMS of 0.1, typical microphone input is 0.01-0.001
            rms_before = np.sqrt(np.mean(mono**2))
            if rms_before > 0.0001:  # Avoid division by zero on silence
                gain = 0.1 / rms_before
                gain = min(gain, 100.0)  # Cap at 100x amplification
                mono = mono * gain
            else:
                gain = 1.0

            rms_after = np.sqrt(np.mean(mono**2))

            # OWW accepts ~10–100ms chunks; this is fine with block_size 512 @ 16kHz (~32ms)
            scores = model.predict(mono)  # dict: {model_name: score}

            # Get max score for display
            max_score = max(scores.values()) if scores else 0

            # Show live score meter with audio levels (updates every 10 chunks = ~320ms)
            if chunks_processed % 10 == 0:
                score_str = f"{max_score:.3f}"
                bars = int(max_score * 20)  # Visual bar (max 20 chars at score=1.0)
                bar_str = "|" * bars + "." * (20 - bars)
                audio_level = int(rms_after * 50)  # Audio level bar
                audio_bar = "#" * min(audio_level, 20)
                print(f"\r[{bar_str}] {score_str} | Audio:[{audio_bar:<20}] {rms_after:.3f}  ", end="", flush=True)

            # Log when we see interesting scores
            if max_score > 0.05:
                logger.debug(f"Wake word score spike: {max_score:.3f} at chunk {chunks_processed}")

            # If any model fires above threshold -> wake
            if any(score >= threshold for score in scores.values()):
                try:
                    print("🟢 Wake word detected.")
                except UnicodeEncodeError:
                    print("Wake word detected.")
                return

            # Periodic heartbeat so the console doesn't look frozen
            if time.time() - last_ping >= idle_print_secs:
                logger.debug(f"Still listening for wake word (threshold={threshold})")
                last_ping = time.time()

