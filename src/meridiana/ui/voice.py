"""Meridio's spoken voice (R82, task 14): his answers read aloud in the program's language, off by default (the
speaker in his bubble; the setting `assistant_voice`). Two engines behind one face (`Voice`):
- Kokoro, the natural voice (Daniel, 24/10/2026: «Kokoro era quella buona»; assistant/speech.py): a process of its own
  synthesizes each sentence and QtMultimedia plays it; a man's voice by default (Nicola in Italian), Meridio being
  «he». Used when its model is on the PC (`assistant_voice_engine` "auto", the default, or "kokoro");
- the system's voices through QtTextToSpeech (WinRT or SAPI on Windows, speech-dispatcher on Linux), a man's when
  there is one: the fallback, and the choice "system".

Sentence by sentence as the answer comes, not at its end: the local model writes 9 tokens a second (study 14, 4.4)
and a voice reads about three, so the first sentence is read while the rest is written and the queue never runs dry;
waiting for the end would leave half a minute of silence after the words appear. A sentence is whole when a stop
and a space follow it, so «1.043 V» is not cut (assistant/text.py). Stop, Esc (the bubble closed) and a new question
silence him. No engine, or no voice of the program's language: the speaker is greyed and its tip says why."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QLocale, QObject, QProcess, QTimer, Signal

from .. import log
from ..assistant import speech
from ..assistant import text as words
from ..i18n import _

PREFERRED = ("winrt", "sapi", "speechd", "flite", "darwin", "android")      # "mock" is Qt's, for the tests only


def no_voice(language: str) -> str:
    """Why the speaker is greyed when the system has no voice of the program's language."""
    where = _("add one in Windows (Settings > Time and language > Speech), or a voice of speech-dispatcher on Linux")
    if language == "it":
        return _("No Italian voice on this system: {where}.").format(where=where)
    return _("No English voice on this system: {where}.").format(where=where)


def engines() -> list[str]:
    """The engines Qt offers on this system, the real ones only, best first."""
    try:
        from PySide6.QtTextToSpeech import QTextToSpeech
    except ImportError:
        return []
    found = [e for e in QTextToSpeech.availableEngines() if e != "mock"]
    return sorted(found, key=lambda e: PREFERRED.index(e) if e in PREFERRED else len(PREFERRED))


