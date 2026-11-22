"""The functions Daniel uses, one step each, on the Quick window, offscreen, on a copy of Rho (once the comparison
with the Widgets window of 05/11/2026; only the Quick is left, the engine is always «quick»).

    python tests/quick/confronto/giro.py quick <out dir> [step ...]

A gesture where a synthetic event can make it (keys, clicks on the plan and on the lists), the command of the menu
otherwise, and the function behind a file chooser where a chooser would open (said in the record as «per funzione»).
After every step: what the session holds, the texts with a number that the window shows, the photo of the window.
Writes <out>/giro-quick.json, .log and the photos <step>-quick.png.
Nothing reaches the screen, the pointer or the keyboard: QT_QPA_PLATFORM is offscreen, the profile is a new temporary
folder (percorsi_offscreen sets APPDATA and LOCALAPPDATA before Meridiana is imported).
"""
import json
from pathlib import Path
import re
import shutil
import sys
import time
import traceback

sys.path.insert(0, str(Path(__file__).resolve().parent))
import percorsi_offscreen as po  # noqa: E402  (sets the platform and the profile first)

from PySide6.QtCore import QObject, QPointF  # noqa: E402

RHO = po.ROOT / 'docs/quick/compat/fixtures/rho.meridiana'
IFC = po.ROOT/'tests'/'data'/'ifc'/'Building-Architecture.ifc'
DIGITS = re.compile(r'\d')
STEPS = {}


def step(function):
    STEPS[function.__name__] = function
    return function


