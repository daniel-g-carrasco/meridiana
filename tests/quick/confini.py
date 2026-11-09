"""The bounds check of the Quick window (R406): what the Widgets get from their layouts, walked here over the items.

Widgets cannot draw outside their parent and QFormLayout, FitArea and QScrollArea keep a card's contents in it
(tests/widget/test_nested_groups.py, test_properties.py, test_string_list.py). A Quick item can: nothing stops a Text
from standing over the status bar. `audit` walks the whole tree of one window in its present state and says, for what
is really visible (the clips of its ancestors applied):

    fuori-finestra    a text or a control past the window's edge
    barra-di-stato    a text or a control of a page over the status bar (Daniel's defect, R406)
    fuori-contenitore a text or a control out of the card, section or popup it belongs to
    tagliato          a text cut by a clip with no scrolling in that direction
    sforato           a text larger than its own box, not elided and not wrapped
    sovrapposto       two texts of the same layer over each other
    scheda-grande     a card or a popup larger than the window, or out of it
    senza-barra       a list that scrolls without a scroll bar
    senza-sfumature   a list that scrolls without the soft ends of Controls/EdgeFades (ui/fades.py)
    deformato         a control under the size its contents ask, or an icon button out of its proportions
    margini           a popup whose padding differs left and right

`EXCEPTIONS` holds what is accepted: every line with the reason, none by kind alone. A new one needs its reason.

Offscreen is enough for the logic (the layouts are the same; only glyphs differ by a pixel): `run` says which platform
it ran on. The real window on Direct3D runs with `tools/quick_native_input.py`, or with this file as a script, which
opens the same window on its own hidden desktop:

    python tests/quick/confini.py --out build/confini/report.json             the whole matrix, real windows, hidden
    python tests/quick/confini.py --scale 2 --themes dark --texts large       the same at 200 %
    python tests/quick/confini.py --platform offscreen --sizes 1600x960 --themes light --texts medium
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
import tempfile
import time

from PySide6.QtCore import QRectF

TOLERANCE = 1.5
MIN_OVERLAP = 3.0
UNCLIPPED = (-1e6, -1e6, 2e6, 2e6)
# Controls that only hold a page: the page's own items are what is checked.
CONTAINERS = ('QQuickContentItem', 'QQuickPage', 'QQuickStackView', 'ScrollView_QML',
              'QQuickScrollView', 'QQuickSplitView', 'SplitView_QML')
FIELD_MIN = 56      # a field that shows less than this shows no value (the narrowest in the Widgets: 60, with the arrows)


@dataclass(frozen=True)
class Finding:
    kind: str
    text: str
    where: str
    rect: tuple
    detail: str = ''

    def __str__(self):
        x, y, w, h = self.rect
        return f'{self.kind}: «{self.text[:60]}» at {x:.0f},{y:.0f} {w:.0f}x{h:.0f} in {self.where} {self.detail}'.rstrip()


# (kind, a part of the item's path or of its text, why it is accepted). A substring, so that a line stays narrow.
EXCEPTIONS: list[tuple[str, str, str]] = [
    ('sovrapposto', 'PlanHost', 'The labels of a drawing: they stand on the plan, over each other when zoomed out, as in the Widgets (ui/plan.py).'),
    ('sforato', 'viewCube', 'The faces of the cube: a word on a face drawn smaller than the word, scaled by the view; the Widgets do the same (ui/viewcube).'),
]


def _rect(r):
    return (r.x(), r.y(), r.width(), r.height())


def _intersect(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[0]+a[2], b[0]+b[2]), min(a[1]+a[3], b[1]+b[3])
    return (x1, y1, max(0.0, x2-x1), max(0.0, y2-y1))


def _sticks_out(inner, outer, tolerance=TOLERANCE):
    return (outer[0]-inner[0] > tolerance or outer[1]-inner[1] > tolerance or
            inner[0]+inner[2]-outer[0]-outer[2] > tolerance or inner[1]+inner[3]-outer[1]-outer[3] > tolerance)


def _class(item):
    return item.metaObject().className()


def _name(item):
    name = item.objectName()
    return name or _class(item).split('_QML')[0].replace('QQuick', '')


def _is_text(cls, item):
    return cls.startswith('Label_QML') or item.inherits('QQuickText') or item.inherits('QQuickTextInput') or item.inherits('QQuickTextEdit')


class _Walk:
    def __init__(self, window):
        self.window = window
        self.findings: list[Finding] = []
        self.texts: list[tuple] = []
        self.size = (0.0, 0.0, float(window.width()), float(window.height()))
        self.status = self._status_rect()

    def _status_rect(self):
        pending = [self.window.contentItem()]
        while pending:
            item = pending.pop()
            if item.objectName() == 'statusHint':
                parent = item.parentItem()
                return _rect(parent.mapRectToScene(parent.boundingRect())), parent
            pending.extend(item.childItems())
        return None, None

    def add(self, kind, text, where, rect, detail=''):
        self.findings.append(Finding(kind, text, where, tuple(round(v, 1) for v in rect), detail))

    def run(self):
        root = self.window.contentItem()
        self._visit(root, dict(clip=UNCLIPPED, cuts=(), card=None, layer='main', scroll=(False, False), opacity=1.0,
                               path='', status=False))
        self._overlaps()
        return self.findings

    def _visit(self, item, state):
        if not item.isVisible():
            return
        opacity = state['opacity']*item.opacity()
        if opacity < 0.05:
            return
        cls = _class(item)
        name = _name(item)
        here = dict(state, opacity=opacity, path=(state['path']+'/'+name)[-160:])
        if self.status[1] is item:
            here['status'] = True
        if cls.startswith('QQuickOverlay') or cls.startswith('QQuickPopupItem'):
            here['layer'] = 'popup:'+str(id(item)) if cls.startswith('QQuickPopupItem') else 'overlay'
            if cls.startswith('QQuickPopupItem'):
                here.update(card=_rect(item.mapRectToScene(item.boundingRect())), clip=UNCLIPPED, cuts=())
                self._popup(item, here)
        elif cls.startswith('Card_QML') or cls.startswith('DockPanel_QML') or item.property('sectionControl') is True:
            rect = _rect(item.mapRectToScene(item.boundingRect()))
            here['card'] = rect
            if cls.startswith(('Card_QML', 'DockPanel_QML')) and _sticks_out(rect, self.size):
                self.add('scheda-grande', str(item.property('title') or ''), here['path'], rect, 'card out of the window')
        flickable = item.inherits('QQuickFlickable')
        if flickable:
            here['scroll'] = self._flickable(item, here)
        if item.clip():      # the box, not boundingRect: a field's is as wide as its text
            rect = _rect(item.mapRectToScene(QRectF(0, 0, item.width(), item.height())))
            here['clip'] = _intersect(here['clip'], rect)
            here['cuts'] = here['cuts']+(name,)
        if _is_text(cls, item):
            self._text(item, here)
        elif item.inherits('QQuickControl') and not item.inherits('QQuickScrollBar') and not name.endswith('ContentControl') and not cls.startswith(CONTAINERS):
            self._control(item, here, cls)
        for child in item.childItems():
            self._visit(child, here)

    def _flickable(self, item, state):
        v = item.property('contentHeight') > item.height()+1 and item.property('interactive') is not False
        h = item.property('contentWidth') > item.width()+1 and item.property('interactive') is not False
        old = state['scroll']
        if v or h:
            kids = item.childItems()
            bar = any(k.inherits('QQuickScrollBar') or _class(k).startswith('ScrollBar_QML') for k in kids)
            if not bar and item.parentItem() is not None:      # a ScrollView keeps the bar beside its Flickable
                bar = any(k.inherits('QQuickScrollBar') for k in item.parentItem().childItems())
            if not bar:
                self.add('senza-barra', '', state['path'], _rect(item.mapRectToScene(item.boundingRect())),
                         f'contents {item.property("contentWidth"):.0f}x{item.property("contentHeight"):.0f}')
            if v and not self._has_fades(item):
                self.add('senza-sfumature', '', state['path'], _rect(item.mapRectToScene(item.boundingRect())))
        return (old[0] or v, old[1] or h)

    def _has_fades(self, flickable):
        names = ('topFade', 'bottomFade', 'scroll-fade-top', 'scroll-fade-bottom')
        for start in (flickable, flickable.parentItem()):
            pending = [(start, 0)] if start is not None else []
            while pending:
                item, depth = pending.pop()
                if item.objectName() in names:
                    return True
                if depth < 3:
                    pending.extend((c, depth+1) for c in item.childItems() if c is not flickable or depth == 0)
        return False

    def _bounds(self, shown, rect, state, label):
        """What holds for a text and for a control alike. `rect` the whole, `shown` what its clips leave."""
        if _sticks_out(shown, self.size):
            self.add('fuori-finestra', label, state['path'], shown)
        status = self.status[0]
        if status is not None and not state['status'] and state['layer'] == 'main':
            over = _intersect(shown, status)
            if over[2] > 1 and over[3] > 1:
                self.add('barra-di-stato', label, state['path'], shown)
        if state['card'] is not None and _sticks_out(shown, state['card']):
            self.add('fuori-contenitore', label, state['path'], shown, f'card {state["card"]}')

    def _text(self, item, state):
        text = item.property('text')
        if not isinstance(text, str) or not text.strip() or item.width() <= 0 or item.height() <= 0:
            return
        local = item.boundingRect()
        if item.inherits('QQuickText'):     # elided or wrapped, the laid out text stays in the box: no enum to read
            if local.width() > item.width()+TOLERANCE:
                self.add('sforato', text, state['path'], _rect(item.mapRectToScene(local)),
                         f'{local.width():.0f} wide in {item.width():.0f}')
            if local.height() > item.height()+2.5 and not self._inside_its_control(item, local):
                self.add('sforato', text, state['path'], _rect(item.mapRectToScene(local)),
                         f'{local.height():.0f} tall in {item.height():.0f}')
        rect = _rect(item.mapRectToScene(local))
        shown = _intersect(rect, state['clip'])
        if shown[2] <= 0 or shown[3] <= 0:
            return
        scroll_v, scroll_h = state['scroll']
        # A field scrolls its own text, a long placeholder too: that is how a line edit works, in the Widgets as well.
        parent = item.parentItem()
        if item.inherits('QQuickTextInput') or (parent is not None and parent.inherits('QQuickTextInput')):
            scroll_h = True
        if (rect[2]-shown[2] > TOLERANCE and not scroll_h) or (rect[3]-shown[3] > TOLERANCE and not scroll_v):
            self.add('tagliato', text, state['path'], rect, f'shown {shown[2]:.0f}x{shown[3]:.0f} by {state["cuts"][-1:]}')
        self._bounds(shown, rect, state, text)
        self.texts.append((shown, text, state['layer'], state['path'], item))

    def _inside_its_control(self, item, local):
        """The word of a button, taller than the box its padding leaves, still in the button: nothing is cut."""
        rect, parent = _rect(item.mapRectToScene(local)), item.parentItem()
        for _i in range(4):
            if parent is None:
                return False
            if parent.inherits('QQuickControl') or parent.inherits('QQuickTextInput'):
                return not _sticks_out(rect, _rect(parent.mapRectToScene(QRectF(0, 0, parent.width(), parent.height()))))
            parent = parent.parentItem()
        return False

    def _control(self, item, state, cls):
        if item.width() <= 0 or item.height() <= 0:
            return
        rect = _rect(item.mapRectToScene(item.boundingRect()))
        shown = _intersect(rect, state['clip'])
        if shown[2] <= 0 or shown[3] <= 0:
            return
        label = str(item.property('text') or item.property('tip') or _name(item))
        self._bounds(shown, rect, state, label)
        field = cls.startswith(('ComboBox_QML', 'TextField_QML', 'NumberField_QML', 'PlantChoice_QML'))
        if field and item.width() < FIELD_MIN:
            self.add('deformato', label, state['path'], rect, f'field {item.width():.0f} wide, under {FIELD_MIN}')
        icon = item.property('iconName')
        if isinstance(icon, str) and icon and not (item.property('text') or ''):
            ratio = item.width()/item.height()
            if not 0.8 <= ratio <= 1.5:
                self.add('deformato', label, state['path'], rect, f'icon button {item.width():.0f}x{item.height():.0f}')

    def _popup(self, item, state):
        rect = state['card']
        if _sticks_out(rect, self.size):
            self.add('scheda-grande', '', state['path'], rect, 'popup out of the window')
        control = item.property('popup') or item
        left, right = control.property('leftPadding'), control.property('rightPadding')
        if isinstance(left, (int, float)) and isinstance(right, (int, float)) and abs(left-right) > 1:
            self.add('margini', '', state['path'], rect, f'padding {left} and {right}')

    def _overlaps(self):
        texts = sorted(self.texts, key=lambda t: t[0][1])
        for at, (a, text, layer, path, item) in enumerate(texts):
            for b, other, other_layer, other_path, other_item in texts[at+1:]:
                if b[1] > a[1]+a[3]:
                    break
                if layer != other_layer or text == other or item is other_item:
                    continue
                over = _intersect(a, b)
                if over[2] > MIN_OVERLAP and over[3] > MIN_OVERLAP and not _related(item, other_item):
                    self.add('sovrapposto', f'{text} / {other}', path, over, other_path)


def _related(a, b):
    """A placeholder over its own field and a floating label over its own control are not a defect."""
    for one, two in ((a, b), (b, a)):
        parent = one.parentItem()
        for _i in range(3):
            if parent is None:
                break
            if parent is two:
                return True
            parent = parent.parentItem()
    return False


def excused(finding: Finding):
    return next((why for kind, part, why in EXCEPTIONS
                 if kind == finding.kind and (part in finding.where or part in finding.text)), None)


def audit(window, *, strict=False, settled=True):
    """The findings on `window` as it is now, the accepted ones left out (all of them with `strict`). With `settled` a
    finding must still be there a moment later: a form fading out over the new one is a transition, not a defect."""
    found = _Walk(window).run()
    if found and settled:
        from quick.gestures import pump
        pump(450)
        again = set(_Walk(window).run())
        found = [f for f in found if f in again]
    seen, unique = set(), []
    for f in found:
        if f not in seen and (strict or excused(f) is None):
            seen.add(f)
            unique.append(f)
    return unique


# The states. Each is a pair (name, function of the host); the function leaves the window in that state.
def _select(kind, index=0):
    def go(host):
        project = host.bridge.session.project
        if kind == 'site':
            oid = project.site.id if hasattr(project.site, 'id') else ''
            host.bridge.select('site', oid, '')
        elif kind == 'building':
            host.bridge.select('building', project.buildings[index].id, '')
        else:
            host.bridge.select(kind, getattr(project, kind+'s')[index].id, '')
    return go


def _plant(section, string=-1, subfield=False):
    def go(host):
        controllers = host.parts.controllers
        if subfield:
            project = host.bridge.session.project
            host.bridge.select('subfield', project.subfields[0].id, '')
        controllers['plantActions'].openSection(section)
        if string >= 0:
            controllers['plant'].selectString(string)
    return go


def _sweep(host):
    """Every module selected: the summary's place for the selection, full."""
    plan = host.plan
    plan.editor.swept = [(sfid, m.key) for sfid, result in plan.editor.results.items() for m in result.modules]
    plan._overlays()
    plan.stateChanged.emit()


