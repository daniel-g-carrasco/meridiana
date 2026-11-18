"""One real 3D picture from the program for the sketches: ui/report_3d.py's windowless renderer (QQuickRenderControl,
needs a real GPU platform, not offscreen) on a test project shaped like the sketches (a 120 x 40 m shed, 30 deg
rows, an office block beside it). Two versions: the program's ReportScene.qml as it is, and a copy with ambient
occlusion turned on (nothing of the program is changed: the module's QML_FILE is pointed at the copy). No window is
shown. Output: docs/studio/24-relazione/foto/render-*.png. Run with the default platform (QT_QPA_PLATFORM unset)."""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "src")]
OUT = ROOT / "docs" / "studio" / "24-relazione" / "foto"
SIZE = (2200, 1440)


def project():
    from meridiana import model
    p = model.Project(name="Bozzetto")
    p.site = model.Site(lat=45.5226, lon=9.0300, address="Rho (MI)")
    shed = model.Building(id=p.new_id("b"), name="Capannone C1", footprint=[[0, 0], [120, 0], [120, 40], [0, 40]],
                          height=9.5)
    office = model.Building(id=p.new_id("b"), name="Uffici", footprint=[[124, 4], [146, 4], [146, 22], [124, 22]],
                            height=7.0)
    p.buildings += [shed, office]
    p.subfields.append(model.SubField(id=p.new_id("s"), name="Sud", ring=[[2, 1.5], [118, 1.5], [118, 38.5], [2, 38.5]],
                                      building=shed.id, params={"tilt": 30.0}, filled=True))
    return p


def main() -> None:
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from meridiana import jobs
    from meridiana.ui import report_3d
    p = project()
    results, _keys, _laid = jobs.layout_of(p)
    n = sum(len(getattr(r, "modules", []) or []) for r in results.values())
    print("modules laid:", n)
    OUT.mkdir(parents=True, exist_ok=True)
    for tag, qml in (("base", None), ("ao", HERE / "FR-ReportSceneAO.qml")):
        if qml is not None:
            src = report_3d.QML_FILE.read_text(encoding="utf-8")
            src = src.replace("antialiasingQuality: SceneEnvironment.VeryHigh",
                              "antialiasingQuality: SceneEnvironment.VeryHigh\n"
                              "            aoStrength: 100; aoDistance: 400.0; aoSoftness: 50; aoSampleRate: 4; aoDither: true")
            qml.write_text(src, encoding="utf-8")
            report_3d.release()
            report_3d._RENDERER = None
            report_3d.QML_FILE = qml
            report_3d._CACHE.clear()
        t0 = time.perf_counter()
        pictures = report_3d.render(p, results, SIZE)
        dt = time.perf_counter() - t0
        if not pictures:
            print(tag, "nothing rendered (Qt Quick 3D without a renderer here?)")
            continue
        for vid, png in pictures.items():
            path = OUT / f"render-{tag}-{vid}.png"
            path.write_bytes(png)
            print(tag, vid, f"{len(png) / 1024:.0f} kB", path)
        print(tag, f"{dt * 1000:.0f} ms for {len(pictures)} views at {SIZE}")
    report_3d.release()
    app.quit()


if __name__ == "__main__":
    main()
