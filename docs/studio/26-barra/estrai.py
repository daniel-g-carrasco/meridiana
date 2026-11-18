"""Study 26: the real bars read from a real window (offscreen, Italian): per phase the groups, the tools, the word under
each icon, the action's whole text, key and tooltip, the icon's SVG, the theme's tokens for accent indigo. Writes
barre.json, from which genera.py draws. From the root of the repository, with the tests' environment:
python docs/studio/26-barra/estrai.py <folder of a compiled locale>. Nothing of the program is changed."""

import json
import os
import sys
import unittest
from pathlib import Path

os.environ["LANGUAGE"] = "it"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import _setup  # noqa: E402
from _fixtures import capannone  # noqa: E402

from meridiana import config, i18n, phases, theme_colors  # noqa: E402

i18n._locale_dirs = lambda: [Path(sys.argv[1])]
i18n.setup("it")
from meridiana import shortcuts  # noqa: E402
from meridiana.ui import icons  # noqa: E402

HERE = Path(__file__).resolve().parent


class Case(unittest.TestCase):
    def runTest(self):
        pass


case = Case()
win = _setup.window(case, capannone(), cfg=config.Config(background="none", network_pvgis=False, accent="indigo",
                                                         language="it"), size=(1920, 1080))
out = {"phases": [], "icons": {}, "tokens": {}}
missing = []


def icon_of(name):
    data = icons.svg(name)
    if not data:
        missing.append(name)
        return ""
    out["icons"][name] = data.decode("utf-8")
    return name


for phase in phases.phases():
    bar = win.tabs.bar(win.tabs.index_of_phase(phase.id))
    entry = {"id": phase.id, "n": phase.number, "title": phase.title, "groups": []}
    for g in bar.groups:
        tools = []
        for t in g.group.tools:
            if t.command not in g.shared:
                continue
            fam = []
            for f in t.family():
                b = g.shared.get(f.command)
                if f.command not in g.shared:
                    continue
                if hasattr(b, "family"):
                    word, a = b.family[f.command]
                else:
                    word, a = b.label, b.defaultAction()
                fam.append({"cmd": f.command, "word": word, "text": shortcuts.plain(a.text()),
                            "key": a.shortcut().toString(), "tip": a.toolTip(), "icon": icon_of(f.icon or f.command),
                            "enabled": a.isEnabled(), "checkable": a.isCheckable()})
            tools.append({"primary": t.primary, "family": fam})
        entry["groups"].append({"title": g.group.title, "tools": tools})
    out["phases"].append(entry)
for name in ("plan", "3d", "both", "fit", "zoom_in", "zoom_out", "site", "folder-open"):     # for the windows of study 27
    icon_of(name)
for name, dark in (("light", False), ("dark", True)):
    d = theme_colors.derive("#5b4bb0", dark)
    tokens = d.tokens if hasattr(d, "tokens") else d
    out["tokens"][name] = {k: tokens[k] for k in ("window", "panel", "view", "card", "field", "line", "line_soft", "card_line",
                                                  "text", "text2", "muted", "accent", "accent_fg", "hover", "press", "danger", "select_bg")}
out["missing"] = missing
(HERE / "barre.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
print("groups", sum(len(p["groups"]) for p in out["phases"]), "icons", len(out["icons"]), "missing", missing)
case.doCleanups()
