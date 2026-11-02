"""Render the pages of a PDF to PNG with QtPdf (already a dependency of Meridiana): the eye's check of a test."""
from PySide6.QtCore import QSize
from PySide6.QtPdf import QPdfDocument


def pages_to_png(pdf: str, prefix: str, pages=(0, 1), width: int = 1000) -> list[str]:
    doc = QPdfDocument()
    doc.load(pdf)
    out = []
    for i in pages:
        if i >= doc.pageCount():
            break
        size = doc.pagePointSize(i)
        image = doc.render(i, QSize(width, round(width * size.height() / size.width())))
        path = f"{prefix}-p{i + 1}.png"
        image.save(path)
        out.append(path)
    return out
