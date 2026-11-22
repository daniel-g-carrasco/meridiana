"""The focus ring only from the keyboard (Daniel 14/11/2026: «L'anello del fuoco compare solo quando ci si arriva con
la tastiera (Tab, Maiusc+Tab, scorciatoie), non dopo un clic del mouse»), one rule for every control: Theme.focusRing.

On the real controls, offscreen, with the events Qt receives from a mouse and a keyboard: a click gives the control the
focus and no pixel of the focus' grey; a Tab to it gives it its ring. Then the sources: every ring or border drawn in
Theme.colors.focus asks Theme.focusRing, so that no control decides on its own again."""
import re
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import delete

setUpModule = _setup.keep_global_state

QML = Path(__file__).resolve().parents[3] / "src" / "meridiana" / "gui" / "qml" / "Meridiana"

# each control after a plain button that takes the first Tab; the point clicked inside it
CONTROLS = {
    "button": ('M.Button { objectName: "target"; text: "Salva" }', (20, 10)),
    "checkbox": ('M.CheckBox { objectName: "target"; text: "Ombre" }', (10, 10)),
    "radio": ('M.RadioButton { objectName: "target"; text: "Sud" }', (10, 10)),
    "field": ('M.TextField { objectName: "target"; width: 160; text: "Capannone" }', (40, 12)),
    "area": ('M.TextArea { objectName: "target"; width: 160; height: 60; text: "Note" }', (40, 20)),
    "combo": ('M.ComboBox { objectName: "target"; width: 160; model: ["Uno", "Due"] }', (40, 12)),
    "segments": ('M.Segments { objectName: "target"; model: ["Pianta", "3D"] }', (12, 10)),
    "help": ('M.HelpMark { objectName: "target"; tip: "Aiuto" }', (10, 10)),
}


class KeyboardRing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def scene(self, body):
        from meridiana.gui.backend.controls import install_controls
        engine = QQmlEngine()
        theme = install_controls(engine, dict(theme="light", reducedMotion=True))
        component = QQmlComponent(engine)
        component.setData(("import QtQuick\nimport Meridiana.Theme\nimport Meridiana.Controls as M\n"
                           "Row { spacing: 24; x: 20; y: 20\n"
                           'M.Button { objectName: "first"; text: "Prima" }\n' + body + "\n}").encode(), QUrl())
        self.assertFalse(component.isError(), "\n".join(e.toString() for e in component.errors()))
        root = component.create()
        root.setParent(engine)
        window = QQuickWindow()
        window.setColor(QColor(theme.colors["panel"]))
        window.resize(520, 160)
        root.setParentItem(window.contentItem())
        window.show()
        window.requestActivate()
        self.assertTrue(QTest.qWaitForWindowExposed(window))

        def cleanup():
            window.close()
            delete(root)
            delete(window)
            delete(engine)
        self.addCleanup(cleanup)
        return root, window, theme

    def ring_pixels(self, window, item, colour):
        """The pixels of exactly the focus' grey in the item's box and a few pixels round it (the rings stand outside):
        exact, so that the softened edge of a dark sign (a radio's dot) does not count as grey."""
        from meridiana.gui.capture import grab
        _setup.wait_until(self.app, lambda: not grab(window).isNull())
        image = grab(window)
        dpr = image.devicePixelRatio()
        corner = item.mapToScene(QPointF(0, 0))
        left, top = max(0, int((corner.x() - 6) * dpr)), max(0, int((corner.y() - 6) * dpr))
        right = min(image.width(), int((corner.x() + item.width() + 6) * dpr))
        bottom = min(image.height(), int((corner.y() + item.height() + 6) * dpr))
        want = QColor(colour).rgb()
        return sum(image.pixel(x, y) == want for y in range(top, bottom) for x in range(left, right))

    def away(self, window, target):
        QTest.mouseMove(window, QPoint(500, 150))
        _setup.wait_until(self.app, lambda: not target.property("hovered"))

    def test_a_click_gives_the_focus_without_the_ring_and_a_tab_gives_the_ring(self):
        for name, (body, at) in CONTROLS.items():
            with self.subTest(control=name):
                root, window, theme = self.scene(body)
                target = root.findChild(QQuickItem, "target")
                first = root.findChild(QQuickItem, "first")
                focus = theme.colors["focus"]
                self.away(window, target)
                rest = self.ring_pixels(window, target, focus)
                # the mouse: a press and a release where a user clicks it
                point = target.mapToScene(QPointF(*at)).toPoint()
                QTest.mouseClick(window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
                self.away(window, target)
                if name == "help":
                    # the mark opens its bubble, which takes the focus; closed, nothing of the ring either
                    QTest.keyClick(window, Qt.Key.Key_Escape)
                else:
                    _setup.wait_until(self.app, lambda t=target: t.hasActiveFocus())
                    self.assertTrue(target.hasActiveFocus())
                # no pixel of the focus' grey more than at rest (a combo's arrow turns from grey to ink when active)
                clicked = self.ring_pixels(window, target, focus)
                self.assertLessEqual(clicked, rest, "a ring after a click")
                # the keyboard: from the first button, Tab
                first.forceActiveFocus(Qt.FocusReason.MouseFocusReason)
                _setup.wait_until(self.app, lambda f=first: f.hasActiveFocus())
                QTest.keyClick(window, Qt.Key.Key_Tab)
                _setup.wait_until(self.app, lambda t=target: t.hasActiveFocus())
                ring = self.ring_pixels(window, target, focus)
                # more than the control's height in pixels of the grey: the smallest ring (a radio's, round, most of
                # its pixels softened) has about two and a half times as many
                self.assertGreater(ring - max(rest, clicked), target.height(), "no ring after Tab")
                # Shift+Tab away: the ring goes with the keyboard
                QTest.keyClick(window, Qt.Key.Key_Backtab)
                _setup.wait_until(self.app, lambda f=first: f.hasActiveFocus())
                self.assertLessEqual(self.ring_pixels(window, target, focus), rest)
                self.doCleanups()

    def test_every_ring_in_the_focus_grey_asks_the_one_rule(self):
        own = []
        for path in sorted(QML.rglob("*.qml")):
            rel = path.relative_to(QML).as_posix()
            if rel in ("Theme/Theme.qml", "Controls/Highlight.qml"):
                continue        # the rule itself; the one highlight (Meridio's, a check opened), which is not a focus (R617)
            text = path.read_text(encoding="utf-8")
            for number, line in enumerate(text.splitlines(), 1):
                code = line.split("//", 1)[0]
                if re.search(r"\bvisualFocus\b", code) and "alias visualFocus" not in code:
                    own.append(f"{rel}:{number}: visualFocus")
                if re.search(r"(border\.width|visible)\s*:[^;]*\bactiveFocus\b", code):
                    own.append(f"{rel}:{number}: activeFocus")
            if "Theme.colors.focus" in text and "Theme.focusRing(" not in text:
                own.append(f"{rel}: Theme.colors.focus without Theme.focusRing")
        self.assertEqual(own, [], "a ring decided by the control itself: use Theme.focusRing(item)")


if __name__ == "__main__":
    unittest.main()
