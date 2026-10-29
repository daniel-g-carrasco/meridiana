"""The settings, stored as JSON in the config folder (paths.py).

No secret is ever here: a password lives in the keyring (extras/secrets).
Writes are atomic (temporary file, fsync, rename) so a crash or a full disk
can never leave a half-written file behind, and the file as it was before
stays next to it (config.json.bak): a damaged file, or one that is gone, is
replaced by that previous save rather than by nothing, and what happened is
told (Config.notices). The file carries a format version: an older format
is migrated on reading; a newer one (an app downgraded) is read for what
this version knows and written back whole, the unknown settings kept.

Adding a setting: a field with a default of the right type (bool, int,
str, or a dict of lists of text: a value of another type in the file counts
as damage). Renaming or
changing one: a migration step in MIGRATIONS and CONFIG_VERSION + 1.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import SLUG

CONFIG_VERSION = 22


def _v1_to_v2(data: dict) -> dict:
    """Version 2 keeps the keys the designer changed (shortcuts.py): none yet."""
    return {**data, "shortcuts": data.get("shortcuts", {})}


def _v2_to_v3(data: dict) -> dict:
    """Version 3 has the chosen colour and the backgrounds of the theme (study 13, section 12)."""
    return {**data, "accent": data.get("accent", "bronze"), "backgrounds": data.get("backgrounds", "meridiana")}


def _v3_to_v4(data: dict) -> dict:
    """Version 4 has the navigation of the views (navigation.py, camera.py; study 15, 2.6)."""
    return {**data, "navigation": data.get("navigation", "autocad"), "orbit": data.get("orbit", "turntable"),
            "pivot": data.get("pivot", "cursor")}


def _v4_to_v5(data: dict) -> dict:
    """Version 5 has the switch of the assistant (study 14, 7.3): shown, as it was."""
    return {**data, "assistant": data.get("assistant", True)}


def _v5_to_v6(data: dict) -> dict:
    """Version 6 has the veil over the plan's imagery (view_colours.VEIL, Daniel 23/10/2026)."""
    return {**data, "veil": data.get("veil", 0.4)}


def _v6_to_v7(data: dict) -> dict:
    """Version 7 has the look of the toolbar: the icons alone, as Daniel would have it by default (R19)."""
    return {**data, "toolbar": data.get("toolbar", "icons")}


def _v7_to_v8(data: dict) -> dict:
    """Version 8 has the assistant docked in the panels or floating (R17): floating, as it was."""
    return {**data, "assistant_docked": data.get("assistant_docked", False)}


def _v8_to_v9(data: dict) -> dict:
    """Version 9 has the three network switches of the privacy page (study 18, G 6.2): on, as the program
    behaved, and now said."""
    return {**data, "network_geocoding": data.get("network_geocoding", True),
            "network_pvgis": data.get("network_pvgis", True), "network_tiles": data.get("network_tiles", True)}


def _v9_to_v10(data: dict) -> dict:
    """Version 10: the toolbar is the bar of the phase (task 17b, design C1) and `toolbar` changes meaning:
    "text" is the words under the icons, "icons" the icons alone; "icons and text beside" no longer exists.
    Daniel's choice of 23/10/2026 is the text under the icons by default, so every file gets "text" (the old
    "icons" was the old default, not a choice one can tell apart). `toolbar_place` is new: on top, or on the
    left side with the icons alone (study 17, B2)."""
    return {**data, "toolbar": "text", "toolbar_place": data.get("toolbar_place", "top")}


def _v10_to_v11(data: dict) -> dict:
    """Version 11 has Meridio's movements and drawing (study 17, G; R34) and the size of his speech bubble
    (R15): animated, smooth, 320 x 400, as he was."""
    return {**data, "assistant_animated": data.get("assistant_animated", True),
            "assistant_style": data.get("assistant_style", "smooth"),
            "assistant_width": data.get("assistant_width", 320), "assistant_height": data.get("assistant_height", 400)}


def _v11_to_v12(data: dict) -> dict:
    """Version 12 has the view of the Checks panel (task 17e): by level, as Daniel chose (F2)."""
    return {**data, "checks_view": data.get("checks_view", "level")}