class Giro:
    def __init__(self, engine, out):
        from quick.percorsi import modellazione
        if engine != 'quick':
            raise ValueError(f'only the Quick window is left, not {engine!r}')
        self.engine = engine
        self.out = Path(out).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.folder = po.WORK/'progetto'
        self.folder.mkdir()
        self.file = self.folder/RHO.name
        shutil.copy2(RHO, self.file)
        self.started = time.perf_counter()
        # no map from the network, no PVGIS, no updates
        from meridiana.app.platform import config
        from meridiana.app.platform.paths import Paths
        base = po.WORK/'quick-profile'
        quiet = config.Config(background='none', network_tiles=False, network_pvgis=False, check_updates=False,
                              assistant_animated=False)
        config.save(quiet, Paths(*(base/n for n in ('config', 'state', 'data', 'cache'))).config_file)
        self.app, self.host, self.window = po.quick_host(self.file, po.WORK)
        self.hand = po.OffscreenHand(self.app, self.window)
        self.log = (self.out/f'giro-{engine}.log').open('w', encoding='utf8')
        self.pilot = modellazione.Pilot(engine, self.app, self.host, self.window, self.hand, self.out, 'giro', self.log)
        self.records = []
        self.current = 'avvio'

    # what is there

    @property
    def session(self):
        return self.host.bridge.session

    @property
    def project(self):
        return self.session.project

    def say(self, text):
        print(text, file=self.log, flush=True)

    def spin(self, ms):
        po.pump(ms)

    def wait(self, condition, seconds):
        end = time.perf_counter()+seconds
        while time.perf_counter() < end:
            if condition():
                return True
            po.pump(100)
        return bool(condition())

    def counts(self):
        from meridiana.core.energy import system
        s, p = self.session, self.project
        modules = sum(getattr(s.results.get(sf.id), 'count', 0) or 0 for sf in p.subfields)
        strings = (p.energy.get('strings') or {}).get('runs') or []
        try:
            inverters = len(system.inverter_entries(p.energy))
        except Exception as error:          # said in the record
            inverters = repr(error)[:80]
        return {'edifici': len(p.buildings), 'sottocampi': len(p.subfields), 'esclusioni': len(p.exclusions),
                'oggetti': len(p.props), 'moduli': modules, 'stringhe': len(strings),
                'moduli_in_stringa': sum(len(r.get('modules') or []) for r in strings), 'inverter': inverters}

    def energy(self):
        e = self.session.energy or {}
        sim = e.get('sim')
        if sim is None:
            return {'calcolato': False, 'errore': str(e.get('error_sim'))[:120] if e else ''}
        out = {'calcolato': True, 'stale': bool(self.session.energy_stale())}
        for k, v in vars(sim).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = round(float(v), 3)
        return out

    def phase(self):
        return str(self.window.property('phase'))

    def texts(self):
        """The texts with a digit that the window shows, top to bottom."""
        found = []
        def walk(item, shown=True):
            shown = shown and item.isVisible() and item.opacity() > 0
            if not shown:
                return
            text = item.property('text')
            if isinstance(text, str) and text and DIGITS.search(text) and item.width() > 0 and item.height() > 0:
                p = item.mapToScene(QPointF(0, 0))
                if 0 <= p.x() < self.window.width() and 0 <= p.y() < self.window.height():
                    found.append((round(p.y()), round(p.x()), text))
            for child in item.childItems():
                walk(child, shown)
        walk(self.window.contentItem())
        return [t for _y, _x, t in sorted(found)][:400]

    # what is shown

    def photo(self, name):
        path = self.out/f'{name}-{self.engine}.png'
        image = self.window.grabWindow()
        image.save(str(path))
        return path.name

    def close_popups(self):
        self.hand.key('esc')
        self.spin(300)

    def command(self, cid):
        """The command as the menu runs it."""
        done = self.host.shell.trigger(cid)
        self.spin(400)
        return done

    def checks_shown(self):
        item = next((i for i in self.pilot.walk() if i.objectName() == 'checks-page'), None)
        return item is not None and self.pilot.shown(item) and self._shown_up(item)

    @staticmethod
    def _shown_up(item):
        while item is not None:
            if not item.isVisible() or item.opacity() <= 0:
                return False
            item = item.parentItem()
        return True

    def open_checks(self):
        if not self.checks_shown():
            self.command('panel_checks')
            self.spin(1200)
        return self.checks_shown()

    def notice(self):
        plan = self.host.plan
        return {'hint': str(getattr(plan, 'hint', '')), 'notice': str(getattr(plan, 'notice', ''))}

    def show_phase(self, pid):
        self.command('phase_'+pid)
        self.spin(800)

    def undo_all_to(self, state_key, limit=6):
        for _ in range(limit):
            if self.session.state_key() == state_key:
                return True
            self.command('undo')
            self.pilot.settle(30)
        return self.session.state_key() == state_key

    # running

    def run(self, names):
        self.say(f'motore {self.engine}, progetto {self.file}')
        for name in names:
            self.current = name
            self.pilot.layer = self.window.findChild(QObject, 'worldLayer')
            start = time.perf_counter()
            record = {'passo': name, 'motore': self.engine}
            try:
                record['fatti'] = STEPS[name](self) or {}
                record['esito_driver'] = 'ok'
            except Exception:
                record['esito_driver'] = 'errore'
                record['traceback'] = traceback.format_exc()[-1500:]
                self.say(record['traceback'])
            record['secondi'] = round(time.perf_counter()-start, 1)
            try:
                record['fase'] = self.phase()
                record['testi'] = self.texts()
                record['foto'] = self.photo(name)
            except Exception:
                record['foto_errore'] = traceback.format_exc()[-600:]
            self.records.append(record)
            self.say(f'[{name}] {record["esito_driver"]} {record["secondi"]} s {json.dumps(record.get("fatti"), ensure_ascii=False, default=str)[:600]}')
            (self.out/f'giro-{self.engine}.json').write_text(json.dumps(self.records, ensure_ascii=False, indent=1, default=str),
                                                           encoding='utf8')


# the steps, in the order of the work

@step
def apertura(g):
    """File: the project opened, its layouts back."""
    g.wait(lambda: all(sf.id in g.session.results for sf in g.project.subfields if sf.filled), 120)
    g.pilot.settle(60)
    title = g.window.property('title')
    return {'conteggi': g.counts(), 'percorso_sessione': str(g.session.path), 'titolo': title,
            'modificato': bool(g.session.dirty()) if callable(getattr(g.session, 'dirty', None)) else None}