class Kokoro(QObject):
    """The natural voice: the worker process (assistant/kokoro_worker.py) and the sound it makes. Sentences said
    before the model is loaded wait; Stop drops what is waiting and what is playing, and the frames of the sentences
    said before it are thrown away when they come."""

    ready = Signal()
    failed = Signal(str)

    def __init__(self, folder: Path, python: str, voice: str, language: str, fake: bool = False, parent=None):
        super().__init__(parent)
        self.folder, self.python, self.voice, self.language, self.fake = folder, python, voice, language, fake
        self.process: QProcess | None = None
        self.frames = speech.Frames()
        self.loaded = False
        self.waiting: list[str] = []
        self.next_id = 0
        self.floor = 0                      # frames of a sentence below this id are dropped (said before Stop)
        self.pending = bytearray()          # PCM not yet given to the sound card
        self.sink = None
        self.device = None
        self.played: list[int] = []         # the ids of the sentences played, for the tests
        self.pump = QTimer(self)
        self.pump.setInterval(20)
        self.pump.timeout.connect(self._pump)
        self.stopping = False
        self.load_timeout = QTimer(self)
        self.load_timeout.setSingleShot(True)
        self.load_timeout.setInterval(60000)
        self.load_timeout.timeout.connect(lambda: self._fail(
            _("Kokoro did not load within 60 seconds. Check the model files and Python in Settings > Assistant.")))

    def start(self) -> None:
        p = QProcess(self)
        p.setProgram(self.python)
        args = [str(speech.worker_script()), "--dir", str(self.folder)]
        if getattr(sys, "frozen", False) and self.python == sys.executable:
            args = ["--kokoro-worker", "--dir", str(self.folder)]
        p.setArguments(args + (["--fake"] if self.fake else []))
        p.readyReadStandardOutput.connect(self._out)
        p.readyReadStandardError.connect(self._err)
        p.errorOccurred.connect(self._error)
        p.finished.connect(self._finished)
        self.process = p
        p.start()
        self.load_timeout.start()

    def say(self, sentence: str) -> None:
        if not self.loaded:
            self.waiting.append(sentence)
            return
        self.next_id += 1
        request = {"id": self.next_id, "text": sentence, "voice": self.voice, "lang": self.language, "speed": 1.0}
        self.process.write((json.dumps(request, ensure_ascii=False) + "\n").encode("utf-8"))

    def stop(self) -> None:
        self.waiting = []
        self.floor = self.next_id + 1
        self.pending = bytearray()
        self.pump.stop()
        if self.process is not None and self.loaded:
            self.process.write(b'{"drop": true}\n')
        if self.sink is not None:
            # a sink stopped does not open again on Windows (start() gave nothing, 25/10/2026): a new one next time
            sink, self.sink = self.sink, None
            sink.stop()
            sink.deleteLater()
        self.device = None

    def speaking(self) -> bool:
        """Something to hear: sound not played yet, or a sentence said whose sound has not come (the worker
        synthesizes the next while this one plays)."""
        from PySide6.QtMultimedia import QAudio
        coming = self.next_id >= self.floor and max(self.played, default=0) < self.next_id
        return (bool(self.pending) or bool(self.waiting) or coming or
                (self.sink is not None and self.sink.state() == QAudio.State.ActiveState))

    def close(self) -> None:
        self.stopping = True
        self.load_timeout.stop()
        self.stop()
        if self.process is not None:
            self.process.kill()
            self.process.waitForFinished(1000)

    def _err(self) -> None:
        text = bytes(self.process.readAllStandardError()).decode("utf-8", "replace")
        for line in text.splitlines():
            if line.strip() == "ready":
                if self.stopping:           # the load timeout came first: its failure stands, the sentences wait for
                    continue                # the voice that takes Kokoro's place (Voice._kokoro_failed)
                self.load_timeout.stop()
                self.loaded = True
                waiting, self.waiting = self.waiting, []
                for sentence in waiting:
                    self.say(sentence)
                self.ready.emit()
            elif line.startswith("error "):
                log.complain("voice", RuntimeError(line[6:]))
                if not self.loaded:
                    self._fail(_("The natural voice did not start: {why}").format(why=line[6:]))

    def _out(self) -> None:
        try:
            frames = self.frames.feed(bytes(self.process.readAllStandardOutput()))
        except ValueError as error:
            self._fail(str(error))
            return
        for sentence, pcm in frames:
            if sentence >= self.floor:
                self.played.append(sentence)
                self.pending += pcm
        self._pump()

    def _pump(self) -> None:
        if not self.pending:
            self.pump.stop()
            return
        if self.device is None:
            from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
            if self.sink is None:
                fmt = QAudioFormat()
                fmt.setSampleRate(speech.RATE)
                fmt.setChannelCount(1)
                fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
                device = QMediaDevices.defaultAudioOutput()
                if device.isNull():
                    self._fail(_("No sound output on this PC."))
                    return
                self.sink = QAudioSink(device, fmt, self)
            self.device = self.sink.start()
            if self.device is None:
                self._fail(_("The sound output did not open."))
                return
        free = self.sink.bytesFree()
        if free > 0:
            n = self.device.write(bytes(self.pending[:free - free % 2]))
            if n > 0:
                del self.pending[:n]
        if self.pending and not self.pump.isActive():
            self.pump.start()

    def _error(self, _e) -> None:
        try:
            why = self.process.errorString() if self.process is not None else ""
        except RuntimeError:                # the process already let go
            why = ""
        self._fail(_("The natural voice did not start: {why}").format(why=why))

    def _finished(self, *_a) -> None:
        if not self.stopping:
            self._fail(_("The natural voice stopped."))

    def _fail(self, why: str) -> None:
        """Said a turn later, never inside the process's or the sink's own signal: whoever listens may close the
        process and start another voice (the crash of 25/10/2026 came from a worker killed inside its own read)."""
        if self.stopping:
            return
        self.stopping = True
        self.pump.stop()
        self.load_timeout.stop()
        QTimer.singleShot(0, self, lambda: self.failed.emit(why))


