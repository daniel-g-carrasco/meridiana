"""Local issue drafts. Nothing is sent; the designer reviews and submits in the browser."""
from dataclasses import dataclass
import re
from urllib.parse import urlencode

from . import GITHUB_REPO


def redact_diagnostics(text: str) -> str:
    """Remove paths and credential-bearing lines from explicitly selected diagnostics."""
    text = re.sub(r'(?im)^.*(?:authorization|api[_ -]?key|token|password|secret)["\x27]?\s*[:=].*$', '[redacted]', text)
    text = re.sub(r'File "([^"]+)"', lambda m: 'File "' + re.split(r'[/\\]', m[1])[-1] + '"', text)
    text = re.sub(r'(?i)\b[A-Z]:[\\/][^\s"<>]+', '[local path]', text)
    text = re.sub(r'/(?:home|Users|var/home)/[^\s"<>]+', '[local path]', text)
    return text[:12000]


@dataclass
class Draft:
    title: str
    description: str
    version: str
    system: str
    python: str
    context: str = ""
    diagnostics: str = ""
    include_environment: bool = True

    def body(self) -> str:
        parts = [self.description.strip()]
        if self.include_environment:
            parts.append(f"### Environment\nMeridiana: {self.version}\nSystem: {self.system}\nPython: {self.python}")
        if self.context:
            parts.append("### Selected context\n" + self.context)
        if self.diagnostics:
            parts.append("### Selected diagnostics\n```text\n" + redact_diagnostics(self.diagnostics).replace('```', "'''") + "\n```")
        return "\n\n".join(parts)

    def issue_url(self) -> str:
        if not self.title.strip() or not self.description.strip():
            raise ValueError("A title and description are required")
        url = f"https://github.com/{GITHUB_REPO}/issues/new?" + urlencode({"title": self.title[:180], "body": self.body()})
        if len(url) > 12000:
            raise ValueError("The draft is too long for a browser link")
        return url
