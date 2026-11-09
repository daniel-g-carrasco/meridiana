"""Meridio's natural voice in a process of its own (assistant/speech.py): requests as JSON lines on stdin, a frame of
16-bit PCM at 24 kHz on stdout for each sentence. Standalone: any Python with the package kokoro-onnx runs it, and
it imports nothing of Meridiana.

    python kokoro_worker.py --dir <folder of the model> [--fake]

    python kokoro_worker.py --dir <folder> --wav <file.wav> '{"text": "…", "voice": "if_sara", "speed": 1.15, "pitch": 1}'
                                                                          one sentence into a WAV file, then out

stdin:  {"id": 3, "text": "…", "voice": "if_sara", "lang": "it", "speed": 1.15, "pitch": 1}   a sentence to say
        (pitch in semitones, by resampling: see `shifted`)
        {"drop": true}                                                            forget the sentences waiting
stdout: b"MRDV", the sentence's id and the bytes that follow (two little-endian uint32), then the PCM
stderr: «ready» once the model is loaded; «error <why>» when something fails (the request is skipped)

--fake answers with silence as long as the sentence would take, without the model: the tests' worker."""

from __future__ import annotations

import json
import queue
import struct
import sys
import threading
from pathlib import Path

MAGIC = b"MRDV"
HEADER = struct.Struct("<4sII")
RATE = 24000
MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
# the program's language as espeak names it: "en" alone is refused («not supported by the espeak backend»)
LANGS = {"en": "en-us"}


def say(line: str) -> None:
    sys.stderr.write(line.replace("\n", " ") + "\n")
    sys.stderr.flush()


def shifted(samples, semitones: float):
    """The voice `semitones` higher (R492, Daniel 06/11/2026: Sara +1): the samples resampled shorter by the factor
    2^(s/12), band-limited (an FFT, numpy only: this worker runs in any Python with kokoro-onnx), so the pitch and the
    formants rise together and nothing above the band folds back. The caller asks the model for a speech slower by
    the same factor, so the length is the one wanted."""
    import numpy as np
    if not semitones or len(samples) < 2:
        return samples
    n = len(samples)
    m = max(1, round(n / 2 ** (semitones / 12)))
    spectrum = np.fft.rfft(samples)
    bins = m // 2 + 1
    if bins <= len(spectrum):
        spectrum = spectrum[:bins]
    else:
        spectrum = np.concatenate([spectrum, np.zeros(bins - len(spectrum), dtype=spectrum.dtype)])
    return (np.fft.irfft(spectrum, m) * (m / n)).astype(np.float32)


def synthesizer(folder: Path, fake: bool):
    if fake:
        def silence(text: str, voice: str, lang: str, speed: float, pitch: float = 0.0) -> bytes:
            return bytes(2 * int(RATE * 0.06 * max(1, len(text)) / max(0.5, speed)))
        return silence
    import numpy as np
    from kokoro_onnx import Kokoro
    model = Kokoro(str(folder / MODEL_FILES[0]), str(folder / MODEL_FILES[1]))

    def kokoro(text: str, voice: str, lang: str, speed: float, pitch: float = 0.0) -> bytes:
        factor = 2 ** (pitch / 12)
        samples, rate = model.create(text, voice=voice, speed=speed / factor, lang=LANGS.get(lang, lang))
        if rate != RATE:
            raise ValueError(f"the model speaks at {rate} Hz, not {RATE}")
        samples = shifted(samples, pitch)
        return (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    return kokoro


def write_wav(path: Path, pcm: bytes) -> None:
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)


def main(argv: list[str]) -> int:
    fake = "--fake" in argv
    folder = Path(argv[argv.index("--dir") + 1]) if "--dir" in argv else Path(".")
    try:
        synth = synthesizer(folder, fake)
    except Exception as error:  # noqa: BLE001  said to the program, which falls back to the system's voice
        say(f"error {type(error).__name__}: {error}")
        return 1
    if "--wav" in argv:             # one sentence into a file and out (Settings > Assistant, «Listen»)
        request = json.loads(argv[argv.index("--wav") + 2])
        write_wav(Path(argv[argv.index("--wav") + 1]),
                  synth(str(request.get("text", "")), str(request.get("voice", "im_nicola")),
                        str(request.get("lang", "it")), float(request.get("speed", 1.0)),
                        float(request.get("pitch", 0.0))))
        say("done")
        return 0
    say("ready")
    todo: queue.Queue = queue.Queue()

    def read() -> None:
        for line in sys.stdin:
            try:
                msg = json.loads(line)
            except ValueError:
                say(f"error not a request: {line[:60]}")
                continue
            if msg.get("drop"):
                while True:
                    try:
                        todo.get_nowait()
                    except queue.Empty:
                        break
                continue
            todo.put(msg)
        todo.put(None)
    threading.Thread(target=read, daemon=True).start()
    out = sys.stdout.buffer
    while True:
        msg = todo.get()
        if msg is None:
            return 0
        try:
            pcm = synth(str(msg.get("text", "")), str(msg.get("voice", "im_nicola")), str(msg.get("lang", "it")),
                        float(msg.get("speed", 1.0)), float(msg.get("pitch", 0.0)))
        except Exception as error:  # noqa: BLE001  one sentence lost, the voice goes on
            say(f"error {type(error).__name__}: {error}")
            pcm = b""                   # an empty frame: the program knows the sentence is done
        out.write(HEADER.pack(MAGIC, int(msg.get("id", 0)), len(pcm)) + pcm)
        out.flush()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
