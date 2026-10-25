"""What leaves the PC when Meridio asks a cloud model (study 14, 6.6; task 14, step 3), decided here and nowhere
else:
- the local model is the default, and a cloud provider is asked only after the designer's consent, given once per
  provider and kept in the settings (`consented`, `consent`); the card says what would leave (`what_leaves`);
- a project marked reserved never goes to the cloud, whatever the settings (`allowed`): its questions go to the
  local model;
- towards the cloud the project's name, its address and its file's name are replaced by placeholders, and put back
  in what the model writes (`Redactor`); the coordinates are rounded to 0.01 degree (about 1 km) by the tools
  themselves, for every model: none needs them closer;
- from the cloud back to the local model, yes (it is more private); from the local model to the cloud, never by
  itself.
No Qt."""

from __future__ import annotations

import copy
import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..i18n import _

PLACEHOLDERS = {"project": "[PROJECT]", "address": "[ADDRESS]", "file": "[FILE]"}
PART = 4                        # a part of the address shorter than this («MI», «20») is not a secret by itself


def provider_names() -> dict:
    return {"anthropic": "Anthropic (Claude)"}


@dataclass
class Redactor:
    """The secrets of a project and their placeholders, longest first so that a name inside another is not cut."""
    pairs: list = field(default_factory=list)          # (secret, placeholder)

    @classmethod
    def of(cls, project, path: Path | str | None = None, more: dict | None = None) -> Redactor:
        """The project's name, its address (and the parts of it between commas), the file's name; `more` adds
        others by kind (a client's name, when the report has one)."""
        found: list[tuple[str, str]] = []

        def add(secret, placeholder: str) -> None:
            secret = (secret or "").strip()
            if len(secret) >= PART and all(secret.casefold() != s.casefold() for s, _p in found):
                found.append((secret, placeholder))
        add(project.name, PLACEHOLDERS["project"])
        address = project.site.address or ""
        add(address, PLACEHOLDERS["address"])
        for part in re.split(r"[,;\n]", address):
            add(part, PLACEHOLDERS["address"])
        if path:
            add(Path(path).stem, PLACEHOLDERS["file"])
            add(Path(path).name, PLACEHOLDERS["file"])
        for kind, secret in (more or {}).items():
            add(secret, f"[{kind.upper()}]")
        found.sort(key=lambda pair: -len(pair[0]))
        return cls(found)

    def redact(self, text: str) -> str:
        for secret, placeholder in self.pairs:
            text = re.sub(re.escape(secret), placeholder, text, flags=re.IGNORECASE)
        return text

    def restore(self, text: str) -> str:
        """What the model wrote with the placeholders, with the real names again (the first secret of each
        placeholder: the whole name, not a part of it)."""
        first: dict = {}
        for secret, placeholder in sorted(self.pairs, key=lambda pair: -len(pair[0])):
            first.setdefault(placeholder, secret)
        for placeholder, secret in first.items():
            text = text.replace(placeholder, secret)
        return text

    def messages(self, messages: list[dict]) -> list[dict]:
        """A copy of the conversation as it may leave: the questions and the tools' answers redacted. An answer of
        the cloud model itself (`raw`) came from there and goes back as it is."""
        out = copy.deepcopy(messages)
        for m in out:
            if m["role"] in ("user", "tool") or (m["role"] == "assistant" and not m.get("raw")):
                m["content"] = self.redact(m.get("content") or "")
            for c in m.get("calls") or []:
                c["arguments"] = _redact_value(c.get("arguments"), self)
        return out


def _redact_value(value, redactor: Redactor):
    if isinstance(value, str):
        return redactor.redact(value)
    if isinstance(value, dict):
        return {k: _redact_value(v, redactor) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v, redactor) for v in value]
    return value


def consented(consents: dict, family: str) -> bool:
    """Whether the designer said yes to this provider (the settings' table: provider -> [date])."""
    return bool(consents.get(family))


def consent(consents: dict, family: str, today: dt.date | None = None) -> dict:
    """The table with the consent to `family` given today."""
    return {**consents, family: [(today or dt.date.today()).isoformat()]}


def allowed(project, family: str, consents: dict) -> str:
    """Whether a question may go to a cloud provider now: "" yes, "reserved" (never, for this project) or
    "consent" (to be asked first)."""
    if getattr(project, "reserved", False):
        return "reserved"
    if not consented(consents, family):
        return "consent"
    return ""


def what_leaves(family: str, model: str) -> list[str]:
    """The lines of the consent card: what is sent, to whom, what they do with it (study 14, 3.1 and 6.6)."""
    who = provider_names().get(family, family)
    return [
        _("To {who}, model {model}: your questions and what Meridio reads to answer them (the checks, a summary "
          "of the project, the results), never the project file.").format(who=who, model=model),
        _("The project's name, its address and the file's name are replaced by placeholders; the coordinates are "
          "rounded to about 1 km."),
        _("Anthropic does not train its models on what the API receives and deletes it within 30 days (its "
          "commercial terms, read on 22/10/2026). The servers may be outside the EU."),
        _("A project marked reserved never leaves the PC: its questions go to the local model."),
    ]
