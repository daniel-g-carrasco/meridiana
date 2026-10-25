"""The preferences of whoever uses the program (not of the project: they live in the settings, config.py), one
page each: the appearance, the navigation of the views, the keyboard, the assistant, the report, the maps
(ui/map_sources.py) and the privacy."""

from __future__ import annotations

import html
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QPushButton, QRadioButton, QScrollArea, QTabWidget,
                               QVBoxLayout, QWidget)

from .. import assistant, config, navigation
from ..i18n import _
from .appearance import Appearance
from .design import strong
from .shortcuts_dialog import ShortcutsEditor


def orbit_names() -> dict:
    return {"turntable": _("Turntable: the vertical stays vertical"), "arcball": _("Arcball: free")}


def pivot_names() -> dict:
    return {"cursor": _("The point under the cursor"), "selection": _("The middle of the selection"),
            "centre": _("The middle of the view")}


class NavigationPage(QWidget):
    """The mouse in the views (study 15, 2.6): FreeCAD's styles, AutoCAD and SketchUp; the orbit; its centre."""

    def __init__(self, cfg: config.Config, parent=None):
        super().__init__(parent)
        box = QVBoxLayout(self)
        form = QFormLayout()
        self.style = QComboBox()
        for key, name in navigation.style_names().items():
            self.style.addItem(name, key)
        self.style.setCurrentIndex(max(0, self.style.findData(cfg.navigation)))
        form.addRow(_("Mouse style"), self.style)
        self.orbit = QComboBox()
        for key, name in orbit_names().items():
            self.orbit.addItem(name, key)
        self.orbit.setCurrentIndex(max(0, self.orbit.findData(cfg.orbit)))
        form.addRow(_("Orbit"), self.orbit)
        self.pivot = QComboBox()
        for key, name in pivot_names().items():
            self.pivot.addItem(name, key)
        self.pivot.setCurrentIndex(max(0, self.pivot.findData(cfg.pivot)))
        form.addRow(_("Centre of the orbit"), self.pivot)
        self.hint = QCheckBox(_("Show the pivot on passing over"))
        self.hint.setChecked(cfg.pivot_hint)
        form.addRow("", self.hint)
        box.addLayout(form)
        self.hint_keys = QLabel()                    # which key, for the style chosen
        self.hint_keys.setWordWrap(True)
        box.addWidget(self.hint_keys)
        # the chosen style in words, from navigation.py (Daniel, 23/10/2026: what one does and what the other does)
        self.audience = QLabel()
        self.audience.setWordWrap(True)
        box.addWidget(self.audience)
        self.gestures = QLabel()
        self.gestures.setWordWrap(True)
        self.gestures.setTextFormat(Qt.TextFormat.RichText)
        box.addWidget(self.gestures)
        note = QLabel(_("A gesture is the buttons and keys held while the mouse moves. The same styles as FreeCAD, "
                        "plus AutoCAD and SketchUp. The plan pans and zooms the same way; the orbit is for the 3D "
                        "view."))
        note.setWordWrap(True)
        box.addWidget(note)
        box.addStretch(1)
        self.style.currentIndexChanged.connect(lambda _i: self._show())
        self._show()

    def _show(self) -> None:
        key = self.style.currentData()
        self.audience.setText(navigation.audience(key))
        keys = navigation.orbit_key_text(key)
        self.hint_keys.setText(
            _("With the orbit's key held ({keys} in this style) and the mouse moving, a cross-hair shows where the "
              "orbit would turn.").format(keys=keys) if keys else
            _("This style orbits with a button alone, with no key to hold: the pivot shows only while orbiting."))
        self.hint.setEnabled(bool(keys))
        rows ="".join(f"<tr><td style='padding: 2px 12px 2px 0'>{strong(html.escape(what))}</td>"
                       f"<td style='padding: 2px 0'>{html.escape(how)}</td></tr>"
                       for what, how in navigation.table(key))
        self.gestures.setText(f"<table>{rows}</table>")

    def choice(self) -> tuple[str, str, str, bool]:
        return self.style.currentData(), self.orbit.currentData(), self.pivot.currentData(), self.hint.isChecked()