@step
def calcolo_f5(g):
    """The year: what the window computes by itself after the opening, then F5."""
    first = time.perf_counter()
    g.wait(lambda: g.session.energy and g.session.energy.get('sim') is not None and not g.session.energy_stale(), 420)
    alone = {'dopo_apertura_s': round(time.perf_counter()-first, 1), 'anno': g.energy(),
             'generazione': g.session.energy_generation}
    g.show_phase('production')
    before = g.session.energy_generation
    g.hand.key('f5')
    g.spin(1500)
    started = g.session.energy_generation != before or bool(getattr(g.host.bridge, 'computing', False))
    t0 = time.perf_counter()
    g.wait(lambda: g.session.energy_generation != before and g.session.energy.get('sim') is not None
           and not g.session.energy_stale(), 420)
    return {'da_solo': alone, 'f5_parte': started, 'f5_s': round(time.perf_counter()-t0, 1),
            'generazioni': [before, g.session.energy_generation], 'anno_dopo_f5': g.energy()}


@step
def producibilita(g):
    g.show_phase('production')
    g.spin(1500)
    return {'anno': g.energy()}


@step
def non_aggiornato(g):
    """A change that moves the modules: does the window say that the year is old? Then Ctrl+Z."""
    g.show_phase('production')
    key = g.session.state_key()
    sf = next(s for s in g.project.subfields if s.filled)
    tilt = float((sf.params or {}).get('tilt') or 0)

    def change(p):
        target = next(s for s in p.subfields if s.id == sf.id)
        target.params = dict(target.params or {}, tilt=tilt+5)
    g.session.edit('Inclinazione +5', change)
    g.pilot.settle(60)
    g.spin(1500)
    out = {'per_funzione': 'inclinazione del primo sottocampo +5 gradi con session.edit',
           'stale_nucleo': bool(g.session.energy_stale())}
    out['fasi_segnate'] = list(g.host.shell.stalePhases)
    out['stato_anno'] = dict(g.host.shell.yearState)
    g.photo('non_aggiornato-segno')
    g.hand.key('z', ('ctrl',))
    g.pilot.settle(60)
    g.spin(1500)
    out['ctrl_z_torna'] = g.session.state_key() == key
    if not out['ctrl_z_torna']:
        out['ctrl_z_comando'] = g.undo_all_to(key)
    out['stale_dopo_annulla'] = bool(g.session.energy_stale())
    out['fasi_segnate_dopo'] = (list(g.host.shell.stalePhases))
    return out


@step
def consumi(g):
    g.show_phase('consumption')
    g.spin(1500)
    return {'chiavi_energia': sorted(k for k in (g.session.energy or {}) if 'cons' in k or 'load' in k)}


@step
def economia(g):
    g.show_phase('economics')
    g.spin(1500)
    return {'chiavi_energia': sorted(k for k in (g.session.energy or {}) if 'econ' in k or 'balance' in k or 'self' in k)}


@step
def impianto(g):
    g.show_phase('plant')
    g.spin(2500)
    out = {'conteggi': g.counts()}
    summary = g.host.parts.controllers.get('plantSummary')
    out['riepilogo'] = summary.property('totals') if summary is not None else None
    return out


def _dialog_step(g, cid, wait_s=3):
    g.show_phase('plant')
    g.keep_dialog = False
    ok = g.command(cid)
    g.spin(wait_s*1000)
    out = {'comando_attivo': ok}
    names = sorted({i.objectName() for i in g.pilot.walk() if i.objectName() and g.pilot.shown(i)
                    and any(k in i.objectName().lower() for k in ('catalog', 'dialog', 'sizing', 'proposal', 'popup'))})
    out['oggetti_visibili'] = names[:30]
    return out


@step
def catalogo_inverter(g):
    out = _dialog_step(g, 'inverter_catalog')
    g.photo('catalogo_inverter-aperto')
    g.close_popups()
    return out


@step
def catalogo_ottimizzatori(g):
    out = _dialog_step(g, 'browse_optimizers')
    g.photo('catalogo_ottimizzatori-aperto')
    g.close_popups()
    return out


@step
def inverter_auto(g):
    out = _dialog_step(g, 'inverter_auto', 20)
    g.photo('inverter_auto-aperto')
    g.close_popups()
    out['conteggi'] = g.counts()
    return out


@step
def stringhe_auto(g):
    out = _dialog_step(g, 'strings_auto', 20)
    g.photo('stringhe_auto-aperto')
    g.close_popups()
    out['conteggi'] = g.counts()
    return out


@step
def schede_componenti(g):
    """Where the data sheet of an inverter and of an optimizer is offered (presence of the control, not opened)."""
    g.show_phase('plant')
    g.spin(1000)
    names = sorted({i.objectName() for i in g.pilot.walk() if 'sheet' in i.objectName().lower()})
    return {'controlli': names}


