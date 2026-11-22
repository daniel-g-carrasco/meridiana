"""R617 (Daniel 14/11/2026: «unifica pure»): the program's dynamic highlights on one definition.

- in the files of the census no highlight writes its own colour, width, gap or duration: they come from
  design.Highlight (`Theme.highlight` in QML) and from the theme's and the views' colours;
- what outlines an element of the interface is `M.Highlight` (Meridio's, the check opened from its mark), the side of a
  drawing lit is `M.LitSide` (the plan's pills, the Properties, the side a command takes); Meridio's own Spotlight and
  the plan's doubled lit side are gone;
- on the pixels: the highlight around an element and the one inside a row stand at the same distance on the four sides
  (within 1 px), the line as thick as the scale says, the corners concentric (radius = the element's +/- the gap: the
  diagonal's gap is the sides'); the lit side is centred on its line and as wide as the scale says."""
import ast
import math
import re
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import delete

setUpModule = _setup.keep_global_state

SRC = Path(__file__).resolve().parents[3] / "src" / "meridiana"
QML = SRC / "gui" / "qml" / "Meridiana"

# the files of the census (R617): where the highlights were drawn each on its own
CENSUS_QML = ["Checks/ChecksPage.qml", "Properties/SideHighlight.qml", "Plan/SidePills.qml", "Plan/SelectionOverlay.qml",
              "Assistant/AssistantLayer.qml", "Controls/Highlight.qml", "Controls/LitSide.qml"]
HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def code_of(text):
    """QML without its comments."""
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


class Sources(unittest.TestCase):
    def test_one_component_for_each_form(self):
        self.assertFalse((QML / "Assistant" / "Spotlight.qml").exists(), "Meridio's highlight is M.Highlight now")
        controls = (QML / "Controls" / "qmldir").read_text(encoding="utf-8")
        self.assertIn("Highlight 1.0 Highlight.qml", controls)
        self.assertIn("LitSide 1.0 LitSide.qml", controls)
        layer = code_of((QML / "Assistant" / "AssistantLayer.qml").read_text(encoding="utf-8"))
        self.assertRegex(layer, r'M\.Highlight\s*\{\s*objectName:\s*"assistantSpotlight"')
        checks = code_of((QML / "Checks" / "ChecksPage.qml").read_text(encoding="utf-8"))
        # R663 (Daniel 16/11/2026): the check opened is selected as a row of the lists, its ground select_bg, no line
        self.assertNotRegex(checks, r'M\.Highlight\s*\{')
        self.assertRegex(checks, r'"checkOpened"[^}]*Theme\.colors\.select_bg')
        for rel in ("Plan/SidePills.qml", "Properties/SideHighlight.qml"):
            text = code_of((QML / rel).read_text(encoding="utf-8"))
            self.assertNotIn("ShapePath", text, f"{rel}: the lit side is M.LitSide, not a Shape of its own")
            self.assertIn("M.LitSide", text, rel)
        plan = code_of((QML / "Plan" / "Plan.qml").read_text(encoding="utf-8"))
        self.assertRegex(plan, r'Controls\.LitSide\s*\{[^}]*objectName:\s*"collectSide"')

    def test_no_colour_width_gap_or_duration_by_hand_in_the_census(self):
        own = []
        for rel in CENSUS_QML:
            text = code_of((QML / rel).read_text(encoding="utf-8"))
            for number, line in enumerate(text.splitlines(), 1):
                found = [HEX.search(line) and "colour " + HEX.search(line).group(0),
                         re.search(r"\b(strokeWidth|border\.width|lineWidth)\s*[:=]\s*[0-9.]+\s*($|[;}])", line)
                         and "width by hand",
                         re.search(r"\bwidth\s*:\s*[0-9.]+\s*[,}]", line) and "stroke width by hand",
                         re.search(r"\b\d+\s*/\s*255\b", line) and "veil by hand",
                         rel.startswith("Controls/") and re.search(r"\b(interval|duration)\s*:\s*\d", line)
                         and "duration by hand"]
                own += [f"{rel}:{number}: {what}" for what in found if what]
        self.assertEqual(own, [], "a highlight's value is design.Highlight's (Theme.highlight), its colour the theme's")

    def _functions(self, path, names):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return {node.name: node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name in names}

    def test_the_plan_and_the_preview_take_the_scale(self):
        found = self._functions(SRC / "gui" / "backend" / "plan.py", {"_overlays", "_light_modules", "_lit_objects"})
        # R598: the pens moved beside the plan's scene (plan_scene.py), where the plan and its tools take them
        found.update(self._functions(SRC / "gui" / "backend" / "plan_scene.py", {"lit_pens"}))
        self.assertEqual(set(found), {"_overlays", "_light_modules", "_lit_objects", "lit_pens"})
        own = []
        for name, node in found.items():
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str) and HEX.fullmatch(sub.value):
                    own.append(f"{name}: colour {sub.value}")
                if isinstance(sub, ast.Call) and getattr(sub.func, "id", getattr(sub.func, "attr", "")) in (
                        "light", "_light_modules", "lit_pens"):
                    own += [f"{name}: {ast.unparse(sub)}" for a in sub.args
                            if isinstance(a, ast.Constant) and isinstance(a.value, (int, float))]
        self.assertEqual(own, [], "the plan's highlights take design.Highlight and the views' colours")
        paint = self._functions(SRC / "gui" / "backend" / "dialogs_preview.py", {"paint"})["paint"]
        self.assertIn("design.Highlight.SIDE", ast.unparse(paint), "the preview's field lit is the plan's lit side")

    def test_the_scale_is_written_once(self):
        from meridiana.app.interface import view_colours
        from meridiana.gui.style import design
        h = design.Highlight
        self.assertEqual((h.SELECT, h.HOVER, h.HALO, h.SIDE),
                         tuple(view_colours.WIDTHS[k] for k in ("select", "hover", "select_halo", "side")))
        self.assertEqual(h.LINE, design.Line.HAIR)
        self.assertEqual(h.FOCUS, design.Line.FOCUS)
        # the keyboard's ring thicker than the highlight's line; R685 (Daniel 16/11/2026): the selection and what is
        # under the pointer are the views' one thin line, told apart by their tint
        self.assertGreater(h.FOCUS, h.LINE)
        self.assertEqual(h.SELECT, h.HOVER)
        self.assertEqual(h.SELECT, view_colours.Annotation.STROKE)