def _v12_to_v13(data: dict) -> dict:
    """Version 13 has the help box at the foot of the right panel open or folded (task 17d, design C3): open,
    as Daniel asked for it."""
    return {**data, "help_open": data.get("help_open", True)}


def _v13_to_v14(data: dict) -> dict:
    """Version 14: M is Move and Measure goes to D (study 16, B; Daniel, 23/10/2026). The keys kept are only those
    the designer changed (shortcuts.differences): one who had given Measure other keys besides M keeps them, with
    D in the place of M; Measure left with D alone is the default again, and leaves the settings. A key the
    designer gave to another command stays theirs (shortcuts.settle)."""
    keys = data.get("shortcuts")
    measure = keys.get("tool_measure") if isinstance(keys, dict) else None
    if not isinstance(measure, list) or "M" not in measure:
        return data
    moved = []
    for k in measure:
        k = "D" if k == "M" else k
        if k not in moved:
            moved.append(k)
    keys = dict(keys)
    if moved == ["D"]:
        del keys["tool_measure"]
    else:
        keys["tool_measure"] = moved
    return {**data, "shortcuts": keys}


def _v14_to_v15(data: dict) -> dict:
    """Version 15 has the menu bar hidden until Alt (R40, R53; Daniel's choice of 24/10/2026) and the projects
    opened last, for the File page."""
    return {**data, "menu_bar": data.get("menu_bar", False), "recent": data.get("recent", [])}


def _v15_to_v16(data: dict) -> dict:
    """Version 16 has the author's profiles for the report (R61, reports.py), none, and the one chosen for a new
    project."""
    return {**data, "report_profiles": data.get("report_profiles", []), "report_profile": data.get("report_profile", "")}


def _v16_to_v17(data: dict) -> dict:
    """Version 17 has where Meridio thinks (task 14, R82): the local model by default, its server's address and
    model, the Claude model for the cloud, the consents given to a cloud provider (provider -> the ISO date) and
    his spoken voice, off. No key: the keyring keeps it (assistant/keys.py)."""
    return {**data, "assistant_provider": data.get("assistant_provider", "local"),
            "assistant_local_url": data.get("assistant_local_url", "http://127.0.0.1:9931/v1"),
            "assistant_local_model": data.get("assistant_local_model", ""),
            "assistant_cloud_model": data.get("assistant_cloud_model", "claude-haiku-5-5"),
            "assistant_consent": data.get("assistant_consent", {}),
            "assistant_voice": data.get("assistant_voice", False)}


def _v17_to_v18(data: dict) -> dict:
    """Version 18 has Meridio's natural voice (Kokoro, ui/voice.py; Daniel, 24/10/2026): which engine speaks
    ("auto": Kokoro when its model is on the PC, else the system's), which voice ("" a man's), where the model is
    and which Python runs it ("" the default places and the program's own)."""
    return {**data, "assistant_voice_engine": data.get("assistant_voice_engine", "auto"),
            "assistant_voice_name": data.get("assistant_voice_name", ""),
            "assistant_kokoro_dir": data.get("assistant_kokoro_dir", ""),
            "assistant_kokoro_python": data.get("assistant_kokoro_python", "")}


def _v18_to_v19(data: dict) -> dict:
    """Version 19 has the map sources the designer adds (R36, Preferences > Maps), none, and the background "auto",
    the best source for the site, as the default: the old default, the national orthophoto, becomes "auto" (in
    Italy it is still the national orthophoto, or the open orthophoto of the region where there is one; the 2012
    one is chosen by name when wanted); a source chosen by name stays."""
    background = data.get("background", "pcn")
    return {**data, "map_sources": data.get("map_sources", []),
            "background": "auto" if background == "pcn" else background}


def _v19_to_v20(data: dict) -> dict:
    """Version 20 has what Meridio's character and his local models need (R105, R106): whether he has presented
    himself, not yet (he does it the first time his bubble opens, also for whoever used him before: his manner is
    new), and the API of the local server ("" an OpenAI-compatible one, as it was; "ollama" Ollama's own)."""
    return {**data, "assistant_introduced": data.get("assistant_introduced", False),
            "assistant_local_runtime": data.get("assistant_local_runtime", "")}