def _tree_click(g, kind, oid, ctrl=False):
    """A click on the row of the left panel; returns how it was made."""
    tree = g.host.parts.controllers['project_tree']
    name = f'tree-row-{kind}-{oid}'
    items = [i for i in g.pilot.walk() if i.objectName() == name and g.pilot.shown(i)]
    if not items:
        g.command('panel_project')
        g.spin(800)
        items = [i for i in g.pilot.walk() if i.objectName() == name and g.pilot.shown(i)]
    if items:
        x, y = g.pilot.centre(items[0])
        g.hand.click(x, y, modifiers=('ctrl',) if ctrl else ())
        g.spin(400)
        return 'clic sulla riga'
    if ctrl:
        many = list(g.session.selected_many() or []) or [g.session.selection[1]]
        tree.selectMany(kind, many+[oid])
    else:
        tree.select(kind, oid)
    g.spin(400)
    return 'per funzione (riga non trovata)'


@step
def selezione_albero(g):
    g.show_phase('model')
    b = g.project.buildings[0]
    how = _tree_click(g, 'building', b.id)
    return {'come': how, 'selezione': list(g.session.selection)}


@step
def selezione_multipla(g):
    g.show_phase('model')
    a, b = g.project.buildings[0], g.project.buildings[1]
    first = _tree_click(g, 'building', a.id)
    second = _tree_click(g, 'building', b.id, ctrl=True)
    many = g.session.selected_many() if callable(getattr(g.session, 'selected_many', None)) else None
    return {'come': [first, second], 'selezione': list(g.session.selection), 'insieme': list(many or [])}


def _centroid(ring):
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return sum(xs)/len(xs), sum(ys)/len(ys)


def _plan_on_building(g):
    g.show_phase('model')
    if _view(g) != 'plan':
        g.command('view_plan')
    b = g.project.buildings[0]
    xs, ys = [p[0] for p in b.footprint], [p[1] for p in b.footprint]
    w, h = max(xs)-min(xs), max(ys)-min(ys)
    east = max(pt[0] for x in g.project.buildings for pt in x.footprint)
    side = (east+w+30)-(min(xs)-10)
    g.pilot.plan_alone = True
    g.pilot.fit(min(xs)-10, min(ys)-side*0.25, side, side*0.6, mpp=side/700)
    g.pilot.layer = g.window.findChild(QObject, 'worldLayer')
    from shapely.geometry import Point, Polygon
    others = [Polygon(e.ring) for e in g.project.exclusions] + [Polygon(sf.ring) for sf in g.project.subfields]
    shape = Polygon(b.footprint)
    c = _centroid(b.footprint)
    for i in range(1, 20):
        for j in range(1, 20):
            q = (min(xs)+w*i/20, min(ys)+h*j/20)
            if shape.contains(Point(q).buffer(1.5)) and not any(o.buffer(1.5).contains(Point(q)) for o in others):
                c = q
                break
        else:
            continue
        break
    east = max(pt[0] for x in g.project.buildings for pt in x.footprint)
    target = (east+w/2+15, _centroid(b.footprint)[1])
    return b, c, target


def _pick_building(g, c):
    """A click on the building, then Esc while what is selected is a part of it (the hint of the Quick says so)."""
    g.pilot.tool('tool_select')
    g.pilot.click(*c)
    path = [list(g.session.selection)]
    for _ in range(3):
        if g.session.selection[0] == 'building':
            break
        g.hand.key('esc')
        g.spin(200)
        path.append(list(g.session.selection))
    return path


@step
def copia_incolla(g):
    b, c, target = _plan_on_building(g)
    key = g.session.state_key()
    before = len(g.project.buildings), len(g.project.subfields)
    selected = _pick_building(g, c)
    g.hand.key('c', ('ctrl',))
    after_copy = g.notice()
    g.pilot.at(*target)
    g.hand.key('v', ('ctrl',))
    g.pilot.at(target[0]+0.5, target[1])
    after_v = g.notice()
    g.pilot.click(*target)
    g.pilot.settle(30)
    g.photo('copia_incolla-dopo')
    after = len(g.project.buildings), len(g.project.subfields)
    said = g.notice()
    back = g.undo_all_to(key)
    return {'selezione': selected, 'edifici_sottocampi_prima': before, 'edifici_sottocampi_dopo': after,
            'dopo_ctrl_c': after_copy, 'dopo_ctrl_v': after_v, 'dopo_clic': said, 'annullato': back,
            'destinazione': [round(v, 1) for v in target]}


