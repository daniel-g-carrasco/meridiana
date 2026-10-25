"""Meridio's spoken voice (ui/voice.py; R82): Qt's text to speech with its test engine («mock», which speaks nothing
and says what it would): each sentence read as soon as it is whole while the answer comes, the names withheld put
back, silence at Stop; an engine without a voice of the program's language, or no engine at all, greys the speaker
and says why; «mock» is never the program's engine. In the window: finestra/test_assistant_chat.py. PySide6 and a
display (offscreen will do)."""

import unittest
from unittest import mock

import _setup
from _setup import wait_until

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


def mock_engine_or_skip(test) -> None:
    try:
        from PySide6.QtTextToSpeech import QTextToSpeech
    except ImportError:
        raise unittest.SkipTest("QtTextToSpeech") from None
    if "mock" not in QTextToSpeech.availableEngines():
        raise unittest.SkipTest("Qt's mock engine of text to speech is not in this PySide6")


class Voice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_sentences_are_read_as_they_are_whole_and_stop_silences_him(self):
        mock_engine_or_skip(self)
        from PySide6.QtTextToSpeech import QTextToSpeech

        from meridiana.ui.voice import Voice
        v = Voice("en", engine="mock")
        self.addCleanup(v.deleteLater)
        v.restore = lambda text: text.replace("[PROJECT]", "Capannone Rho")
        v.set_on(True)
        self.assertTrue(wait_until(self.app, lambda: v.ready, 5))
        self.assertEqual(v.tts.engine(), "mock")
        for piece in ("The voltage of the [PRO", "JECT] is 1.043 V. Then", " the shade."):
            v.feed(piece)
        self.assertEqual(v.said, ["The voltage of the Capannone Rho is 1.043 V."])
        self.assertTrue(wait_until(self.app, lambda: v.speaking(), 5))
        v.flush()
        self.assertEqual(v.said[-1], "Then the shade.")
        v.stop()
        self.assertTrue(wait_until(self.app, lambda: v.tts.state() == QTextToSpeech.State.Ready, 5))
        self.assertEqual(v.buffer, "")
        v.set_on(False)
        v.feed("Not read. ")
        self.assertEqual(len(v.said), 2)

    def test_no_voice_of_the_language_greys_the_speaker_and_says_why(self):
        mock_engine_or_skip(self)
        from meridiana.ui.voice import Voice
        v = Voice("it", engine="mock")                     # the mock engine speaks English and Norwegian only
        self.addCleanup(v.deleteLater)
        heard = []
        v.availableChanged.connect(lambda ok, why: heard.append((ok, why)))
        v.set_on(True)
        self.assertTrue(wait_until(self.app, lambda: heard, 5))
        [(ok, why)] = heard
        self.assertFalse(ok)
        self.assertIn("No Italian voice", why)
        self.assertEqual(v.available(), (False, why))
        v.feed("Una frase. ")
        self.assertEqual(v.said, [])

    def test_no_engine_at_all_is_said_and_mock_is_never_the_programs(self):
        from meridiana.ui import voice
        with mock.patch.object(voice, "engines", return_value=[]):
            ok, why = voice.Voice("it").available()
        self.assertFalse(ok)
        self.assertIn("No speech engine", why)
        self.assertNotIn("mock", voice.engines())



