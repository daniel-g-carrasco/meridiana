"""Meridio's natural voice (Daniel, 24/10/2026: «Kokoro era quella buona»): Kokoro, an open text to speech model
(82 M parameters, Apache-2.0, run by the package kokoro-onnx), with a man's voice by default, Meridio being «he».
Synthesis runs in a process of its own (kokoro_worker.py): the model's 330 MB stay out of the program, the window
never waits, and Stop drops what is waiting. This module finds the model and the Python that runs it and reads the
worker's frames; ui/voice.py plays them. No Qt.

The model is the two files of Kokoro 1.0 for kokoro-onnx (MODEL_FILES), looked for in the folder of the settings,
in MERIDIANA_KOKORO_DIR, in the data folder (voices/kokoro) and where a manual install puts them on Linux
(~/.local/opt/kokoro, ~/.local/share/kokoro). The Python is the one of the settings, else the program's own; it
needs kokoro-onnx (on Windows the program's own has it; Python 3.15 has no onnxruntime yet, 24/10/2026)."""

from __future__ import annotations

import hashlib
import os
import struct
import sys
from pathlib import Path

from ..i18n import _

MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
# where the program downloads them when the designer asks (Preferences > Assistant): the release of kokoro-onnx that
# carries Kokoro 1.0, with each file's size and SHA-256 (measured on 24/10/2026 on the files of that release)
MODEL_SOURCE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL_BYTES = {"kokoro-v1.0.onnx": 325_532_387, "voices-v1.0.bin": 28_214_398}
MODEL_SHA256 = {"kokoro-v1.0.onnx": "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
                "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"}
RATE = 24000                    # Hz, 16-bit mono: what the worker sends
# the voices by language, a man's first (Meridio is «he»): Kokoro 1.0 has these two in Italian
VOICES = {"it": ("im_nicola", "if_sara"), "en": ("am_michael", "af_heart")}
MAGIC = b"MRDV"
HEADER = struct.Struct("<4sII")             # magic, sentence id, bytes of PCM that follow


def voice_names() -> dict:
    return {"im_nicola": _("Nicola, a man's voice"), "if_sara": _("Sara, a woman's voice"),
            "am_michael": _("Michael, a man's voice"), "af_heart": _("Heart, a woman's voice")}


def default_voice(language: str) -> str:
    return VOICES.get(language, VOICES["en"])[0]


def voice_for(language: str, chosen: str = "") -> str:
    """The voice to speak `language` with: the one chosen when it is of that language, else the man's."""
    return chosen if chosen in VOICES.get(language, ()) else default_voice(language)


def model_dirs(configured: str = "", data_dir: Path | None = None, environ=None) -> list[Path]:
    """Where the model is looked for, in order."""
    environ = os.environ if environ is None else environ
    out = []
    for raw in (configured, environ.get("MERIDIANA_KOKORO_DIR", "")):
        if raw:
            out.append(Path(raw).expanduser())
    if data_dir is not None:
        out.append(Path(data_dir) / "voices" / "kokoro")
    home = Path.home()
    out += [home / ".local" / "opt" / "kokoro", home / ".local" / "share" / "kokoro"]
    if environ.get("XDG_DATA_HOME"):
        out.append(Path(environ["XDG_DATA_HOME"]) / "kokoro")
    if environ.get("LOCALAPPDATA"):
        out += [Path(environ["LOCALAPPDATA"]) / "Meridiana" / "data" / "voices" / "kokoro",
                Path(environ["LOCALAPPDATA"]) / "kokoro"]
    # Common manual installs keep the files in models/ rather than alongside the environment.
    return list(dict.fromkeys(p for root in out for p in (root, root / "models")))


def find_model(configured: str = "", data_dir: Path | None = None, environ=None) -> Path | None:
    """The first folder that has both files of the model; None when there is none."""
    for d in model_dirs(configured, data_dir, environ):
        if all((d / f).is_file() for f in MODEL_FILES):
            return d
    return None


class Stopped(Exception):
    """The download was stopped by the designer."""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_model(dest: Path, progress=lambda done, total: None, stopped=lambda: False, session=None) -> None:
    """The two files of the model into `dest` (the data folder's voices/kokoro), each written beside its name and
    given it only once its SHA-256 is the release's: a download stopped (Stopped) or wrong (ValueError) or cut
    (OSError, requests' errors) leaves nothing; a file already there and right is not downloaded again.
    `progress(bytes done, bytes in all)` after each piece."""
    import requests
    http = session or requests
    dest.mkdir(parents=True, exist_ok=True)
    total = sum(MODEL_BYTES.values())
    done = 0
    for name in MODEL_FILES:
        target = dest / name
        if target.is_file() and target.stat().st_size == MODEL_BYTES[name] and _sha256(target) == MODEL_SHA256[name]:
            done += MODEL_BYTES[name]
            progress(done, total)
            continue
        part = target.with_name(name + ".part")
        h = hashlib.sha256()
        try:
            with http.get(MODEL_SOURCE + name, stream=True, timeout=(10, 60),
                          headers={"User-Agent": "Meridiana"}) as response:
                response.raise_for_status()
                with open(part, "wb") as f:
                    for chunk in response.iter_content(1 << 20):
                        if stopped():
                            raise Stopped()
                        f.write(chunk)
                        h.update(chunk)
                        done += len(chunk)
                        progress(done, total)
            if h.hexdigest() != MODEL_SHA256[name]:
                raise ValueError(_("{file} did not arrive whole: its fingerprint is not the release's.").format(
                    file=name))
            os.replace(part, target)
        finally:
            if part.exists():
                part.unlink()