@step
def taglia_incolla(g):
    b, c, target = _plan_on_building(g)
    key = g.session.state_key()
    selected = _pick_building(g, c)
    g.hand.key('x', ('ctrl',))
    g.pilot.settle(10)
    gone = not any(x.id == b.id for x in g.project.buildings)
    g.pilot.at(*target)
    g.hand.key('v', ('ctrl',))
    g.pilot.at(target[0]+0.5, target[1])
    g.pilot.click(*target)
    g.pilot.settle(30)
    moved = [round(v, 1) for v in _centroid(g.project.buildings[-1].footprint)] if g.project.buildings else None
    count = len(g.project.buildings), len(g.project.subfields)
    said = g.notice()
    back = g.undo_all_to(key)
    return {'selezione': selected, 'tolto_dopo_ctrl_x': gone, 'edifici_sottocampi_dopo': count, 'centro_ultimo': moved,
            'dopo_clic': said, 'annullato': back}


@step
def copia_trascinando(g):
    """Ctrl held while a building chosen in the left panel is dragged: the copy of move.copy in both windows."""
    b, c, target = _plan_on_building(g)
    key = g.session.state_key()
    before = len(g.project.buildings), len(g.project.subfields)
    how = _tree_click(g, 'building', b.id)
    g.pilot.tool('tool_move')
    a, z = g.pilot.world(*c), g.pilot.world(*target)
    from PySide6.QtCore import QEvent, Qt
    ctrl = Qt.KeyboardModifier.ControlModifier
    g.hand.move(*a, 4)
    g.hand._mouse(QEvent.Type.MouseButtonPress, *a, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, ctrl)
    g.hand.held = Qt.MouseButton.LeftButton
    for i in range(1, 15):
        x, y = a[0]+(z[0]-a[0])*i/14, a[1]+(z[1]-a[1])*i/14
        g.hand._mouse(QEvent.Type.MouseMove, x, y, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, ctrl)
        g.spin(16)
    g.hand.held = Qt.MouseButton.NoButton
    g.hand._mouse(QEvent.Type.MouseButtonRelease, *z, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, ctrl)
    g.pilot.settle(30)
    g.photo('copia_trascinando-dopo')
    after = len(g.project.buildings), len(g.project.subfields)
    said = g.notice()
    back = g.undo_all_to(key)
    return {'scelta': how, 'strumento': str(g.pilot.tool_name()), 'edifici_sottocampi_prima': before,
            'edifici_sottocampi_dopo': after, 'dopo': said, 'annullato': back}


def _view(g):
    return str(g.window.property('viewMode'))


@step
def vista_3d(g):
    g.show_phase('model')
    g.command('view_3d')
    g.spin(3000)
    return {'vista': _view(g)}


@step
def vista_affiancate(g):
    g.command('view_both')
    g.spin(3000)
    return {'vista': _view(g)}


@step
def vista_zoom(g):
    g.command('view_plan')
    g.spin(800)
    a = g.pilot.mpp()
    g.command('zoom_in')
    g.spin(600)
    b = g.pilot.mpp()
    g.session.select('site', '')
    g.spin(300)
    g.command('fit')
    g.spin(800)
    c = g.pilot.mpp()
    g.command('view_north')
    g.spin(400)
    return {'vista': _view(g), 'metri_per_pixel': [round(a, 4), round(b, 4), round(c, 4)]}


@step
def verifiche(g):
    g.show_phase('plant')
    shown = g.open_checks()
    from collections import Counter
    from meridiana.core.rules import checks
    out = {'pannello_aperto': shown}
    out['conteggi_finestra'] = g.host.shell.checkCounts
    backend = g.host.parts.controllers['checks']
    out['righe'] = [(r.get('key') if r.get('header') else '', r.get('text')) for r in (backend.property('rows') or [])][:60]
    try:
        items = checks.gather(g.project, g.session.good_results(), g.session.energy, None, True)
        out['nucleo'] = dict(Counter(i.level for i in items))
    except Exception as error:
        out['nucleo'] = repr(error)[:200]
    return out