class NaturalVoice(unittest.TestCase):
    """Kokoro, the natural voice (Daniel, 24/10/2026: «Kokoro era quella buona»): its worker in a process of its own
    with --fake (silence as long as the sentence, no model), the frames played in order, Stop dropping what was said
    before it, a man's voice by default, the system's voice when it does not start. No sound: the sound card is not
    opened (Kokoro._pump stands in)."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def model(self, root):
        from meridiana.assistant import speech
        for name in speech.MODEL_FILES:
            (root / name).write_bytes(b"")
        return root

    def settings(self, folder, engine="fake", python="", name=""):
        from types import SimpleNamespace
        return SimpleNamespace(assistant_voice_engine=engine, assistant_voice_name=name,
                               assistant_kokoro_dir=str(folder), assistant_kokoro_python=python)

    def test_the_frames_the_model_and_a_mans_voice(self):
        import tempfile
        from pathlib import Path

        from meridiana.assistant import speech
        f = speech.Frames()
        data = speech.frame(3, b"\x01\x00" * 5) + speech.frame(4, b"")
        self.assertEqual(f.feed(data[:7]), [])                            # in any pieces
        self.assertEqual(f.feed(data[7:]), [(3, b"\x01\x00" * 5), (4, b"")])
        with self.assertRaises(ValueError):
            speech.Frames().feed(b"XXXX" + bytes(8))
        self.assertEqual(speech.voice_for("it"), "im_nicola")             # Meridio is «he»
        self.assertEqual(speech.voice_for("it", "if_sara"), "if_sara")
        self.assertEqual(speech.voice_for("it", "am_michael"), "im_nicola")   # not a voice of the language
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(speech.find_model(str(root), None, environ={}))
            data_dir = root / "data"
            (data_dir / "voices" / "kokoro").mkdir(parents=True)
            self.model(data_dir / "voices" / "kokoro")
            self.assertEqual(speech.find_model("", data_dir, environ={}), data_dir / "voices" / "kokoro")
            mine = root / "mine"
            mine.mkdir()
            self.model(mine)
            self.assertEqual(speech.find_model(str(mine), data_dir, environ={}), mine)    # the settings' first

    def test_what_is_read_aloud_is_words_not_marks(self):
        from meridiana.assistant import speech
        self.assertEqual(speech.speakable("**Il progetto** ha 4 verifiche:"), "Il progetto ha 4 verifiche:")
        self.assertEqual(speech.speakable("- Copertura: il 3,7% perso."), "Copertura: il 3,7% perso.")
        self.assertEqual(speech.speakable("## Riepilogo"), "Riepilogo")
        self.assertEqual(speech.speakable("Fammi sapere! 😊"), "Fammi sapere!")
        self.assertEqual(speech.speakable("1.043 V ≥ 1.000 V"), "1.043 V maggiore o uguale a 1.000 V")
        self.assertEqual(speech.speakable("Vedi [il manuale](manual:plant)."), "Vedi il manuale.")
        for nothing in ("", "   ", "---", "😊", "**", "✅ ⚠️"):
            self.assertEqual(speech.speakable(nothing), "", nothing)

    def test_the_voice_stopped_half_way_speaks_again_with_a_new_sink(self):
        """25/10/2026: Stop between two sentences, then more words: the sound comes back (a new sink), and a failure is
        told a turn later, never inside the process's own signal."""
        import tempfile
        from pathlib import Path

        from meridiana.ui import voice
        tmp = Path(tempfile.mkdtemp())
        v = voice.Voice("it", settings=self.settings(self.model(tmp)))
        self.addCleanup(v.close)
        v.set_on(True)
        self.assertTrue(wait_until(self.app, lambda: v.ready, 20))
        k = v.kokoro
        sinks = []
        real_pump = voice.Kokoro._pump

        class Sink:
            def __init__(self):
                self.stopped = False

            def stop(self):
                self.stopped = True

            def deleteLater(self):
                pass

        def pump(kokoro):
            if kokoro.device is None:
                kokoro.sink = Sink()
                sinks.append(kokoro.sink)
                kokoro.device = object()
            kokoro.pending.clear()
        with mock.patch.object(voice.Kokoro, "_pump", pump):
            v.feed("Prima frase. ")
            v.flush()
            self.assertTrue(wait_until(self.app, lambda: 1 in k.played, 20))
            v.stop()
            self.assertIsNone(k.sink)                                     # let go, not kept to start again
            self.assertTrue(sinks[0].stopped)
            v.feed("Seconda frase. ")
            v.flush()
            self.assertTrue(wait_until(self.app, lambda: 2 in k.played, 20))
            self.assertEqual(len(sinks), 2)                               # a new one
        del real_pump
        told = []
        k.failed.connect(told.append)
        k._fail("prova")
        self.assertEqual(told, [])                                        # not inside the caller
        self.assertTrue(wait_until(self.app, lambda: told == ["prova"], 5))

    def test_the_model_is_downloaded_whole_or_not_at_all(self):
        """Preferences > Assistant downloads the model (speech.download_model): a file takes its name only with the
        release's fingerprint; one stopped or wrong leaves nothing; one already there is not downloaded again."""
        import hashlib
        import tempfile
        from pathlib import Path

        from meridiana.assistant import speech
        blobs = {name: (name * 50).encode() for name in speech.MODEL_FILES}

        class Response:
            def __init__(self, data):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def raise_for_status(self):
                pass

            def iter_content(self, n):
                return [self.data[i:i + 100] for i in range(0, len(self.data), 100)]

        class Session:
            def __init__(self):
                self.asked = []

            def get(self, url, **_kw):
                name = url.rsplit("/", 1)[1]
                self.asked.append(name)
                return Response(blobs[name])
        sizes = {n: len(b) for n, b in blobs.items()}
        sums = {n: hashlib.sha256(b).hexdigest() for n, b in blobs.items()}
        dest = Path(tempfile.mkdtemp()) / "voices" / "kokoro"
        with mock.patch.object(speech, "MODEL_BYTES", sizes), mock.patch.object(speech, "MODEL_SHA256", sums):
            seen = []
            s = Session()
            speech.download_model(dest, lambda d, t: seen.append((d, t)), session=s)
            self.assertEqual(speech.find_model(str(dest), None, environ={}), dest)
            self.assertEqual(seen[-1], (sum(sizes.values()), sum(sizes.values())))
            again = Session()
            speech.download_model(dest, session=again)                  # right already: nothing asked
            self.assertEqual(again.asked, [])
            other = Path(tempfile.mkdtemp())
            with self.assertRaises(speech.Stopped):
                speech.download_model(other, stopped=lambda: True, session=Session())
            self.assertEqual(list(other.iterdir()), [])                  # nothing left half written
            with mock.patch.dict(sums, {speech.MODEL_FILES[0]: "0" * 64}), self.assertRaises(ValueError):
                speech.download_model(other, session=Session())
            self.assertEqual(list(other.iterdir()), [])

    def test_the_sentences_are_played_in_order_and_stop_drops_what_was_said_before(self):
        import tempfile
        from pathlib import Path

        from meridiana.ui import voice
        tmp = Path(tempfile.mkdtemp())
        v = voice.Voice("it", settings=self.settings(self.model(tmp)))
        self.addCleanup(v.close)
        self.assertEqual(v.available(), (True, ""))
        heard = []
        with mock.patch.object(voice.Kokoro, "_pump", lambda k: (heard.append(len(k.pending)), k.pending.clear())):
            v.set_on(True)
            self.assertEqual(v.kind, "kokoro")
            self.assertEqual(v.voice_name, "Nicola, a man's voice")
            v.feed("Il sottocampo Sud è a posto. Le stringhe ")             # one whole sentence, one still coming
            v.flush()
            self.assertTrue(wait_until(self.app, lambda: v.ready and len(v.kokoro.played) == 2, 20))
            self.assertEqual(v.kokoro.played, [1, 2])
            self.assertTrue(all(n > 0 for n in heard))
            # Stop: what was said before it is dropped when it comes
            v.feed("Una frase lunga che non sentirò mai fino in fondo. ")
            v.flush()                                                      # the answer ended: said, id 3
            v.stop()                                                       # before its frame came
            v.feed("Questa sì. ")
            v.flush()
            self.assertTrue(wait_until(self.app, lambda: 4 in v.kokoro.played, 20))
            self.assertNotIn(3, v.kokoro.played)

    def test_the_installed_program_never_runs_itself_as_the_voices_python(self):
        # the frozen executable given the worker's script would open a second window (task 18f): a Python of the
        # PATH runs it, never the Store's alias; with none the natural voice is not offered and «Kokoro» says why
        import tempfile
        from pathlib import Path

        from meridiana.assistant import speech
        from meridiana.ui import voice
        store = str(Path("C:/Users/x/AppData/Local/Microsoft/WindowsApps/python.exe"))
        real = str(Path("C:/Python312/pythonw.exe"))
        self.assertEqual(speech.worker_python("", frozen=True, which=lambda name: None), "")
        self.assertEqual(speech.worker_python("", frozen=True, which=lambda name: store), "")
        self.assertEqual(speech.worker_python("", frozen=True, which=lambda name: real), real)
        self.assertEqual(speech.worker_python("C:/py/python.exe", frozen=True, which=lambda name: None),
                         "C:/py/python.exe")                         # the settings' first, frozen or not
        self.assertTrue(speech.worker_python("", frozen=False))       # from the sources: the program's own
        self.assertEqual(speech.worker_script().name, "kokoro_worker.py")
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(speech, "worker_python", lambda configured="", frozen=None, which=None: configured):
            only = voice.Voice("it", settings=self.settings(self.model(tmp), engine="kokoro"))
            self.assertIsNone(only.natural_model())
            ok, why = only.available()
            self.assertFalse(ok)
            self.assertIn("kokoro-onnx", why)
            # named in the preferences, the model is found again
            named = voice.Voice("it", settings=self.settings(tmp, engine="kokoro", python="C:/py/python.exe"))
            self.assertEqual(named.natural_model(), tmp)

    def test_a_natural_voice_that_does_not_start_says_why_or_gives_way_to_the_systems(self):
        import tempfile
        from pathlib import Path

        from meridiana.ui import voice
        tmp = Path(tempfile.mkdtemp())
        nowhere = str(tmp / "no-python.exe")
        only = voice.Voice("it", settings=self.settings(self.model(tmp), engine="kokoro", python=nowhere))
        self.addCleanup(only.close)
        told = []
        only.availableChanged.connect(lambda ok, why: told.append((ok, why)))
        only.set_on(True)
        self.assertTrue(wait_until(self.app, lambda: bool(told), 10))
        self.assertFalse(told[0][0])
        self.assertIn("natural voice", told[0][1])
        self.assertFalse(only.on)
        # «auto»: the system's voice in its place, the sentences that waited with it
        auto = voice.Voice("it", settings=self.settings(self.model(tmp), engine="auto", python=nowhere))
        self.addCleanup(auto.close)
        with mock.patch.object(voice.Voice, "_start_system", lambda v: setattr(v, "kind", "system")):
            auto.set_on(True)
            auto.feed("Una frase. ")
            self.assertTrue(wait_until(self.app, lambda: auto.kind == "system", 10))
        self.assertIsNone(auto.kokoro)
        # «system»: Kokoro is not even looked for
        self.assertIsNone(voice.Voice("it", settings=self.settings(tmp, engine="system")).natural_model())

if __name__ == "__main__":
    unittest.main()
