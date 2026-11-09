"""The report as one document of data, for template.typ: the cover, the contents, the chapters of the template the project
chose, the attachments' separators, what the header and the footer say. The images are not drawn here: each is named
with what makes it (`Composed.makers`), and the interface runs them a step at a time."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .. import __version__, reports
from ..i18n import _, language, number
from . import blocks as B
from . import chapters as C
from . import look
from .chapters import Picture  # noqa: F401  (the interfaces give their 3D pictures so)
from .register import Register

MAX_TOC_ON_COVER = 22            # entries; more and the contents have a page of their own


class NoPlant(ValueError):
    """The project has no module laid: there is no plant to write a report on (R459)."""


def no_plant(data: dict) -> str:
    """Why the report cannot be written, said for the designer; "" when it can: a project without modules has no plant,
    and Typst stopped on it with «cannot divide by zero» (R459)."""
    if any(getattr(r, "modules", None) for r in (data.get("results") or {}).values()):
        return ""
    return _("There is no plant to write the report on: no module is laid. Lay the modules (Layout), compute the "
             "production, then export the report.")


def texts() -> dict:
    """The words of the document that are not the chapters': the same for the PDF, the ODT and the DOCX."""
    return {"page_of": _("page {n} of {total}"), "contents": _("Contents"), "report": _("Technical report"),
            "attachment": _("Attachment"), "plant": _("Plant"), "where": _("where:"),
            "with_values": _("With the values:"), "result": _("result"), "reference": _("Reference"),
            "symbol": _("Symbol"), "quantity": _("Quantity"), "value": _("Value and unit"), "source": _("Source"),
            "figure": _("Figure")}


@dataclass
class Composed:
    document: dict               # what data.json holds
    makers: dict                 # file name in the report's folder -> make() giving its bytes
    chosen: list                 # the chapters written


def with_notes(data: dict) -> dict:
    """The data with the notes of the rules worked out once, for the chapter of the checks and for its presence, and
    with the checks the document prints: what asks the designer for something stays in the window."""
    if data.get("rules_facts") is not None and "rules_notes" not in data:
        from .. import rules
        data = {**data, "rules_notes": rules.notes(data["rules_facts"])}
    if data.get("checks"):
        from ..checks import for_document
        data = {**data, "checks": for_document(data["checks"])}
    return data


def _cover_rows(project, settings: dict, profile: dict | None) -> list[tuple[str, str]]:
    rows = []
    variants = getattr(project, "variants", [])
    if len(variants) > 1:
        here = project.current_variant()
        rows.append((_("Variant"), here["name"] + (f" · {here['note']}" if here.get("note") else "")))
    if settings.get("client"):
        rows.append((_("Client"), settings["client"]))
    s = project.site
    where = f"{number(s.lat, 5)}°, {number(s.lon, 5)}°"
    if settings.get("address", True) and s.address:
        where = f"{s.address} ({where})"
    rows.append((_("Site"), where))
    if profile and profile.get("signer"):
        rows.append((_("Designer"), profile["signer"]))
    rows.append((_("Date"), date.today().strftime("%d/%m/%Y")))
    if settings.get("revision"):
        rows.append((_("Revision"), settings["revision"]))
    return rows


def _meta(project, settings: dict, profile: dict | None) -> list[dict]:
    """The who and the what of the cover, in columns: the client, the site, the designer, the document."""
    s = project.site
    where = f"{number(s.lat, 5)}°, {number(s.lon, 5)}°"
    if settings.get("address", True) and s.address:
        where = f"{s.address} ({where})"
    out = []
    if settings.get("client"):
        out.append({"t": _("Client"), "lines": [settings["client"]]})
    out.append({"t": _("Site"), "lines": [where]})
    if profile:
        lines = [x for x in (profile.get("firm"), profile.get("signer"), profile.get("register")) if x]
        lines += [x for x in (profile.get(k) for k in ("address", "phone", "email", "web")) if x]
        if lines:
            out.append({"t": _("Designer"), "lines": lines})
    document = [date.today().strftime("%d/%m/%Y")]
    if settings.get("revision"):
        document.insert(0, f"{_('Revision')}: {settings['revision']}")
    variants = getattr(project, "variants", [])
    if len(variants) > 1:
        here = project.current_variant()
        document.append(f"{_('Variant')}: {here['name']}" + (f" · {here['note']}" if here.get("note") else ""))
    out.append({"t": _("Date"), "lines": document})
    return out


def _what(project, data: dict, ctx) -> str:
    """The line under the title: what was made."""
    sim = data.get("sim")
    if sim is None:
        return _("Photovoltaic system")
    bits = [f"{_('Photovoltaic system')}, {number(sim.p_stc_kw, 2)} kWp"]
    mods = C._modules(project, data.get("results") or {})
    invs = C._inverters(data.get("plant"))
    made = ", ".join(f"{n} × {name}" for name, n, _p in mods + invs)
    if made:
        bits.append(made)
    bits.append(f"{C.kwh(sim.energy_kwh)} kWh")
    bits.append(f"PR {number(100 * sim.pr, 1)} %")
    return " · ".join(bits)


def _attachment_block(k: int, a, n: int, raster_dpi: int) -> dict:
    """The page before an attachment: what it is, its file, its pages."""
    from pathlib import Path
    title = _("Attachment {n}: {title}").format(n=k, title=a.title)
    items = [B.facts([(_("File"), Path(a.path).name), (_("Pages"), str(a.pages))]),
             B.para(_("The pages that follow are the file as it was given, without the report's header and footer."),
                    "muted")]
    if a.protected:
        items.append(B.para(_("The file is protected against changes: its pages follow as images at {dpi} dpi.").format(
            dpi=raster_dpi), "muted"))
    return {"k": "attachment", "n": k, "id": f"attachment:{k}", "title": title, "pages": a.pages, "items": items}