def _unsweep(host):
    host.plan.editor.swept = []
    host.plan._overlays()
    host.plan.stateChanged.emit()
    host.parts.controllers['plant'].selectUnit(host.parts.controllers['plant'].working)


def _long_message(host):
    """What the proposal says when it ends: it stood under the sections, over the status bar (R406)."""
    host.parts.controllers['plant'].tell(
        'Impianto > Stringhe: 57 stringhe assegnate; 76 moduli restano senza collegamento. Scegli l\'inverter di lavoro '
        'e controlla i suoi ingressi. Annulla ripristina il cablaggio di prima.\nCondizioni di progetto di PVsyst, 60 e '
        '20 °C di cella, finché la producibilità non è calcolata.')


PHASES = ('model', 'plant', 'production', 'consumption', 'economics', 'report')
SUBSTATES = {
    'model': [('building', _select('building')), ('subfield', _select('subfield'))],
    'plant': [('panels', _plant('panels')), ('subfield', _plant('panels', subfield=True)), ('inverter', _plant('inverter')),
              ('string', _plant('inverter', string=0)), ('storage', _plant('storage')), ('message', _long_message), ('swept', _sweep), ('inverter-chosen', _unsweep)],
}
FILE_SECTIONS = ('open', 'save', 'export', 'catalogues', 'help', 'new', 'registry', 'preferences')
DIALOGS = ('new', 'site', 'canopy', 'template', 'shortcuts', 'registry', 'about', 'report_bug')


