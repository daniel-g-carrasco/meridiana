"""Drive Meridiana in a real window and keep screenshots, timings and Qt messages.

Run through tools/real_session.sh. The default tour visits every phase in both
themes. --toolbars LABEL records every bar at the requested widths and text
sizes, before or after a change to their grouping.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from PySide6.QtCore import QLibraryInfo, QObject, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from _fakes import nothing_local, offline
from _fixtures import capannone

from meridiana import config, i18n
from meridiana.paths import Paths
from meridiana.ui.window import MainWindow

PHASES = ("model", "plant", "production", "consumption", "economics", "report")
THEMES = (("light", "chiaro"), ("dark", "scuro"))
TEXT_SIZES = (("medium", "medio"), ("large", "grande"))


class Tour(QObject):
    def __init__(self, app: QApplication, args: argparse.Namespace):
        super().__init__()
        self.app = app
        self.args = args
        self.output = ROOT / "docs" / "revisioni" / "foto"
        self.output.mkdir(parents=True, exist_ok=True)
        self.lines: list[str] = []
        self.messages: list[str] = []
        self.started = time.monotonic()
        cfg = config.Config(theme="light", background="none", assistant=False, check_updates=False,
                            network_tiles=False, network_geocoding=False, network_pvgis=False, language="it")
        paths = Paths.from_env()
        self.win = MainWindow(paths, cfg)
        self.win.relayout_timer.setInterval(0)
        self.win.assistant_chat.make_local = offline
        self.win.assistant_chat.survey = nothing_local
        target = paths.data / "giro-reale.meridiana"
        target.parent.mkdir(parents=True, exist_ok=True)
        capannone().save(target)
        self.win.open_path(target)
        self.win.resize(1600, 950)
        self.win.show()

    def note(self, text: str) -> None:
        line = f"{time.monotonic() - self.started:8.3f} s  {text}"
        self.lines.append(line)
        print(line, flush=True)

    def wait(self, ms: int) -> None:
        end = time.monotonic() + ms / 1000
        while time.monotonic() < end:
            self.app.processEvents()
            time.sleep(0.002)

    def until(self, condition, seconds: float = 30.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.app.processEvents()
            if condition():
                return True
            time.sleep(0.01)
        return condition()

    def shot(self, name: str, widget=None) -> None:
        self.app.processEvents()
        subject = widget or self.win
        begun = time.monotonic()
        image = subject.grab()
        path = self.output / f"{name}.png"
        ok = image.save(str(path))
        self.note(f"foto {path.name}: {image.width()} x {image.height()}, salvata={ok}, "
                  f"grab={(time.monotonic() - begun) * 1000:.1f} ms")
        if not ok:
            raise RuntimeError(f"Could not save {path}")

    def click_phase(self, pid: str) -> None:
        tabs = self.win.tabs.tabBar()
        index = self.win.tabs.index_of_phase(pid)
        begun = time.monotonic()
        QTest.mouseClick(tabs, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         tabs.tabRect(index).center())
        self.wait(350)
        if self.win.phase() != pid:
            raise RuntimeError(f"The click did not open {pid}")
        self.note(f"fase {pid}: clic e attesa={(time.monotonic() - begun) * 1000:.1f} ms")

    def set_theme(self, theme: str) -> None:
        begun = time.monotonic()
        self.win.cfg.theme = theme
        self.win.theme.apply()
        self.wait(350)
        self.note(f"tema {theme}: {(time.monotonic() - begun) * 1000:.1f} ms")

    def tour(self) -> None:
        wanted = [sf.id for sf in self.win.project.subfields if sf.filled]
        if not self.until(lambda: all(sid in self.win.results for sid in wanted)):
            raise RuntimeError("The fixture layout did not finish")
        self.until(lambda: self.win.skeleton is None, 15)
        self.note(f"3D: skeleton assente={self.win.skeleton is None}, "
                  f"dimensione={self.win.view3d.width()} x {self.win.view3d.height()}")
        for number, pid in enumerate(PHASES, 1):
            self.click_phase(pid)
            if pid == "model":
                QTest.mouseMove(self.win.plan.viewport())
                self.note("pianta raggiunta col puntatore")
            for theme, italian in THEMES:
                self.set_theme(theme)
                self.shot(f"kimi12-giro-{number:02d}-{pid}-{italian}")
        self.click_phase("model")
        self.win.plan.zoom_at(0.0, self.win.plan.viewport().rect().center())
        self.wait(500)
        if self.win.plan.transform().m11() > 0.001:
            raise RuntimeError("The plan did not zoom out to the continents")
        for theme, italian in THEMES:
            self.set_theme(theme)
            self.shot(f"kimi12-mondo-{italian}")
        self.win.plan.fit()
        self.wait(250)
        begun = time.monotonic()
        QTest.mouseClick(self.win.tabs.header.file_button, Qt.MouseButton.LeftButton)
        self.wait(90)
        self.shot("kimi12-giro-file-meta")
        self.until(lambda: self.win.file_page.entrance is None, 3)
        self.note(f"File aperto col clic: {(time.monotonic() - begun) * 1000:.1f} ms")
        QTest.mouseClick(self.win.file_page.items["preferences:appearance"], Qt.MouseButton.LeftButton)
        self.wait(250)
        if self.win.file_page.body.currentWidget() is not self.win.file_page.sections["preferences"]:
            raise RuntimeError("The Settings section did not open")
        for theme, italian in THEMES:
            self.set_theme(theme)
            self.shot(f"kimi12-impostazioni-{italian}")
        settings = self.win.file_page.settings
        sizes = settings.appearance.text_size
        previous = self.win.cfg.text_size
        changed = "large" if previous != "large" else "medium"
        sizes.setCurrentIndex(sizes.findData(changed))
        if not self.until(lambda: self.win.cfg.text_size == changed, 3):
            raise RuntimeError("The text size did not apply at once")
        QTest.mouseClick(settings.undo, Qt.MouseButton.LeftButton)
        if not self.until(lambda: self.win.cfg.text_size == previous, 3):
            raise RuntimeError("The settings undo did not restore the text size")
        self.note(f"Impostazioni: testo {previous} -> {changed} -> {previous}, applicazione e annullamento")
        for key in ("open", "import", "export", "catalogues", "help"):
            QTest.mouseClick(self.win.file_page.items[key], Qt.MouseButton.LeftButton)
            self.wait(150)
            if self.win.file_page.body.currentWidget() is not self.win.file_page.sections[key]:
                raise RuntimeError(f"The File section {key} did not open")
        self.shot("kimi12-giro-file-aiuto")
        QTest.keyClick(self.win.file_page, Qt.Key.Key_Escape)
        self.wait(250)
        if self.win.file_page.isVisible():
            raise RuntimeError("Escape did not close File")
        self.note("File chiuso con Esc")

    def file_proposals(self) -> None:
        from meridiana.ui import motion
        page = self.win.file_page
        was_reduced = motion.reduced()
        motion.set_reduced(False)
        self.set_theme("light")
        try:
            for kind, name in (("slide", "scorrimento"), ("sheet", "foglio"), ("fade", "dissolvenza")):
                page.entrance_kind = kind
                self.note(f"proposta {name}: durata={page.entrance_duration} ms")
                self.shot(f"kimi11-file-{name}-0")
                QTest.mouseClick(self.win.tabs.header.file_button, Qt.MouseButton.LeftButton)
                if not self.until(lambda: page.entrance is not None and page.entrance.after is not None, 3):
                    raise RuntimeError(f"No entrance for {kind}")
                entrance = page.entrance
                entrance.animation.pause()
                for percent in (25, 50, 75, 100):
                    entrance.animation.setCurrentTime(round(page.entrance_duration * percent / 100))
                    self.wait(30)
                    self.shot(f"kimi11-file-{name}-{percent}")
                    self.note(f"proposta {name}, fotogramma={percent} %, valore={entrance.t:.3f}, "
                              f"tempo={entrance.animation.currentTime()} ms, stato={entrance.animation.state()}")
                QTest.keyClick(page, Qt.Key.Key_Escape)
                self.wait(200)
                if page.isVisible():
                    raise RuntimeError(f"File did not close after {kind}")
        finally:
            motion.set_reduced(was_reduced)

    def toolbars(self) -> None:
        from meridiana.ui import theme
        label = self.args.toolbars
        for text_size, text_name in TEXT_SIZES:
            theme.change_text_size(text_size, self.app)
            self.win._toolbar_style()
            for width in (1280, 1600, 1920):
                self.win.resize(width, 1000)
                self.wait(300)
                for pid in PHASES:
                    self.click_phase(pid)
                    card = self.win.tabs.header.card
                    for colour, italian in THEMES:
                        self.set_theme(colour)
                        self.shot(f"kimi11-strumenti-{label}-{pid}-{italian}-{width}-{text_name}", card)
        theme.change_text_size("medium", self.app)

    def run(self) -> None:
        try:
            self.note(f"piattaforma={self.app.platformName()}, Qt={QLibraryInfo.version().toString()}, "
                      f"schermi={[(s.name(), s.size().width(), s.size().height()) for s in self.app.screens()]}")
            if self.args.toolbars:
                self.toolbars()
            elif self.args.file_proposals:
                self.file_proposals()
            else:
                self.tour()
            self.note("giro completato")
            code = 0
        except Exception:
            self.lines.append(traceback.format_exc())
            traceback.print_exc()
            code = 1
        finally:
            suffix = f"-{self.args.toolbars}" if self.args.toolbars else "-file" if self.args.file_proposals else ""
            destination = ROOT / "docs" / "revisioni" / f"kimi12-giro{suffix}.txt"
            destination.write_text("\n".join(self.lines + ["", "Avvisi Qt:"] + self.messages) + "\n",
                                   encoding="utf-8")
            self.win.close()
            self.app.exit(code)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toolbars", metavar="LABEL", help="record every phase bar with this before/after label")
    parser.add_argument("--file-proposals", action="store_true", help="record the three File entrances at five times")
    args = parser.parse_args()
    os.environ.setdefault("PYTHON_KEYRING_BACKEND", "keyring.backends.null.Keyring")
    i18n.setup("it")
    app = QApplication(sys.argv[:1])
    messages: list[str] = []

    def qt_message(kind, context, text):
        line = f"{kind!s}: {text} ({context.file}:{context.line})"
        messages.append(line)
        print(line, file=sys.stderr, flush=True)

    from PySide6.QtCore import qInstallMessageHandler
    qInstallMessageHandler(qt_message)
    tour = Tour(app, args)
    tour.messages = messages
    QTimer.singleShot(0, tour.run)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
