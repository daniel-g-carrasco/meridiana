"""Quick settings, sharing Config and its atomic writer with the Widgets application."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtQml import QJSValue
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import QKeyCombination, Qt

from meridiana import config, navigation, reports, shortcuts, theme_colors, tiles
from meridiana.i18n import number
from .settings_text import _
from . import settings_schema as schema
from .settings_schema import INTERNAL_FIELDS as INTERNAL_FIELDS, SECTIONS


class SettingsBackend(QObject):
    changed = Signal(str, 'QVariant')
    stateChanged = Signal()
    metadataChanged = Signal()
    sectionChanged = Signal()
    commandRequested = Signal(str)
    listened = Signal(str)          # the WAV of «Listen» once written (R492); played by `play`

    def __init__(self, cfg, config_path=None, theme=None, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.config_path = Path(config_path) if config_path is not None else None
        self.theme = theme
        self._section = 'appearance'
        self._error = ''
        self._history = []
        self._closed = False
        self._shortcut_proposal = None
        self.data_dir = None
        self.site = None
        self._pending = None
        self._typing = QTimer(self, singleShot=True, interval=400)
        self._typing.timeout.connect(self.flushPending)
        from .settings_services import SettingsServices
        self._services = SettingsServices(self)
        self._apply_theme()

    @Property(QObject, constant=True)
    def services(self):
        return self._services

    @Property('QVariantList', constant=True)
    def categories(self):
        return schema.categories()

    @Property(str, notify=sectionChanged)
    def section(self):
        return self._section

    @section.setter
    def section(self, value):
        self.showSection(value)

    @Slot(str)
    def showSection(self, section):
        if self._closed:
            return
        self.flushPending()
        if section in SECTIONS and section != self._section:
            self._section = section
            self._error = ''
            self.sectionChanged.emit()
            self.metadataChanged.emit()
            self.stateChanged.emit()

    @Property('QVariantMap', notify=stateChanged)
    def values(self):
        data = deepcopy(self.cfg.to_json())
        data['reduced_motion'] = bool(self.cfg.extra.get('reduced_motion', False))
        return data

    @Property(str, notify=stateChanged)
    def defaultProfile(self):
        return reports.default_profile(self.cfg.report_profiles, self.cfg.report_profile) or reports.NOBODY

    @Property('QVariantList', notify=metadataChanged)
    def fields(self):
        return schema.fields_for(self._section, self.cfg)

    @Property(bool, notify=stateChanged)
    def canUndo(self):
        return bool(self._history)

    @Property(bool, notify=stateChanged)
    def shortcutConflict(self):
        return self._shortcut_proposal is not None

    @Property(str, notify=stateChanged)
    def error(self):
        return self._error

    @Property('QVariantMap', constant=True)
    def text(self):
        return dict(undo=_('Undo the last change'), reset=_('Restore defaults for this section'),
                    confirm=_('Restore the default values of this section?'), restore=_('Restore defaults'),
                    cancel=_('Keep the current values'), preview=_('Preview'), custom=_('Another colour'),
                    layout=_('Restore the panel layout'), panels=_('Panels'), search=_('Search'), command=_('Command'), keys=_('Keys'),
                    building=_('Building 1'), south=_('Sub-field South'), east=_('Sub-field East'),
                    lay=_('Lay the modules'), warning=_('To check: the row pitch is below the limit angle'),
                    additional=_('Other settings'),
                    privacyChannel=_('Automatic installation is available for installed Windows builds. Flatpak updates come from your desktop software centre; portable and source builds are updated manually.'),
                    privacyRecovery=_('The project file keeps the images you import (without their metadata) and the recovery copy in the state folder keeps the whole project until it is saved.'),
                    newKeys=_('New keys'), defaults=_('Default'), allDefaults=_('All defaults'),
                    use=_('Use'), none=_('No key'), shortcutSearch=_('Search a command or a key'),
                    keyboardNote=_('Single letters work everywhere except while writing in a field. On a laptop the F keys may need Fn (or Fn+Esc to lock it).'),
                    privacyLead=_('Meridiana sends nothing about you anywhere. Three services receive what they need to answer, and each can be switched off here; off, the program uses what is already in the cache and says so.'),
                    reportLead=_('Meridiana has no name in it: what you write here stays in the settings of this PC and is printed only on the reports signed with that profile.'),
                    addProfile=_('New profile'), addMap=_('New source'), remove=_('Remove'),
                    profiles=_('Profiles'), sources=_('Your sources'), builtin=_("The program's sources"),
                      noProfiles=_('No profile yet. Add a profile to sign your reports.'), noLogo=_('none'),
                    mapBackground=_('Background of the plan'), atSite=_('At the site of the project'),
                    mapBackgroundNote=_("Automatic takes the best source for the site of each project: the open orthophoto of the region or of the country where there is one, else Sentinel-2 at 10 m. A source chosen here or in the plan's Background menu is used where it covers the site; elsewhere the automatic one is. The attribution of the source in use is always on the plan, at the bottom right."),
                    mapLicences=_("Each licence was read on its official page on 25/10/2026: the address and the date are in the tooltip. Esri, Google, Bing and Azure are not here: their terms want an account and a key and forbid keeping the tiles; they can be added below with your own key, under their terms."),
                    noSources=_('No custom map source yet.'), cloud=_('Cloud providers'), model=_('Model'),
                    endpoint=_('API address'), save=_('Apply'), key=_('Set the key…'), forget=_('Remove the key'),
                    consent=_('Withdraw all consent to send questions to cloud providers'),
                    capabilities=_('Read the capabilities'), layer=_('Layer'), searchLocal=_('Search again'),
                    localModels=_('Local models on this PC'), useLocal=_('Use it'),
                    choose=_('Choose…'), logo=_('Logo of the report'), logoFilter=_('Images (*.png *.jpg *.jpeg)'),
                    takeShortcut=_('Assign these keys and remove them from the other commands'),
                    testLocal=_('Test'), stop=_('Cancel'),
                    downloadVoice=_('Download the natural voice (about 350 MB)…'),
                    downloadNote=_("Download Kokoro's model (two files, about 350 MB) from its official release on GitHub into the folder above. Licence: Apache-2.0. Nothing of yours is sent."),
                    cloudNote=_('Saving makes no API request. Sending a question asks for consent first.'),
                    keyNote=_("The key stays in the system's keyring; a project marked reserved never goes to the cloud."))

    @Property('QVariantMap', notify=stateChanged)
    def appearancePreview(self):
        dark = self.theme.dark if self.theme is not None else self.cfg.theme == 'dark'
        derived = theme_colors.derive(theme_colors.seed_for(self.cfg.accent), dark, self.cfg.backgrounds)
        report = derived.report
        return dict(contrast=_('Text on the colour {a}:1, the colour on the view {b}:1 (at least 4.5:1).').format(
            a=number(report.on_accent, 1), b=number(report.on_view, 1)),
            note=theme_colors.retouch_note(report, dark) or _('The colour is used as it is.'))

    @Property('QVariantList', notify=stateChanged)
    def shortcutRows(self):
        bindings = shortcuts.bindings(self.cfg.shortcuts)
        defaults = shortcuts.bindings({})
        return [dict(key=c.id, label=shortcuts.plain(c.text), group=shortcuts.groups().get(c.group, ''),
                     keys='; '.join(bindings[c.id]), defaults='; '.join(defaults[c.id])) for c in shortcuts.commands()]

    @Slot(int, int, result=str)
    def captureKey(self, key, modifiers):
        return QKeySequence(QKeyCombination(Qt.KeyboardModifier(modifiers), Qt.Key(key))).toString()

    @Slot(str)
    def defaultShortcut(self, command):
        self.setShortcut(command, shortcuts.bindings({}).get(command, []))

    @Property('QVariantList', constant=True)
    def profileFields(self):
        labels = reports.profile_labels()
        hints = dict(name=_("as you will choose it, for example «Studio»"), signer=_('for example Ing. Name Surname'),
                     register=_('register, province and number'), web='www…', accent=_('#1c6e8c, the blue of the report when empty'))
        return [dict(key=key, label=labels[key], hint=hints.get(key, '')) for key in ('name', 'signer', 'register', 'firm', 'address', 'phone', 'email', 'web', 'accent', 'logo')]

    @Property('QVariantList', constant=True)
    def mapFields(self):
        return [dict(key=key, label=label) for key, label in (
            ('name', _('Name')), ('kind', _('Type')), ('url', _('Address')), ('attribution', _('Attribution')),
            ('licence', _('Licence')), ('licence_url', _('Licence address')), ('imagery', _('It is')),
            ('max_zoom', _('Highest zoom')), ('layer', _('Layer')), ('crs', _('Coordinate reference system')),
            ('matrix_set', _('Tile matrix set')), ('capabilities', _('Capabilities address')))]

    @Property('QVariantList', constant=True)
    def mapImageryOptions(self):
        return [dict(value='photo', label=_('Photo')), dict(value='map', label=_('Map'))]

    @Property(int, constant=True)
    def mapMaxZoom(self):
        return tiles.MAX_ZOOM

    @Property(bool, notify=metadataChanged)
    def hasSite(self):
        return self.site is not None

    @Property('QVariantList', notify=metadataChanged)
    def siteSources(self):
        from meridiana.ui.map_sources import _rows
        sources = tiles.covering(tiles.catalogue(self.cfg.map_sources), self.site[1], self.site[0]) if self.site else []
        return [dict(name=n, licence=l, tip=t) for n, l, t in _rows(sources)]

    @Property('QVariantList', constant=True)
    def sourceRows(self):
        from meridiana.ui.map_sources import _rows
        return [dict(name=n, licence=l, tip=t) for n, l, t in _rows(tiles.SOURCES.values())]

    @Property('QVariantList', constant=True)
    def builtinSources(self):
        return [dict(name=tiles.display_name(s), licence=tiles.display_licence(s), attribution=s.credit(),
                     url=s.licence_url, checked=s.checked) for s in tiles.SOURCES.values()]

    @Property('QVariantList', notify=stateChanged)
    def cloudProfiles(self):
        from meridiana.assistant import setup
        return [dict(key=k, label=v.name, **setup.profile(self.cfg, k)) for k, v in setup.CLOUD.items()]

    @Property('QVariantMap', notify=stateChanged)
    def navigationHelp(self):
        keys = navigation.orbit_key_text(self.cfg.navigation)
        hint = _("With the orbit's key held ({keys} in this style) and the mouse moving, a cross-hair shows where the orbit would turn.").format(keys=keys) if keys else _('This style orbits with a button alone, with no key to hold: the pivot shows only while orbiting.')
        return dict(audience=navigation.audience(self.cfg.navigation), hint=hint,
                    note=_('A gesture is the buttons and keys held while the mouse moves. The same styles as FreeCAD, plus AutoCAD and SketchUp. The plan pans and zooms the same way; the orbit is for the 3D view.'),
                    gestures=[dict(action=a, gesture=g) for a, g in navigation.table(self.cfg.navigation)])

    @Slot()
    def refresh(self):
        self.metadataChanged.emit()
        self.stateChanged.emit()

    def _fail(self, message):
        if self._closed:
            return False
        self._error = str(message)
        self.stateChanged.emit()
        return False

    def _get(self, key):
        return self.cfg.extra.get(key, False) if key == 'reduced_motion' else getattr(self.cfg, key)

    def _apply_theme(self):
        if self.theme is not None:
            self.theme.configure({key: getattr(self.cfg, key) for key in
                                  ('theme', 'accent', 'backgrounds', 'font', 'text_size')} |
                                 {'reduced_motion': bool(self.cfg.extra.get('reduced_motion', False))})

    def _validate(self, key, value):
        if key not in {k for values in SECTIONS.values() for k in values}:
            raise ValueError(_('Unknown setting: {key}').format(key=key))
        if key == 'reduced_motion':
            if type(value) is not bool:
                raise ValueError(_('Choose on or off.'))
            return
        config.Config.from_json({key: value})
        if key == 'report_profile' and value == '':
            return  # No explicit choice: resolve the sole profile, or Nobody.
        choices = schema.choices(self.cfg).get(key)
        if choices and value not in choices:
            if key != 'accent' or not theme_colors.valid_hex(value):
                raise ValueError(_('Choose one of the available values.'))
        if key == 'veil' and not 0 <= value <= 1:
            raise ValueError(_('Enter a value between 0 and 1.'))
        if key in schema.RANGES and key not in ('veil', 'size', 'assistant_voice_pitch', 'assistant_voice_speed'):
            low, high, _decimals = (schema.RANGES[key][name] for name in ('minimum', 'maximum', 'decimals'))
            if not low <= value <= high:
                raise ValueError(_('Enter a value between {low} and {high}.').format(low=number(low, _decimals),
                                                                                    high=number(high, _decimals)))
        if key == 'assistant_voice_pitch' and not -3 <= value <= 4:
            raise ValueError(_('Enter a value between {low} and {high}.').format(low=-3, high=4))
        if key == 'assistant_voice_speed' and not 0.8 <= value <= 1.4:
            raise ValueError(_('Enter a value between {low} and {high}.').format(low=number(0.8), high=number(1.4)))
        if key in ('assistant_width', 'assistant_height') and not 160 <= value <= 2400:
            raise ValueError(_('Enter a size between 160 and 2400 pixels.'))
        if key in ('report_profiles', 'map_sources') and (not isinstance(value, list) or
                any(not isinstance(item, dict) for item in value)):
            raise ValueError(_('Use a list of records.'))

    def _commit(self, changes, record=True, validate=True):
        if self._closed:
            return False
        changes = {k: deepcopy(v) for k, v in changes.items() if self._get(k) != v}
        if not changes:
            self._error = ''
            self.stateChanged.emit()
            return True
        try:
            if validate:
                for key, value in changes.items():
                    self._validate(key, value)
            candidate = deepcopy(self.cfg)
            before = {key: deepcopy(self._get(key)) for key in changes}
            for key, value in changes.items():
                if key == 'reduced_motion':
                    candidate.extra[key] = value
                else:
                    setattr(candidate, key, value)
            if self.config_path is not None:
                config.save(candidate, self.config_path)
        except (ValueError, TypeError, OSError) as error:
            return self._fail(error)
        for key, value in changes.items():
            if key == 'reduced_motion':
                self.cfg.extra[key] = deepcopy(value)
            else:
                setattr(self.cfg, key, deepcopy(value))
        if record:
            self._history.append(before)
            del self._history[:-30]
        self._error = ''
        self._apply_theme()
        if changes.keys() & {'report_profiles', 'map_sources', 'check_updates', 'navigation'}:
            self.metadataChanged.emit()
        self.stateChanged.emit()
        for key, value in changes.items():
            self.changed.emit(key, value)
        return True

    @Slot(str, 'QVariant', result=bool)
    def setValue(self, key, value):
        self.flushPending()
        if isinstance(value, QJSValue):
            value = value.toVariant()
        if key == 'assistant_voice_pitch' and isinstance(value, float) and value.is_integer():
            value = int(value)          # the number field gives 2.0 for 2
        if key == 'assistant_voice_speed' and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        try:
            self._validate(key, value)
        except (ValueError, TypeError) as error:
            return self._fail(error)
        return self._commit({key: value})

    @Slot(str)
    def runAction(self, action):
        """A field's button (SettingField.qml): «Listen» beside the voice's speed."""
        if action == 'listen':
            self.listen()

    def listen(self, out=None, language=None):
        """A sentence of trial with the voice, the pitch and the speed of the settings (R492), written by Kokoro's
        worker in a process of its own into a WAV file, then played. The window does not wait."""
        import json
        import sys
        import tempfile

        from PySide6.QtCore import QProcess

        from meridiana.assistant import context, speech
        folder = speech.find_model(self.cfg.assistant_kokoro_dir)
        if folder is None:
            return self._fail(_('Kokoro is not on this PC: download its model in Settings > Assistant.'))
        language = language or context.language()
        pitch, speed = speech.voice_settings(self.cfg)
        request = {"text": speech.speakable(speech.LISTEN.get(language, speech.LISTEN["en"]), language),
                   "voice": speech.voice_for(language, self.cfg.assistant_voice_name), "lang": language,
                   "speed": speed, "pitch": pitch}
        out = Path(out) if out else Path(tempfile.gettempdir()) / 'meridiana-ascolta.wav'
        python = speech.worker_python(self.cfg.assistant_kokoro_python, model_dir=folder)
        args = [str(speech.worker_script()), "--dir", str(folder)]
        if getattr(sys, "frozen", False) and python == sys.executable:
            args = ["--kokoro-worker", "--dir", str(folder)]
        process = QProcess(self)
        process.setProgram(python)
        process.setArguments(args + ["--wav", str(out), json.dumps(request, ensure_ascii=False)])
        process.finished.connect(lambda code, _status: self._listened(process, out, code))
        self._listening = process
        process.start()
        return True

    def _listened(self, process, out, code):
        why = bytes(process.readAllStandardError()).decode("utf-8", "replace").strip()
        process.deleteLater()
        self._listening = None
        if code != 0 or not out.is_file():
            return self._fail(_('The sentence of trial did not come: {why}').format(why=why or code))
        self.play(out)
        self.listened.emit(str(out))

    def play(self, path):
        from PySide6.QtMultimedia import QSoundEffect
        self._effect = QSoundEffect(self)
        self._effect.setSource(QUrl.fromLocalFile(str(path)))
        self._effect.play()

    @Slot(result=bool)
    def undoLast(self):
        self.flushPending()
        if not self._history:
            return False
        if not self._commit(self._history[-1], record=False, validate=False):
            return False
        self._history.pop()
        self.stateChanged.emit()
        return True

    @Slot(str, result=bool)
    def restoreDefaults(self, section):
        self.flushPending()
        if section not in SECTIONS:
            return self._fail(_('Unknown section.'))
        defaults = config.Config(theme='light', accent='indigo', backgrounds='grey', font='plex')
        changes = {key: False if key == 'reduced_motion' else getattr(defaults, key) for key in SECTIONS[section]}
        if section == 'keyboard':
            changes['shortcuts'] = shortcuts.differences(shortcuts.bindings({}), self.cfg.shortcuts)
        return self._commit(changes, validate=False)

    @Slot(str, 'QVariantList', result=bool)
    def setShortcut(self, command, keys):
        self._shortcut_proposal = None
        current = shortcuts.bindings(self.cfg.shortcuts)
        if command not in current or any(not isinstance(k, str) for k in keys):
            return self._fail(_('Unknown command or invalid keys.'))
        normalized = list(dict.fromkeys(shortcuts.normalize(k) for k in keys if k.strip()))
        for key in normalized:
            reason = shortcuts.problem(key)
            if reason:
                return self._fail(reason)
            clashes = shortcuts.clashes(current, command, key)
            if clashes:
                self._shortcut_proposal = (command, normalized)
                labels = {c.id: shortcuts.plain(c.text) for c in shortcuts.commands()}
                return self._fail(_('Already used by: {commands}').format(commands=', '.join(labels[c] for c in clashes)))
        current[command] = normalized
        return self.setValue('shortcuts', shortcuts.differences(current, self.cfg.shortcuts))

    @Slot(result=bool)
    def takeShortcut(self):
        if self._shortcut_proposal is None:
            return False
        command, keys = self._shortcut_proposal
        current = shortcuts.bindings(self.cfg.shortcuts)
        for other in current:
            current[other] = [key for key in current[other] if key not in keys]
        current[command] = keys
        result = self.setValue('shortcuts', shortcuts.differences(current, self.cfg.shortcuts))
        if result:
            self._shortcut_proposal = None
            self.stateChanged.emit()
        return result

    def setDataDirectory(self, folder):
        """Supply the shell's existing Paths.data; no user paths are guessed."""
        self.data_dir = Path(folder)

    @Slot(result=bool)
    def addProfile(self):
        self.flushPending()
        profiles = deepcopy(self.cfg.report_profiles)
        number = len(profiles) + 1
        while any(p.get('name') == f'{_("Profile")} {number}' for p in profiles):
            number += 1
        profiles.append(dict.fromkeys(reports.PROFILE_KEYS, '') | {'name': f'{_("Profile")} {number}'})
        return self.setValue('report_profiles', profiles)

    @Slot(int, str, str, result=bool)
    def editProfile(self, index, key, value):
        self.flushPending()
        profiles = deepcopy(self.cfg.report_profiles)
        if not 0 <= index < len(profiles) or key not in reports.PROFILE_KEYS:
            return self._fail(_('Choose a profile.'))
        value = value.strip()
        if key == 'name' and (not value or any(i != index and p.get('name') == value for i, p in enumerate(profiles))):
            return self._fail(_('Choose a unique profile name.'))
        if key == 'accent' and value and not theme_colors.valid_hex(value):
            return self._fail(_('Use a colour such as #1c6e8c.'))
        if key == 'logo' and value:
            if value.startswith('file:'):
                value = QUrl(value).toLocalFile()
            from meridiana.ui.report import logo_problem
            problem = logo_problem(Path(value))
            if problem:
                return self._fail(problem)
            if self.data_dir is not None:
                try:
                    source = Path(value)
                    data = source.read_bytes()
                    folder = self.data_dir / 'logos'
                    folder.mkdir(parents=True, exist_ok=True)
                    destination = folder / f'{source.stem}-{hashlib.sha256(data).hexdigest()[:12]}{source.suffix.lower()}'
                    if destination.exists():
                        if destination.read_bytes() != data:
                            return self._fail(_('A different logo already has that file name.'))
                    else:
                        with destination.open('xb') as stream:
                            stream.write(data)
                    value = destination.name
                except OSError as error:
                    return self._fail(_('The logo could not be copied: {error}').format(error=error))
        old_name = profiles[index].get('name', '')
        profiles[index][key] = value
        changes = {'report_profiles': profiles}
        if key == 'name' and self.cfg.report_profile == old_name:
            changes['report_profile'] = value
        return self._commit(changes, validate=False)

    @Slot(int, result=bool)
    def removeProfile(self, index):
        self.flushPending()
        profiles = deepcopy(self.cfg.report_profiles)
        if not 0 <= index < len(profiles):
            return False
        removed = profiles.pop(index)
        changes = {'report_profiles': profiles}
        if self.cfg.report_profile == removed.get('name'):
            changes['report_profile'] = ''
        return self._commit(changes)

    @Slot(result=bool)
    def addMapSource(self):
        self.flushPending()
        sources = deepcopy(self.cfg.map_sources)
        sources.append(dict(key=tiles.new_key(), name=_('New source'), kind='xyz', url='', attribution='',
                            licence='', licence_url='', imagery='photo', max_zoom=19))
        return self.setValue('map_sources', sources)

    @Slot(int, str, 'QVariant', result=bool)
    def editMapSource(self, index, key, value):
        self.flushPending()
        sources = deepcopy(self.cfg.map_sources)
        if not 0 <= index < len(sources) or key not in {f['key'] for f in self.mapFields}:
            return self._fail(_('Choose a source.'))
        if key == 'max_zoom':
            try:
                value = int(value)
            except (ValueError, TypeError):
                return self._fail(_('Enter a whole number.'))
            if not 1 <= value <= tiles.MAX_ZOOM:
                return self._fail(_('Zoom is outside the allowed range.'))
        elif not isinstance(value, str):
            return self._fail(_('Enter text.'))
        if key == 'kind' and value not in tiles.KINDS or key == 'imagery' and value not in tiles.IMAGERY:
            return self._fail(_('Choose one of the available values.'))
        sources[index][key] = value
        return self.setValue('map_sources', sources)

    @Slot(int, result=str)
    def mapProblems(self, index):
        return '\n'.join(tiles.problems(self.cfg.map_sources[index])) if 0 <= index < len(self.cfg.map_sources) else ''

    @Slot(int, result=bool)
    def removeMapSource(self, index):
        self.flushPending()
        sources = deepcopy(self.cfg.map_sources)
        if not 0 <= index < len(sources):
            return False
        removed = sources.pop(index)
        changes = {'map_sources': sources}
        if self.cfg.background == removed.get('key'):
            changes['background'] = 'auto'
        return self._commit(changes)

    @Slot(str, str, str, result=bool)
    def setCloudProfile(self, provider, model, endpoint):
        from meridiana.assistant import setup
        try:
            if provider not in setup.CLOUD:
                raise ValueError(_('Choose a provider.'))
            if not model.strip():
                raise ValueError(_('Enter the model name.'))
            endpoint = setup.validate_endpoint(endpoint)
            candidate = deepcopy(self.cfg)
            setup.remember(candidate, provider, model.strip(), endpoint)
            return self._commit({'assistant_cloud_profiles': candidate.assistant_cloud_profiles,
                                 'assistant_cloud_model': candidate.assistant_cloud_model})
        except ValueError as error:
            return self._fail(error)

    @Slot(str, str, str, result=bool)
    def setSecret(self, provider, secret, service):
        if self._closed:
            return False
        from meridiana.assistant import keys, setup
        if service not in (keys.SERVICE, 'meridiana-maps'):
            return self._fail(_('Unknown key service.'))
        try:
            if secret.strip():
                keys.put(provider, secret, service)
            else:
                keys.forget(provider, service)
            setup.keys_changed()
        except keys.KeyringMissing as error:
            return self._fail(_('The system keyring is not available: {reason}').format(reason=error))
        self._error = ''
        self.stateChanged.emit()
        return True

    @Slot(str)
    def requestCommand(self, command):
        self.flushPending()
        self.commandRequested.emit(command)

    def _stage(self, kind, index, key, value):
        if self._closed:
            return
        identity = (kind, index, key)
        if self._pending is not None and self._pending[:3] != identity:
            self.flushPending()
        self._pending = (*identity, value)
        self._typing.start()

    @Slot(str, str)
    def stageValue(self, key, value):
        self._stage('value', -1, key, value)

    @Slot(int, str, str)
    def stageProfile(self, index, key, value):
        self._stage('profile', index, key, value)

    @Slot(int, str, str)
    def stageMapSource(self, index, key, value):
        self._stage('map', index, key, value)

    @Slot()
    def flushPending(self):
        self._typing.stop()
        pending, self._pending = self._pending, None
        if pending is None:
            return
        kind, index, key, value = pending
        if kind == 'value':
            self.setValue(key, value)
        elif kind == 'profile':
            self.editProfile(index, key, value)
        else:
            self.editMapSource(index, key, value)

    @Slot()
    def close(self):
        """Flush typed edits before the engine closes, then cancel/disconnect work."""
        if self._closed:
            return
        self.flushPending()
        self._services.close()
        self._closed = True


def install_settings(engine, cfg, config_path=None, theme=None):
    """Install controls and expose a backend; the shell may instead pass it explicitly."""
    from .controls import install_controls
    installed_theme = install_controls(engine, theme)
    backend = SettingsBackend(cfg, config_path, installed_theme, engine)
    engine.rootContext().setContextProperty('settingsBackend', backend)
    engine._settings_backend = backend
    return backend