class Voice(QObject):
    """The speaker. `language` is the program's ("it"); `engine` a Qt engine by name (the tests give "mock") for the
    system's voice alone; `settings` the configuration (the engine, the voice, the model's folder, the Python that
    runs it); `data_dir` the program's data folder (where a model may be). `restore` puts back the names withheld
    from the cloud before a sentence is read."""

    availableChanged = Signal(bool, str)

    def __init__(self, language: str = "it", engine: str | None = None, settings=None, data_dir: Path | None = None,
                 parent=None):
        super().__init__(parent)
        self.language = language
        self.engine = engine
        self.settings = settings
        self.data_dir = data_dir
        self.tts = None
        self.kokoro: Kokoro | None = None
        self.kind = ""                      # "kokoro" or "system", once started
        self.on = False
        self.ready = False
        self.buffer = ""
        self.queue: list[str] = []          # sentences waiting for the engine to be ready
        self.said: list[str] = []           # what was given to the engine, for the tests
        self.voice_name = ""
        self.why = ""
        self.restore = lambda text: text

    def _choice(self, key: str, default: str = "") -> str:
        return str(getattr(self.settings, key, default) or default) if self.settings is not None else default

    def natural_model(self) -> Path | None:
        """The folder of Kokoro's model when the natural voice is the one to use (never with a Qt engine given)."""
        if self.engine is not None or self._choice("assistant_voice_engine", "auto") == "system":
            return None
        if not speech.worker_python(self._choice("assistant_kokoro_python")):
            return None                 # the installed program with no Python found to run it (speech.worker_python)
        return speech.find_model(self._choice("assistant_kokoro_dir"), self.data_dir)

    def available(self) -> tuple[bool, str]:
        """Whether the speaker can be switched on, and why not."""
        if self.why:
            return False, self.why
        if self.natural_model() is not None:
            return True, ""
        if self._choice("assistant_voice_engine", "auto") == "kokoro" and self.engine is None:
            if not speech.worker_python(self._choice("assistant_kokoro_python")):
                return False, _("No Python on this PC runs the natural voice: name one that has the package "
                                "kokoro-onnx in Settings > Assistant.")
            return False, _("The natural voice's model (Kokoro) is not on this PC: its two files go in the folder "
                            "of Settings > Assistant.")
        if self.engine is None and not engines():
            return False, _("No speech engine on this system (on Linux: speech-dispatcher with a voice).")
        return True, ""

    def set_on(self, on: bool) -> None:
        self.on = on
        if on:
            self._start()
        else:
            self.stop()

    def reconfigure(self) -> None:
        """The preferences changed: the engine made again."""
        self.close()
        self.why = ""
        if self.on:
            self._start()

    def close(self) -> None:
        """The engine let go: the natural voice's process ended."""
        self.stop()
        if self.kokoro is not None:
            self.kokoro.close()
            self.kokoro.deleteLater()
            self.kokoro = None
        if self.tts is not None:
            self.tts.deleteLater()
            self.tts = None
        self.kind, self.ready = "", False

    def _start(self) -> None:
        if self.kind:
            return
        folder = self.natural_model()
        if folder is not None:
            voice = speech.voice_for(self.language, self._choice("assistant_voice_name"))
            self.kokoro = Kokoro(folder, speech.worker_python(self._choice("assistant_kokoro_python"),
                                                             model_dir=folder), voice,
                                 self.language, self._choice("assistant_voice_engine") == "fake", self)
            self.kokoro.ready.connect(self._kokoro_ready)
            self.kokoro.failed.connect(self._kokoro_failed)
            self.kind = "kokoro"
            self.voice_name = speech.voice_names().get(voice, voice)
            self.kokoro.start()
            return
        if self._choice("assistant_voice_engine", "auto") == "kokoro" and self.engine is None:
            self._refuse(self.available()[1])
            return
        self._start_system()

    def _kokoro_ready(self) -> None:
        self.ready = True
        waiting, self.queue = self.queue, []
        for sentence in waiting:
            self._say(sentence)

    def _kokoro_failed(self, why: str) -> None:
        """The natural voice did not start or stopped: the system's voice in its place unless the choice was
        «Kokoro» alone, with the sentences that were waiting."""
        log.complain("voice", RuntimeError(why))
        kokoro, self.kokoro = self.kokoro, None
        if kokoro is not None:
            kokoro.close()
            kokoro.deleteLater()
        self.kind, self.ready = "", False
        if self._choice("assistant_voice_engine", "auto") == "kokoro":
            self._refuse(why)
            return
        self._start_system()

    def _start_system(self) -> None:
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech
        except ImportError:
            self._refuse(_("No speech engine on this system (on Linux: speech-dispatcher with a voice)."))
            return
        name = self.engine or (engines() or [""])[0]
        if not name:
            self._refuse(_("No speech engine on this system (on Linux: speech-dispatcher with a voice)."))
            return
        self.kind = "system"
        self.tts = QTextToSpeech(name, self)
        self.tts.stateChanged.connect(self._state)
        self.tts.errorOccurred.connect(lambda _r, text: log.complain("voice", RuntimeError(text)))
        self._state(self.tts.state())

    def _state(self, state) -> None:
        from PySide6.QtTextToSpeech import QTextToSpeech, QVoice
        if state == QTextToSpeech.State.Error and not self.ready:
            self._refuse(_("The speech engine did not start: {why}").format(why=self.tts.errorString()))
            return
        if state != QTextToSpeech.State.Ready or self.ready:
            return
        want = QLocale(self.language).language()
        locales = [loc for loc in self.tts.availableLocales() if loc.language() == want]
        if not locales:
            self._refuse(no_voice(self.language))
            return
        self.tts.setLocale(locales[0])
        voices = self.tts.availableVoices()
        # Meridio is «he»: a man's voice when there is one (Windows 11 in Italian: Cosimo, beside Elsa)
        voice = next((v for v in voices if v.gender() == QVoice.Gender.Male), voices[0] if voices else None)
        if voice is not None:
            self.tts.setVoice(voice)
            self.voice_name = voice.name()
        self.ready = True
        waiting, self.queue = self.queue, []
        for sentence in waiting:
            self._say(sentence)

    def _refuse(self, why: str) -> None:
        self.why = why
        self.on = False
        self.queue = []
        self.availableChanged.emit(False, why)

    def feed(self, piece: str) -> None:
        """A piece of the answer: each sentence read as soon as it is whole."""
        if not self.on:
            return
        self.buffer += piece
        done, self.buffer = words.sentences(self.buffer)
        for sentence in done:
            self._say(sentence)

    def flush(self) -> None:
        """The answer ended: what is left is the last sentence."""
        if not self.on:
            return
        done, self.buffer = words.sentences(self.buffer, final=True)
        for sentence in done:
            self._say(sentence)

    def _say(self, sentence: str) -> None:
        sentence = speech.speakable(self.restore(sentence), self.language)
        if not sentence:
            return                          # a heading's marks, a lone emoji: nothing to read
        if not self.ready:
            self.queue.append(sentence)
            return
        self.said.append(sentence)
        if self.kind == "kokoro" and self.kokoro is not None:
            self.kokoro.say(sentence)
        elif self.tts is not None:
            self.tts.enqueue(sentence)

    def stop(self) -> None:
        """Silence: what is being read and what is waiting."""
        self.buffer = ""
        self.queue = []
        if self.kokoro is not None:
            self.kokoro.stop()
        if self.tts is not None:
            self.tts.stop()

    def speaking(self) -> bool:
        if self.kokoro is not None:
            return self.kokoro.speaking()
        if self.tts is None:
            return False
        from PySide6.QtTextToSpeech import QTextToSpeech
        return self.tts.state() in (QTextToSpeech.State.Speaking, QTextToSpeech.State.Synthesizing)
