"""Quick pedigree rows and on-demand formula rendering outside the GUI thread."""
from __future__ import annotations

import base64
from collections import OrderedDict
import hashlib
import io
import threading

from PySide6.QtCore import QObject, Property, QRunnable, QThreadPool, Signal, Slot
from PySide6.QtGui import QImage

from meridiana.energy.pedigree import Record, kind_names, limits
from meridiana.i18n import _
from meridiana.paths import shipped


_MATH_LOCK = threading.Lock()
_FONTS = shipped("fonts")


def render_formula(tex: str, size: float, color: str, family: str, dpr: float) -> dict:
    """Serialize mathtext's global font state; this function only runs in workers."""
    with _MATH_LOCK:
        import matplotlib
        from matplotlib.font_manager import FontProperties, fontManager
        from matplotlib.mathtext import math_to_image

        # Font registration here does not import the Widgets theme or touch Qt fonts.
        for path in _FONTS.rglob("*.ttf") if _FONTS else ():
            if not any(font.fname == str(path) for font in fontManager.ttflist):
                fontManager.addfont(str(path))
        buf = io.BytesIO()
        with matplotlib.rc_context({"savefig.transparent": True, "mathtext.fontset": "custom",
                                    "mathtext.rm": family, "mathtext.it": family + ":italic",
                                    "mathtext.bf": family + ":bold"}):
            math_to_image(f"${tex}$", buf, prop=FontProperties(family=family, size=size * 72 / 96),
                          dpi=96 * dpr, format="png", color=color)
        data = buf.getvalue()
        image = QImage.fromData(data)
        return dict(source="data:image/png;base64," + base64.b64encode(data).decode("ascii"),
                    width=image.width() / dpr, height=image.height() / dpr, error="")


class _FormulaSignals(QObject):
    ready = Signal(str, "QVariantMap")


class _FormulaJob(QRunnable):
    def __init__(self, key, args):
        super().__init__()
        self.key, self.args = key, args
        self.signals = _FormulaSignals()

    def run(self):
        try:
            result = render_formula(*self.args)
        except Exception as error:
            # The page retains the readable formula and exposes the reason.
            result = dict(source="", width=0, height=0, error=str(error))
        self.signals.ready.emit(self.key, result)


class PedigreeBackend(QObject):
    """Set records in Python; QML asks only for formulas entering its viewport.

    Formula keys include theme and DPR. Late replies cannot replace newer images.
    A bounded per-page cache avoids retaining years of calculation output.
    """

    changed = Signal()
    formulaReady = Signal(str, "QVariantMap")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._cache = OrderedDict()
        self._jobs = {}

    @Property("QVariantList", notify=changed)
    def rows(self):
        return self._rows

    @Property("QVariantMap", notify=changed)
    def labels(self):
        return dict(empty=_("Nothing computed yet."), symbol=_("Symbol"), quantity=_("Quantity"),
                    value=_("Value and unit"), source=_("Source"))

    def show_records(self, records: list[Record]) -> None:
        rows, kinds = [], kind_names()

        def quantity(q, result=False):
            src = q.source
            return dict(kind="quantity", symbol=q.symbol, text=q.label, value=q.text(), result=result,
                        sourceKind=kinds.get(src.kind, src.kind) if src else "",
                        sourceLabel=src.label if src else "", sourceRef=src.ref if src else "")

        for record in records:
            rows.append(dict(kind="record", text=record.title))
            for step in record.steps:
                rows.append(dict(kind="step", text=step.title, key=step.key))
                if step.explanation:
                    rows.append(dict(kind="explanation", text=step.explanation))
                if step.formula:
                    rows.append(dict(kind="formula", text=step.formula))
                if step.inputs or step.result is not None:
                    rows.append(dict(kind="header", text=""))
                    rows.extend(quantity(q) for q in step.inputs)
                    if step.result is not None:
                        rows.append(quantity(step.result, True))
                if step.reference:
                    rows.append(dict(kind="reference", text=_("Reference") + ": " + step.reference))
        if records:
            rows.append(dict(kind="record", text=_("What the model does not include")))
            rows.append(dict(kind="explanation", text=_(
                "The steps above are the whole of the calculation. What it leaves out, and what it only estimates, is "
                "listed here so that the report does not promise it.")))
            rows.extend(dict(kind="limit", text=text) for text in limits())
        self._rows = rows
        self.changed.emit()

    @Slot(str, float, str, str, float, result="QVariantMap")
    def requestFormula(self, tex, size, color, family, dpr):
        args = (tex, size, color, family, max(1.0, dpr))
        key = hashlib.sha256(repr(args).encode("utf-8")).hexdigest()
        if key in self._cache:
            self._cache.move_to_end(key)
            return dict(key=key, **self._cache[key])
        if key not in self._jobs:
            job = _FormulaJob(key, args)
            self._jobs[key] = job
            job.signals.ready.connect(self._ready)
            QThreadPool.globalInstance().start(job)
        return dict(key=key, source="", width=0, height=0, error="")

    @Slot(str, "QVariantMap")
    def _ready(self, key, result):
        self._jobs.pop(key, None)
        self._cache[key] = result
        while len(self._cache) > 512:
            self._cache.popitem(last=False)
        self.formulaReady.emit(key, result)
