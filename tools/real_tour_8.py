"""Exercise R148 in Meridiana's real window, without any external service.

Run through tools/real_session.sh. Screenshots and the log go to docs/revisioni.
"""

from __future__ import annotations

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

from meridiana import config, i18n
from meridiana.paths import Paths
from meridiana.ui.window import MainWindow


class Tour(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.output = ROOT / "docs" / "revisioni" / "foto"
        self.output.mkdir(parents=True, exist_ok=True)
        self.lines: list[str] = []
        self.messages: list[str] = []
        self.external: list[str] = []
        self.started = time.monotonic()
        cfg = config.Config(theme="light", background="none", assistant=False, check_updates=False,
                            network_tiles=True, network_geocoding=True, network_pvgis=True, language="it",
                            assistant_provider="claude")
        self.win = MainWindow(Paths.from_env(), cfg)
        self.win.relayout_timer.setInterval(0)
        self.win.plan.tile_timer.setInterval(60000)
        self.win.plan.loader.net.get = self.forbidden
        self.win.assistant_chat.make_local = self.local
        self.win.assistant_chat.make_cloud = self.cloud
        self.win.assistant_chat.survey = nothing_local
        self.local_calls = 0
        self.cloud_calls = 0
        self.win.resize(1600, 950)
        self.win.show()

    def note(self, text: str) -> None:
        line = f"{time.monotonic() - self.started:8.3f} s  {text}"
        self.lines.append(line)
        print(line, flush=True)

    def forbidden(self, request):
        self.external.append(request.url().toString())
        raise AssertionError(f"Unexpected external request: {self.external[-1]}")

    def local(self):
        self.local_calls += 1
        return offline()

    def cloud(self, _key=""):
        self.cloud_calls += 1
        raise AssertionError("A reserved project tried to use Claude")

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

    def shot(self, name: str) -> None:
        self.app.processEvents()
        image = self.win.grab()
        path = self.output / f"{name}.png"
        if not image.save(str(path)):
            raise RuntimeError(f"Could not save {path}")
        self.note(f"foto {path.name}: {image.width()} x {image.height()}")

    def theme(self, name: str) -> None:
        self.win.cfg.theme = name
        self.win.theme.apply()
        self.wait(350)

    def type(self, widget, text: str) -> None:
        widget.setFocus(Qt.FocusReason.OtherFocusReason)
        widget.selectAll()
        QTest.keyClicks(widget, text)
        self.wait(80)

    def run(self) -> None:
        try:
            self.note(f"piattaforma={self.app.platformName()}, Qt={QLibraryInfo.version().toString()}, "
                      f"schermi={[(s.name(), s.size().width(), s.size().height()) for s in self.app.screens()]}")
            QTest.mouseClick(self.win.tabs.header.file_button, Qt.MouseButton.LeftButton)
            self.wait(300)
            QTest.mouseClick(self.win.file_page.items["new"], Qt.MouseButton.LeftButton)
            self.wait(300)
            page = self.win.file_page.new_project
            page.send = self.forbidden
            page.preview.loader.net.get = self.forbidden
            self.type(page.query, "rh")
            if not any(row.source == "ISTAT" for row in page.suggestion_rows.values()):
                raise AssertionError("The local ISTAT suggestions did not appear")
            self.note("suggerimenti locali ISTAT mentre si scrive, nessuna ricerca online")
            QTest.mouseClick(page.optional, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                             page.optional.rect().topLeft() + page.optional.rect().center() / 20)
            if not page.optional.isChecked():
                page.optional.setChecked(True)
            QTest.mouseClick(page.reserved, Qt.MouseButton.LeftButton)
            if not page.reserved.isChecked() or not page.preview.loader.offline:
                raise AssertionError("The reserved mark did not stop the preview")
            self.type(page.query, '45°31\'21,36"N 9°01\'48,00"E')
            if page.candidate is None or not page.create.isEnabled():
                raise AssertionError("The DMS point was not accepted")
            self.type(page.name, "Progetto riservato Rho")
            self.type(page.distributor, "E-distribuzione")
            self.type(page.pod, "IT001E12345678")
            self.type(page.voltage.lineEdit(), "400")
            self.type(page.practice, "PR-2026-42")
            for name, italian in (("light", "chiaro"), ("dark", "scuro")):
                self.theme(name)
                self.shot(f"kimi8-riservato-nuovo-{italian}")
            if self.external:
                raise AssertionError(f"Requests before consent: {self.external}")
            QTest.mouseClick(page.create, Qt.MouseButton.LeftButton)
            self.wait(500)
            project = self.win.project
            if not project.reserved or project.network_consent:
                raise AssertionError("The new project did not start with every consent off")
            if project.network.voltage_v != 400 or project.network.technical_rule() != "CEI 0-21":
                raise AssertionError("The optional grid data did not reach the project")
            if not self.win.plan.loader.offline:
                raise AssertionError("The main map went online without consent")
            self.note("progetto creato da DMS, dati di rete facoltativi e consensi inizialmente vuoti")
            props = self.win.props
            self.win._compute_energy(fetch=True)
            if self.win.energy_job.fetch:
                raise AssertionError("PVGIS was requested without project consent")
            if not self.until(lambda: not self.win.busy_wait.waiting):
                raise AssertionError("The cached weather computation did not finish")
            QTest.mouseClick(props.maps_consent, Qt.MouseButton.LeftButton)
            self.win.plan.tile_timer.stop()
            QTest.mouseClick(props.weather_consent, Qt.MouseButton.LeftButton)
            if set(project.network_consent) != {"tiles", "pvgis"}:
                raise AssertionError("The separate project consents were not stored")
            for name, italian in (("light", "chiaro"), ("dark", "scuro")):
                self.theme(name)
                self.shot(f"kimi8-riservato-proprieta-{italian}")
            self.win.assistant_chat.ask("Riassumi il progetto")
            if not self.until(lambda: self.win.assistant_chat.job is None, 10):
                raise AssertionError("The fake local answer did not finish")
            if self.local_calls != 1 or self.cloud_calls or self.external:
                raise AssertionError("A reserved project contacted Claude or another service")
            self.note("consensi separati, PVGIS fermo prima del consenso, Meridio locale e Claude mai chiamato")
            self.note("giro completato senza richieste esterne")
            code = 0
        except Exception:
            self.lines.append(traceback.format_exc())
            traceback.print_exc()
            code = 1
        finally:
            destination = ROOT / "docs" / "revisioni" / "kimi8-giro.txt"
            destination.write_text("\n".join(self.lines + ["", "Avvisi Qt:"] + self.messages) + "\n",
                                   encoding="utf-8")
            self.win.session.mark_saved()
            self.win.close()
            self.app.exit(code)


def main() -> int:
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
    tour = Tour(app)
    tour.messages = messages
    QTimer.singleShot(0, tour.run)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