def _v20_to_v21(data: dict) -> dict:
    """Version 21 has the size of the text (R133, Daniel 26/10/2026: «farei 12, 13 e 14 come piccolo, medio e
    grande»): the medium one, the 13 px of before."""
    return {**data, "text_size": data.get("text_size", "medium")}


def _v21_to_v22(data: dict) -> dict:
    """Optional updates and resumable onboarding do not alter existing project settings."""
    return {**data, "auto_install_updates": data.get("auto_install_updates", False),
            "pending_update": data.get("pending_update", {}),
            "tour_status": data.get("tour_status", "new"), "tour_step": data.get("tour_step", 0)}


# from one format version to the next, in order: {from_version: step}
MIGRATIONS: dict[int, Callable[[dict], dict]] = {1: _v1_to_v2, 2: _v2_to_v3, 3: _v3_to_v4, 4: _v4_to_v5,
                                                 5: _v5_to_v6, 6: _v6_to_v7, 7: _v7_to_v8, 8: _v8_to_v9,
                                                 9: _v9_to_v10, 10: _v10_to_v11, 11: _v11_to_v12,
                                                 12: _v12_to_v13, 13: _v13_to_v14, 14: _v14_to_v15,
                                                 15: _v15_to_v16, 16: _v16_to_v17, 17: _v17_to_v18,
                                                 18: _v18_to_v19, 19: _v19_to_v20,
                                                 20: _v20_to_v21, 21: _v21_to_v22}


