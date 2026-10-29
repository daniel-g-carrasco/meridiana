"""Exercise R150 in Meridiana's real window, with invented local data only.

Run through tools/real_session.sh. Screenshots and the log go to docs/revisioni.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from PySide6.QtCore import QLibraryInfo, QObject, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from meridiana import config, i18n, registry
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
        self.started = time.monotonic()
        cfg = config.Config(theme="light", background="none", assistant=False, check_updates=False,
                            network_tiles=False, network_geocoding=False, network_pvgis=False, language="it")
        self.win = MainWindow(Paths.from_env(), cfg)
        self.win.relayout_timer.setInterval(0)
        self.win.plan.tile_timer.setInterval(60000)
        self.work = self.win.paths.data / "prova-r150"
        self.work.mkdir(parents=True, exist_ok=True)
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

    def select_job(self, job_id: str) -> None:
        page = self.win.file_page.registry_page
        for row in range(page.job_list.count()):
            item = page.job_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == job_id:
                page.job_list.setCurrentRow(row)
                self.wait(100)
                return
        raise AssertionError("The job is not visible in the registry")

    def answer_warning(self, button: QMessageBox.StandardButton) -> None:
        def click():
            dialog = self.app.activeModalWidget()
            if dialog is None:
                QTimer.singleShot(20, click)
                return
            dialog.button(button).click()
        QTimer.singleShot(0, click)

    def run(self) -> None:
        try:
            self.note(f"piattaforma={self.app.platformName()}, Qt={QLibraryInfo.version().toString()}, "
                      f"schermi={[(s.name(), s.size().width(), s.size().height()) for s in self.app.screens()]}")
            QTest.mouseClick(self.win.tabs.header.file_button, Qt.MouseButton.LeftButton)
            self.wait(300)
            QTest.mouseClick(self.win.file_page.items["registry"], Qt.MouseButton.LeftButton)
            self.wait(300)
            page = self.win.file_page.registry_page
            QTest.mouseClick(page.new_client, Qt.MouseButton.LeftButton)
            self.type(page.client_name, "Cliente esempio")
            QTest.mouseClick(page.save_client, Qt.MouseButton.LeftButton)
            QTest.mouseClick(page.new_job, Qt.MouseButton.LeftButton)
            self.type(page.job_code, "00125")
            self.type(page.job_name, "Commessa esempio")
            QTest.mouseClick(page.save_job, Qt.MouseButton.LeftButton)
            job = self.win.registry.list_jobs()[0]
            self.select_job(job["id"])
            folder = self.work / "cartella-commessa"
            folder.mkdir()
            with patch.object(QFileDialog, "getExistingDirectory", return_value=str(folder)):
                QTest.mouseClick(page.link_folder, Qt.MouseButton.LeftButton)
            manifest = folder / registry.MANIFEST_NAME
            if manifest.exists():
                raise AssertionError("A folder manifest appeared before consent")
            consent = page.folder_box.itemAt(0).widget()
            QTest.mouseClick(consent, Qt.MouseButton.LeftButton)
            if not manifest.is_file():
                raise AssertionError("The folder consent did not write the manifest")
            self.note("cliente, commessa e cartella creati; manifesto solo dopo il consenso")
            for name, italian in (("light", "chiaro"), ("dark", "scuro")):
                self.theme(name)
                self.shot(f"kimi9-registro-{italian}")
            QTest.mouseClick(consent, Qt.MouseButton.LeftButton)
            if manifest.exists():
                raise AssertionError("Revoking folder consent did not remove the manifest")
            QTest.mouseClick(consent, Qt.MouseButton.LeftButton)
            exported = self.work / "registro.json"
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(exported), "JSON")):
                QTest.mouseClick(page.export_registry, Qt.MouseButton.LeftButton)
            data = registry.read_exchange(exported)
            data["clients"].append({"id": "cliente-importato-prova", "name": "Cliente importato esempio",
                                    "kind": "other", "contacts": {}, "notes": "", "archived": False,
                                    "created": "2026-10-28T00:00:00+00:00", "updated": "2026-10-28T00:00:00+00:00"})
            exported.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with patch.object(QFileDialog, "getOpenFileName", return_value=(str(exported), "JSON")):
                QTest.mouseClick(page.import_registry, Qt.MouseButton.LeftButton)
            if len(self.win.registry.list_clients()) != 1 or page.apply_import.isHidden():
                raise AssertionError("The import preview changed data or offered no apply command")
            self.shot("kimi9-import-anteprima-scuro")
            QTest.mouseClick(page.apply_import, Qt.MouseButton.LeftButton)
            if len(self.win.registry.list_clients()) != 2:
                raise AssertionError("Applying the import did not merge the new client")
            self.note("export JSON, anteprima senza scritture e unione per id")
            QTest.mouseClick(page.new_job, Qt.MouseButton.LeftButton)
            self.type(page.job_code, "00126")
            self.type(page.job_name, "Commessa riservata esempio")
            QTest.mouseClick(page.job_reserved, Qt.MouseButton.LeftButton)
            QTest.mouseClick(page.save_job, Qt.MouseButton.LeftButton)
            reserved = next(row for row in self.win.registry.list_jobs() if row["reserved"])
            self.select_job(reserved["id"])
            reserved_folder = self.work / "cartella-riservata"
            reserved_folder.mkdir()
            with patch.object(QFileDialog, "getExistingDirectory", return_value=str(reserved_folder)):
                QTest.mouseClick(page.link_folder, Qt.MouseButton.LeftButton)
            reserved_consent = page.folder_box.itemAt(0).widget()
            if reserved_consent.isEnabled() or (reserved_folder / registry.MANIFEST_NAME).exists():
                raise AssertionError("A reserved job can have a folder manifest")
            cancelled = self.work / "annullato.json"
            self.answer_warning(QMessageBox.StandardButton.Cancel)
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(cancelled), "JSON")):
                QTest.mouseClick(page.export_registry, Qt.MouseButton.LeftButton)
            if cancelled.exists():
                raise AssertionError("Cancelling the reserved export warning wrote the file")
            allowed = self.work / "consentito.json"
            self.answer_warning(QMessageBox.StandardButton.Yes)
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(allowed), "JSON")):
                QTest.mouseClick(page.export_registry, Qt.MouseButton.LeftButton)
            if not allowed.is_file():
                raise AssertionError("Accepting the reserved export warning did not write the file")
            self.note("commessa riservata senza manifesto; export riservato annullato e poi confermato")
            QTest.mouseClick(self.win.file_page.items["new"], Qt.MouseButton.LeftButton)
            self.wait(300)
            new = self.win.file_page.new_project
            new.job.setCurrentIndex(new.job.findData(reserved["id"]))
            if not new.reserved.isChecked() or not new.preview.loader.offline or new.search.isEnabled():
                raise AssertionError("Selecting a reserved job did not stop online search and tiles")
            new.job.setCurrentIndex(new.job.findData(job["id"]))
            new.reserved.setChecked(False)
            self.type(new.query, "45.5226, 9.03")
            self.type(new.name, "Progetto esempio")
            for name, italian in (("light", "chiaro"), ("dark", "scuro")):
                self.theme(name)
                self.shot(f"kimi9-nuovo-{italian}")
            QTest.mouseClick(new.create, Qt.MouseButton.LeftButton)
            self.wait(500)
            target = self.work / "progetto.meridiana"
            with patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "Meridiana")):
                if not self.win._save_as():
                    raise AssertionError("The linked project was not saved")
            if self.win.project.report.get("client") != "Cliente esempio":
                raise AssertionError("Choosing only the job did not carry its client")
            self.win.open_path(target)
            if self.win.current_job_id != job["id"] or self.win.registry.project_at(target) is None:
                raise AssertionError("The project job link did not survive reopening")
            series = self.win.current_project_id
            self.win._save_revision()
            if self.win.path == target or self.win.current_project_id != series:
                raise AssertionError("The revision did not keep the project series")
            self.win.open_path(target)
            if self.win.current_job_id != job["id"] or self.win.current_project_id != series:
                raise AssertionError("Reopening the earlier revision lost its identity")
            self.note("commessa riservata subito offline; R02 e riapertura di R01 con la stessa serie")
            self.note("giro completato")
            code = 0
        except Exception:
            self.lines.append(traceback.format_exc())
            traceback.print_exc()
            code = 1
        finally:
            destination = ROOT / "docs" / "revisioni" / "kimi9-giro.txt"
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
