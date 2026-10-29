"""Role-aware message blocks using the HTML subset supported by QTextDocument."""
from html import escape


def message_html(author: str, body: str, *, outgoing: bool, colours: dict) -> str:
    """Body is already rendered safe HTML; author is always plain text."""
    background = colours['field'] if outgoing else colours['view']
    header = (f'<p style="margin:0 0 6px 0;color:{colours["muted"]}">'
              f'<b>{escape(author)}</b></p>')
    content = (f'<td width="90%" bgcolor="{background}" style="color:{colours["text"]}">'
               f'{header}{body}</td>')
    gutter = '<td width="10%"></td>'
    cells = gutter + content if outgoing else content + gutter
    return f'<table width="100%" border="0" cellspacing="0" cellpadding="8"><tr>{cells}</tr></table><p style="margin:0;font-size:4px">&nbsp;</p>'