_MARKUP = [(r"\[([^\]]+)\]\([^)]+\)", r"\1"),           # a link: its words
           (r"[*_`#>|~]+", " "),                                 # emphasis, code, headings, quotes, tables
           (r"^\s*(?:[-+]|\d+[.)])\s+", ""),                   # a list's mark at the start
           (r"\s+", " ")]
_SAYS = {"it": {"→": ", ", "≥": " maggiore o uguale a ", "≤": " minore o uguale a ", "×": " per ", "±": " più o meno "},
         "en": {"→": ", ", "≥": " at least ", "≤": " at most ", "×": " by ", "±": " plus or minus "}}


def speakable(sentence: str, language: str = "it") -> str:
    """What is to be read aloud of a sentence the model wrote in Markdown: the marks of emphasis, code, headings and
    lists taken out, the arrows and comparison signs said in words, the emoji left out (the voice read «asterisco
    asterisco» and the names of the faces, 25/10/2026); "" when nothing is left to say."""
    import re
    text = sentence
    for sign, words in _SAYS.get(language, _SAYS["en"]).items():
        text = text.replace(sign, words)
    text = "".join(ch for ch in text if not (0x1F000 <= ord(ch) <= 0x1FAFF or 0x2600 <= ord(ch) <= 0x27BF
                                            or ord(ch) in (0xFE0F, 0x200D)))
    for pattern, repl in _MARKUP:
        text = re.sub(pattern, repl, text, flags=re.M)
    text = text.strip(" -")
    return text if any(ch.isalnum() for ch in text) else ""


def worker_script() -> Path:
    """The worker as a script: in a build too (the Windows bundle carries it as a file next to the frozen modules,
    the Flatpak with the sources), so that another Python can run it."""
    return Path(__file__).with_name("kokoro_worker.py")


def found_python(which=None) -> str:
    """A Python on the PATH (pythonw first on Windows: no console beside the program), never the Microsoft Store's
    alias in WindowsApps, which only offers to install one; "" when there is none."""
    import shutil
    which = which or shutil.which
    for name in (("pythonw", "python") if os.name == "nt" else ("python3", "python")):
        path = which(name)
        if path and "windowsapps" not in (part.lower() for part in Path(path).parts):
            return str(path)
    return ""


def worker_python(configured: str = "", frozen: bool | None = None, which=None,
                  model_dir: Path | None = None) -> str:
    """An explicit interpreter, a valid adjacent environment, or this program's Python.
    The Windows bundle runs its worker through --kokoro-worker with its own bundled dependencies.
    Flatpak uses its sandbox runtime, never a host virtualenv with incompatible library paths.
    """
    if configured:
        return configured
    if getattr(sys, "frozen", False) if frozen is None else frozen:
        return sys.executable
    # Prefer a dedicated environment next to discovered weights; is_file rejects broken symlinks.
    # A Flatpak must use its own runtime: host virtualenv interpreters are not ABI-compatible in the sandbox.
    if model_dir is not None and not os.environ.get("FLATPAK_ID"):
        # never a folder of one PC (~/fvtest/kokoro-venv, Daniel's laptop, was here): another one is named in Settings
        roots = [Path(model_dir), Path(model_dir).parent, Path.home() / ".local/opt/kokoro"]
        for root in roots:
            for prefix in (root / "venv", root / ".venv", root):
                executable = prefix / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                if executable.is_file():
                    return str(executable)
    exe = Path(sys.executable)
    if os.name == "nt" and exe.name.lower() == "python.exe" and exe.with_name("pythonw.exe").is_file():
        return str(exe.with_name("pythonw.exe"))
    return str(exe)


def frame(sentence: int, pcm: bytes) -> bytes:
    return HEADER.pack(MAGIC, sentence, len(pcm)) + pcm


class Frames:
    """The worker's stdout cut into its frames, whatever the pieces it comes in."""

    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[tuple[int, bytes]]:
        self.buffer += data
        out = []
        while len(self.buffer) >= HEADER.size:
            magic, sentence, n = HEADER.unpack_from(self.buffer)
            if magic != MAGIC:
                raise ValueError("the voice's worker sent something that is not a frame")
            if len(self.buffer) < HEADER.size + n:
                break
            out.append((sentence, bytes(self.buffer[HEADER.size:HEADER.size + n])))
            del self.buffer[:HEADER.size + n]
        return out