def overlaps_quick(g):
    """The rows of the Checks list that are drawn: their places in the list, and which ones overlap."""
    lst = g.window.findChild(QObject, 'checks-list')
    if lst is None:
        found = [i for i in g.pilot.walk() if i.objectName() == 'checks-list']
        lst = found[0] if found else None
    if lst is None:
        return {'errore': 'checks-list non trovata'}
    content = lst.property('contentItem')
    top = lst.property('contentY') or 0
    height = lst.height()
    rows = []
    for d in content.childItems():
        name = d.objectName()
        if not (name.startswith('checks-group-') or name.startswith('checks-row-')) or not Giro._shown_up(d):
            continue
        y = d.y()-top
        if y+d.height() < 0 or y > height:
            continue
        label = ''
        for c in g.pilot.walk(d):
            t = c.property('text')
            if isinstance(t, str) and t and c.isVisible():
                label = t
                break
        rows.append({'nome': name, 'y': round(d.y(), 1), 'alto': round(d.height(), 1), 'testo': label[:60]})
    rows.sort(key=lambda r: r['y'])
    bad = []
    for a, b in zip(rows, rows[1:], strict=False):
        if b['y'] < a['y']+a['alto']-0.5:
            bad.append(f"{a['nome']} ({a['y']}+{a['alto']}) sotto {b['nome']} ({b['y']})")
    headers = [r['testo'] for r in rows if r['nome'].startswith('checks-group-')]
    doubles = sorted({h for h in headers if headers.count(h) > 1})
    zero = [r['nome'] for r in rows if r['alto'] < 4]
    backend = g.host.parts.controllers['checks']
    model_rows = [(r.get('key') if r.get('header') else '', r.get('text', '')[:60]) for r in (backend.property('rows') or [])]
    return {'righe': rows, 'sovrapposte': bad, 'intestazioni_doppie': doubles, 'altezza_zero': zero,
            'delegati_disegnati': len(rows), 'righe_del_modello': len(model_rows), 'modello': model_rows[:40],
            'lista_visibile': Giro._shown_up(lst)}


@step
def verifiche_gruppi(g):
    """Every group of the Checks opened and closed with a click on its header; after each click, the rows drawn."""
    g.show_phase('plant')
    out = {'passi': [], 'pannello_aperto': g.open_checks()}
    backend = g.host.parts.controllers['checks']
    keys = [r.get('key') for r in (backend.property('rows') or []) if r.get('header')]
    out['gruppi'] = keys
    for round_ in (1, 2):
        for key in keys:
            # the list makes only the rows near its view: the header is brought to the top first, as the wheel would
            index = next((n for n, r in enumerate(backend.property('rows') or []) if r.get('header') and r.get('key') == key), -1)
            lst = next((i for i in g.pilot.walk() if i.objectName() == 'checks-list'), None)
            if lst is not None and index >= 0:
                from PySide6.QtCore import Q_ARG, QMetaObject
                QMetaObject.invokeMethod(lst, 'positionViewAtIndex', Q_ARG(int, index), Q_ARG(int, 1))
                g.spin(500)
            item = next((i for i in g.pilot.walk() if i.objectName() == 'checks-group-'+key and g.pilot.shown(i)
                         and Giro._shown_up(i)), None)
            if item is None:
                out['passi'].append({'gruppo': key, 'giro': round_, 'clic': 'intestazione non visibile'})
                continue
            x, y = g.pilot.centre(item)
            g.hand.click(x, y)
            g.spin(900)
            state = overlaps_quick(g)
            state.pop('righe', None) if not state.get('sovrapposte') and not state.get('intestazioni_doppie') else None
            out['passi'].append({'gruppo': key, 'giro': round_, **state})
            g.photo(f'{g.current}-{round_}-' + key.replace('|', '_'))
    return out


@step
def verifiche_aree(g):
    """The same, with the checks grouped by area (Strings, Shading, Production...), as Daniel had them."""
    g.host.parts.controllers['checks'].setView('area')
    g.spin(800)
    out = verifiche_gruppi(g)
    out['vista'] = 'area'
    return out


