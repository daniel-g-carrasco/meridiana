"""Readable technical text for Qt rich text, on screen and on paper.

Use only QTextDocument's supported CSS subset. Margins and padding are pixels;
type on paper is in points. Application themes provide colours, not layout.

On paper (R291) the hierarchy is four clear steps (23, 16, 12, 10.5 pt, all semibold), each level with less room
above it than the one before; the tables are a point smaller than the text, with tight cells, a header row on a
light ground and a hairline under every row; a highlighted row (`tr.result`) stands for the result of a step or
the row the reader is in; a group row (`td.group`) names the rows that follow.
"""


def css(*, ink: str, muted: str, rule: str, head: str, paper: bool = False) -> str:
    unit = 'pt' if paper else 'px'
    sizes = (23, 16, 12, 10.5) if paper else (24, 20, 16, 14)
    above = (0, 24, 18, 14)                              # px above a heading of each level
    below = (8, 8, 6, 4)
    out = [f'body {{ color: {ink}; }}',
           'p { margin-top: 0px; margin-bottom: 8px; line-height: 125%; }',
           'li { margin-top: 4px; margin-bottom: 4px; }',
           'ul, ol { margin-top: 4px; margin-bottom: 12px; }']
    for level, size in enumerate(sizes, 1):
        out.append(f'h{level} {{ font-size: {size}{unit}; font-weight: 600; '
                   f'margin-top: {above[level - 1]}px; margin-bottom: {below[level - 1]}px; }}')
    cell = 'padding: 4px 6px;' if paper else 'padding: 6px 8px;'
    small = ' font-size: 9.5pt;' if paper else ''
    out += ['table.grid { border-collapse: collapse; margin-top: 4px; margin-bottom: 14px; }',
            f'table.grid th {{ background-color: {head}; font-weight: 600; border-bottom: 1px solid {rule}; }}',
            f'table.grid td {{ border-bottom: 1px solid {rule}; }}',
            f'table.grid th, table.grid td {{ {cell} vertical-align: top;{small} }}',
            f'table.grid td.group {{ font-weight: 600; padding-top: 10px; border-bottom: 1px solid {ink}; }}',
            f'.muted, .caption, td.label {{ color: {muted}; }}',
            'table.facts { margin-top: 2px; margin-bottom: 14px; }',
            f'.result {{ background-color: {head}; font-weight: 600; }}',
            '.formula { margin-top: 12px; margin-bottom: 12px; }']
    return '\n'.join(out)
