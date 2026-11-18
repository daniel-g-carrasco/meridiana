"""R495, R501: the census of the areas that scroll, on the real workbench with a calculated year.

For every phase (every tab of the result pages), every File section and every Settings section, at the window
sizes asked: each visible vertical Flickable with its overflow (content height less height: over 0 a bar), whether
the content height keeps changing with no input (a measure that feeds itself), and every visible text that lies
under a visible scroll bar (R501: the bar never covers the content).

    PYTHONPATH="tests;src" QT_QPA_PLATFORM=offscreen python -m quick.confini_scorrimento <year.pickle> 1600x900 ...

The pickle comes from tests/quick/grafici/calculated_rho.py on a copy of a project. Not a test: the suite proves
the rules on the pages (tests/quick/grafici/test_pages.py, tests/quick/pagine/test_settings_qml.py).
"""
import pickle
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QMetaObject, QPointF, QRectF, Q_ARG, Qt
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import item, pump, wait_for

FILE_SECTIONS = ("new", "open", "registry", "export", "catalogues", "help")
SETTINGS_SECTIONS = ("appearance", "navigation", "keyboard", "assistant", "report", "maps", "privacy")


def visible_items(root):
    pending = [root]
    while pending:
        node = pending.pop()
        if not node.isVisible() or node.opacity() <= 0:
            continue
        pending.extend(node.childItems())
        yield node


def label(node):
    names, up = [], node
    while up is not None and len(names) < 3:
        if up.objectName():
            names.append(up.objectName())
        up = up.parentItem()
    return (node.metaObject().className().split("_QML")[0] + ":" + "/".join(names))[:64]


def scene_rect(node, width=None):
    origin = node.mapToScene(QPointF(0, 0))
    return QRectF(origin.x(), origin.y(), node.width() if width is None else width, node.height())


def clip_rect(node):
    """The part of the scene where the node can be seen: its rect cut by every clipping ancestor."""
    rect, up = scene_rect(node), node.parentItem()
    while up is not None:
        if up.clip():
            rect = rect.intersected(scene_rect(up))
        up = up.parentItem()
    return rect


def covered_texts(window):
    """Texts drawn under a visible vertical scroll bar (R501)."""
    nodes = list(visible_items(window.contentItem()))
    bars = [n for n in nodes if n.inherits("QQuickScrollBar") and n.property("orientation") == Qt.Orientation.Vertical
            and n.property("size") is not None and n.property("size") < 1 and n.width() > 0]
    found = []
    for bar in bars:
        area = scene_rect(bar)
        inner = set(visible_items(bar))
        for node in nodes:
            if node in inner or not node.inherits("QQuickText") or not str(node.property("text") or "").strip():
                continue
            painted = min(node.width(), node.property("contentWidth") or node.width())
            # From the left edge: the texts of a page lie to the left; one set to the right is read as left-set
            # (QQuickText's alignment has no converter in PySide), so a short one there can be missed.
            shown = scene_rect(node, painted).intersected(clip_rect(node))
            overlap = shown.intersected(area)
            if overlap.width() > .5 and overlap.height() > .5:
                found.append((label(bar), str(node.property("text"))[:40].replace("\n", " "), round(overlap.width(), 1)))
    return found


def survey(win, tag, out, covers):
    pump(400)
    for node in visible_items(win.contentItem()):
        if not node.inherits("QQuickFlickable") or node.height() < 40 or node.width() < 40:
            continue
        if node.property("contentHeight") <= node.height() + .5 and node.property("contentWidth") > node.width() + .5:
            continue  # scrolls sideways only
        first, drift = node.property("contentHeight"), []
        for _ in range(8):
            pump(40)
            if abs(node.property("contentHeight") - first) > .5:
                drift.append(round(node.property("contentHeight")))
        out.setdefault((tag, label(node)), []).append(
            (round(node.property("contentHeight") - node.height(), 2), drift))
    for cover in covered_texts(win):
        covers.setdefault(cover, []).append(tag)


def main():
    fixture = pickle.loads(Path(sys.argv[1]).read_bytes())
    sizes = [tuple(int(v) for v in arg.split("x")) for arg in sys.argv[2:]] or [(1600, 900)]
    app = create_app()
    out, covers = {}, {}
    with tempfile.TemporaryDirectory() as temporary:
        host = QuickWindow(fixture["project"], Path(temporary), real_views=True)
        win, bridge = host.window, host.bridge
        try:
            bridge.accept_layout(bridge.session.generation, fixture["results"], fixture["keys"])
            bridge._finished(bridge.session.generation, fixture["energy"], [], {})
            win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            win.resize(*sizes[0])
            win.show()
            result = host.parts.controllers["results"]
            for size in sizes:
                win.resize(*size)
                pump(500)
                for phase in [p["id"] for p in host.shell.phases]:
                    host.shell.trigger("phase_" + phase)
                    pump(600)
                    scroll = next((n for n in visible_items(win.contentItem()) if n.objectName() == "results-scroll"), None)
                    if scroll is None:
                        survey(win, phase, out, covers)
                        continue
                    wait_for(lambda: not result.busy, 60)
                    for index in range(len(scroll.property("tabs") or [])):
                        QMetaObject.invokeMethod(scroll, "select", Q_ARG("QVariant", index))
                        wait_for(lambda i=index, view=scroll: view.property("displayedIndex") == i, 15)
                        pump(300)
                        survey(win, f"{phase}#{index}", out, covers)
                    QMetaObject.invokeMethod(scroll, "select", Q_ARG("QVariant", 0))
                win.setProperty("fileOpen", True)
                pump(500)
                backend = item(win, "filePartLoader").property("item").property("backend")
                for section in FILE_SECTIONS + tuple("preferences:" + s for s in SETTINGS_SECTIONS):
                    backend.selectSection(section)
                    pump(700)
                    survey(win, "file:" + section, out, covers)
                win.setProperty("fileOpen", False)
                pump(300)
            print("sizes", sizes, "scale", win.devicePixelRatio())
            for (tag, name), rows in out.items():
                overs = [r[0] for r in rows]
                mark = "  <== always a little over" if len(overs) == len(sizes) > 1 and all(0 < o < 60 for o in overs) else ""
                if any(0 < o < 1 for o in overs):
                    mark += "  <== a bar for under a pixel"
                drift = [r[1] for r in rows if r[1]]
                if drift:
                    mark += "  <== drift " + str(drift[:2])
                print(f"{tag:28} {name:64} {overs}{mark}")
            print("texts under a bar:", len(covers))
            for (bar, text, width), tags in covers.items():
                print(f"  {bar:64} {width:5} px  «{text}»  in {sorted(set(tags))[:4]}")
            print("warnings", len(host.warnings), host.warnings[:5])
        finally:
            host.close()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()


if __name__ == "__main__":
    main()