@dataclass
class Config:
    theme: str = "system"                # "system", "light", "dark"
    accent: str = "bronze"               # the theme's colour: "system", a ready-made one by name, or "#rrggbb"
    backgrounds: str = "meridiana"       # "meridiana", "tinted" (from the colour), "grey"
    text_size: str = "medium"            # "small", "medium", "large": the text at 12, 13 or 14 px (design.TEXT_SIZES)
    toolbar: str = "text"                # the bar of the phase: "text" under the icons (hidden by itself in a low
    #                                      window), or "icons" alone (study 17, B4; design C1)
    toolbar_place: str = "top"           # "top" under the row of the phases, or "left" on the side, icons alone
    navigation: str = "autocad"          # the mouse's style (navigation.STYLES): AutoCAD's hands until Daniel says
    orbit: str = "turntable"             # "turntable" (the vertical stays) or "arcball"
    pivot: str = "cursor"                # the orbit's centre: "cursor", "selection", "centre" (of the view)
    pivot_hint: bool = True              # the pivot's cross-hair on passing over, with the orbit's key held (16g)
    assistant: bool = True               # the assistant and its item in the status bar; off hides everything
    assistant_docked: bool = False       # the conversation in a panel of the window, not floating over the views
    assistant_animated: bool = True      # Meridio's small movements; off, he only changes state
    assistant_style: str = "smooth"      # his drawing: "smooth" or "pixel" (R34)
    assistant_width: int = 320           # the size of his speech bubble, as last resized
    assistant_height: int = 400
    # where Meridio thinks (task 14): "local" (an OpenAI-compatible server on this PC, llama-server by default) or
    # "claude" (Anthropic's API, with the key in the keyring and the designer's consent); the local server's address
    # and model ("" for the one it serves), the Claude model; the consents given, provider -> [ISO date]
    assistant_provider: str = "local"
    assistant_local_url: str = "http://127.0.0.1:9931/v1"
    assistant_local_model: str = ""
    assistant_local_runtime: str = ""    # its API: "" OpenAI-compatible (llama-server, LM Studio...), "ollama" its own
    assistant_cloud_model: str = "claude-haiku-5-5"
    assistant_consent: dict = field(default_factory=dict)
    assistant_voice: bool = False        # Meridio reads his answers aloud (ui/voice.py)
    assistant_introduced: bool = False   # he presented himself (persona.presentation), the first time he was opened
    # the voice: "auto" (Kokoro, the natural one, when its model is on the PC, else the system's), "kokoro",
    # "system"; the voice's name ("" a man's: Nicola in Italian); the model's folder and the Python that runs it
    # ("" the default places, assistant/speech.py, and the program's own Python)
    assistant_voice_engine: str = "auto"
    assistant_voice_name: str = ""
    assistant_kokoro_dir: str = ""
    assistant_kokoro_python: str = ""
    language: str = ""                   # "" = the desktop's; "en", "it"
    check_updates: bool = True           # Windows: a newer release, once a day at start
    auto_install_updates: bool = False
    pending_update: dict = field(default_factory=dict)
    tour_status: str = "new"             # new, active, paused, skipped, done
    tour_step: int = 0
    last_update_check: str = ""          # ISO date of the last check made on its own
    last_folder: str = ""                # the folder of the last project opened or saved
    last_project: str = ""               # reopened at start when it still exists
    background: str = "auto"             # the plan's imagery: "auto" (the best for the site), a source of tiles.py
    #                                      or of map_sources by key, "none"
    # the map sources the designer added (Preferences > Maps; tiles.to_dict each): no key in them, the keyring has it
    map_sources: list = field(default_factory=list)
    veil: float = 0.4                    # how much the imagery is darkened under the drawing, 0 to 1
    checks_view: str = "level"           # the Checks panel grouped by "level", "object", "area" or for "delivery"
    help_open: bool = True               # the help box at the foot of the right panel open, or folded to its title
    menu_bar: bool = False               # the menu bar always shown; off, Alt shows it (ui/menubar.py)
    recent: list = field(default_factory=list)      # the projects opened last, newest first (the File page)
    # the author of the reports (Preferences > Report, reports.PROFILE_KEYS each): no name is in the program; the
    # one a project's report is signed with when the project chose none
    report_profiles: list = field(default_factory=list)
    report_profile: str = ""
    # what leaves the PC, each with its switch (Preferences > Privacy): the address typed, to OpenStreetMap's
    # Nominatim; the site's coordinates, to PVGIS; the area in view, to the map servers (tiles.SOURCES)
    network_geocoding: bool = True
    network_pvgis: bool = True
    network_tiles: bool = True
    # the keys changed by the designer, command id -> keys (shortcuts.py); only what differs from the defaults
    shortcuts: dict = field(default_factory=dict)
    # settings of a newer version this one does not know, written back as they were
    extra: dict = field(default_factory=dict, compare=False, repr=False)
    # what load() had to do to read the file (Notice); never saved
    notices: list = field(default_factory=list, compare=False, repr=False)

    def to_json(self) -> dict:
        data = asdict(self)
        extra = data.pop("extra")
        del data["notices"]
        out = {**extra, **data}
        out["version"] = CONFIG_VERSION
        return out

    @classmethod
    def from_json(cls, data) -> "Config":
        """ValueError or TypeError when `data` is not a configuration."""
        if not isinstance(data, dict):
            raise ValueError(f"not a {SLUG} configuration")
        own = {"extra", "notices", "version"}
        known = {f.name for f in fields(cls)} - own
        cfg = cls(**_typed(cls, {k: v for k, v in data.items() if k in known}))
        cfg.extra = {k: v for k, v in data.items() if k not in known and k not in own}
        return cfg


def _typed(cls, kwargs: dict) -> dict:
    """ValueError when a value has not the type of the field's default (a
    number for a switch, a word for a number): such a file is damaged, and
    the previous save is a better start than a crash later on."""
    for f in fields(cls):
        if f.name in kwargs and f.default_factory is dict and f.name != "extra":
            value = kwargs[f.name]
            if value.__class__ is not dict or any(v.__class__ is not list or any(x.__class__ is not str for x in v)
                                                  for v in value.values()):
                raise ValueError(f"{f.name}: {value!r} is not a table of keys")
            continue
        if f.name not in kwargs or f.default is None or f.default.__class__ not in (bool, int, float, str):
            continue
        value = kwargs[f.name]
        if f.default.__class__ is bool and value.__class__ is not bool:
            raise ValueError(f"{f.name}: {value!r} is not a switch")
        if f.default.__class__ is int and value.__class__ is not int:
            raise ValueError(f"{f.name}: {value!r} is not a number")
        if f.default.__class__ is float and (value.__class__ not in (int, float) or not math.isfinite(value)):
            raise ValueError(f"{f.name}: {value!r} is not a number")      # a text veil crashed the window at start
        if f.default.__class__ is str and value.__class__ is not str:
            raise ValueError(f"{f.name}: {value!r} is not text")
    return kwargs


