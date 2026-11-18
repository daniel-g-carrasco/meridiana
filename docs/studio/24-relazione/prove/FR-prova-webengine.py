"""Qt WebEngine (Chromium) printing FR-prova-righe.html to PDF with `tr { break-inside: avoid }`: time from the
first import to the PDF, weight of the PDF, pages 1-2 as PNG. Needs the PySide6_WebEngine wheel (in the dev venv,
NOT in Meridiana's requirements). Run offscreen from build/claude-r07."""
import sys
import time
from pathlib import Path

T_IMPORT = time.perf_counter()
from PySide6.QtCore import QMarginsF, QUrl                                       # noqa: E402
from PySide6.QtGui import QPageLayout, QPageSize                                 # noqa: E402
from PySide6.QtWebEngineCore import QWebEnginePage                               # noqa: E402
from PySide6.QtWidgets import QApplication                                       # noqa: E402

HERE = Path(__file__).parent
ROWS = "".join(f"<tr><td>{n}</td><td>Tensione a vuoto della stringa alla temperatura minima del sito, "
               f"confrontata con la tensione massima ammessa dall'inverter (CEI 64-8/7, art. 712.512.1.1)</td>"
               f"<td>{900 + n * 3} V su 1.000 V</td><td>conforme</td></tr>" for n in range(1, 41))


def main() -> None:
    source = sys.argv[1] if len(sys.argv) > 1 else ""
    app = QApplication(sys.argv)
    t_app = time.perf_counter()
    if source:
        html = Path(source).read_text(encoding="utf-8")
        base = QUrl.fromLocalFile(str(Path(source).resolve()))
        out = HERE / f"FR-prova-webengine-{Path(source).stem}.pdf"
    else:
        html = (HERE / "FR-prova-righe.html").read_text(encoding="utf-8").replace("<!--ROWS-->", ROWS)
        base = QUrl.fromLocalFile(str(HERE) + "/")
        out = HERE / "FR-prova-webengine.pdf"
    page = QWebEnginePage()
    layout = QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
                         QMarginsF(20, 20, 20, 20), QPageLayout.Unit.Millimeter)
    if source:
        layout.setMargins(QMarginsF(0, 0, 0, 0))

    def loaded(ok: bool) -> None:
        page.printToPdf(str(out), layout)

    def printed(path: str, ok: bool) -> None:
        dt = time.perf_counter() - T_IMPORT
        from FR_pdf_png import pages_to_png
        pngs = pages_to_png(str(out), str(out.with_suffix("")))
        print(f"WebEngine: ok={ok}, {dt * 1000:.0f} ms dall'import (app pronta dopo {(t_app - T_IMPORT) * 1000:.0f} ms), "
              f"{out.stat().st_size / 1024:.0f} kB, {pngs}")
        app.quit()

    page.loadFinished.connect(loaded)
    page.pdfPrintingFinished.connect(printed)
    page.setHtml(html, base)
    app.exec()


if __name__ == "__main__":
    main()
