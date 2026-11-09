"""Meridio's voice as Daniel chose it (R492, 06/11/2026): Sara, one semitone up, 1.15 times as fast; the pitch and the
speed in the Settings with «Listen»; the settings saved before keep their sound."""
import json
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import QApplication

from _setup import wait_until
from meridiana import config
from meridiana.assistant import kokoro_worker, speech

RATE = 24000
SENTENCE = speech.speakable(speech.LISTEN["it"], "it")


def f0(samples):
    """The median fundamental frequency of the voiced frames (autocorrelation on 40 ms)."""
    x = np.asarray(samples, dtype=np.float64)
    size, hop, lo, hi = int(.04 * RATE), int(.01 * RATE), int(RATE / 450), int(RATE / 70)
    floor, found = .02 * np.max(np.abs(x)), []
    for start in range(0, len(x) - size, hop):
        frame = x[start:start + size] * np.hanning(size)
        if np.sqrt(np.mean(frame ** 2)) < floor:
            continue
        ac = np.correlate(frame, frame, "full")[size - 1:]
        ac /= ac[0]
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] > .5:
            found.append(RATE / lag)
    return float(np.median(found))


def pcm(data):
    return np.frombuffer(data, dtype="<i2").astype(np.float64) / 32768


class ShiftTest(unittest.TestCase):
    def test_one_semitone_up_is_six_per_cent_higher_and_shorter_without_folding(self):
        t = np.arange(RATE * 2) / RATE
        tone = sum(np.sin(2 * np.pi * 200 * h * t) / h for h in range(1, 10)).astype(np.float32)
        up = kokoro_worker.shifted(tone, 1)
        self.assertAlmostEqual(f0(up) / f0(tone), 2 ** (1 / 12), delta=0.006)
        self.assertAlmostEqual(len(up) / len(tone), 2 ** (-1 / 12), delta=0.001)
        spectrum = np.abs(np.fft.rfft(up))
        top = spectrum[int(len(spectrum) * 11 / 12):]          # above 11 kHz: nothing folded back
        self.assertLess(top.max(), spectrum.max() * 1e-3)
        self.assertIs(kokoro_worker.shifted(tone, 0), tone)


class SettingsTest(unittest.TestCase):
    def test_the_new_default_and_the_choices_saved_before(self):
        self.assertEqual((config.Config().assistant_voice_pitch, config.Config().assistant_voice_speed), (1, 1.15))
        self.assertEqual(speech.voice_for("it"), "if_sara")
        self.assertEqual(speech.voice_for("it", "im_nicola"), "im_nicola")
        self.assertEqual(speech.voice_settings(config.Config()), (1.0, 1.15))
        self.assertEqual(speech.voice_settings(config.Config(assistant_voice_pitch=9, assistant_voice_speed=3.0)),
                         (4.0, 1.4))
        with tempfile.TemporaryDirectory() as tmp:
            for name, expected in (("", (1, 1.15)), ("im_nicola", (0, 1.0))):
                path = Path(tmp) / f"config-{name or 'auto'}.json"
                path.write_text(json.dumps({"version": 28, "assistant_voice_name": name}), encoding="utf-8")
                cfg = config.load(path)
                self.assertEqual((cfg.assistant_voice_pitch, cfg.assistant_voice_speed), expected, name)
        self.assertEqual(config.CONFIG_VERSION, 32)          # 29 brought the voice (R492), 30 R523, 31 the 3D's edges, 32 R548


class ModelTest(unittest.TestCase):
    """With the real model, when it is on the PC (it is not in the CI)."""

    @classmethod
    def setUpClass(cls):
        cls.folder = speech.find_model()
        if cls.folder is None:
            raise unittest.SkipTest("Kokoro's model is not on this PC")
        try:
            cls.synth = staticmethod(kokoro_worker.synthesizer(cls.folder, False))
        except ImportError as error:
            raise unittest.SkipTest(f"kokoro-onnx: {error}") from error
        cls.app = QApplication.instance() or QApplication([])

    def test_english_is_said_too(self):
        self.assertGreater(len(self.synth("Hello, I am Meridio.", "am_michael", "en", 1.15, 1)), RATE)

    def test_sara_one_semitone_up_and_faster_has_the_pitch_and_the_length_expected(self):
        plain = pcm(self.synth(SENTENCE, "if_sara", "it", 1.0, 0))
        chosen = pcm(self.synth(SENTENCE, "if_sara", "it", 1.15, 1))
        self.assertAlmostEqual(f0(chosen) / f0(plain), 1.06, delta=0.03)       # about +6 %
        self.assertAlmostEqual(len(chosen) / len(plain), 1 / 1.15, delta=0.04)  # about 1/1.15

    def test_listen_in_the_settings_writes_the_sentence_with_the_settings(self):
        from meridiana.quick.backend.settings import SettingsBackend
        from meridiana.quick.backend import settings_schema
        cfg = config.Config()
        backend = SettingsBackend(cfg)
        played = []
        backend.play = played.append                 # no sound in the tests: the file only
        fields = {f["key"]: f for f in settings_schema.fields_for("assistant", cfg)}
        self.assertEqual((fields["assistant_voice_pitch"]["minimum"], fields["assistant_voice_pitch"]["maximum"]), (-3, 4))
        self.assertEqual((fields["assistant_voice_speed"]["minimum"], fields["assistant_voice_speed"]["maximum"]), (0.8, 1.4))
        self.assertEqual(fields["assistant_voice_speed"]["action"], "listen")
        self.assertTrue(backend.setValue("assistant_voice_pitch", 2.0))
        self.assertEqual(cfg.assistant_voice_pitch, 2)
        self.assertFalse(backend.setValue("assistant_voice_speed", 1.6))
        self.assertTrue(backend.setValue("assistant_voice_pitch", 1))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "ascolta.wav"
            heard = []
            backend.listened.connect(heard.append)
            self.assertTrue(backend.listen(out, language="it"))
            self.assertTrue(wait_until(self.app, lambda: heard, 120))
            self.assertEqual(played, [out])
            with wave.open(str(out)) as w:
                self.assertEqual((w.getframerate(), w.getnchannels()), (RATE, 1))
                said = pcm(w.readframes(w.getnframes()))
        plain = pcm(self.synth(SENTENCE, "if_sara", "it", 1.0, 0))
        self.assertAlmostEqual(f0(said) / f0(plain), 1.06, delta=0.03)


if __name__ == "__main__":
    unittest.main()