@dataclass(frozen=True)
class Notice:
    """What load() had to do: "recovered" (the file was damaged: the previous
    save was used; `detail` is where the damaged file was put), "fresh" (damaged
    and nothing to recover: the app starts anew; `detail` as above), "missing"
    (the file was gone: the previous save was used), "newer" (saved by a
    newer version; `detail` is its format version)."""
    kind: str
    detail: str = ""
    reason: str = ""


class Damaged(Exception):
    """The file is there and is not a configuration."""


def backup_file(path: Path) -> Path:
    return path.with_name(path.name + ".bak")


def migrate(data: dict) -> dict:
    """An older format brought to this one, one version at a time."""
    version = data.get("version", 1)
    if version.__class__ is not int:
        raise ValueError(f"format version {version!r}")
    while version < CONFIG_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            raise ValueError(f"no migration from format version {version}")
        data = step(data)
        version += 1
        data["version"] = version
    return data


def _read(path: Path) -> tuple[Config, int]:
    """The configuration in `path` and its format version; FileNotFoundError,
    or Damaged with the reason."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise
    except (OSError, ValueError) as e:          # bad JSON and bad UTF-8 are ValueErrors
        raise Damaged(f"{type(e).__name__}: {e}") from e
    try:
        if not isinstance(data, dict):
            raise ValueError(f"not a {SLUG} configuration")
        version = data.get("version", 1)
        return Config.from_json(migrate(data)), version if version.__class__ is int else 1
    except (TypeError, ValueError) as e:
        raise Damaged(f"{type(e).__name__}: {e}") from e


def _set_aside(path: Path) -> Path:
    """The damaged file, kept next to the settings under another name."""
    aside = path.with_name(path.name + time.strftime(".broken-%Y%m%d-%H%M%S"))
    try:
        os.replace(path, aside)
    except OSError:
        pass
    return aside


def load(path: Path) -> Config:
    """The settings, whatever the file's state (see the module's docstring);
    cfg.notices says what had to be done."""
    notices: list[Notice] = []
    version = CONFIG_VERSION
    recovered = False
    try:
        cfg, version = _read(path)
    except FileNotFoundError:
        try:
            cfg, version = _read(backup_file(path))
            notices.append(Notice("missing"))
            recovered = True
        except (FileNotFoundError, Damaged):
            cfg = Config()
    except Damaged as e:
        aside = _set_aside(path)
        try:
            cfg, version = _read(backup_file(path))
            notices.append(Notice("recovered", str(aside), str(e)))
            recovered = True
        except (FileNotFoundError, Damaged):
            cfg = Config()
            notices.append(Notice("fresh", str(aside), str(e)))
    if version > CONFIG_VERSION:
        notices.append(Notice("newer", str(version)))
    if not path.exists() or recovered:
        try:
            save(cfg, path)
        except OSError:
            pass
    cfg.notices = notices
    return cfg


def save(cfg: Config, path: Path) -> None:
    """Atomic: the new file is complete before it takes the old one's place,
    and the old one stays as the backup (a hard link where the disk allows,
    a copy elsewhere: never a moment without a settings file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".config-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg.to_json(), f, indent=2, ensure_ascii=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        _keep_previous(path)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def _keep_previous(path: Path) -> None:
    bak = backup_file(path)
    try:
        if not path.exists():
            return
        bak.unlink(missing_ok=True)
        try:
            os.link(path, bak)
        except OSError:
            shutil.copyfile(path, bak)
    except OSError:
        pass                    # a backup that cannot be made must not stop the save