TH = 40


def differ(a, b, x, y):
    if x < 0 or y < 0 or x >= a.width() or y >= a.height():
        return 0
    p, q = QColor(a.pixel(x, y)), QColor(b.pixel(x, y))
    return max(abs(p.red() - q.red()), abs(p.green() - q.green()), abs(p.blue() - q.blue()))


def run(a, b, start, direction, reach=12, th=TH):
    """From `start` (a point on an edge, in continuous coordinates: pixel (i, j) covers [i, i+1] x [j, j+1]) along
    `direction`: where the highlight begins and how thick it is, in pixels (scale 1), read every half pixel."""
    first = last = None
    for k in range(reach * 2 + 1):
        t = k / 2 + .25
        if differ(a, b, math.floor(start[0] + direction[0] * t), math.floor(start[1] + direction[1] * t)) > th:
            first = t if first is None else first
            last = t
        elif first is not None:
            break
    return (None, None) if first is None else (first - .25, last - first + .5)


class Pixels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def scene(self, body):
        from meridiana.gui.backend.controls import install_controls
        engine = QQmlEngine()
        theme = install_controls(engine, dict(theme="light", reducedMotion=True))
        component = QQmlComponent(engine)
        component.setData(("import QtQuick\nimport Meridiana.Theme\nimport Meridiana.Controls as M\n"
                           "Item { width: 420; height: 260\n" + body + "\n}").encode(), QUrl())
        self.assertFalse(component.isError(), "\n".join(e.toString() for e in component.errors()))
        root = component.create()
        root.setParent(engine)
        window = QQuickWindow()
        window.setColor(QColor(theme.colors["panel"]))
        window.resize(420, 260)
        root.setParentItem(window.contentItem())
        window.show()
        self.assertTrue(QTest.qWaitForWindowExposed(window))

        def cleanup():
            window.close()
            delete(root)
            delete(window)
            delete(engine)
        self.addCleanup(cleanup)
        return root, window, theme

    def grabs(self, window, mark):
        from meridiana.gui.capture import grab
        mark.setProperty("active", False)
        _setup.wait_until(self.app, lambda: not mark.isVisible())
        before = grab(window)
        mark.setProperty("active", True)
        _setup.wait_until(self.app, lambda: mark.isVisible() and mark.property("progress") == 1)
        _setup.wait_until(self.app, lambda: grab(window) != before)      # a frame drawn with it
        return before, grab(window)

    def gaps(self, before, after, rect, radii, inside, edge):
        x, y, w, h = rect
        s = -1 if inside else 1
        e = edge if inside else 0
        sides = [((x + e, y + h / 2), (-s, 0)), ((x + w - e, y + h / 2), (s, 0)),
                 ((x + w / 2, y + e), (0, -s)), ((x + w / 2, y + h - e), (0, s))]
        straight = [run(before, after, start, d) for start, d in sides]
        corners = []
        k = 1 / math.sqrt(2)
        for (cx, cy, dx, dy), r in zip(((x, y, -1, -1), (x + w, y, 1, -1), (x + w, y + h, 1, 1), (x, y + h, -1, 1)), radii, strict=True):
            if r > 0:
                c = (cx - dx * r, cy - dy * r)
                rr = r - e
                # a hair line on a diagonal covers each pixel only in part: a lower threshold
                corners.append(run(before, after, (c[0] + dx * k * rr, c[1] + dy * k * rr), (dx * k * s, dy * k * s),
                                   th=TH / 2))
        return straight, corners

    def check(self, straight, corners, line, label):
        self.assertTrue(all(g is not None for g, _ in straight), f"{label}: a side without its line {straight}")
        gaps = [g for g, _ in straight]
        self.assertLessEqual(max(gaps) - min(gaps), 1, f"{label}: the four gaps {gaps}")
        for _g, t in straight:
            self.assertLessEqual(abs(t - line), 1, f"{label}: the line {straight}")
        middle = sum(g + t / 2 for g, t in straight) / 4
        for g, t in corners:
            self.assertIsNotNone(g, f"{label}: a corner without its line")
            # concentric: along the corner's diagonal the line's middle stands where it stands on the sides (radius =
            # the element's +/- the gap). The same line with the element's radius alone would stand 0,8 px farther
            # (gap x (sqrt 2 - 1) at a gap of 2): the middle, not the first pixel, because on a diagonal the hair line
            # spreads over the pixels it crosses
            self.assertLessEqual(abs(g + t / 2 - middle), .5, f"{label}: corner {corners} against sides {straight}")

    def test_around_an_element_and_inside_a_row_centred_and_concentric(self):
        root, window, theme = self.scene("""
            Rectangle { id: button; x: 60; y: 40; width: 96; height: 28; radius: 6
                color: Theme.colors.field; border.width: 1; border.color: Theme.colors.line }
            M.Highlight { objectName: "around"; persistent: true
                targetRect: Qt.rect(button.x, button.y, button.width, button.height); radii: [6, 6, 6, 6] }
            Rectangle { id: row; x: 60; y: 120; width: 240; height: 34; topLeftRadius: 6; topRightRadius: 6
                color: Theme.colors.card; border.width: 1; border.color: Theme.colors.line }
            M.Highlight { objectName: "inside"; persistent: true; inside: true; edgeLine: 1
                targetRect: Qt.rect(row.x, row.y, row.width, row.height); radii: [6, 6, 0, 0] }""")
        line = theme.highlight["LINE"]
        gap = theme.highlight["GAP"]
        around = next(c for c in root.childItems() if c.objectName() == "around")
        before, after = self.grabs(window, around)
        straight, corners = self.gaps(before, after, (60, 40, 96, 28), [6] * 4, False, 0)
        self.check(straight, corners, line, "around")
        self.assertLessEqual(abs(min(g for g, _ in straight) - gap), 1, straight)
        inside = next(c for c in root.childItems() if c.objectName() == "inside")
        before, after = self.grabs(window, inside)
        straight, corners = self.gaps(before, after, (60, 120, 240, 34), [6, 6, 0, 0], True, 1)
        self.check(straight, corners, line, "inside")
        self.assertLessEqual(abs(min(g for g, _ in straight) - gap), 1, straight)

    def test_the_lit_side_is_centred_on_its_line(self):
        from meridiana.gui.capture import grab
        root, window, theme = self.scene("""
            M.LitSide { objectName: "flat"; anchors.fill: parent; ink: "magenta"; a: Qt.point(40, 60); b: Qt.point(300, 60) }
            M.LitSide { objectName: "slant"; anchors.fill: parent; ink: "magenta"; a: Qt.point(40, 120); b: Qt.point(300, 220) }""")
        side = theme.highlight["SIDE"]
        marks = [c for c in root.childItems() if c.objectName() in ("flat", "slant")]
        for mark in marks:
            mark.setVisible(False)
        _setup.wait_until(self.app, lambda: not grab(window).isNull())
        before = grab(window)
        for mark in marks:
            mark.setVisible(True)
        _setup.wait_until(self.app, lambda: grab(window) != before)      # a frame drawn with them
        after = grab(window)
        for (a, b), label in ((((40, 60), (300, 60)), "flat"), (((40, 120), (300, 220)), "slant")):
            mx, my = a[0] + (b[0] - a[0]) * .5, a[1] + (b[1] - a[1]) * .5
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            n = (-(b[1] - a[1]) / length, (b[0] - a[0]) / length)
            reach = []
            for s in (1, -1):
                far = 0
                for k in range(1, 21):          # pixel (i, j) covers [i, i+1] x [j, j+1]: read at its floor
                    t = k / 2
                    if differ(before, after, math.floor(mx + s * n[0] * t), math.floor(my + s * n[1] * t)) > TH:
                        far = t
                reach.append(far)
            self.assertLessEqual(abs(reach[0] - reach[1]), 1, f"{label}: not centred on its line {reach}")
            self.assertLessEqual(abs(reach[0] + reach[1] - side), 1.5, f"{label}: width {reach} against {side}")


if __name__ == "__main__":
    unittest.main()