class PrivacyPage(QWidget):
    """What leaves the PC, said in words, each service with its switch (study 18, G 6.2: three services were
    called without a line anywhere)."""

    def __init__(self, cfg: config.Config, parent=None):
        super().__init__(parent)
        box = QVBoxLayout(self)
        head = QLabel(_("Meridiana sends nothing about you anywhere. Three services receive what they need to "
                        "answer, and each can be switched off here; off, the program uses what is already in "
                        "the cache and says so."))
        head.setWordWrap(True)
        box.addWidget(head)
        self.geocoding = QCheckBox(_("Find the site: the address typed goes to OpenStreetMap's Nominatim"))
        self.geocoding.setChecked(cfg.network_geocoding)
        box.addWidget(self.geocoding)
        self.pvgis = QCheckBox(_("Weather and PVGIS estimate: the site's coordinates (five decimals) go to the "
                                 "European Commission's PVGIS"))
        self.pvgis.setChecked(cfg.network_pvgis)
        box.addWidget(self.pvgis)
        self.tiles = QCheckBox(_("Map under the plan: the area in view goes to the server of the source in use, "
                                 "named at the bottom right of the plan (Preferences > Maps lists them; the Italian "
                                 "national orthophoto is served over plain http)"))
        self.tiles.setChecked(cfg.network_tiles)
        box.addWidget(self.tiles)
        # the check for a newer version (updates.py): by itself in the Windows build only, the Help menu anywhere
        self.updates = QCheckBox(_("Updates: once a day at start, the Windows program asks GitHub whether a newer "
                                   "version is out; nothing about you or your projects is sent"))
        self.updates.setChecked(cfg.check_updates)
        box.addWidget(self.updates)
        note = QLabel(_("The project file keeps the images you import (without their metadata) and the "
                        "recovery copy in the state folder keeps the whole project until it is saved."))
        note.setWordWrap(True)
        box.addWidget(note)
        box.addStretch(1)

    def choice(self) -> tuple[bool, bool, bool]:
        return self.geocoding.isChecked(), self.pvgis.isChecked(), self.tiles.isChecked()


