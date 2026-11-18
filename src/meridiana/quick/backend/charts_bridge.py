"""Small QML boundary: prepare on first display, export on request, lazy formulas."""
from __future__ import annotations

import io
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from threading import Lock

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtGui import QImage
from PySide6.QtQml import qmlRegisterType

from meridiana.i18n import _, language
from . import charts_scene

_FORMULAS = ThreadPoolExecutor(max_workers=1, thread_name_prefix="quick-formulas")
_FONT_LOCK = Lock()
_FORMULA_FONTS_READY = False


def _register_formula_fonts():
    """Register distributed faces once, including when the theme already loaded them."""
    global _FORMULA_FONTS_READY
    with _FONT_LOCK:
        if _FORMULA_FONTS_READY:
            return
        from matplotlib import font_manager
        known = {Path(entry.fname).resolve() for entry in font_manager.fontManager.ttflist}
        from meridiana.paths import shipped
        fonts = shipped("fonts")        # data/ in a checkout, share/ in the Windows package
        for path in (fonts.rglob("*.ttf") if fonts else ()):
            if path.resolve() not in known:
                font_manager.fontManager.addfont(str(path))
                known.add(path.resolve())
        _FORMULA_FONTS_READY = True


@lru_cache(maxsize=512)
def _formula(tex, color, family, size, scale):
    import matplotlib
    from matplotlib.font_manager import FontProperties
    from matplotlib.mathtext import math_to_image
    _register_formula_fonts()
    output = io.BytesIO()
    with matplotlib.rc_context({"savefig.transparent": True, "mathtext.fontset": "custom",
                                "mathtext.rm": family, "mathtext.it": family+":italic",
                                "mathtext.bf": family+":bold"}):
        math_to_image("$"+tex+"$", output, prop=FontProperties(family=family, size=size),
                      dpi=100*scale, format="png", color=color)
    return charts_scene.image_url(QImage.fromData(output.getvalue(), "PNG"))


class ChartServices(QObject):
    formulaReady = Signal(str, str, str)
    errorOccurred = Signal(str)
    italian = Property(bool, lambda self: language() == 'it', constant=True)

    @Property("QVariantMap", constant=True)
    def labels(self):
        return {key: _(value) for key, value in dict(graph="Chart", table="Table", svg="Save SVG…",
                png="Save PNG…", all="Show all", total="Total", calculate="Compute", empty="Nothing computed yet.",
                source="Source", reference="Reference", symbol="Symbol", quantity="Quantity", value="Value and unit",
                how="How it is computed", preparing="Preparing…", chooseBattery="Choose battery…",
                where="where:", withValues="With the values:", result="result").items()}

    @Property("QVariantList", constant=True)
    def lightSeries(self):
        return charts_scene.SERIES[False]

    @Property("QVariantList", constant=True)
    def darkSeries(self):
        return charts_scene.SERIES[True]

    @Property("QVariantList", constant=True)
    def sequential(self):
        """The heat maps' ramp, light to dark (the scale beside the map, R494)."""
        return charts_scene.SEQUENTIAL

    @Slot("QVariantMap", result="QVariantMap")
    def prepare(self, data):
        return charts_scene.prepare(data)

    @Slot("QVariantMap", QUrl, str, "QVariantList", float, float, result=bool)
    def exportChart(self, data, url, family, hidden, view_start=0., view_end=1.):
        try:
            charts_scene.export_chart(data, url.toLocalFile(), family=family, hidden=hidden,
                                      view_start=view_start, view_end=view_end)
        except (ValueError, OSError, RuntimeError) as error:
            self.errorOccurred.emit(str(error))
            return False
        return True

    @Slot(str, str, str, str, float, float)
    def requestFormula(self, key, tex, color, family, size, scale):
        future = _FORMULAS.submit(_formula, tex, color, family, size, scale)

        def ready(done):
            try:
                url, error = done.result(), ""
            except (ValueError, RuntimeError, OSError) as exc:
                url, error = "", str(exc)
            # The worker can finish after its page was closed.
            import shiboken6
            if shiboken6.isValid(self):
                self.formulaReady.emit(key, url, error)
        future.add_done_callback(ready)


_REGISTERED = False


def register():
    global _REGISTERED
    if not _REGISTERED:
        qmlRegisterType(ChartServices, "Meridiana.ChartBackend", 1, 0, "ChartServices")
        _REGISTERED = True
