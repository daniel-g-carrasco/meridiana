"""Exercise R193-R197 in Meridiana's real hidden window and keep screenshots."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))

from PySide6.QtCore import QPoint, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from real_tour import Tour
from _fakes import FakeServer, text_answer, tool_answer

from meridiana import assistant as core
from meridiana import i18n
from meridiana.assistant import providers


class FinishTour(Tour):
    def run(self) -> None:
        server = FakeServer([
            tool_answer([("propose_edit", {"kind": "subfield", "id": "s1", "changes": {"params.tilt": 20},
                                           "reason": "meno ombre tra le file"})]),
            text_answer("Ho preparato la proposta: guardala e applicala se va bene."),
        ])
        try:
            self.win.resize(1280, 850)
            self.win.assistant_chat.make_local = lambda: providers.OpenAICompatible(base_url=server.url)
            self.win._show_assistant(True)
            self.win.cfg.assistant_introduced = True
            self.click_phase("economics")
            self.win.economics_page.side.ensureWidgetVisible(self.win.economics_page.community)
            bar = self.win.economics_page.side.verticalScrollBar()
            bar.setValue(min(bar.maximum(), bar.value() + 180))
            self.wait(100)
            for theme, italian in (("light", "chiaro"), ("dark", "scuro")):
                self.set_theme(theme)
                self.wait(1000)
                self.note(f"CER {theme}: checkbox={self.win.economics_page.community.palette().windowText().color().name()}, "
                          f"tokens={self.win.theme.style.tokens['text']}")
                subject = self.win if theme == "dark" else self.win.economics_page.side
                self.shot(f"kimi24-cer-spenta-{italian}", subject)
            self.set_theme("light")
            self.win.economics_page.community.setChecked(True)
            self.shot("kimi24-cer-accesa-chiaro", self.win.economics_page.side)
            self.win.economics_page.community.setChecked(False)
            self.assert_project_unchanged()
            if not self.win._save():
                raise RuntimeError("The project did not save")
            self.shot("kimi24-salvataggio-barra", self.win.statusBar())
            self.win.assistant.open_panel()
            self.win.assistant.ask("Alza l'inclinazione del sottocampo")
            if not self.until(lambda: self.win.assistant.mood.state == core.IDLE and self.win.assistant_chat.job is None):
                raise RuntimeError("Meridio did not finish")
            if not self.win.assistant_chat.cards:
                raise RuntimeError("Meridio did not show the proposal at once")
            self.until(lambda: not self.win.assistant.speak_timer.isActive(), 5)
            from meridiana.ui import assistant as ui
            a = self.win.assistant
            last = a.questions_box.mapTo(a.panel, QPoint(0, a.questions_box.height())).y()
            self.note(f"assistant={ui.__file__}; bubble={a.bubble.height()}, hint={a.panel.sizeHint().height()}, "
                      f"questions={a.questions_box.height()}, last={last}, field={a.field.y()}")
            for theme, italian in (("light", "chiaro"), ("dark", "scuro")):
                self.set_theme(theme)
                self.shot(f"kimi24-meridio-proposta-{italian}", self.win.assistant.bubble)
            QTest.mouseMove(self.win.assistant.questions[0])
            self.shot("kimi24-meridio-hover", self.win.assistant.questions_box)
            self.note("CER, salvataggio e proposta immediata verificati nella finestra reale")
            code = 0
        except Exception:
            import traceback
            traceback.print_exc()
            code = 1
        finally:
            server.close()
            self.win.session.mark_saved()
            self.win.close()
            self.app.exit(code)

    def assert_project_unchanged(self) -> None:
        if self.win.project.subfields[0].params["tilt"] != 15.0:
            raise RuntimeError("The proposal was applied without the designer")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    os.environ.setdefault("PYTHON_KEYRING_BACKEND", "keyring.backends.null.Keyring")
    i18n.setup("it")
    app = QApplication(sys.argv[:1])
    tour = FinishTour(app, argparse.Namespace(toolbars="", file_proposals=False))
    QTimer.singleShot(0, tour.run)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
