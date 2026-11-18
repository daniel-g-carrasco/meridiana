"""Exercise R151 in Meridiana's real window, with invented local data and fake providers only.

Run through tools/real_session.sh. Screenshots and the log go to docs/revisioni.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from PySide6.QtCore import QLibraryInfo, QObject, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox

from _fakes import FakeAnthropic, nothing_local, offline
from _fixtures import capannone

from meridiana import assistant, config, i18n
from meridiana.assistant import providers, tools
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
        cfg = config.Config(theme="light", background="none", assistant=True, check_updates=False,
                            network_tiles=False, network_geocoding=False, network_pvgis=False, language="it")
        self.win = MainWindow(Paths.from_env(), cfg)
        self.win.relayout_timer.setInterval(0)
        self.win.plan.tile_timer.setInterval(60000)
        self.win.assistant_chat.make_local = offline
        self.win.assistant_chat.survey = nothing_local
        self.work = self.win.paths.data / "prova-r151"
        self.folder = self.work / "cartella-commessa"
        self.folder.mkdir(parents=True, exist_ok=True)
        reg = self.win.registry
        client = reg.create_client("Cliente esempio")
        self.job = reg.create_job("26042", "Commessa esempio", client["id"])
        reg.link_folder(self.job["id"], self.folder)
        self.paths = {}
        for title, series, revision in (("Capannone riferimento", "riferimento", "R01"),
                                        ("Capannone precedente", "recente", "R02"),
                                        ("Capannone recente", "recente", "R04"),
                                        ("Altro capannone", "altro", "R05")):
            project = capannone(title)
            project.job_id = self.job["id"]
            project.series_id = series
            path = self.folder / f"{title.replace(' ', '-')}_{revision}.meridiana"
            project.save(path)
            self.paths[title] = path
        self.win.open_path(self.paths["Capannone riferimento"])
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

    def answer(self, button: QMessageBox.StandardButton) -> None:
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
            if not self.until(lambda: len(self.win.registry.list_index()) == 4):
                raise AssertionError("The linked projects were not indexed in the background")
            chat = self.win.assistant_chat
            state = chat.conversation.state
            found = tools.run("search_projects", {"query": "Capannone"}, chat.host, state)
            reference = next(item for item in json.loads(found.content)["projects"]
                             if item["title"] == "Capannone riferimento")
            similar = tools.run("similar_projects", {"project_id": reference["id"]}, chat.host, state)
            result = json.loads(similar.content)["projects"]
            if [item["title"] for item in result] != ["Altro capannone", "Capannone recente"]:
                raise AssertionError(f"Unexpected similar projects: {result}")
            if "stesso montaggio" not in result[0]["reason"] or "R05" not in result[0]["reason"]:
                raise AssertionError("The similarity reason is incomplete")
            opened = tools.run("prepare_open_project", {"project_id": result[0]["id"]}, chat.host, state)
            self.win.assistant.open_panel()
            chat._tool_done(None, opened)
            self.wait(300)
            card = chat.cards[opened.proposal.id]
            self.note(f"scheda apertura: altezza={card.height()}, richiesta={card.sizeHint().height()}, "
                      f"etichette={[(label.height(), label.sizeHint().height(), label.heightForWidth(label.width())) for label in card.findChildren(QLabel)]}")
            for theme, italian in (("light", "chiaro"), ("dark", "scuro")):
                self.theme(theme)
                self.note(f"scheda {italian}: altezza={card.height()}, richiesta={card.sizeHint().height()}, "
                          f"minimo_layout={card.layout().minimumSize().height()}, "
                          f"etichette={[label.geometry().getRect() for label in card.findChildren(QLabel)]}, "
                          f"pulsanti={[button.geometry().getRect() for button in card.buttons.values()]}, "
                          f"contenitore={chat.widget.cards.height()}, richiesto={chat.widget.cards.sizeHint().height()}, "
                          f"domande_y={chat.widget.questions_box.y()}")
                self.shot(f"kimi10-apertura-{italian}")
            if self.win.path != self.paths["Capannone riferimento"]:
                raise AssertionError("Meridio opened a project before the click")
            self.win.edit("Modifica prova", lambda project: setattr(project, "name", "Lavoro non salvato"))
            card = chat.cards[opened.proposal.id]
            self.answer(QMessageBox.StandardButton.Cancel)
            QTest.mouseClick(card.buttons["apply"], Qt.MouseButton.LeftButton)
            self.wait(250)
            if self.win.project.name != "Lavoro non salvato" or opened.proposal.id not in chat.cards:
                raise AssertionError("Cancelling the unsaved choice lost the current work or the card")
            self.answer(QMessageBox.StandardButton.Discard)
            QTest.mouseClick(card.buttons["apply"], Qt.MouseButton.LeftButton)
            self.wait(350)
            if self.win.project.name != "Altro capannone" or self.win.path != self.paths["Altro capannone"]:
                raise AssertionError("The confirmed project did not open")
            self.note("indice, ricerca simile motivata, percorso e revisione; annulla e poi scarta prima di aprire")
            created = tools.run("prepare_task", {"action": "create", "text": "Verificare il collegamento di rete",
                                                 "due": "2026-11-02", "job_id": self.job["id"]}, chat.host, state)
            chat._tool_done(None, created)
            self.wait(250)
            self.shot("kimi10-attivita-scuro")
            if self.win.registry.list_tasks():
                raise AssertionError("A task was written before its confirmation")
            chat.cards[created.proposal.id].buttons["apply"].click()
            listed = tools.run("list_tasks", {}, chat.host, state)
            task_id = json.loads(listed.content)["tasks"][0]["id"]
            completed = tools.run("prepare_task", {"action": "complete", "task_id": task_id}, chat.host, state)
            chat._tool_done(None, completed)
            chat.cards[completed.proposal.id].buttons["apply"].click()
            if not self.win.registry.list_tasks(include_done=True)[0]["done"]:
                raise AssertionError("The confirmed task was not completed")
            self.note("attività creata e completata soltanto dopo i due clic")
            client = FakeAnthropic([[("tool", "search_projects", {"query": "Capannone"})], [("text", "Fatto.")]])
            chat.make_cloud = lambda key: providers.Anthropic(model="claude-haiku-5-5", client=client)
            chat.keys = SimpleNamespace(get=lambda family: "chiave-finta")
            self.win.cfg.assistant_provider = "claude"
            self.win.cfg.assistant_consent = {"anthropic": ["2026-10-29"]}
            self.win.assistant.ask("Cerca Altro capannone e Cliente esempio")
            if not self.until(lambda: self.win.assistant.mood.state == assistant.IDLE and chat.job is None, 15):
                raise AssertionError("The fake Claude conversation did not finish")
            sent = json.dumps(client.calls, default=str)
            for secret in ("Altro capannone", "Capannone recente", "Cliente esempio", "26042", str(self.folder)):
                if secret in sent:
                    raise AssertionError(f"Archive data reached the fake cloud: {secret}")
            self.note("provider cloud finto: solo alias, nessun nome, percorso o commessa")
            self.note("giro completato")
            code = 0
        except Exception:
            self.lines.append(traceback.format_exc())
            traceback.print_exc()
            code = 1
        finally:
            destination = ROOT / "docs" / "revisioni" / "kimi10-giro.txt"
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
