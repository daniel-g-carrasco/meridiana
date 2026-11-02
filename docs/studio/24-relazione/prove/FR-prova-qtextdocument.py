"""Does QTextDocument (today's engine) split a table row between two pages? Lays out FR-prova-righe.html on A4
as report.py does (96 dpi, 2 cm margins), prints it with QPdfWriter, renders pages 1-2 to PNG. Prints the time
and the PDF's weight. Run offscreen from build/claude-r07."""
import sys
import time
from pathlib import Path

from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QFontDatabase, QGuiApplication, QPageLayout, QPageSize, QPainter, QPdfWriter, QTextDocument

HERE = Path(__file__).parent
ROWS = "".join(f"<tr><td>{n}</td><td>Tensione a vuoto della stringa alla temperatura minima del sito, "
               f"confrontata con la tensione massima ammessa dall'inverter (CEI 64-8/7, art. 712.512.1.1)</td>"
               f"<td>{900 + n * 3} V su 1.000 V</td><td>conforme</td></tr>" for n in range(1, 41))


def main() -> None:
    app = QGuiApplication(sys.argv)
    for f in ("Inter-Regular.ttf", "Inter-SemiBold.ttf"):
        QFontDatabase.addApplicationFont(str(HERE.parents[1] / "data" / "fonts" / "inter" / f))
    html = (HERE / "FR-prova-righe.html").read_text(encoding="utf-8").replace("<!--ROWS-->", ROWS)
    t0 = time.perf_counter()
    doc = QTextDocument()
    font = doc.defaultFont()
    font.setFamily("Inter")
    font.setPointSizeF(10.5)
    doc.setDefaultFont(font)
    doc.setHtml(html)
    dpi = 96.0
    size = QPageSize(QPageSize.PageSizeId.A4).size(QPageSize.Unit.Inch)
    page = QSizeF(size.width() * dpi, size.height() * dpi)
    margin = int(2.0 / 2.54 * dpi)
    frame = doc.rootFrame().frameFormat()
    frame.setMargin(margin)
    doc.rootFrame().setFrameFormat(frame)
    doc.setPageSize(page)
    pages = doc.pageCount()
    out = HERE / "FR-prova-qtextdocument.pdf"
    writer = QPdfWriter(str(out))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    writer.setResolution(int(dpi))
    painter = QPainter(writer)
    for i in range(pages):
        if i:
            writer.newPage()
        painter.save()
        painter.translate(0, -i * page.height())
        doc.drawContents(painter)
        painter.restore()
    painter.end()
    dt = time.perf_counter() - t0
    from FR_pdf_png import pages_to_png
    pngs = pages_to_png(str(out), str(HERE / "FR-prova-qtextdocument"))
    print(f"QTextDocument: {pages} pagine, {dt * 1000:.0f} ms, {out.stat().st_size / 1024:.0f} kB, {pngs}")


if __name__ == "__main__":
    main()