def settle(host, ms=320):
    from quick.gestures import pump
    pump(ms)


def workspace(host):
    from quick.gestures import item
    return item(host.window, 'workspace')


def set_panels(host, how):
    space = workspace(host)
    if how == 'wide':
        space.setProperty('rightExtent', min(560.0, host.window.width()*0.45))
        space.setProperty('leftExtent', min(420.0, host.window.width()*0.3))
    elif how == 'narrow':
        space.setProperty('rightExtent', host.window.property('panelMinimum') or 120.0)
        space.setProperty('leftExtent', 120.0)
    else:
        metrics = host.shell.metrics
        space.setProperty('rightExtent', metrics['rightWidth'])
        space.setProperty('leftExtent', metrics['leftWidth'])


def walk_states(host, dialogs=True):
    """Every state of one window at one size, theme and text: yields its name once the window is in it."""
    window = host.window
    for phase in PHASES:
        window.setProperty('fileOpen', False)
        window.showPhase(phase)
        settle(host)
        yield phase
        for name, go in SUBSTATES.get(phase, ()):
            go(host)
            settle(host)
            yield f'{phase}/{name}'
    files = host.parts.controllers.get('files')
    if files is not None:
        window.setProperty('fileOpen', True)
        settle(host, 500)
        for section in file_sections(files):
            files.selectSection(section)
            settle(host)
            yield f'file/{section}'
        window.setProperty('fileOpen', False)
        settle(host)
    if dialogs:
        window.showPhase('plant')
        settle(host)
        actions = host.parts.controllers['plantActions']
        for kind in ('catalog', 'sizing', 'proposal', 'storage', 'clear'):
            actions.open(kind)
            settle(host)
            yield f'dialog/plant-{kind}'
            actions.dismiss()
            settle(host, 120)
        chooser = host.parts.controllers.get('dialogs')
        if chooser is not None:
            window.showPhase('model')
            for kind in DIALOGS:
                chooser.open(kind)
                settle(host)
                yield f'dialog/{kind}'
                chooser.cancel()
                settle(host, 120)