class MeridioPage(QWidget):
    """Where Meridio thinks (task 14): the local model (the default) or Claude, the local models of this PC found
    with the one to use and the steps when there is none (R105, ui/assistant_local.py), the local server and its
    kind, the Claude model, the key in the system's keyring (set or removed here at once, never in the settings),
    the consent given, the spoken voice. `survey` looks for the local models (assistant/local.survey, a stand-in in
    the tests)."""

    def __init__(self, cfg: config.Config, parent=None, data_dir=None, survey=None):
        super().__init__(parent)
        from ..assistant import costs
        from .assistant_local import LocalModels
        from .style import Group
        self.cfg = cfg
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        group = Group(_("Where {name} thinks").format(name=assistant.NAME))
        inside = QVBoxLayout(group)
        self.local = QRadioButton(_("The local model, on this PC: nothing leaves it (the default)"))
        self.claude = QRadioButton(_("Claude, with your key and after your consent: for the hard questions"))
        choice = QButtonGroup(self)
        for b in (self.local, self.claude):
            choice.addButton(b)
            inside.addWidget(b)
        (self.claude if cfg.assistant_provider == "claude" else self.local).setChecked(True)
        self.locals = LocalModels(survey, lambda: (self.url.text().strip(), self.model.text().strip(),
                                                   self.api.currentData()), self)
        self.locals.chosen.connect(self._use_local)
        inside.addWidget(self.locals)
        form = QFormLayout()
        self.url = QLineEdit(cfg.assistant_local_url)
        form.addRow(_("Local server"), self.url)
        self.api = QComboBox()
        self.api.addItem(_("OpenAI-compatible (llama-server, LM Studio, Jan…)"), "")
        self.api.addItem("Ollama", "ollama")
        self.api.setCurrentIndex(max(0, self.api.findData(cfg.assistant_local_runtime)))
        form.addRow(_("Kind of server"), self.api)
        self.model = QLineEdit(cfg.assistant_local_model)
        self.model.setPlaceholderText(_("the one the server serves"))
        form.addRow(_("Local model"), self.model)
        self.cloud_model = QComboBox()
        for key, text in costs.models().items():
            self.cloud_model.addItem(text, key)
        self.cloud_model.setCurrentIndex(max(0, self.cloud_model.findData(cfg.assistant_cloud_model)))
        form.addRow(_("Claude model"), self.cloud_model)
        inside.addLayout(form)
        row = QHBoxLayout()
        self.key_state = QLabel()
        self.key_state.setWordWrap(True)
        row.addWidget(self.key_state, 1)
        self.set_key = QPushButton(_("Set the key…"))
        self.set_key.clicked.connect(self._set_key)
        row.addWidget(self.set_key)
        self.forget_key = QPushButton(_("Remove the key"))
        self.forget_key.clicked.connect(self._forget_key)
        row.addWidget(self.forget_key)
        inside.addLayout(row)
        given = (cfg.assistant_consent.get("anthropic") or [""])[0]
        self.withdraw = QCheckBox(_("Withdraw the consent to send questions to Claude, given on {date}").format(
            date=given))
        self.withdraw.setVisible(bool(given))
        inside.addWidget(self.withdraw)
        note = QLabel(_("The key stays in the system's keyring; a project marked reserved never goes to the cloud."))
        note.setWordWrap(True)
        inside.addWidget(note)
        box.addWidget(group)
        self.voice = QCheckBox(_("{name} reads his answers aloud, in the language of the program").format(
            name=assistant.NAME))
        self.voice.setChecked(cfg.assistant_voice)
        box.addWidget(self.voice)
        # the natural voice (Kokoro) or the system's, and who speaks (ui/voice.py)
        from ..assistant import speech
        self.data_dir = data_dir
        speaking = QFormLayout()
        self.voice_engine = QComboBox()
        for key, text in (("auto", _("The natural one when it is on the PC, else the system's")),
                          ("kokoro", _("The natural one (Kokoro)")), ("system", _("The system's"))):
            self.voice_engine.addItem(text, key)
        self.voice_engine.setCurrentIndex(max(0, self.voice_engine.findData(cfg.assistant_voice_engine)))
        speaking.addRow(_("Voice"), self.voice_engine)
        self.voice_name = QComboBox()
        self.voice_name.addItem(_("A man's (Meridio is «he»)"), "")
        for key, text in speech.voice_names().items():
            self.voice_name.addItem(text, key)
        self.voice_name.setCurrentIndex(max(0, self.voice_name.findData(cfg.assistant_voice_name)))
        speaking.addRow(_("Who speaks"), self.voice_name)
        self.kokoro_dir = QLineEdit(cfg.assistant_kokoro_dir)
        self.kokoro_dir.setPlaceholderText(_("the folder with kokoro-v1.0.onnx and voices-v1.0.bin"))
        self.kokoro_dir.textChanged.connect(lambda _t: self._show_model())
        speaking.addRow(_("Kokoro's model"), self.kokoro_dir)
        self.kokoro_python = QLineEdit(cfg.assistant_kokoro_python)
        # the installed program has no Python of its own: the one found on the PATH, or none (speech.worker_python)
        own = not getattr(sys, "frozen", False)
        self.kokoro_python.setPlaceholderText(_("the program's own") if own else
                                              speech.worker_python("") or _("none found: a Python with kokoro-onnx"))
        speaking.addRow(_("Python for Kokoro"), self.kokoro_python)
        box.addLayout(speaking)
        self.model_state = QLabel()
        self.model_state.setWordWrap(True)
        box.addWidget(self.model_state)
        self.download = QPushButton(_("Download the natural voice (about 350 MB)…"))
        self.download.clicked.connect(self._download)
        box.addWidget(self.download, 0, Qt.AlignmentFlag.AlignLeft)
        self._show_model()
        self._show_key()

    def _use_local(self, url: str, model: str, api: str) -> None:
        """«Use it» on a local model found: the fields filled, the local model chosen (OK keeps it)."""
        self.url.setText(url)
        self.model.setText(model)
        self.api.setCurrentIndex(max(0, self.api.findData(api)))
        self.local.setChecked(True)

    def _download(self) -> None:
        """Kokoro's model from its official release into the data folder, after the designer said yes: a thread
        downloads, a progress window says how far and stops it (assistant/speech.download_model)."""
        import threading

        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QMessageBox, QProgressDialog

        from ..assistant import speech
        if self.data_dir is None:
            return
        dest = self.data_dir / "voices" / "kokoro"
        ask = QMessageBox.question(self, _("Natural voice"), _(
            "Download Kokoro's model (two files, about 350 MB) from its official release on GitHub "
            "({source}) into {folder}? Nothing of yours is sent.").format(source=speech.MODEL_SOURCE, folder=dest))
        if ask != QMessageBox.StandardButton.Yes:
            return
        state = {"done": 0, "total": 1, "stop": False, "error": None, "over": False}

        def run() -> None:
            try:
                speech.download_model(dest, lambda d, t: state.update(done=d, total=t), lambda: state["stop"])
            except speech.Stopped:
                pass
            except Exception as error:  # noqa: BLE001  said in the page, whatever the network or the disk says
                state["error"] = error
            state["over"] = True
        bar = QProgressDialog(_("Downloading the natural voice…"), _("Cancel"), 0, 1000, self)
        bar.setWindowTitle(_("Natural voice"))
        bar.setMinimumDuration(0)
        bar.canceled.connect(lambda: state.update(stop=True))
        thread = threading.Thread(target=run, name="kokoro-download", daemon=True)
        timer = QTimer(self)

        def tick() -> None:
            bar.setValue(int(1000 * state["done"] / max(1, state["total"])))
            bar.setLabelText(_("Downloading the natural voice: {done} of {total} MB").format(
                done=state["done"] // 1_000_000, total=state["total"] // 1_000_000))
            if state["over"]:
                timer.stop()
                bar.close()
                if state["error"] is not None:
                    self.model_state.setText(_("The download did not end: {why}").format(why=state["error"]))
                else:
                    self._show_model()
        timer.timeout.connect(tick)
        timer.start(150)
        thread.start()

    def _show_model(self) -> None:
        from ..assistant import speech
        found = speech.find_model(self.kokoro_dir.text().strip(), self.data_dir)
        self.download.setVisible(found is None and self.data_dir is not None)
        self.model_state.setText(
            _("Natural voice: the model is in {folder}.").format(folder=found) if found else
            _("Natural voice: no model on this PC. Its two files (kokoro-onnx 1.0, about 330 MB) go in the folder "
              "above, or in {folder}; the Python that runs it needs the package kokoro-onnx.").format(
                folder=(self.data_dir / "voices" / "kokoro") if self.data_dir else "voices/kokoro"))

    def _show_key(self) -> None:
        from ..assistant import keys
        try:
            key = keys.get("anthropic")
        except keys.KeyringMissing:
            self.key_state.setText(_("No keyring on this system: Claude cannot be used."))
            self.set_key.setEnabled(False)
            self.forget_key.setEnabled(False)
            return
        self.key_state.setText(_("Claude key in the system's keyring: {key}").format(key=keys.masked(key)) if key
                               else _("No Claude key yet."))
        self.forget_key.setEnabled(bool(key))

    def _set_key(self) -> None:
        from ..assistant import keys
        key, ok = QInputDialog.getText(self, _("Claude key"), _("Your Anthropic API key (it goes to the system's "
                                                               "keyring, never to a file):"), QLineEdit.EchoMode.Password)
        if ok and key.strip():
            keys.put("anthropic", key)
        self._show_key()

    def _forget_key(self) -> None:
        from ..assistant import keys
        try:
            keys.forget("anthropic")
        except keys.KeyringMissing as error:
            self.key_state.setText(_("The key could not be removed: {why}").format(why=error))
            return
        self._show_key()

    def choice(self) -> dict:
        return {"assistant_provider": "claude" if self.claude.isChecked() else "local",
                "assistant_local_url": self.url.text().strip() or "http://127.0.0.1:9931/v1",
                "assistant_local_model": self.model.text().strip(),
                "assistant_local_runtime": self.api.currentData() or "",
                "assistant_cloud_model": self.cloud_model.currentData(), "withdraw": self.withdraw.isChecked(),
                "assistant_voice": self.voice.isChecked(),
                "assistant_voice_engine": self.voice_engine.currentData(),
                "assistant_voice_name": self.voice_name.currentData(),
                "assistant_kokoro_dir": self.kokoro_dir.text().strip(),
                "assistant_kokoro_python": self.kokoro_python.text().strip()}


class ReportPage(QWidget):
    """Who signs the reports (R61, reports.py): profiles with the name and title, the register, the firm, the
    contacts and the logo, written here once and chosen for each project; the one for the projects that choose
    none. Nothing of them is in the program: they stay in the settings of this PC."""

    def __init__(self, cfg: config.Config, parent=None):
        super().__init__(parent)
        from .. import reports
        self.profiles = [p for p in (reports.clean_profile(x) for x in cfg.report_profiles) if p]
        self.current = -1
        self.loading = False
        box = QVBoxLayout(self)
        note = QLabel(_("Meridiana has no name in it: what you write here stays in the settings of this PC and is "
                        "printed only on the reports signed with that profile."))
        note.setWordWrap(True)
        box.addWidget(note)
        row = QHBoxLayout()
        self.chooser = QComboBox()
        self.chooser.currentIndexChanged.connect(self._chosen)
        row.addWidget(self.chooser, 1)
        add = QPushButton(_("New profile"))
        add.clicked.connect(self._add)
        row.addWidget(add)
        self.remove = QPushButton(_("Remove"))
        self.remove.clicked.connect(self._remove)
        row.addWidget(self.remove)
        box.addLayout(row)
        form = QFormLayout()
        labels = reports.profile_labels()
        self.fields: dict[str, QLineEdit] = {}
        hints = {"name": _("as you will choose it, for example «Studio»"), "signer": _("for example Ing. Name Surname"),
                 "register": _("register, province and number"), "web": "www…"}
        for key in ("name", "signer", "register", "firm", "address", "phone", "email", "web"):
            edit = QLineEdit()
            edit.setPlaceholderText(hints.get(key, ""))
            edit.textEdited.connect(lambda _t, key=key: self._typed(key))
            form.addRow(labels[key], edit)
            self.fields[key] = edit
        logo = QHBoxLayout()
        self.logo = QLabel("")
        self.logo.setWordWrap(True)
        logo.addWidget(self.logo, 1)
        choose = QPushButton(_("Choose…"))
        choose.clicked.connect(self._choose_logo)
        logo.addWidget(choose)
        self.drop_logo = QPushButton(_("Remove"))
        self.drop_logo.clicked.connect(lambda: self._set_logo(""))
        logo.addWidget(self.drop_logo)
        form.addRow(labels["logo"], logo)
        self.form = QWidget()
        self.form.setLayout(form)
        box.addWidget(self.form)
        default = QFormLayout()
        self.default = QComboBox()
        default.addRow(_("For the projects that choose none"), self.default)
        box.addLayout(default)
        box.addStretch(1)
        self._fill(0 if self.profiles else -1)
        self.default.setCurrentIndex(max(0, self.default.findData(cfg.report_profile)))

    def _fill(self, index: int) -> None:
        self.loading = True
        try:
            self.chooser.clear()
            for p in self.profiles:
                self.chooser.addItem(p["name"])
            keep = self.default.currentData() if self.default.count() else None
            self.default.clear()
            self.default.addItem(_("Nobody"), "")
            for p in self.profiles:
                self.default.addItem(p["name"], p["name"])
            if keep is not None:
                self.default.setCurrentIndex(max(0, self.default.findData(keep)))
            self.current = index
            self.chooser.setCurrentIndex(index)
            self.form.setEnabled(index >= 0)
            self.remove.setEnabled(index >= 0)
            p = self.profiles[index] if index >= 0 else {}
            for key, edit in self.fields.items():
                edit.setText(p.get(key, ""))
            self._show_logo(p.get("logo", ""))
        finally:
            self.loading = False

    def _show_logo(self, path: str) -> None:
        self.logo.setText(Path(path).name if path else _("none"))
        self.drop_logo.setEnabled(bool(path))

    def _chosen(self, index: int) -> None:
        if not self.loading and index != self.current:
            self._fill(index)

    def _typed(self, key: str) -> None:
        if self.loading or self.current < 0:
            return
        p = self.profiles[self.current]
        if key == "name":
            new = self.fields["name"].text().strip()
            if not new or any(q["name"] == new for i, q in enumerate(self.profiles) if i != self.current):
                return                          # a profile needs a name of its own: the last good one stays
            p["name"] = new
            self.loading = True
            self.chooser.setItemText(self.current, new)
            self.default.setItemText(self.current + 1, new)     # «Nobody» first, then the profiles in order
            self.default.setItemData(self.current + 1, new)
            self.loading = False
        else:
            p[key] = self.fields[key].text().strip()

    def _add(self) -> None:
        names = {p["name"] for p in self.profiles}
        name, n = _("Profile"), 1
        while name in names:
            n += 1
            name = f"{_('Profile')} {n}"
        self.profiles.append({k: "" for k in ("signer", "register", "firm", "address", "phone", "email", "web",
                                              "logo")} | {"name": name})
        self._fill(len(self.profiles) - 1)
        self.fields["name"].setFocus()
        self.fields["name"].selectAll()

    def _remove(self) -> None:
        if self.current < 0:
            return
        del self.profiles[self.current]
        self._fill(min(self.current, len(self.profiles) - 1))

    def _choose_logo(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        name, _f = QFileDialog.getOpenFileName(self, _("Logo of the report"), str(Path.home()),
                                               _("Images (*.png *.jpg *.jpeg)"))
        if name:
            self._set_logo(name)

    def _set_logo(self, path: str) -> None:
        if self.current >= 0:
            self.profiles[self.current]["logo"] = path
            self._show_logo(path)

    def choice(self) -> tuple[list, str]:
        """The profiles as written (a logo chosen now is still where it was: the window keeps a copy) and the one
        for the projects that choose none."""
        return [dict(p) for p in self.profiles], self.default.currentData() or ""


class Preferences(QDialog):
    def __init__(self, cfg: config.Config, bindings: dict, theme, parent=None, page: str = ""):
        super().__init__(parent)
        self.setWindowTitle(_("Preferences"))
        self.resize(680, 600)
        self.cfg = cfg
        box = QVBoxLayout(self)
        self.pages = QTabWidget()
        self.appearance = Appearance(cfg, theme, self)
        self.pages.addTab(self.appearance, _("Appearance"))
        self.navigation = NavigationPage(cfg, self)
        self.pages.addTab(self.navigation, _("Navigation"))
        self.keys = ShortcutsEditor(bindings, self)
        self.pages.addTab(self.keys, _("Keyboard"))
        panel = QWidget()                        # not `page`: that is the page asked for (study 18, G 9.5)
        inside = QVBoxLayout(panel)
        self.assistant = QCheckBox(_("Show {name}, the assistant, and its item in the status bar").format(
            name=assistant.NAME))
        self.assistant.setChecked(cfg.assistant)
        inside.addWidget(self.assistant)
        note = QLabel(_("Off, nothing of the assistant is left in the window: not the character, not the item in "
                        "the status bar, not its key (Ctrl+L)."))
        note.setWordWrap(True)
        inside.addWidget(note)
        self.assistant_docked = QCheckBox(_("Dock the conversation in the panels, as Project and Properties"))
        self.assistant_docked.setChecked(cfg.assistant_docked)
        inside.addWidget(self.assistant_docked)
        note = QLabel(_("Off, it floats over the views and the conversation opens as its speech bubble. The "
                        "conversation is the same either way; the button at its head does the same."))
        note.setWordWrap(True)
        inside.addWidget(note)
        self.assistant_animated = QCheckBox(_("{name} animated: the rays turn, the eyes blink and glance, a face "
                                              "now and then").format(name=assistant.NAME))
        self.assistant_animated.setChecked(cfg.assistant_animated)
        inside.addWidget(self.assistant_animated)
        note = QLabel(_("Off, or when the desktop asks for less motion, the character only changes expression "
                        "with its state, and the speech bubble opens and closes at once."))
        note.setWordWrap(True)
        inside.addWidget(note)
        form = QFormLayout()
        self.assistant_style = QComboBox()
        for key, name in (("smooth", _("Smooth")), ("pixel", _("Pixel"))):
            self.assistant_style.addItem(name, key)
        self.assistant_style.setCurrentIndex(max(0, self.assistant_style.findData(cfg.assistant_style)))
        form.addRow(_("Drawing"), self.assistant_style)
        inside.addLayout(form)
        paths = getattr(parent, "paths", None)
        # the window's search of the local models: a stand-in in the tests, which never knock at the PC's ports
        survey = getattr(getattr(parent, "assistant_chat", None), "survey", None)
        self.meridio = MeridioPage(cfg, panel, data_dir=getattr(paths, "data", None), survey=survey)
        inside.addWidget(self.meridio)
        inside.addStretch(1)
        scroll = QScrollArea()                   # the page is taller than the dialog: it scrolls
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(panel)
        self.assistant_page = scroll
        self.pages.addTab(scroll, _("Assistant"))
        self.report = ReportPage(cfg, self)
        self.pages.addTab(self.report, _("Report"))
        from .map_sources import MapsPage
        project = getattr(parent, "project", None)
        site = (project.site.lat, project.site.lon) if getattr(project, "site", None) is not None else None
        self.maps = MapsPage(cfg, site, network=lambda: self.privacy.tiles.isChecked())
        maps = QScrollArea()                     # taller than the dialog, as the assistant's page
        maps.setWidgetResizable(True)
        maps.setFrameShape(QScrollArea.Shape.NoFrame)
        maps.setWidget(self.maps)
        self.maps_page = maps
        self.pages.addTab(maps, _("Maps"))
        self.privacy = PrivacyPage(cfg, self)
        self.pages.addTab(self.privacy, _("Privacy"))
        box.addWidget(self.pages, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)
        self.show_page(page)

    def show_page(self, name: str) -> None:
        widget = {"appearance": self.appearance, "navigation": self.navigation, "keyboard": self.keys,
                  "assistant": self.assistant_page, "report": self.report, "maps": self.maps_page,
                  "privacy": self.privacy}.get(name)
        if widget is not None:
            self.pages.setCurrentWidget(widget)
