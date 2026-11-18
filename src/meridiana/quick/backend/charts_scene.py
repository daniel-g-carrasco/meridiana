"""Retained chart coordinates and paper export. No Widgets or plotting library."""
from __future__ import annotations

import base64
import math
from pathlib import Path

import numpy as np
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QPointF, QRectF, QSize, QSizeF
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPainterPathStroker, QPen, QPolygonF
from PySide6.QtSvg import QSvgGenerator

from meridiana.i18n import number
from meridiana import theme_colors

# R494 (Daniel 06/11/2026, style B «Terra e talpa»): terracotta, dark sage, ochre; slot 8, the negative steps of
# «changes» beside the terracotta ones, a slate blue (the study's red failed against the terracotta: normal vision
# 12.5 light, 8.4 dark, under 15); the others as before. Checked with the dataviz skill's validator, the first three
# on #fcfcfb and #1a1a19 and slot 8 against the first: pass in both modes (ochre 2.88:1 on light: the table and the
# legend carry it). The heat maps in one ramp of the same earth, light to dark. The report keeps its own colours
# (report_typst/look.py).
SERIES = {False: ["#a4532c", "#1f8b72", "#c88a1c", "#eda100", "#e87ba4", "#008300", "#6250d6", "#3a6aa8"],
          True: ["#c4633a", "#1f9a82", "#b08a1c", "#c98500", "#d55181", "#008300", "#9085e9", "#5d8fd0"]}
SEQUENTIAL = ["#f4efe6", "#eee2d7", "#e7d4c6", "#e0c5b2", "#d9b49c", "#d1a180", "#c98a5a",
              "#bb8053", "#ac744b", "#9b6742", "#875836", "#6d4428", "#4a2410"]


def finite(value):
    return value is not None and math.isfinite(float(value))


def palette(dark=False, accent="indigo", background="grey"):
    t = theme_colors.derive(theme_colors.PRESETS[accent], dark, background).tokens
    chart = t.get("chart", {})
    return dict(surface=chart.get("surface", t["view"]), ink=t["text"], ink2=t["text2"], muted=t["muted"],
                grid=chart.get("grid", t["line_soft"]), axis=chart.get("axis", t["line"]),
                accent=t["accent"], series=SERIES[bool(dark)], sequential=SEQUENTIAL)


def image_url(image):
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(bytes(data)).decode("ascii")


def image_bytes(url):
    return base64.b64decode(url.split(",", 1)[1])


def _linear_ticks(lo, hi, decimals=0, count=5):
    raw = max((hi-lo)/count, 1e-12)
    decade = 10**math.floor(math.log10(raw))
    step = next(v for v in (1, 2, 2.5, 5, 10) if v*decade >= raw)*decade
    digits = max(decimals, 0)
    while digits < 8 and not math.isclose(step*10**digits, round(step*10**digits), abs_tol=1e-8):
        digits += 1
    return [(value, number(value, digits, grouping=True))
            for i in range(math.ceil(lo/step), math.floor(hi/step)+1) if finite(value := i*step)]


def _ticks(lo, hi, decimals):
    return [dict(position=(hi-value)/(hi-lo), label=label) for value, label in _linear_ticks(lo, hi, decimals)]