def file_sections(files):
    from meridiana.quick.backend.settings import SECTIONS
    return [*FILE_SECTIONS, *(f'preferences:{section}' for section in SECTIONS)]


def run(host, *, sizes=((1600, 960), (1000, 640), (800, 560)), themes=('light', 'dark'), texts=('medium', 'large'),
        panels=('default', 'narrow', 'wide'), photos=None, log=None):
    """The matrix on one window. Returns {state: [findings]}, only the states with findings."""
    from PySide6.QtCore import Qt
    report: dict[str, list] = {}
    count = 0
    host.window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
    host.window.show()
    for theme in themes:
        host.theme.configure({'theme': theme})
        for text in texts:
            host.theme.configure({'textSize': text})
            for width, height in sizes:
                host.window.resize(width, height)
                settle(host, 200)
                for how in panels:
                    set_panels(host, how)
                    settle(host, 150)
                    for state in walk_states(host):
                        count += 1
                        found = audit(host.window)
                        if found:
                            key = f'{theme}/{text}/{width}x{height}/{how}/{state}'
                            report[key] = found
                            if photos is not None:
                                photos.mkdir(parents=True, exist_ok=True)
                                host.window.grabWindow().save(str(photos/(key.replace('/', '_')+'.png')))
                        if log is not None:
                            log(count, state, found)
    report['_count'] = count
    return report


