#!/usr/bin/env python3
"""Show the procedural props in Meridiana's 3D view and optionally capture all review pictures."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from meridiana import layout, mesh, props, roofs  # noqa: E402


def _join(parts):
    return tuple(np.concatenate([part[index] for part in parts]).astype(np.float32) for index in range(3))


def _placed(shape, x, z, y=0.0):
    pos, nor, col = shape
    offset = np.array((x, y, z), dtype=np.float32)
    return pos + offset, nor, col


def _box(width, depth, z0, z1, colour, x=0.0, z=0.0):
    ring = ((-width / 2, -depth / 2), (width / 2, -depth / 2),
            (width / 2, depth / 2), (-width / 2, depth / 2))
    return _placed(mesh.prism_triangles(ring, z0, z1, colour), x, z)


def _grid(x0, x1, z0, z1):
    segments = []
    for x in range(int(x0), int(x1) + 1):
        segments.append(((x, 0.008, z0), (x, 0.008, z1)))
    for z in range(int(z0), int(z1) + 1):
        segments.append(((x0, 0.008, z), (x1, 0.008, z)))
    return mesh.ribbons(np.asarray(segments), 0.015, (0.48, 0.53, 0.43))


def lineup_scene():
    """Every prop in category rows, with a one-metre grid and the two scale references."""
    parts = [_grid(-24, 24, -14, 14)]
    for index, kind in enumerate(props.TREE_KINDS):
        shape = props.tree(kind, rotation=index * 17.0)
        parts.append(_placed(shape, -16 + index * 8, -9))
    for index, kind in enumerate(props.OBSTACLE_KINDS):
        shape = props.obstacle(kind, rotation=(index % 4) * 15.0)
        parts.append(_placed(shape, -18 + index * 3, 0))
    for index, kind in enumerate(props.PERSON_KINDS):
        parts.append(_placed(props.person(kind), -10 + index * 4, 9))
    parts.append(_placed(props.car("compact", rotation=-12), 9, 9))
    parts.append(_placed(props.car("suv", rotation=12), 16, 9))
    parts.append(_box(4.0, 0.20, 0.0, 2.0, mesh.WALL, -20, 9))
    parts.append(_box(1.13, 0.035, 0.0, 2.28, mesh.MODULE, -16, 9))
    return _join(parts), np.zeros((0, 20), dtype=np.float32)


def _modules(centres, z, tilt):
    placed = [layout.PlacedModule(row=row, slot=slot, group=0, corners=[], centre=centre, z=z,
                                  tilt=tilt, azimuth=0.0)
              for row, slot, centre in centres]
    return mesh.module_table(placed, along=1.13, across=2.28)


def realistic_scene():
    """A shed with photovoltaic modules, trees, people and two cars under a covered parking bay."""
    footprint = [(-20.0, -6.0), (2.0, -6.0), (2.0, 6.0), (-20.0, 6.0)]
    parts = [mesh.building_triangles(footprint, roofs.flat(footprint, 5.0))]
    roof_centres = [(row, slot, (-17 + slot * 4.0, -4.0 + row * 2.6))
                    for row in range(4) for slot in range(5)]
    canopy_centres = [(row, slot, (10.5 + slot * 2.5, -1.5 + row * 3.0))
                      for row in range(2) for slot in range(3)]
    table = np.concatenate((_modules(roof_centres, 5.15, 20.0), _modules(canopy_centres, 3.15, 0.0)))

    parts.append(_box(10.0, 8.0, 2.85, 3.0, mesh.ROOF_FLAT, 13, -1))
    for x in (8.5, 17.5):
        for z in (-4.5, 2.5):
            parts.append(_box(0.18, 0.18, 0.0, 2.85, mesh.OBSTACLE, x, z))
    parts.append(_placed(props.obstacle("plant"), -15, 0, 5.0))
    parts.append(_placed(props.obstacle("chimney"), -5, 2, 5.0))
    for kind, x, z, rotation in (("broadleaf", -25, 4, 0), ("conifer", -24, -6, 0),
                                 ("palm", 23, -6, 20), ("shrub", 5, 4, 0)):
        parts.append(_placed(props.tree(kind, rotation=rotation), x, z))
    for kind, x, z, rotation in (("adult", -1, 9, 15), ("walking", 2, 10, -20),
                                 ("child", 1, 11, 0), ("worker", 6, 8, 45)):
        parts.append(_placed(props.person(kind, rotation=rotation), x, z))
    parts.append(_placed(props.car("compact", colours={"car": (0.55, 0.62, 0.67)}), 11, 1))
    parts.append(_placed(props.car("suv", colours={"car": (0.47, 0.55, 0.42)}), 15, -3))
    return _join(parts), table.astype(np.float32)


def shot_jobs():
    """The twelve captures in Gallery.apply's theme, scene and viewpoint order."""
    return [(theme, scene, view) for scene in ("galleria", "realistica") for theme in ("light", "dark")
            for view in ("assonometrica", "fronte", "alto")]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", action="store_true", help="Capture both scenes, themes and three viewpoints")
    parser.add_argument("--output", type=Path, default=ROOT / "docs" / "revisioni" / "foto" / "oggetti-3d")
    parser.add_argument("--scene", choices=("galleria", "realistica"), default="galleria")
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    parser.add_argument("--view", choices=("assonometrica", "fronte", "alto"), default="assonometrica")
    args = parser.parse_args()
    os.environ.setdefault("QML_DISABLE_DISK_CACHE", "1")
    os.environ.setdefault("QT_DISABLE_SHADER_DISK_CACHE", "1")

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

    from meridiana import camera
    from meridiana.config import Config
    from meridiana.ui import design
    from meridiana.ui.theme import Theme
    from meridiana.ui.view3d import View3D

    app = QApplication([])
    app.setApplicationName("Meridiana props gallery")

    class Gallery(QWidget):
        def __init__(self):
            super().__init__()
            self.setObjectName("props-gallery")
            self.setWindowTitle("Meridiana, oggetti 3D")
            column = QVBoxLayout(self)
            column.setContentsMargins(12, 12, 12, 12)
            self.caption = QLabel()
            design.set_text(self.caption, design.Text.HEADING)
            column.addWidget(self.caption)
            self.view = View3D()
            self.view.fitted = True
            self.view.cube.hide()
            self.view.marks.hide()
            column.addWidget(self.view, 1)
            self.resize(1600, 1000)

        def apply(self, theme_name, scene_name, view_name):
            theme = Theme(Config(theme=theme_name, background="none"), app=app)
            self.setStyleSheet(f"QWidget#props-gallery {{ background: {theme.tokens['panel']}; }}")
            shape, table = lineup_scene() if scene_name == "galleria" else realistic_scene()
            self.view.show_scene(shape, table)
            bearings = {"assonometrica": (35.0, -32.0), "fronte": (0.0, -12.0), "alto": (0.0, -90.0)}
            aspect = max(self.view.width(), 1) / max(self.view.height(), 1)
            self.view.backend.camera = camera.axonometric(shape[0], *bearings[view_name], aspect, margin=0.04)
            self.view.backend.cameraChanged.emit()
            self.view.backend.changed.emit()
            self.view.set_sun(42.0, 135.0)
            self.view._changed()
            scene_text = "Oggetti e riferimenti di scala" if scene_name == "galleria" else "Capannone e parcheggio"
            theme_text = "chiaro" if theme_name == "light" else "scuro"
            self.caption.setText(f"{scene_text} | {view_name} | tema {theme_text}")

    window = Gallery()
    window.show()
    if not args.shots:
        window.apply(args.theme, args.scene, args.view)
        return app.exec()

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    jobs = shot_jobs()
    failures = []

    def capture(index):
        if not window.view.drawn() or window.view.image.isNull():
            failures.append("the 3D view produced no image")
        else:
            theme, scene, view = jobs[index]
            name = f"{scene}-{'chiaro' if theme == 'light' else 'scuro'}-{view}.png"
            path = output / name
            if not window.grab().save(str(path)):
                failures.append(f"could not save {path}")
            else:
                print(path, flush=True)
        advance(index + 1)

    def advance(index):
        if failures or index == len(jobs):
            app.exit(1 if failures else 0)
            return
        window.apply(*jobs[index])
        QTimer.singleShot(700, lambda: capture(index))

    QTimer.singleShot(300, lambda: advance(0))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