@step
def salva(g):
    """Ctrl+S on the project opened from its file."""
    before = g.file.stat().st_mtime_ns, g.file.stat().st_size
    g.spin(1100)
    g.hand.key('s', ('ctrl',))
    g.spin(3000)
    after = g.file.stat().st_mtime_ns, g.file.stat().st_size
    out = {'scritto': after != before, 'dimensione': [before[1], after[1]], 'percorso_sessione': str(g.session.path)}
    if not out['scritto']:
        out['comando'] = g.command('save')
        g.spin(3000)
        after = g.file.stat().st_mtime_ns, g.file.stat().st_size
        out['scritto_col_comando'] = after != before
    files = g.host.parts.controllers['files']
    out['dopo_ctrl_s'] = {k: str(files.property(k))[:200] for k in ('status', 'error', 'section', 'projectPath')}
    out['pagina_file_aperta'] = bool(g.window.property('fileOpen'))
    g.photo('salva-ctrl_s')
    g.window.setProperty('fileOpen', False)
    g.spin(500)
    out['salva_come'] = files.saveAs(str(g.file))           # what the chooser would do with the same name
    g.spin(1500)
    out['percorso_dopo_salva_come'] = str(g.session.path)
    mark = g.file.stat().st_mtime_ns
    g.spin(1100)
    g.hand.key('s', ('ctrl',))
    g.spin(3000)
    out['ctrl_s_dopo_salva_come'] = g.file.stat().st_mtime_ns != mark
    from meridiana.core.model import model
    again, _notice = model.Project.load(g.file)
    out['riletto'] = {'edifici': len(again.buildings), 'sottocampi': len(again.subfields),
                      'stringhe': len((again.energy.get('strings') or {}).get('runs') or [])}
    return out


@step
def salva_revisione(g):
    before = sorted(p.name for p in g.folder.iterdir())
    g.hand.key('r', ('ctrl', 'shift'))
    g.spin(3000)
    after = sorted(p.name for p in g.folder.iterdir())
    out = {'file_nuovi': sorted(set(after)-set(before))}
    if not out['file_nuovi']:
        out['comando'] = g.command('save_revision')
        g.spin(3000)
        out['file_nuovi_col_comando'] = sorted(set(p.name for p in g.folder.iterdir())-set(before))
    return out


@step
def recenti(g):
    files = g.host.parts.controllers['files']
    recent = files.property('recent')
    g.window.setProperty('fileOpen', True)
    g.spin(1500)
    g.photo('recenti-pagina')
    g.window.setProperty('fileOpen', False)
    g.spin(500)
    return {'recenti': [str(r)[:160] for r in (recent or [])][:6]}


@step
def relazione_pdf(g):
    g.show_phase('report')
    g.spin(2000)
    target = po.WORK/f'relazione-{g.engine}.pdf'
    start = time.perf_counter()
    report = g.host.parts.controllers['report']
    g.spin(3000)
    before_state = {k: str(report.property(k))[:200] for k in ('busy', 'ready', 'error', 'exportState', 'status', 'pageCount')}
    outdated = bool(g.session.year_outdated())
    report.exportPdf(str(target))
    how = 'per funzione: report.exportPdf (al posto della finestra di scelta del file)'
    g.spin(3000)
    during = {k: str(report.property(k))[:200] for k in ('busy', 'ready', 'error', 'exportState', 'status', 'progress')}
    g.wait(lambda: target.exists() and target.stat().st_size > 0, 300)
    g.spin(1000)
    if not target.exists():
        # asked while the preview was being made: asked again once the page is ready, as the designer would
        g.wait(lambda: not report.property('busy'), 300)
        g.spin(1000)
        second = time.perf_counter()
        report.exportPdf(str(target))
        g.wait(lambda: target.exists() and target.stat().st_size > 0 and not report.property('busy'), 300)
        g.spin(1500)
        how += '; la prima richiesta, fatta mentre l anteprima era in corso, non ha scritto nulla: ripetuta a pagina pronta'
        during['seconda_richiesta_s'] = round(time.perf_counter()-second, 1)
    out = {'come': how, 'secondi': round(time.perf_counter()-start, 1), 'scritto': target.exists()}
    out.update(prima=before_state, durante=during, anno_vecchio=outdated,
               dopo={k: str(report.property(k))[:200] for k in ('busy', 'error', 'exportState', 'status')})
    if target.exists():
        data = target.read_bytes()
        out['byte'] = len(data)
        out['pagine'] = len(re.findall(rb'/Type\s*/Page[^s]', data))
        shutil.copy2(target, g.out/target.name)
    return out


