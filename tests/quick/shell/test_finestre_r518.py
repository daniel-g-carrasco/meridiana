"""R518, R519, R520, R524, R525: the windows, the tabs' hover, the scroll bars, the sections' heads and the menus,
measured on the window's picture at 1, 1.5 and 2.

R518 (Daniel 07/11/2026: «le finestre non sono congruenti… quella della stringatura in automatico non ha gli stessi
margini che hanno le altre»): every window of the program opened one by one; on its picture the ink inside the frame
(pixels away from the window's ground) is as far from the frame on the left, the right and the bottom as in every
other, the title's ink as far from the top, the buttons as far from the right and the bottom side: one value each,
within one device pixel. R519: a phase tab under the pointer as far from the open tab at its right as at its left.
R520: no text of a list, a table or a page that scrolls under its bar. R524: a section's head under the pointer one
colour from its top to its bottom. R525: the entry under the pointer in a combo's list as in a menu: the same grey,
the same distance from the list's sides.

    python -m unittest quick.shell.test_finestre_r518
    python tests/quick/shell/test_finestre_r518.py shot <folder> <label> [root]     (pictures for the comparison)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

CHILD = r'''
import json, os, sys, tempfile
from pathlib import Path
os.environ.setdefault('QSG_RENDER_LOOP', 'basic')
import _setup
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent
from meridiana import i18n, jobs
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import click, item, mouse, pump
from quick.parity.differential import connected_fixture

app = _setup.qt_or_skip()
create_app()
i18n.setup('it')
project = connected_fixture()
results, keys, _laid = jobs.layout_of(project)
folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
# the tests' clear-sky year inside the project, so that the comparison of the variants has its figures offline
try:
    from _fixtures import clear_sky_meteo, write_cache
    from meridiana import atomic
    from meridiana.energy import meteo
    weather = Path(folder.name) / 'weather'
    write_cache(clear_sky_meteo(), weather)
    for lat, lon in ((project.site.lat, project.site.lon), (45.5226, 9.03)):
        if meteo._cache_file(weather, 'tmy', lat, lon).exists():
            raw, _ = atomic.read_json(meteo._cache_file(weather, 'tmy', lat, lon))
            project.climate = dict(getattr(project, 'climate', {}) or {}, tmy=raw)
            break
except Exception as error:          # the capture goes on; the comparison then says what is missing
    print('no weather:', error, file=sys.stderr)
host = QuickWindow(project, Path(folder.name), real_views=True, theme={'theme': 'light'})
host.bridge.accept_layout(host.bridge.session.generation, results, keys)
win = host.window
win.resize(1600, 960)
win.show()
out = {'dialogs': {}, 'scroll': [], 'menus': {}}
shot = os.environ.get('R518_SHOT')
NAMES = ('panel', 'window', 'hover', 'line', 'card_line', 'card')
image = None
try:
    component = QQmlComponent(host.engine)
    component.setData(('import QtQuick\nimport Meridiana.Theme\nQtObject { '
                       + '; '.join(f'property color {n}: Theme.colors.{n}' for n in NAMES) + ' }').encode(),
                      QUrl('file:///r518.qml'))
    colours = component.create()
    raw = {k: QColor(colours.property(k)) for k in NAMES}

    def over(colour, ground):
        a = colour.alphaF()
        return tuple(round(getattr(colour, k)() * a + getattr(ground, k)() * (1 - a)) for k in ('red', 'green', 'blue'))

    c = {k: over(v, raw['panel']) for k, v in raw.items()}
    ctx = host.engine.rootContext()
    plant, actions = ctx.contextProperty('plantBackend'), ctx.contextProperty('plantActions')
    tasks = ctx.contextProperty('shellTasks')
    host.shell.trigger('phase_plant')
    pump(1500)
    dpr = win.devicePixelRatio()

    def grab():
        global image
        image = win.grabWindow()

    def rgb(x, y):
        p = image.pixelColor(int(x), int(y))
        return p.red(), p.green(), p.blue()

    def dist(a, b):
        return sum((p - q) ** 2 for p, q in zip(a, b)) ** .5

    def rect(obj):
        p = obj.mapToScene(QPointF(0, 0))
        return p.x() * dpr, p.y() * dpr, obj.width() * dpr, obj.height() * dpr

    def walk(root):
        pending = [root]
        while pending:
            obj = pending.pop()
            yield obj
            pending.extend(obj.childItems())

    def shown(obj):
        while obj is not None:
            if not obj.isVisible():
                return False
            obj = obj.parentItem()
        return True

    def away():
        mouse(app, win, QEvent.Type.MouseMove, QPointF(3, win.height() - 3), Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
        pump(250)

    def move_to(obj, fx=.5, fy=.5):
        p = obj.mapToScene(QPointF(obj.width() * fx, obj.height() * fy))
        mouse(app, win, QEvent.Type.MouseMove, p, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
        pump(350)

    def save(name, r, pad=8):
        if shot:
            Path(shot).mkdir(parents=True, exist_ok=True)
            x, y = max(0, int(r[0] - pad * dpr)), max(0, int(r[1] - pad * dpr))
            image.copy(x, y, int(r[2] + 2 * pad * dpr), int(r[3] + 2 * pad * dpr)).save(str(Path(shot) / f'{name}.png'))

    # R519: the hover of the tab at the left and at the right of the open one (Impianto)
    tabs = {}
    for name, step in (('modelTab', -1), ('productionTab', 1)):
        tab = item(win, name)
        move_to(tab)
        grab()
        veil = over(raw['hover'], raw['window'])
        r, o = rect(tab), rect(item(win, 'plantTab'))
        cy = int(r[1] + r[3] / 2)
        # from the open tab's side outwards: past its outline, then the ground up to the hover's first pixel
        x = int(o[0]) + 2 if step < 0 else int(o[0] + o[2]) - 3
        while dist(rgb(x, cy), c['panel']) <= 6:
            x += step                       # the open tab's own ground
        while dist(rgb(x, cy), veil) > 6 and dist(rgb(x, cy), raw['window'].getRgb()[:3]) > 6:
            x += step                       # its outline
        n = 0
        while n < 80 and dist(rgb(x + step * n, cy), veil) > 6:
            n += 1
        tabs[name] = n
        save(f'tab-{name}', (min(r[0], o[0]), r[1], abs(o[0] - r[0]) + max(r[2], o[2]), r[3]))
    out['tabs'] = tabs
    away()

    # R524: the head of the section «Pannelli» open, under the pointer: one colour from its top to its bottom
    actions.openSection('panels')
    pump(500)
    head = item(win, 'plant-section-panels')
    move_to(head, .8, .5)
    grab()
    r = rect(head)
    x = int(r[0] + r[2] * .9)
    column = [rgb(x, y) for y in range(int(r[1] + 2 * dpr), int(r[1] + r[3] - 1))]
    out['head_spread'] = max(dist(p, column[len(column) // 3]) for p in column)
    save('section-head', r)
    away()

    # R518: every window, opened one by one
    def frames():
        return [o for o in walk(win.contentItem()) if o.objectName() == 'dialogFrame' and shown(o) and o.width() > 0]

    def ink_margins(frame, name):
        r = rect(frame)
        x0, y0, x1, y1 = int(r[0]), int(r[1]), int(r[0] + r[2]) - 1, int(r[1] + r[3]) - 1
        ground = rgb(x0 + r[2] / 2, y0 + 3 * dpr)
        inset = int(10 * dpr)
        def inked(x, y):
            return dist(rgb(x, y), ground) > 40
        rows = range(y0 + inset, y1 - inset)
        cols = range(x0 + inset, x1 - inset)
        edge = int(2 * dpr) + 1                 # past the frame's line, soft at 1.5
        left = next(x for x in range(x0 + edge, x1) if any(inked(x, y) for y in rows[::2])) - x0
        right = x1 - next(x for x in range(x1 - edge, x0, -1) if any(inked(x, y) for y in rows[::2]))
        top = next(y for y in range(y0 + edge, y1) if any(inked(x, y) for x in cols[::2])) - y0
        bottom = y1 - next(y for y in range(y1 - edge, y0, -1) if any(inked(x, y) for x in cols[::2]))
        found = dict(left=left, right=right, top=top, bottom=bottom, width=round(r[2]))
        buttons = [o for o in walk(frame.parentItem()) if o.objectName() == 'dialogButtons' and shown(o)]
        if buttons:
            b = rect(buttons[0])
            found['buttons_right'] = round(x1 + 1 - (b[0] + b[2]))
            found['buttons_bottom'] = round(y1 + 1 - (b[1] + b[3]))
        out['dialogs'][name] = found
        save(f'dialog-{name}', r)

    def scroll_check(where):
        """R520: no text box of what scrolls under a scroll bar shown."""
        for bar in walk(where):
            if bar.property('fades') is None or bar.property('orientation') != Qt.Orientation.Vertical or not shown(bar):
                continue
            if (bar.property('size') or 1) >= 1:
                continue
            view = bar.property('fadesOf') or bar.parentItem()
            content = view.property('contentItem') if view is not None and view.property('contentItem') is not None else view
            b = bar.mapToScene(QPointF(0, 0)).x()
            for t in walk(content):
                text = t.property('text')
                if not isinstance(text, str) or not text.strip() or not shown(t) or t.property('paintedWidth') is None:
                    continue
                p = t.mapToScene(QPointF(0, 0))
                vtop = view.mapToScene(QPointF(0, 0)).y()
                if p.y() + t.height() < vtop or p.y() > vtop + view.height():
                    continue
                pad = t.property('rightPadding') or 0
                end = p.x() + t.width() - pad          # the box the text is laid in: it is what may reach the bar
                if end > b + .5:
                    out['scroll'].append([where.objectName() or 'window', bar.objectName() or view.objectName(), text[:40], round(end - b, 1)])

    def dialog(name, open_it, close_it):
        open_it()
        pump(700)
        away()
        grab()
        found = frames()
        if not found:
            out['dialogs'][name] = 'not shown'
        else:
            frame = max(found, key=lambda f: f.width() * f.height())
            try:
                ink_margins(frame, name)
            except StopIteration:
                out['dialogs'][name] = 'no ink'
            scroll_check(frame.parentItem())
        close_it()
        pump(400)

    def safe_name(o):
        try:
            return o.objectName()
        except RuntimeError:                    # a wrapper left by an object gone (see parts.attach, 0e2131ba)
            return ''

    def plant_dialog(kind):
        return lambda: actions.open(kind)

    for kind in ('clear', 'sizing', 'storage', 'proposal', 'catalog'):
        dialog(kind, plant_dialog(kind), actions.dismiss)
    every = [o for r in host.engine.rootObjects() for o in r.findChildren(QObject)]
    sheet = next((o for o in item(win, 'plant-inverters').findChildren(QObject) if safe_name(o) == 'plant-datasheet-dialog'), None)
    if sheet is not None:
        unit = next(u for u in plant.units if u['card'])
        item(win, 'plant-inverters').setProperty('sheet', unit['record'])
        dialog('datasheet', lambda: sheet.metaObject().invokeMethod(sheet, 'open'), lambda: sheet.metaObject().invokeMethod(sheet, 'close'))
    shell_dialog = next((o for o in every if safe_name(o) == 'shellCommandDialog'), None)
    if shell_dialog is not None:
        dialog('about', lambda: tasks.showDialog.emit('about'), lambda: shell_dialog.metaObject().invokeMethod(shell_dialog, 'close'))

        def compare():
            # a project with two variants and the table filled: an empty window shows nothing (Daniel 07/11: «NIENTE?»)
            import time
            tasks.commitVariant('new', 'Variante 2')
            pump(500)
            host.shell.trigger('compare_variants')
            start = time.time()
            while time.time() - start < 300 and (tasks.property('busy') or not tasks.property('rows')):
                pump(500)
            out['compare_rows'] = len(tasks.property('rows') or [])
        dialog('compare', compare, lambda: shell_dialog.metaObject().invokeMethod(shell_dialog, 'close'))
    variant = next((o for o in every if safe_name(o) == 'variantDialog'), None)
    if variant is not None:
        dialog('variant', lambda: tasks.variantDialog.emit('new', 'Variante 2'), lambda: variant.metaObject().invokeMethod(variant, 'close'))

    # the plan's windows as the plan opens them, with their own title and words
    from meridiana.i18n import _
    plan_backend = host.plan
    for name, opener in (
            ('imageValueDialog', lambda: plan_backend.underlays.prompt.emit(plan_backend.underlays.texts['rotate'], plan_backend.underlays.texts['angle'])),
            ('relayoutConfirmation', lambda: plan_backend.relayoutRequested.emit(_('Lay again automatically'),
                _('The rows by hand give way to the automatic layout, and the modules taken '
                  'out by hand come back. Undo brings them back. Go on?')))):
        target = next((o for o in every if safe_name(o) == name), None)
        if target is not None:
            dialog(name, opener, lambda o=target: o.metaObject().invokeMethod(o, 'close'))

    # every other window made by now: opened as it is
    def is_dialog(o):
        try:
            return o.property('acceptOnReturn') is not None
        except RuntimeError:                    # gone since the list was made
            return False
    every = [o for r in host.engine.rootObjects() for o in r.findChildren(QObject)]
    for n, other in enumerate(o for o in every if is_dialog(o)):
        name = safe_name(other) or other.property('title') or f'dialog-{n}'
        if name in ('dxfOptions', 'fileCatalogDialog', 'imageValueDialog', 'relayoutConfirmation'):
            continue    # filled only by their own opening (a file and its frames; File's catalogue): not shown empty
        if any(name == k or name.startswith(k) for k in out['dialogs']) or name in ('plant-proposal-dialog', 'plant-catalog-dialog',
                'plant-storage-dialog', 'plant-clear-dialog', 'plant-maker-dialog', 'plant-datasheet-dialog', 'shellCommandDialog', 'variantDialog'):
            continue
        if not other.property('title'):
            other.setProperty('title', 'Titolo di prova')     # the plan's windows get theirs when they open
        dialog(name, lambda o=other: o.metaObject().invokeMethod(o, 'open'), lambda o=other: o.metaObject().invokeMethod(o, 'close'))

    # R525: the entry under the pointer, in the combo «Su cosa» of the proposal and in the inverter's menu
    def entry_hover(name, popup_item, entry):
        move_to(entry)
        grab()
        p, e = rect(popup_item), rect(entry)
        veil = over(raw['hover'], raw['card'])
        cy = int(e[1] + e[3] / 2)
        xs = [x for x in range(int(p[0]), int(p[0] + p[2])) if dist(rgb(x, cy), veil) <= 6]
        ys = [y for y in range(int(p[1]), int(p[1] + p[3])) if dist(rgb(xs[0] + 6 * dpr, y), veil) <= 6] if xs else []
        found = dict(found=bool(xs))
        if xs and ys:
            found.update(left=xs[0] - int(p[0]), right=int(p[0] + p[2]) - 1 - xs[-1], height=len(ys),
                         corner=dist(rgb(xs[0], ys[0]), veil) > 6, colour=list(rgb(xs[0] + 6 * dpr, cy)))
        out['menus'][name] = found
        save(f'menu-{name}', p)

    def popup_items():
        return [o for o in walk(win.contentItem()) if o.metaObject().className().startswith('QQuickPopupItem') and shown(o) and o.height() > 40]

    actions.open('proposal')
    pump(700)
    # R21-F2: PlantChoice is M.ComboBox with `options` (the first of the proposal is «Su cosa»)
    combo = next((o for o in walk(win.contentItem()) if o.metaObject().className().startswith('ComboBox') and o.property('hasOptions') and shown(o)), None)
    if combo is not None:
        click(app, win, combo.mapToScene(QPointF(combo.width() / 2, combo.height() / 2)))
        pump(500)
        pops = [p for p in popup_items() if p.width() < 500]
        entries = [o for o in walk(pops[-1]) if o.property('highlighted') is not None and o.property('text') and shown(o)] if pops else []
        if entries:
            entry_hover('combo', pops[-1], entries[min(1, len(entries) - 1)])
        mouse(app, win, QEvent.Type.KeyPress, QPointF(0, 0), Qt.MouseButton.NoButton, Qt.MouseButton.NoButton) if False else None
        from quick.gestures import key
        key(app, win, Qt.Key.Key_Escape)
        pump(300)
    actions.dismiss()
    pump(300)
    actions.openSection('inverter')
    pump(500)
    item(win, 'plant-inverters').setProperty('contentY', 0)
    pump(200)
    card = item(win, 'inverter-card-' + str(next(u for u in plant.units if u['card'])['number']))
    more = next(o for o in walk(card) if o.property('iconName') == 'ellipsis')
    click(app, win, more.mapToScene(QPointF(more.width() / 2, more.height() / 2)))
    pump(500)
    pops = popup_items()
    entries = [o for o in walk(pops[-1]) if o.property('highlighted') is not None and o.property('text') and shown(o)] if pops else []
    if entries:
        entry_hover('menu', pops[-1], entries[1])
    from quick.gestures import key
    key(app, win, Qt.Key.Key_Escape)
    pump(300)
    # R520 in the window's own lists: the Plant's panel and the checks
    scroll_check(win.contentItem())
finally:
    host.close()
    pump(50)
    folder.cleanup()
print('R518 ' + json.dumps(out))
'''


def measure(scale, shot=None, root=ROOT):
    work = Path(tempfile.mkdtemp(prefix='meridiana-r518-'))
    screen = work / 'screen.json'
    screen.write_text('{"screens": [{"name": "R518", "x": 0, "y": 0, "width": 4000, "height": 2400, '
                      '"logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}', encoding='utf8')
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(Path(root) / 'tests'), str(Path(root) / 'src')]),
               QT_QPA_PLATFORM='offscreen:configfile=' + os.path.relpath(screen, root).replace(os.sep, '/'),
               QSG_RENDER_LOOP='basic', QT_SCALE_FACTOR=str(scale), PYTHONUTF8='1',
               APPDATA=str(work / 'APPDATA'), LOCALAPPDATA=str(work / 'LOCALAPPDATA'))
    if shot:
        env['R518_SHOT'] = str(shot)
    try:
        done = subprocess.run([sys.executable, '-c', CHILD], cwd=root, env=env, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=400)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    lines = [line for line in done.stdout.splitlines() if line.startswith('R518 ')]
    if not lines:
        raise AssertionError(done.stderr[-3000:])
    return json.loads(lines[-1][5:])


def spread(values):
    return max(values) - min(values) if values else 0


class Windows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seen = {s: measure(s) for s in (1, 1.5, 2)}

    def test_r518_every_window_has_the_same_margins_and_buttons(self):
        for scale, m in self.seen.items():
            dialogs = {k: v for k, v in m['dialogs'].items() if isinstance(v, dict)}
            with self.subTest(scale=scale, dialogs=dialogs):
                # dxfOptions opens only with a file and its frames (DxfOptions.show): not measured here
                dialogs = {k: v for k, v in dialogs.items() if k != 'dxfOptions'}
                self.assertGreaterEqual(len(dialogs), 8)
                self.assertGreater(m.get('compare_rows', 0), 3, 'the comparison of the variants with its table')
                for side in ('left', 'top', 'buttons_right', 'buttons_bottom'):
                    values = [v[side] for v in dialogs.values() if side in v]
                    # the left margin is read on the first letter's ink, whose side bearing differs from a letter to
                    # another («F», «C», «I»): up to 1.5 logical pixels more at 2
                    room = (1 if side != 'left' else 1 + scale) + (1 if scale == 1.5 else 0)      # 1.5: text between pixels
                    self.assertLessEqual(spread(values), room, (side, {k: v.get(side) for k, v in dialogs.items()}))
                # nothing beyond the margin: no ink nearer the frame than the buttons on the right and at the bottom, nor
                # than the title on the left
                for name, v in dialogs.items():
                    if 'buttons_right' in v:
                        self.assertGreaterEqual(v['right'], v['buttons_right'] - 1, (name, v))
                        self.assertGreaterEqual(v['bottom'], v['buttons_bottom'] - 1, (name, v))

    def test_r519_the_hover_of_a_tab_is_as_far_from_the_open_tab_on_both_sides(self):
        for scale, m in self.seen.items():
            with self.subTest(scale=scale, tabs=m['tabs']):
                # at 1.5 the open tab's outline falls between two device pixels and blends with the hover's edge
                self.assertLessEqual(abs(m['tabs']['modelTab'] - m['tabs']['productionTab']), 1 if scale != 1.5 else 3, m['tabs'])

    def test_r520_no_text_under_a_scroll_bar(self):
        for scale, m in self.seen.items():
            with self.subTest(scale=scale):
                self.assertEqual(m['scroll'], [])

    def test_r524_the_head_of_a_section_under_the_pointer_is_one_colour(self):
        for scale, m in self.seen.items():
            with self.subTest(scale=scale):
                self.assertLessEqual(m['head_spread'], 6, m['head_spread'])

    def test_r525_the_entry_under_the_pointer_as_in_every_menu(self):
        for scale, m in self.seen.items():
            menus = m['menus']
            with self.subTest(scale=scale, menus=menus):
                self.assertTrue(menus['combo'].get('found') and menus['menu'].get('found'), menus)
                for side in ('left', 'right', 'height'):
                    self.assertLessEqual(abs(menus['combo'][side] - menus['menu'][side]), 1, (side, menus))
                self.assertTrue(menus['combo']['corner'] and menus['menu']['corner'], menus)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'shot':
        where = Path(sys.argv[4]) if len(sys.argv) > 4 else ROOT
        for s in (1, 1.5, 2):
            print(s, json.dumps(measure(s, Path(sys.argv[2]) / f'{sys.argv[3]}-s{s}', where)))
    else:
        unittest.main()
