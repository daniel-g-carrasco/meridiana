"""Pagination rules verified against QTextDocument's actual layout, rather than browser-only CSS."""
from PySide6.QtGui import QTextCursor, QTextFormat


def keep_together(doc, groups: list[tuple[int, int]]) -> int:
    """Keep small explicit block ranges on one page. Oversize groups remain splittable, without blank pages."""
    page = doc.pageSize().height()
    margin = doc.rootFrame().frameFormat().topMargin() + doc.rootFrame().frameFormat().bottomMargin()
    moved = 0
    for start, end in groups:
        first, last = doc.findBlock(start), doc.findBlock(end)
        if not first.isValid() or not last.isValid():
            continue
        layout = doc.documentLayout()
        a, b = layout.blockBoundingRect(first), layout.blockBoundingRect(last)
        if int(a.top() // page) == int((b.bottom() - 0.01) // page):
            continue
        height = 0.0
        block = first
        while block.isValid() and block.position() <= last.position():
            fmt = block.blockFormat()
            height += layout.blockBoundingRect(block).height() + max(fmt.topMargin(), fmt.bottomMargin())
            block = block.next()
        if height > page - margin:
            continue
        fmt = first.blockFormat()
        flag = QTextFormat.PageBreakFlag.PageBreak_AlwaysBefore
        if fmt.pageBreakPolicy() & flag:
            continue
        fmt.setPageBreakPolicy(fmt.pageBreakPolicy() | flag)
        QTextCursor(first).setBlockFormat(fmt)
        doc.pageCount()
        moved += 1
    return moved