@step
def preferenze(g):
    g.command('preferences')
    g.spin(2000)
    g.photo('preferenze-aperte')
    out = {}
    out['aperta'] = bool(g.window.property('fileOpen'))
    g.window.setProperty('fileOpen', False)
    g.spin(800)
    return out


def _set(g, key, value):
    """The call of the Quick's Preferences page."""
    g.host.parts.controllers['settings'].setValue(key, value)
    g.spin(1500)
    return 'settings.setValue'


@step
def tema_scuro(g):
    g.show_phase('model')
    how = _set(g, 'theme', 'dark')
    g.show_phase('model')
    g.photo('tema_scuro-scuro')
    _set(g, 'theme', 'light')
    return {'come': how}


@step
def testo_grande(g):
    how = _set(g, 'textSize', 'large')
    g.show_phase('model')
    g.photo('testo_grande-grande')
    _set(g, 'textSize', 'medium')
    return {'come': how}


@step
def meridio(g):
    out = {}
    g.hand.key('l', ('ctrl',))
    g.spin(2500)
    out['oggetti'] = sorted({i.objectName() for i in g.pilot.walk() if g.pilot.shown(i)
                             and 'assist' in i.objectName().lower()})[:12]
    return out


@step
def scorciatoie_dialogo(g):
    g.keep_dialog = False
    g.command('shortcuts')
    g.spin(2000)
    g.photo('scorciatoie_dialogo-aperto')
    g.close_popups()
    return {}


@step
def import_ifc(g):
    g.show_phase('model')
    key = g.session.state_key()
    before = len(g.project.buildings)
    dialogs = g.host.parts.controllers['dialogs']
    g.command('import_ifc')
    g.spin(800)
    dialogs.readFile(str(IFC))
    g.spin(1500)
    g.wait(lambda: (dialogs.property('state') or {}).get('ifcRead') or
           ((not dialogs.property('busy')) and (dialogs.property('state') or {}).get('error')), 120)
    g.spin(800)
    g.photo('import_ifc-finestra')
    state = dialogs.property('state') or {}
    clicked = g.pilot.button('Aggiungi il modello')
    if not clicked:
        dialogs.accept()                  # what «Aggiungi il modello» calls
    how = ('comando import_ifc, file dato alla finestra (readFile), poi ' +
           ('clic su «Aggiungi il modello»' if clicked else 'accept(), la funzione di «Aggiungi il modello»'))
    extra = {'letto': state.get('ifcRead'), 'clic': clicked,
             'stato': {k: str(v)[:160] for k, v in state.items() if isinstance(v, (str, bool, int, float))}}
    g.pilot.settle(30)
    after = len(g.project.buildings)
    names = [b.name for b in g.project.buildings[before:]]
    g.photo('import_ifc-dopo')
    back = g.undo_all_to(key)
    return {'come': how, 'edifici_prima': before, 'edifici_dopo': after, 'nuovi': names, 'annullato': back, **extra}


ORDER = ['apertura', 'calcolo_f5', 'producibilita', 'non_aggiornato', 'consumi', 'economia', 'impianto',
         'catalogo_inverter', 'catalogo_ottimizzatori', 'inverter_auto', 'stringhe_auto', 'schede_componenti',
         'selezione_albero', 'selezione_multipla', 'copia_incolla', 'taglia_incolla', 'copia_trascinando',
         'vista_3d', 'vista_affiancate', 'vista_zoom', 'verifiche', 'verifiche_gruppi', 'verifiche_aree', 'import_ifc', 'salva',
         'salva_revisione', 'recenti', 'relazione_pdf', 'preferenze', 'tema_scuro', 'testo_grande', 'meridio',
         'scorciatoie_dialogo']


def main(engine, out, names):
    g = Giro(engine, out)
    try:
        g.run(names or ORDER)
    finally:
        g.log.close()
        print('fine', engine, len(g.records), f'{time.perf_counter()-g.started:.0f} s')
        po.dispose(engine, g.host)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