def prepare(data):
    """Build canonical coordinates once. Resizing and zoom transform them in QML."""
    kind = data.get("kind", "message")
    result = dict(kind=kind, layers=[], xticks=[], yticks=[], xmin=0., xmax=1., ymin=0., ymax=1.,
                  left=64, rows=0, columns=0, image="", zero=1., mark=None)
    series = data.get("series", [])
    decimals = data.get("decimals", 0)
    if kind == "message":
        return result
    if kind == "heatmap":
        m = np.array(data.get("matrix", []), dtype=float)
        if m.ndim != 2 or not m.size:
            return result
        nr, nc = m.shape
        good = m[np.isfinite(m)]
        lo, hi = (float(good.min()), float(good.max())) if good.size else (0., 1.)
        hi = hi if hi > lo else lo + 1
        ramp = np.array([[QColor(c).red(), QColor(c).green(), QColor(c).blue()] for c in SEQUENTIAL])
        level = np.clip(np.nan_to_num((m-lo)/(hi-lo), nan=0), 0, 1) * (len(ramp)-1)
        ix = np.minimum(level.astype(int), len(ramp)-2)
        rgba = np.empty((nr, nc, 4), dtype=np.uint8)
        rgba[:, :, :3] = ramp[ix]*(1-(level-ix)[:, :, None]) + ramp[ix+1]*(level-ix)[:, :, None]
        rgba[:, :, 3] = np.where(np.isfinite(m), 255, 0)
        image = QImage(rgba.data, nc, nr, nc*4, QImage.Format.Format_RGBA8888).copy()
        cols, rows = data.get("cols", []), data.get("rows", [])
        xt = data.get("ticks") or [(j, cols[j]) for j in range(0, nc, max(1, nc//12))]
        yt = data.get("row_ticks") or list(enumerate(rows))
        result.update(image=image_url(image), columns=nc, rows=nr, xmin=-.5, xmax=nc-.5, ymin=lo, ymax=hi,
                      xticks=[dict(position=(j+.5)/nc, label=s) for j, s in xt],
                      yticks=[dict(position=(i+.5)/nr, label=s) for i, s in yt])
        return result
    categories = data.get("categories", [])
    if kind == "changes":
        values = series[0][1] if series else []
        good = [float(v) for v in values if finite(v)] or [0.]
        lo, hi = min(0., min(good)), max(0., max(good))
        room = .2*max(hi-lo, .1)
        lo, hi = lo-room if lo < 0 else -.05*room, hi+room if hi > 0 else .05*room
        n = max(1, len(values))
        rects = []
        for i, value in enumerate(values):
            if finite(value):
                a, b = (min(0, value)-lo)/(hi-lo), (max(0, value)-lo)/(hi-lo)
                rects.append(dict(x=a, y=(i+.3)/(n+.2), width=b-a, height=.6/(n+.2), value=value, index=i,
                                  slot=0 if value >= 0 else 7))
        result.update(xmin=lo, xmax=hi, left=220, zero=(0-lo)/(hi-lo),
                      layers=[dict(name="", rects=rects, paths=[])],
                      yticks=[dict(position=(i+.6)/(n+.2), label=c) for i, c in enumerate(categories)],
                      xticks=[dict(position=(v-lo)/(hi-lo), label=label+data.get("unit", ""))
                              for v, label in _linear_ticks(lo, hi)])
        return result
    stacked = data.get("stacked", False)
    good = [float(v) for _, values in series for v in values if finite(v)] or [0.]
    lo, hi = min(good), max(good)
    if kind == "bars":
        n = len(categories)
        bottom = [0.]*n
        extents = [0.]
        for _, values in series:
            for j, v in enumerate(values[:n]):
                if finite(v):
                    extents.extend([bottom[j] if stacked else 0, (bottom[j] if stacked else 0)+v])
                    if stacked:
                        bottom[j] += v
        lo, hi = min(extents), max(extents)
        hi = hi*1.05 if hi > lo else lo+1
        xmin, xmax = -.6, max(n, 1)-.4
        result.update(xmin=xmin, xmax=xmax, ymin=lo, ymax=hi)
        bottom = [0.]*n
        count = max(1, len(series))
        width = .7 if stacked or count == 1 else .8/count
        for k, (name, values) in enumerate(series):
            rects = []
            for j, value in enumerate(values[:n]):
                if not finite(value):
                    continue
                x = j if stacked else j-.4+width*(k+.5)
                y0 = bottom[j] if stacked else 0.
                w = width if stacked else width*.92
                rects.append(dict(x=(x-w/2-xmin)/(xmax-xmin), y=(hi-max(y0,y0+value))/(hi-lo),
                                  width=w/(xmax-xmin), height=abs(value)/(hi-lo), value=value, index=j, slot=k%8))
                if stacked:
                    bottom[j] += value
            result["layers"].append(dict(name=name, rects=rects, paths=[]))
        result["xticks"] = [dict(position=(j-xmin)/(xmax-xmin), label=cat) for j, cat in enumerate(categories)]
    elif kind == "line":
        xs = data.get("xs", [])
        xmin, xmax = (min(xs), max(xs)) if xs else (0., 1.)
        if xmax <= xmin:
            xmax = xmin+1
        pad = 0 if len(xs) > 100 else .03*(xmax-xmin)
        xmin, xmax = xmin-pad, xmax+pad
        if data.get("mark_zero", True) or data.get("area", True):
            lo, hi = min(lo, 0.), max(hi, 0.)
        room = .06*((hi-lo) or 1.)
        lo, hi = lo-(room if lo < 0 else 0), hi+room
        result.update(xmin=xmin, xmax=xmax, ymin=lo, ymax=hi)
        for k, (name, values) in enumerate(series):
            paths, path = [], []
            for x, y in zip(xs, values, strict=True):
                if finite(y) and finite(x):
                    path.append(dict(x=(x-xmin)/(xmax-xmin), y=(hi-y)/(hi-lo)))
                elif path:
                    paths.append(path)
                    path = []
            if path:
                paths.append(path)
            result["layers"].append(dict(name=name, rects=[], paths=paths, slot=k%8))
        ticks = data.get("ticks") or _linear_ticks(xmin, xmax, count=6)
        result["xticks"] = [dict(position=(x-xmin)/(xmax-xmin), label=s) for x, s in ticks]
        mark = data.get("mark")
        if mark:
            result["mark"] = dict(position=(mark[0]-xmin)/(xmax-xmin), label=mark[1])
    result["zero"] = hi/(hi-lo)
    result["yticks"] = _ticks(lo, hi, decimals)
    return result


def export_chart(data, path, *, family="IBM Plex Sans", width=1600, hidden=(), view_start=0., view_end=1.):
    """Export the visible x range in light colours, preserving the full y scale."""
    path = Path(path)
    if path.suffix.lower() not in (".png", ".svg"):
        raise ValueError("Expected .png or .svg")
    prepared = prepare(data)
    if not finite(view_start) or not finite(view_end) or not 0 <= view_start < view_end <= 1:
        raise ValueError("Expected 0 <= view_start < view_end <= 1")
    if data.get("kind") != "line":
        view_start, view_end = 0., 1.
    span = view_end-view_start
    height = max(800, 110+len(data.get("categories", []))*30) if data.get("kind") == "changes" else 900
    if path.suffix.lower() == ".svg":
        device = QSvgGenerator()
        device.setFileName(str(path))
        device.setSize(QSize(width, height))
        device.setViewBox(QRectF(0, 0, width, height))
        device.setTitle(data.get("title", ""))
    else:
        device = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(device)
    if not p.isActive():
        raise OSError(f"Cannot write {path}")
    colors = palette(False)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(QRectF(0, 0, width, height), QColor(colors["surface"]))
    font = QFont(family)
    font.setPixelSize(18)
    p.setFont(font)
    p.setPen(QColor(colors["ink"]))
    p.drawText(QPointF(28, 35), data.get("title", ""))
    font.setPixelSize(14)
    p.setFont(font)
    left = max(prepared["left"], max((QFontMetricsF(font).horizontalAdvance(t["label"])+20 for t in prepared["yticks"]), default=64))
    plot = QRectF(left+18, 100, width-left-80, height-190)
    boundary = QPainterPath()
    boundary.addRect(plot)
    def point(x, y):
        return QPointF(plot.left()+x*plot.width(), plot.top()+y*plot.height())
    def data_point(x, y):
        return point((x-view_start)/span, y)
    for tick in prepared["yticks"]:
        at = point(0, tick["position"])
        p.setPen(QPen(QColor(colors["grid"]), 1))
        if data.get("kind") not in ("changes", "heatmap"):
            p.drawLine(at, point(1, tick["position"]))
        p.setPen(QColor(colors["ink2"]))
        p.drawText(QRectF(4, at.y()-14, plot.left()-12, 28), 0x82, tick["label"])
    for tick in prepared["xticks"]:
        if view_start <= tick["position"] <= view_end:
            at = data_point(tick["position"], 1)
            p.drawText(QRectF(at.x()-60, at.y()+12, 120, 26), 0x84, tick["label"])
    p.drawText(QPointF(plot.left(), 76), data.get("unit", ""))
    for index, layer in enumerate(prepared["layers"]):
        if layer["name"] in hidden:
            continue
        color = QColor(colors["series"][index%8])
        for rect in layer["rects"]:
            p.fillRect(QRectF(point(rect["x"], rect["y"]), QSizeF(rect["width"]*plot.width(), rect["height"]*plot.height())),
                       QColor(colors["series"][rect["slot"]]))
            if data.get("kind") == "changes":
                value = number(rect["value"], 1)+data.get("unit", "")
                at = point(rect["x"]+(rect["width"] if rect["value"] >= 0 else 0), rect["y"]+rect["height"]/2)
                p.setPen(QColor(colors["ink2"]))
                at.setX(at.x()+6 if rect["value"] >= 0 else at.x()-QFontMetricsF(font).horizontalAdvance(value)-6)
                p.drawText(at, value)
        for path_points in layer["paths"]:
            polygon = QPolygonF([data_point(v["x"], v["y"]) for v in path_points])
            # Intersect vector geometry explicitly: SVG consumers must get the same crop as PNG.
            p.save()
            p.setClipRect(plot)
            if data.get("area", True) and len(prepared["layers"]) == 1 and len(data.get("xs", [])) <= 400 and path_points:
                fill = QColor(color)
                fill.setAlphaF(.10)
                area = QPainterPath()
                area.addPolygon(QPolygonF([data_point(path_points[0]["x"], prepared["zero"]), *list(polygon),
                                          data_point(path_points[-1]["x"], prepared["zero"])]))
                area.closeSubpath()
                p.fillPath(area.intersected(boundary), fill)
            line_path = QPainterPath()
            if polygon:
                line_path.moveTo(polygon[0])
                for at in list(polygon)[1:]:
                    line_path.lineTo(at)
            stroke = QPainterPathStroker()
            stroke.setWidth(1 if len(data.get("xs", [])) > 400 else 2)
            p.fillPath(stroke.createStroke(line_path).intersected(boundary), color)
            if data.get("markers"):
                for at in polygon:
                    marker = QPainterPath()
                    marker.addEllipse(at, 3.5, 3.5)
                    p.fillPath(marker.intersected(boundary), color)
            p.restore()
    if prepared["image"]:
        p.drawImage(plot, QImage.fromData(image_bytes(prepared["image"])))
        from PySide6.QtGui import QLinearGradient
        gradient = QLinearGradient(plot.right()+20, plot.top(), plot.right()+20, plot.bottom())
        for i, c in enumerate(reversed(SEQUENTIAL)):
            gradient.setColorAt(i/(len(SEQUENTIAL)-1), QColor(c))
        p.fillRect(QRectF(plot.right()+15,plot.top(),12,plot.height()),gradient)
        p.setPen(QColor(colors["ink2"]))
        for at, val in ((0, prepared["ymax"]), (1, prepared["ymin"])):
            p.drawText(QPointF(plot.right()+32,plot.top()+at*plot.height()),number(val,data.get("decimals",1)))
    if prepared["mark"] and view_start <= prepared["mark"]["position"] <= view_end:
        mark = prepared["mark"]
        p.setPen(QPen(QColor(colors["ink2"]),1))
        p.drawLine(data_point(mark["position"],0),data_point(mark["position"],1))
        p.drawText(data_point(mark["position"]+.01*span,.02),mark["label"])
    p.setPen(QColor(colors["ink2"]))
    p.drawText(QPointF(plot.left(), height-44), data.get("xlabel", ""))
    p.drawText(QPointF(28, height-16), data.get("source", ""))
    x = plot.left()
    for i, (name, _) in enumerate(data.get("series", [])):
        if name in hidden:
            continue
        p.fillRect(QRectF(x, 54, 14, 5), QColor(colors["series"][i%8]))
        p.drawText(QPointF(x+22, 63), name)
        x += QFontMetricsF(font).horizontalAdvance(name)+48
    p.end()
    if isinstance(device, QImage) and not device.save(str(path)):
        raise OSError(f"Cannot write {path}")