def summary(report):
    """Findings grouped: kind and text, with how many states show them and one of the states."""
    groups: dict[tuple, list] = {}
    for key, found in report.items():
        if key == '_count':
            continue
        for f in found:
            groups.setdefault((f.kind, f.where[-70:], f.text[:50]), []).append(key)
    return sorted(((k, len(v), v[0]) for k, v in groups.items()), key=lambda g: (g[0][0], -g[1]))


def _open(project_path, cache):
    from meridiana import model
    from meridiana.quick.app import QuickWindow
    from meridiana.quick.sample import recorded_weather
    project, _notice = model.Project.load(project_path)
    recorded_weather(project, cache)
    return QuickWindow(project, cache, real_views=True, theme={'theme': 'light'})


def _child(args, size, panels, out):
    """One window in a process of its own: offscreen as asked, otherwise a real window on a hidden desktop, never on the
    one in use (tools/quick_native_input.py)."""
    import subprocess
    command = [sys.executable, '-X', 'faulthandler', str(Path(__file__).resolve()), '--project', args.project, '--out', str(out),
               '--sizes', size, '--panels', panels, '--themes', *args.themes, '--texts', *args.texts, '--one']
    if args.photos:
        command += ['--photos', str(args.photos)]
    env = dict(os.environ)
    if args.scale:
        env['QT_SCALE_FACTOR'] = str(args.scale)
    if args.platform:
        command += ['--platform', args.platform]
        done = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env)
        return done.returncode, done.stderr
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
    import ctypes
    from quick_native_input import kernel32, launch_on_hidden_desktop
    log = out.with_suffix('.log')
    handle, _pid = launch_on_hidden_desktop(command, log=log, desktop='meridiana-confini', env=env)
    kernel32.WaitForSingleObject(handle, 0xFFFFFFFF)
    code = ctypes.c_ulong()
    kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
    return code.value, log.read_text(errors='replace') if log.exists() else ''