def compose(project, data: dict, *, profile: dict | None = None, only: str = "", attached: list | None = None,
            pictures: dict | None = None, raster_dpi: int = 200) -> Composed:
    """The report's document. `attached`: the attachments that go in ({.path, .title, .pages, .protected}), each behind
    a page of its own after the last chapter; `pictures`: the 3D views the interface can make, id -> Picture, the
    first for the cover; `only`: a chapter alone, under a title of its own (the «How it is computed» of the register of
    the calculations), without cover, contents and attachments."""
    problem = no_plant(data)
    if problem:
        raise NoPlant(problem)
    data = with_notes(data)
    settings = reports.settings(project)
    template = reports.templates()[settings["template"]]
    chosen = reports.plan(project, data)
    if only:
        chapter = reports.chapters()[only]
        chosen = [] if reports.missing(chapter, data) else [chapter]
    ids = tuple(c.id for c in chosen)
    attached = list(attached or [])
    makers: dict = {}

    def image(name: str, make) -> str:
        makers.setdefault(name, make)
        return name

    # the report has its own palette, warm greys: the profile's colour no longer reaches it (R460, look.py)
    accent = look.ACCENT
    register = Register("register" in ids, C.records_of(data))
    ctx = C.Context(project, data, image, settings, register, ids, dict(pictures or {}), accent)
    profile = profile or {}
    today = date.today().strftime("%d/%m/%Y")
    logo_path = profile.get("logo") or ""
    client_site = [x for x in (settings.get("client"),
                               project.site.address if settings.get("address", True) else "") if x]
    firm = profile.get("firm") or profile.get("signer") or ""
    second = " · ".join(x for x in (profile.get("signer") if profile.get("firm") else "", profile.get("register")) if x)
    contacts = " · ".join(x for x in (profile.get(k) for k in ("phone", "email", "web")) if x)
    doc = {
        "lang": language() or "en",
        "accent": accent,
        "missing": [],
        "attachments": [{"k": k, "title": a.title, "pages": a.pages} for k, a in enumerate(attached, 1)],
        "style": look.style(),
        "texts": texts(),
        "doc": {"title": project.name, "author": profile.get("signer") or firm or "",
                "logo_file": logo_path, "logo": None,
                "head_title": project.name or _("Technical report"), "head_sub": " · ".join(client_site),
                "revision": settings.get("revision") or "", "date": today,
                "foot_left": firm, "foot_left2": second or contacts,
                "foot_centre": project.name, "foot_centre2": " · ".join(x for x in (settings.get("revision"), today) if x),
                "foot_right2": contacts if second else "",
                # the kind of document, written at the head of the cover and of every page (Daniel, 06/11/2026), and
                # the place of the logo, dashed, when the profile has none
                "doc_title": _("Technical report of the photovoltaic system"),
                "doc_sub": _("Yield and electrical checks"), "doc_short": _("PV technical report"),
                "logo_placeholder": True},
        "cover": None, "head": None, "toc": "none", "body": [],
    }
    body: list = []
    if only:
        doc["head"] = {"kicker": _("REGISTER OF THE CALCULATIONS"), "title": project.name, "sub": "", "lines": [],
                       "made": ""}
        body.append(B.para(_("How each number of the report is computed: the models, the losses and the thresholds, "
                             "with their sources and formulas. The values hour by hour are in the CSV file of the "
                             "register."), "lead"))
        for c in chosen:
            body.append(B.section(c.title, "slate"))
            body += [x for x in C.BUILDERS[c.id](ctx) if x]
    else:
        made = _("Report made by Meridiana {v}").format(v=__version__)
        sim = data.get("sim")
        if template.contents:
            views = list(ctx.pictures)
            picture = ctx.view(views[0]) if views else ""
            plan = ""
            if not picture and any(getattr(r, "modules", None) for r in (data.get("results") or {}).values()):
                from . import figures
                plan = image("plan.svg", lambda: figures.plan_svg(project, data.get("results") or {},
                                                                  colours={"module": accent}))
            doc["cover"] = {"image": picture or plan, "tint": not picture, "inset": 0 if picture else 3, "max_h": 108.0,
                            "kicker": _("TECHNICAL REPORT"), "title": project.name or _("Photovoltaic system"),
                            "sub": _what(project, data, ctx), "meta": _meta(project, settings, profile), "made": made}
            entries = len(chosen) + len(attached)
            doc["toc"] = "none" if not entries else "cover" if entries <= MAX_TOC_ON_COVER else "page"
        else:
            doc["head"] = {"kicker": _("TECHNICAL REPORT"), "title": project.name or _("Photovoltaic system"),
                           "sub": _what(project, data, ctx) if sim is not None else "",
                           "lines": [f"{a}: {b}" for a, b in _cover_rows(project, settings, profile)], "made": made}
        for n, chapter in enumerate(chosen, 1):
            ctx.chapter, ctx.figures = n, 0
            built = [x for x in C.BUILDERS[chapter.id](ctx) if x]
            body.append(C.in_report(chapter, n, breaks=chapter.id == "summary"))
            body += built
        for k, a in enumerate(attached, 1):
            body.append(_attachment_block(k, a, len(attached), raster_dpi))
    doc["body"] = body
    return Composed(doc, makers, chosen)
