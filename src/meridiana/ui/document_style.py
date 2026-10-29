"""Readable technical text for Qt rich text, on screen and on paper.

Use only QTextDocument's supported CSS subset. Margins and padding are pixels;
type on paper is in points. Application themes provide colours, not layout.
"""


def css(*, ink: str, muted: str, rule: str, head: str, paper: bool = False) -> str:
    unit = 'pt' if paper else 'px'
    sizes = (23, 15, 11.5, 10.5) if paper else (24, 20, 16, 14)
    out = [f'body {{ color: {ink}; }}',
           'p { margin-top: 0px; margin-bottom: 8px; line-height: 125%; }',
           'li { margin-top: 4px; margin-bottom: 4px; }',
           'ul, ol { margin-top: 4px; margin-bottom: 12px; }']
    for level, size in enumerate(sizes, 1):
        before = 0 if level == 1 else (24 if level == 2 else 16)
        out.append(f'h{level} {{ font-size: {size}{unit}; font-weight: 600; '
                   f'margin-top: {before}px; margin-bottom: 8px; }}')
    out += ['table.grid { border-collapse: collapse; margin-top: 6px; margin-bottom: 12px; }',
            f'table.grid th {{ background-color: {head}; font-weight: 600; border-bottom: 1px solid {rule}; }}',
            f'table.grid td {{ border-bottom: 1px solid {rule}; }}',
            'table.grid th, table.grid td { padding: 6px 8px; vertical-align: top; }',
            f'.muted, .caption, td.label {{ color: {muted}; }}',
            'table.facts { margin-bottom: 12px; }',
            f'.result {{ background-color: {head}; font-weight: 600; }}',
            '.formula { margin-top: 12px; margin-bottom: 12px; }']
    return '\n'.join(out)