def _write_whole(args, whole, start):
    written = dict(whole, groups=sorted(whole['groups'].values(), key=lambda g: (g['kind'], -g['states'])),
                   seconds=round(time.perf_counter()-start))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(written, indent=1, ensure_ascii=False), encoding='utf-8')
    return written


def _together(args):
    """The whole matrix, a process for each size and panels; the reports put together."""
    start, whole = time.perf_counter(), dict(states=0, findings={}, groups={}, warnings=[], failed=[])
    with tempfile.TemporaryDirectory(prefix='meridiana-confini-', ignore_cleanup_errors=True) as work:
        for size in args.sizes:
            for panels in args.panels:
                out = Path(work)/f'{size}-{panels}.json'
                code, errors = _child(args, size, panels, out)
                if code or not out.exists():
                    whole['failed'].append(dict(size=size, panels=panels, code=code, tail=errors[-800:]))
                    print(f'{size} {panels}: ended with {code}\n{errors[-800:]}')
                    continue
                part = json.loads(out.read_text(encoding='utf-8'))
                whole['states'] += part['states']
                whole['platform'], whole['scale'] = part['platform'], part['scale']
                whole['warnings'] += part['warnings']
                whole['findings'].update(part['findings'])
                for group in part['groups']:
                    key = (group['kind'], group['where'], group['text'])
                    seen = whole['groups'].setdefault(key, dict(group, states=0))
                    seen['states'] += group['states']
                print(f'{size} {panels}: {part["states"]} states, {len(part["findings"])} with findings', flush=True)
                _write_whole(args, whole, start)
    whole = _write_whole(args, whole, start)
    print(f'{whole["states"]} states on {whole.get("platform")}, scale {whole.get("scale")}, {len(whole["findings"])} with findings, '
          f'{len(whole["groups"])} kinds, {len(whole["failed"])} failed runs, {whole["seconds"]} s')
    for group in whole['groups'][:150]:
        print(f'{group["states"]:5} {group["kind"]:18} {group["text"]!r} :: {group["where"]} :: {group["first"]}')
    return 1 if whole['failed'] or whole['findings'] else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--project', default=str(Path.home()/'dev/meridiana-prove/Prova capannone Rho.meridiana'))
    parser.add_argument('--out', type=Path, default=Path('build/confini/report.json'))
    parser.add_argument('--photos', type=Path)
    parser.add_argument('--platform')
    parser.add_argument('--sizes', nargs='*', default=['1600x960', '1000x640', '800x560'])
    parser.add_argument('--themes', nargs='*', default=['light', 'dark'])
    parser.add_argument('--texts', nargs='*', default=['medium', 'large'])
    parser.add_argument('--panels', nargs='*', default=['default', 'narrow', 'wide'])
    parser.add_argument('--scale', type=float, help='QT_SCALE_FACTOR of the window')
    parser.add_argument('--one', action='store_true', help='one window in this process (used by the whole matrix)')
    args = parser.parse_args()
    if not args.one:
        return _together(args)
    if args.platform:
        os.environ['QT_QPA_PLATFORM'] = args.platform
    if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
        os.environ.setdefault('QSG_RENDER_LOOP', 'basic')       # see tests/quick/sistema/test_confini.py
    from meridiana.quick.app import create_app
    app = create_app()
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='meridiana-confini-', ignore_cleanup_errors=True) as work:
        host = _open(args.project, work)
        from quick.gestures import pump
        host.bridge.recompute()
        pump(3000)
        sizes = [tuple(int(v) for v in s.split('x')) for s in args.sizes]
        report = run(host, sizes=sizes, themes=args.themes, texts=args.texts, panels=args.panels, photos=args.photos)
        count = report.pop('_count')
        groups = summary(report)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(dict(
            platform=app.platformName(), scale=host.window.devicePixelRatio(), states=count,
            seconds=round(time.perf_counter()-start), warnings=host.warnings[:40],
            groups=[dict(kind=k[0], where=k[1], text=k[2], states=n, first=first) for k, n, first in groups],
            findings={key: [asdict(f) for f in found] for key, found in report.items()}),
            indent=1, ensure_ascii=False), encoding='utf-8')
        print(f'{count} states on {app.platformName()}, scale {host.window.devicePixelRatio():g}, '
              f'{sum(len(v) for v in report.values())} findings in {len(report)} states, {len(groups)} kinds of finding')
        for k, n, first in groups[:120]:
            print(f'{n:5} {k[0]:18} {k[2]!r} :: {k[1]} :: {first}')
        sys.stdout.flush()
        os._exit(0)     # a window of this run is not reused: what ends after the report is not what is checked


if __name__ == '__main__':
    # After PYTHONPATH: another checkout can be walked with this check (the branch before a change, say).
    sys.path += [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parents[2]/'src')]
    sys.exit(main())
