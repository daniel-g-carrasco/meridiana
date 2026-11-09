"""Modelling journeys, the same gestures on Quick and on Widgets, in East/North metres on the plan.

A hand is tools/quick_real_cursor.py RealHand (the system's cursor) or NativeInput of
tools/quick_native_input.py (native messages on a hidden desktop): both offer the same calls.
A journey only records what it sees through Pilot.mark, in a JSON file: compare.py reads them.
"""
import json
import os
from collections import Counter
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QPoint, QPointF, QRectF, Qt
from PySide6.QtQuick import QQuickItem

RHO = Path(os.environ.get('MERIDIANA_REAL_HOME') or Path.home())/'dev/meridiana-prove/Prova capannone Rho.meridiana'
VIEW = (-8.0, -8.0, 150.0, 90.0)      # west, south, width, height of the plan shown at the start


def base_project(folder, journey):
    """The Rho project with its modules and system, its drawing and strings gone, as a new file in `folder`."""
    from meridiana import model
    project, _notice = model.Project.load(RHO)
    project.buildings, project.subfields, project.exclusions, project.props = [], [], [], []
    project.energy.pop('strings', None)
    project.name = 'Prova modellazione'
    target = Path(folder)/'prova.meridiana'
    project.save(target)
    return target


class Pilot:
    def __init__(self, engine, app, host, window, hand, out, journey, log):
        self.engine, self.app, self.host, self.window, self.hand = engine, app, host, window, hand
        self.out, self.journey, self.log = Path(out), journey, log
        self.records = []
        self.quick = engine == 'quick'

    # the program

    @property
    def session(self):
        return self.host.bridge.session if self.quick else self.host.session

    @property
    def project(self):
        return self.session.project

    @property
    def view(self):
        return self.host.plan

    def say(self, text):
        print(text, file=self.log, flush=True)

    def spin(self, ms=200):
        self.hand.spin(ms)

    def prepare(self):
        self.spin(1500)
        if self.quick:
            self.layer = self.window.findChild(QObject, 'worldLayer')
        else:
            from PySide6.QtCore import QTimer
            self.watch = QTimer()
            self.watch.timeout.connect(self._modal)
            self.watch.start(400)
        self.fit(*VIEW)
        self.hand.click(*self.neutral())
        self.spin(200)
        self.say(f'primo piano: {self.hand.front()}')

    def fit(self, west, south, width, height, mpp=0.2):
        """Plan alone, the same scale and centre in both programs: direct calls, the journey is about what comes next."""
        if not getattr(self, 'plan_alone', False):
            self.plan_alone = True
            self.host.shell.trigger('view_plan') if self.quick else self.host.commands['view_plan'].trigger()
            self.spin(600)
        cx, cy = west+width/2, south+height/2
        if self.quick:
            plan = self.window.findChild(QObject, 'plan')
            zoom = 1/mpp
            plan.setProperty('fitted', False)
            plan.setProperty('zoom', zoom)
            plan.setProperty('panX', plan.width()/2-cx*zoom)
            plan.setProperty('panY', plan.height()/2+cy*zoom)
            size = (plan.width(), plan.height())
        else:
            v = self.host.plan
            v.resetTransform()
            v.scale(1/mpp, 1/mpp)
            v.centerOn(QPointF(cx, -cy))
            size = (v.viewport().width(), v.viewport().height())
        self.spin(400)
        self.say(f'vista: metri per pixel {self.mpp():.5f}, pianta {size}, angoli {self.world(west, south)} {self.world(west+width, south+height)}')

    def _modal(self):
        from PySide6.QtWidgets import QApplication, QLabel
        dialog = QApplication.activeModalWidget()
        if dialog is not None:
            texts = [w.text() for w in dialog.findChildren(QLabel) if w.isVisible()]
            self.say(f'  finestra modale {type(dialog).__name__} {dialog.windowTitle()!r}: {str(texts)[:300]}')
            self.photo('modale-'+type(dialog).__name__)
            dialog.accept() if hasattr(dialog, 'accept') else dialog.close()

    def mpp(self):
        a, b = self.world(0, 0), self.world(100, 0)
        return 100/max(abs(b[0]-a[0]), .001)

    def neutral(self):
        """A place of the test window without a command: the status line at the bottom."""
        if self.quick:
            return self.centre(self.item('statusHint'))
        bar = self.host.statusBar()
        p = bar.mapToGlobal(bar.rect().center())
        return p.x(), p.y()

    # finding things

    def walk(self, item=None):
        item = item or self.window.contentItem()
        yield item
        for child in item.childItems():
            yield from self.walk(child)

    def shown(self, item):
        return item.isVisible() and item.width() > 0 and item.height() > 0 and item.opacity() > 0

    def centre(self, item):
        p = item.mapToGlobal(QPointF(item.width()/2, item.height()/2))
        return round(p.x()), round(p.y())

    def item(self, name):
        found = [i for i in self.walk() if i.objectName() == name]
        visible = [i for i in found if self.shown(i)]
        return (visible or found or [None])[0]

    def world(self, x, y):
        if self.quick:
            p = self.layer.mapToGlobal(QPointF(x, -y))
            return round(p.x()), round(p.y())
        v = self.host.plan
        p = v.viewport().mapToGlobal(v.mapFromScene(QPointF(x, -y)))
        return p.x(), p.y()

    # gestures

    def phase(self, pid):
        if self.quick:
            self.hand.click(*self.centre(self.item(pid+'Tab')))
        else:
            tabs = self.host.tabs
            index = tabs.index_of_phase(pid)
            bar = tabs.tabBar()
            p = bar.mapToGlobal(bar.tabRect(index).center())
            self.hand.click(p.x(), p.y())
        self.spin(500)
        self.say(f'fase {pid}')

    def tool(self, command):
        """The button of the bar with the real cursor. A command in a split button's menu goes through its
        command, and the log says so."""
        if self.quick:
            item = self.item('tool_'+command)
            if item is not None and self.shown(item) and item.property('enabled') is not False:
                self.hand.click(*self.centre(item))
            else:
                self.say(f'  {command}: senza pulsante visibile, comando diretto')
                self.host.shell.trigger(command)
            if command == 'tool_subfield':
                # R445: the Quick's sub-field is its modules; this journey matches the Widgets, whose sub-field is
                # an area the layout fills: «Fill an area» (the plan's menu) gives the same here
                self.host.plan.activateTool('subfield', {'fill': 'area'})
        else:
            button = None
            for bar in self.host.findChildren(QObject):
                buttons = getattr(bar, 'buttons', None)
                if isinstance(buttons, dict) and command in buttons and buttons[command].isVisible():
                    button = buttons[command]
                    break
            if button is not None and button.isEnabled():
                p = button.mapToGlobal(button.rect().center())
                self.hand.click(p.x(), p.y())
            else:
                self.say(f'  {command}: senza pulsante visibile, comando diretto')
                self.host.commands[command].trigger()
        self.spin(200)

    def at(self, x, y):
        self.hand.move(*self.world(x, y))
        self.spin(60)

    def click(self, x, y):
        self.hand.click(*self.world(x, y))
        self.spin(80)

    def polygon(self, *points):
        for x, y in points:
            self.click(x, y)

    def double(self, x, y):
        self.hand.double_click(*self.world(x, y))
        self.spin(200)

    def drag(self, a, b):
        self.hand.drag(*self.world(*a), *self.world(*b))
        self.spin(150)

    def key(self, name, *modifiers):
        self.hand.key(name, modifiers)
        self.spin(80)

    def typed(self, text):
        self.hand.type_text(text)

    def undo(self):
        self._history('z', 'undo')

    def redo(self):
        self._history('y', 'redo')

    def _history(self, key, command):
        before = self.session.state_key()
        self.key(key, 'ctrl')
        self.settle()
        if self.session.state_key() == before:
            self.say(f'  Ctrl+{key.upper()} senza effetto: {command} con il comando diretto')
            self.host.shell.trigger(command) if self.quick else self.host.commands[command].trigger()
            self.settle()

    def centres(self, index):
        """Where the modules of a sub-field are, in the order of the layout."""
        sf = self.project.subfields[index]
        result = self.session.results.get(sf.id)
        return [tuple(m.centre) for m in result.modules] if result is not None and not isinstance(result, Exception) else []

    def button(self, *names):
        """Click the first visible push button with one of these labels; the log lists what it found."""
        if self.quick:
            found = [i for i in self.walk() if self.shown(i) and i.property('text') and i.property('hovered') is not None
                     and i.property('enabled') is not False]
            texts = [str(i.property('text')).replace('&', '') for i in found]
            chosen = next((i for name in names for i, t in zip(found, texts) if t == name), None)
            if chosen is None:
                self.say(f'  pulsante {names} non trovato')
                return False
            self.hand.click(*self.centre(chosen))
        else:
            from PySide6.QtWidgets import QAbstractButton, QApplication
            found = [b for w in QApplication.topLevelWidgets() if w.isVisible() for b in w.findChildren(QAbstractButton)
                     if b.isVisible() and b.isEnabled() and b.text()]
            chosen = next((b for name in names for b in found if b.text().replace('&', '') == name), None)
            if chosen is None:
                self.say(f'  pulsante {names} non trovato')
                return False
            q = chosen.mapToGlobal(chosen.rect().center())
            self.hand.click(q.x(), q.y(), popup=True)
        self.spin(400)
        self.say(f'  pulsante premuto: {names}')
        return True

    def trigger(self, command):
        self.say(f'  {command}: comando diretto')
        self.host.shell.trigger(command) if self.quick else self.host.commands[command].trigger()
        self.spin(300)

    def edit(self, text, change):
        """A change the panels would make, by function: the log says so."""
        self.say(f'  {text}: per funzione, non dai pannelli')
        self.session.edit(text, change)
        self.spin(200)

    def compute(self, seconds=75):
        self.trigger('compute')
        import time
        start = time.perf_counter()
        before = self.session.energy_generation
        while time.perf_counter() < start+seconds and not (self.session.energy and not self.session.energy_stale()):
            self.spin(500)
        self.say(f'  calcolo: {time.perf_counter()-start:.0f} s, generazioni {before} -> {self.session.energy_generation}, '
                 f'chiavi {sorted(self.session.energy)[:12]}')

    def photo(self, name):
        path = self.out/f'{self.journey}-{self.engine}-{name}.png'
        if self.quick:
            self.window.grabWindow().save(str(path))
        else:
            self.host.grab().save(str(path))
        return path

    def settle(self, seconds=6):
        """The layouts asked for have come back, or `seconds` have gone."""
        import time
        end = time.perf_counter()+seconds
        self.spin(250)
        while time.perf_counter() < end:
            project = self.project
            good = self.session.results
            if all(s.id in good and self.session.layout_keys.get(s.id) == self._key(s)
                   for s in project.subfields if s.filled):
                self.spin(150)
                return True
            self.spin(120)
        return False

    def _key(self, subfield):
        return self.project.layout_key(subfield)

    def tool_name(self):
        return self.host.plan.tool

    def hint(self):
        return self.host.plan.hint if self.quick else ''

    # what is on record

    def state(self):
        from meridiana import checks
        from meridiana.energy import system
        p, s = self.project, self.session
        out = {'tool': str(self.tool_name()), 'undo': s.undo.count() if callable(s.undo.count) else s.undo.count,
               'can_undo': s.undo.can_undo(), 'can_redo': s.undo.can_redo()}
        out['buildings'] = [
            {'name': b.name, 'height': round(b.height, 3), 'corners': len(b.footprint),
             'footprint': [[round(c, 2) for c in pt] for pt in b.footprint],
             'roof': {'type': b.roof.type, 'tilt': b.roof.tilt, 'ridge_height': b.roof.ridge_height,
                      'free': len(b.roof.free_pitches or []),
                      'edges': list(b.roof.edges or [])},
             'pitches': [{'tilt': round(float(getattr(r, 'tilt', 0) or 0), 2),
                          'azimuth': round(float(getattr(r, 'azimuth', 0) or 0), 2),
                          'corners': len(r.ring)} for r in b.pitches()]}
            for b in p.buildings]
        modules = 0
        kwp = 0.0
        subfields = []
        for sf in p.subfields:
            result = s.results.get(sf.id)
            error = str(result) if isinstance(result, Exception) else ''
            count = 0 if (result is None or error) else result.count
            modules += count
            power = self._module_power(sf)
            kwp += count*power/1000
            subfields.append({
                'name': sf.name, 'filled': sf.filled, 'building': sf.building, 'corners': len(sf.ring),
                'ring': [[round(c, 2) for c in pt] for pt in sf.ring], 'modules': count, 'error': error[:160],
                'tilt': None if result is None or error else round(result.tilt, 3),
                'azimuth': None if result is None or error else round(result.azimuth, 3),
                'params': {k: v for k, v in (sf.params or {}).items() if isinstance(v, (int, float, str, bool))}})
        out['subfields'] = subfields
        out['exclusions'] = [{'corners': len(e.ring)} for e in p.exclusions]
        out['props'] = len(p.props)
        out['modules'] = modules
        out['kwp'] = round(kwp, 3)
        runs = (p.energy.get('strings') or {})
        out['strings'] = _strings_summary(p)
        try:
            inverter = system.inverter_of(p) if hasattr(system, 'inverter_of') else None
            items = checks.gather(p, s.good_results(), s.energy, inverter, bool(system.inverter_entries(p.energy)))
            out['checks'] = dict(Counter(i.level for i in items))
            out['checks_text'] = sorted(f'{i.level}: {i.text}' for i in items if i.level in ('fail', 'warn'))
        except Exception as error:
            out['checks_error'] = repr(error)[:200]
        out['energy_kwh'] = _energy(s.energy)
        return out

    def _module_power(self, sf):
        try:
            record = self.project.modules.get(sf.params.get('module') or next(iter(self.project.modules)))
            return float(record.get('power_kw') or 0)*1000
        except Exception:
            return 0.0

    def mark(self, label, note=''):
        """Writes the state: the journey goes on whatever it says."""
        import time
        start = time.perf_counter()
        settled = self.settle(60)
        took = time.perf_counter()-start
        if took > 2:
            self.say(f'  posa in ritardo prima di [{label}]: {took:.1f} s, arrivata {settled}')
        state = self.state()
        state.update(label=label, note=note, settled=settled)
        self.records.append(state)
        (self.out/f'{self.journey}-{self.engine}.json').write_text(
            json.dumps(self.records, ensure_ascii=False, indent=1), encoding='utf8')
        self.say(f'[{label}] tool={state["tool"]} edifici={len(state["buildings"])} '
                 f'falde={sum(len(b["pitches"]) for b in state["buildings"])} '
                 f'sottocampi={len(state["subfields"])} esclusioni={len(state["exclusions"])} '
                 f'moduli={state["modules"]} kWp={state["kwp"]} stringhe={state["strings"]["runs"]} '
                 f'annulli={state["undo"]} {note}')
        return state


def _strings_summary(project):
    data = project.energy.get('strings') or {}
    runs = data.get('runs') if isinstance(data, dict) else None
    auto = data.get('auto') if isinstance(data, dict) else None
    keys = sorted(data) if isinstance(data, dict) else []
    if not runs:
        return {'runs': 0, 'modules': 0, 'sizes': [], 'keys': keys, 'auto': bool(auto), 'auto_text': str(auto)[:120]}
    sizes = [len(r.get('modules') or []) for r in runs]
    return {'runs': len(runs), 'modules': sum(sizes), 'sizes': sizes, 'keys': keys, 'auto': bool(auto),
            'targets': sorted(f"{r.get('inverter', 0)}/{r.get('mppt', 0)}" for r in runs)}


def _energy(energy):
    """The year, if computed: its energy and specific yield, or why there is none."""
    if not energy:
        return None
    sim = energy.get('sim')
    if sim is None:
        return {'error': str(energy.get('error_sim'))[:100]}
    return {'kwh': round(float(sim.energy_kwh), 1), 'kwh_kwp': round(float(sim.specific_yield), 2)}


def facts(pilot):
    """What the driver needs to know about a window; no input beyond the first click."""
    pilot.say(f'hint {pilot.hint()!r} tool {pilot.tool_name()!r}')
    pilot.mark('facts')
    if pilot.quick:
        names = sorted({i.objectName() for i in pilot.walk() if i.objectName().startswith(('tool_', 'planView'))
                        and pilot.shown(i)})
        pilot.say(f'pulsanti {names}')
    else:
        for bar in pilot.host.findChildren(QObject):
            buttons = getattr(bar, 'buttons', None)
            if isinstance(buttons, dict) and buttons:
                pilot.say(f'{type(bar).__name__}: {sorted(buttons)[:30]}')
    module = pilot.project.modules
    pilot.say(f'moduli {str(module)[:400]}')
    pilot.say(f'energy {str(pilot.project.energy)[:400]}')


JOURNEYS = {}


def journey(function):
    JOURNEYS[function.__name__] = function
    return function


def rotated(x, y, w, h, degrees):
    """The corners of a rectangle turned about (x, y)."""
    import math
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return [(x+px*c-py*s, y+px*s+py*c) for px, py in ((0, 0), (w, 0), (w, h), (0, h))]


def rectangle(p, a, b, c):
    """Rectangle mode: two corners give a side, the third the depth."""
    p.click(*a)
    p.click(*b)
    p.at(*c)
    p.click(*c)


@journey
def edifici(p):
    p.phase('model')
    p.mark('avvio')
    p.tool('tool_building')
    p.mark('strumento edificio')
    p.polygon((0, 0), (40, 0), (40, 20), (0, 20))
    p.key('enter')
    p.mark('rettangolo a 4 clic e Invio')
    p.polygon((55, 0), (85, 0), (85, 15), (70, 15), (70, 30), (55, 30))
    p.key('enter')
    p.mark('L a 6 clic e Invio')
    a, b, c, d = rotated(10, 35, 30, 15, 27)
    p.polygon(a, b, c)
    p.double(*d)
    p.mark('ruotato 27 gradi, chiuso con doppio clic')
    p.polygon((90, 40), (100, 40), (110, 40))
    p.key('enter')
    p.mark('tre punti allineati e Invio', 'atteso: rifiuto')
    p.say(f'  dopo il rifiuto: {_message(p)!r}, strumento {p.tool_name()}')
    p.key('esc')
    p.key('esc')
    p.tool('tool_building')
    p.polygon((60, 40), (80, 60), (80, 40), (60, 60))
    p.key('enter')
    p.mark('contorno che si incrocia e Invio', 'atteso: rifiuto')
    p.say(f'  dopo il rifiuto: {_message(p)!r}, strumento {p.tool_name()}')
    p.key('esc')
    p.key('esc')
    p.tool('tool_building')
    p.polygon((90, 50), (90.4, 50), (90.4, 50.4))
    p.key('enter')
    p.mark('triangolo da 0,08 m2 e Invio', 'atteso: rifiuto')
    p.say(f'  dopo il rifiuto: {_message(p)!r}, strumento {p.tool_name()}')
    p.key('esc')
    p.key('esc')
    p.tool('tool_building')
    p.polygon((30, 10), (50, 10), (50, 30), (30, 30))
    p.key('enter')
    p.mark('edificio sovrapposto a un altro')
    p.key('esc')
    p.mark('primo Esc')
    p.key('esc')
    p.mark('secondo Esc: Seleziona')
    for n in range(4):
        p.undo()
        p.mark(f'annulla {n+1}')
    p.redo()
    p.mark('ripeti 1')
    p.redo()
    p.mark('ripeti 2')
    p.key('b')
    p.key('r')
    rectangle(p, (0, 55), (30, 55), (30, 70))
    p.mark('tasto B, tasto R, rettangolo a 3 clic')
    p.key('esc')
    p.key('esc')
    p.mark('fine')
    p.photo('fine')


@journey
def falde(p):
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (40, 0), (40, 20), (0, 20))
    p.key('enter')
    p.polygon((55, 0), (85, 0), (85, 15), (70, 15), (70, 30), (55, 30))
    p.key('enter')
    p.polygon((100, 0), (130, 0), (130, 15), (100, 15))
    p.key('enter')
    p.polygon((0, 35), (40, 35), (40, 60), (0, 60))
    p.key('enter')
    a, b, c, d = rotated(70, 40, 30, 15, 27)
    p.polygon(a, b, c, d)
    p.key('enter')
    p.key('esc')
    p.mark('cinque edifici')
    p.key('c')
    p.mark('tasto C: colmo')
    p.polygon((5, 10), (35, 10))
    p.mark('colmo interno a due clic su rettangolo')
    p.key('esc')
    p.undo()
    p.mark('annulla colmo')
    p.redo()
    p.mark('ripeti colmo')
    p.key('esc')
    p.key('c')
    p.polygon((100, 7.5), (130, 7.5))
    p.mark('colmo da lato a lato: capanna')
    p.key('esc')
    p.key('c')
    p.polygon((60, 5), (62, 25))
    p.key('enter')
    p.mark('colmo su edificio a L, Invio')
    p.key('esc')
    p.key('esc')
    p.key('p')
    p.mark('tasto P: falda')
    p.click(2, 37)
    p.click(38, 37)
    p.at(38, 47)
    p.click(38, 47)
    p.mark('falda libera a 3 clic, senza valori')
    p.click(2, 49)
    p.click(38, 49)
    p.at(38, 58)
    p.key('down')
    p.typed('60')
    p.key('enter')
    p.click(38, 58)
    p.mark('falda con inclinazione digitata 60')
    p.key('esc')
    p.key('p')
    a, b, c, d = rotated(72, 42, 26, 12, 27)
    p.click(*a)
    p.click(*b)
    p.at(*c)
    p.key('tab')
    p.click(*c)
    p.mark('falda non allineata, Tab che scambia la gronda')
    p.key('esc')
    p.key('esc')
    p.mark('Esc Esc dopo la falda')
    p.key('p')
    p.key('r')
    p.polygon((102, 2), (128, 2), (128, 10), (115, 13), (102, 10))
    p.key('enter')
    p.mark('tasto R, falda a 5 vertici')
    p.key('esc')
    p.mark('primo Esc')
    p.key('esc')
    p.mark('secondo Esc')
    p.key('esc')
    p.mark('terzo Esc')
    p.key('p')
    p.click(70, 70)
    p.click(100, 70)
    p.at(100, 75)
    p.click(100, 75)
    p.mark('falda fuori da ogni edificio')
    p.key('esc')
    p.key('esc')
    p.key('esc')
    p.key('p')
    p.click(2, 2)
    p.click(2.2, 2)
    p.at(2.2, 2.1)
    p.click(2.2, 2.1)
    p.mark('falda stretta da 20 cm')
    p.key('esc')
    p.key('esc')
    p.key('esc')
    for n in range(3):
        p.undo()
        p.mark(f'annulla {n+1}')
    for n in range(3):
        p.redo()
        p.mark(f'ripeti {n+1}')
    p.click(20, 42)
    p.mark('clic su una falda libera')
    p.key('delete')
    p.mark('Canc sulla falda')
    p.undo()
    p.mark('annulla Canc')
    p.photo('fine')
    p.phase('plant')
    p.phase('model')
    p.mark('andata e ritorno tra le fasi')


@journey
def modifica(p):
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (40, 0), (40, 20), (0, 20))
    p.key('enter')
    p.polygon((60, 0), (90, 0), (90, 20), (60, 20))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.click(20, 10)
    p.mark('edificio selezionato')
    p.drag((40, 20), (45, 25))
    p.mark('presa d angolo trascinata')
    p.undo()
    p.mark('annulla presa')
    p.key('m')
    p.mark('tasto M con selezione')
    p.click(20, 10)
    p.click(25, 40)
    p.mark('sposta a due punti')
    p.key('esc')
    p.undo()
    p.mark('annulla sposta')
    p.key('esc')
    p.click(20, 10)
    p.tool('tool_rotate')
    p.mark('Ruota premuto')
    p.at(25, 15)
    p.typed('30')
    p.key('enter')
    p.mark('ruota digitando 30')
    p.key('esc')
    p.key('esc')
    p.undo()
    p.mark('annulla ruota')
    p.key('esc')
    p.click(75, 10)
    p.key('m')
    before = p.session.state_key()
    p.click(75, 10)
    p.hand.move(*p.world(75, 40))
    p.hand.spin(100)
    p.key('r')
    p.mark('R dentro Sposta')
    p.click(75, 40)
    p.mark('sposta e gira con R, un clic dopo R')
    if p.session.state_key() == before:
        p.at(90, 40)
        p.click(90, 40)
        p.mark('sposta e gira con R, due clic dopo R')
    p.key('esc')
    p.key('esc')
    if p.session.state_key() != before:
        p.undo()
    p.mark('annulla sposta e gira')
    p.click(75, 10)
    p.key('delete')
    p.mark('Canc su edificio')
    p.undo()
    p.mark('annulla Canc')
    p.click(75, 10)
    p.say('altezza e colmo per funzione')

    def taller(project):
        project.buildings[-1].height = 12.5
    p.edit('altezza 12,5', taller)
    p.mark('altezza 12,5')
    p.key('c')
    p.polygon((62, 10), (88, 10))
    p.mark('colmo sull edificio alto')

    def ridge(project):
        project.buildings[-1].roof.ridge_height = 18
    p.edit('colmo 18', ridge)
    p.mark('altezza di colmo 18')
    p.key('esc')
    p.key('esc')
    p.photo('fine')


@journey
def pensilina(p):
    p.phase('model')
    p.tool('carport')
    p.spin(1200)
    p.photo('dialogo')
    p.mark('Pensilina premuto')
    if p.quick:
        p.button('Mettilo in pianta')
        p.spin(300)
    p.say(f'dopo il dialogo: strumento {p.tool_name()}')
    p.click(30, 30)
    p.spin(800)
    p.photo('posata')
    p.mark('clic sulla pianta')
    p.key('esc')
    p.key('esc')
    p.mark('Esc')
    p.phase('plant')
    p.trigger('canopy_layout')
    p.spin(1500)
    p.photo('su-pensilina')
    p.mark('Su pensilina premuto')
    p.say(f'finestre: {dialog_text(p)}')
    if p.quick:
        p.button('Posa', 'OK', 'Applica', 'Sì')
    p.spin(1500)
    p.mark('Su pensilina confermato')
    p.key('esc')
    p.key('esc')
    p.undo()
    p.mark('annulla Su pensilina')
    p.undo()
    p.mark('annulla pensilina')


@journey
def pannelli(p):
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (60, 0), (60, 30), (0, 30))
    p.key('enter')
    p.polygon((70, 0), (110, 0), (110, 30), (70, 30))
    p.key('enter')
    p.polygon((0, 40), (10, 40), (10, 50), (0, 50))
    p.key('enter')
    p.key('esc')
    p.key('c')
    p.polygon((72, 15), (108, 15))
    p.key('esc')
    p.key('esc')
    p.mark('tre edifici e un colmo')
    p.phase('plant')
    p.tool('tool_subfield')
    p.mark('strumento sottocampo')
    p.double(30, 15)
    p.mark('doppio clic: tutto il tetto piano')
    p.tool('fill')
    p.mark('Posa')
    p.key('esc')
    p.tool('tool_subfield')
    p.double(90, 7)
    p.mark('doppio clic: tutta la falda sud')
    p.tool('fill')
    p.mark('Posa sulla falda')
    p.key('esc')
    p.tool('tool_subfield')
    p.polygon((75, 18), (105, 18), (105, 27), (75, 27))
    p.key('enter')
    p.mark('area disegnata sulla falda nord')
    p.tool('fill')
    p.mark('Posa area disegnata')
    p.key('esc')
    p.tool('tool_subfield')
    p.polygon((2, 42), (3, 42), (3, 43), (2, 43))
    p.key('enter')
    p.tool('fill')
    p.mark('sottocampo 1 m per 1 m', 'non contiene un modulo')
    p.key('esc')
    p.tool('tool_subfield')
    p.polygon((30, 45), (50, 45), (50, 60), (30, 60))
    p.key('enter')
    p.tool('fill')
    p.mark('sottocampo fuori dagli edifici')
    p.key('esc')
    p.key('esc')
    p.phase('model')
    p.key('x')
    p.polygon((20, 10), (30, 10), (30, 20), (20, 20))
    p.key('enter')
    p.mark('esclusione dopo la posa, tetto piano')
    a, b, c, d = rotated(85, 3, 6, 4, 30)
    p.polygon(a, b, c, d)
    p.key('enter')
    p.mark('esclusione ruotata sulla falda')
    p.key('esc')
    p.key('esc')
    p.undo()
    p.mark('annulla esclusione')
    p.redo()
    p.mark('ripeti esclusione')
    p.phase('plant')
    centres = p.centres(0)
    p.say(f'moduli sottocampo 0: {len(centres)}')
    if len(centres) > 30:
        p.click(*centres[10])
        p.mark('clic su un modulo')
        p.key('delete')
        p.mark('Canc su un modulo')
        p.undo()
        p.mark('annulla Canc')
        p.redo()
        p.mark('ripeti Canc')
        p.key('esc')
    p.drag((5, 3), (15, 8))
    p.mark('finestra sui moduli')
    p.key('delete')
    p.mark('Canc sui moduli della finestra')
    p.undo()
    p.mark('annulla finestra')
    p.key('esc')
    p.key('esc')
    p.photo('posa')

    def change(project):
        project.subfields[0].params.update(tilt=30, azimuth=20, portrait=False)
    p.edit('inclinazione 30, azimut 20, orizzontale', change)
    p.mark('sottocampo a 30 gradi, azimut 20, orizzontale')
    p.undo()
    p.mark('annulla parametri')
    p.tool('tool_measure')
    p.key('esc')
    p.trigger('tool_row')
    p.click(32, 40)
    p.click(45, 40)
    p.mark('fila a due clic fuori dai sottocampi')
    p.key('esc')
    p.key('esc')
    p.mark('Esc: Seleziona')
    p.phase('production')
    p.phase('plant')
    p.mark('andata e ritorno')
    p.compute()
    p.mark('calcolo')
    p.photo('fine')


def strings_setup(p):
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (30, 0), (30, 15), (0, 15))
    p.key('enter')
    p.polygon((35, 0), (60, 0), (60, 20), (35, 20))
    p.key('enter')
    p.key('esc')
    p.key('c')
    p.polygon((37, 10), (58, 10))
    p.key('esc')
    p.key('esc')
    p.phase('plant')
    p.tool('tool_subfield')
    p.double(15, 7)
    p.tool('fill')
    p.key('esc')
    p.tool('tool_subfield')
    p.double(48, 5)
    p.tool('fill')
    p.key('esc')
    p.tool('tool_subfield')
    p.double(48, 15)
    p.tool('fill')
    p.key('esc')
    p.key('esc')
    if not p.settle(90):
        p.say('la posa non e arrivata in 90 s')
    p.mark('tre sottocampi posati')


@journey
def stringhe(p):
    p.fit(-5, -5, 75, 40, .08)
    strings_setup(p)
    p.say(f'moduli per sottocampo {[len(p.centres(i)) for i in range(len(p.project.subfields))]}')
    p.tool('strings_auto')
    p.spin(1000)
    p.photo('auto-aperto')
    p.mark('Automatica premuto')
    p.button('Stringa', 'Proponi', 'OK')
    p.spin(4000)
    p.mark('Stringa premuto, 4 secondi dopo')
    p.photo('auto')
    p.undo()
    p.mark('annulla automatica')
    p.redo()
    p.mark('ripeti automatica')
    p.trigger('strings_clear')
    p.spin(800)
    p.photo('cancella-tutte')
    p.mark('Cancella tutte, comando')
    p.say(f'finestre: {dialog_text(p)}')
    p.button('Continua', 'Elimina', 'Cancella', 'Sì', 'Elimina tutte', 'OK')
    p.mark('Cancella tutte, confermato')
    a = p.centres(0)
    b = p.centres(1)
    c = p.centres(2)
    p.tool('strings_manual')
    p.mark('Disegna premuto')
    for m in a[:6]:
        p.click(*m)
    p.key('backspace')
    p.key('enter')
    p.mark('a mano: 6 clic, Backspace, Invio', 'attese 5 nella stringa')
    p.tool('strings_manual')
    for m in a[6:10]:
        p.click(*m)
    p.double(*a[10])
    p.mark('a mano: 4 clic e doppio clic')
    p.tool('strings_manual')
    for m in a[11:14]:
        p.click(*m)
    p.key('esc')
    p.mark('a mano: 3 clic ed Esc', 'non deve restare')
    p.key('esc')
    p.mark('altro Esc: Seleziona')
    p.tool('strings_manual')
    p.click(*a[14])
    p.click(*a[15])
    p.click(*b[0])
    p.click(*c[0])
    p.key('enter')
    p.mark('a mano: stringa su tre orientamenti')
    p.tool('strings_manual')
    p.drag(a[16], a[22])
    p.key('enter')
    p.mark('a mano: trascinando sui moduli')
    p.tool('strings_manual')
    p.click(*a[0])
    p.click(*a[1])
    p.key('enter')
    p.mark('a mano: moduli gia in un altra stringa', 'riassegnazione')
    p.tool('strings_manual')
    for m in b[1:len(b)-1]:
        p.click(*m)
    p.key('enter')
    p.mark('a mano: stringa lunghissima')
    p.undo()
    p.mark('annulla stringa')
    p.redo()
    p.mark('ripeti stringa')
    p.trigger('strings_complete')
    p.spin(800)
    p.button('Stringa', 'Proponi', 'OK')
    p.spin(2500)
    p.mark('Completa')
    p.undo()
    p.mark('annulla Completa')
    p.tool('tool_erase_string')
    p.mark('strumento cancella stringa')
    p.at(*a[3])
    p.spin(200)
    p.click(*a[3])
    p.mark('clic con cancella stringa')
    p.click(*p.centres(0)[-1])
    p.mark('clic con cancella stringa su un modulo fuori stringa', 'deve dirlo')
    p.key('esc')
    p.key('esc')
    p.mark('Esc: Seleziona')
    p.undo()
    p.mark('annulla cancellazione')
    p.phase('model')
    p.key('x')
    p.polygon((3, 3), (12, 3), (12, 9), (3, 9))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.mark('esclusione sopra moduli in stringa')
    p.phase('plant')
    p.mark('tornato in Impianto')
    p.undo()
    p.mark('annulla esclusione')
    p.photo('fine')
    p.compute()
    p.mark('calcolo')


@journey
def grande(p):
    import time
    p.fit(-20, -20, 460, 260, .6)
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (420, 0), (420, 220), (0, 220))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.mark('edificio 420 per 220')
    p.phase('plant')
    p.tool('tool_subfield')
    p.double(200, 100)
    p.tool('fill')
    start = time.perf_counter()
    p.settle(60)
    p.say(f'posa: {time.perf_counter()-start:.1f} s')
    p.mark('posa grande')
    start = time.perf_counter()
    p.key('esc')
    p.key('esc')
    p.drag((50, 50), (120, 100))
    p.say(f'finestra di selezione: {time.perf_counter()-start:.1f} s')
    p.mark('finestra di selezione')
    start = time.perf_counter()
    p.key('delete')
    p.settle(30)
    p.say(f'Canc: {time.perf_counter()-start:.1f} s')
    p.mark('Canc su molti moduli')
    start = time.perf_counter()
    p.undo()
    p.say(f'annulla: {time.perf_counter()-start:.1f} s')
    p.mark('annulla')
    p.key('esc')
    p.phase('model')
    p.key('x')
    p.polygon((200, 100), (230, 100), (230, 130), (200, 130))
    p.key('enter')
    start = time.perf_counter()
    p.settle(60)
    p.say(f'esclusione, nuova posa: {time.perf_counter()-start:.1f} s')
    p.mark('esclusione su posa grande')
    p.key('esc')
    p.key('esc')
    p.phase('plant')
    p.tool('strings_auto')
    p.spin(800)
    p.button('Stringa')
    start = time.perf_counter()
    p.spin(8000)
    p.say(f'stringa automatica su posa grande: {time.perf_counter()-start:.1f} s')
    p.mark('stringa automatica grande')
    p.photo('fine')


@journey
def vista3d(p):
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (40, 0), (40, 20), (0, 20))
    p.key('enter')
    p.polygon((60, 0), (100, 0), (100, 30), (60, 30))
    p.key('enter')
    p.key('esc')
    p.key('c')
    p.polygon((60, 15), (100, 15))
    p.key('esc')
    p.key('esc')
    p.phase('plant')
    p.tool('tool_subfield')
    p.double(20, 10)
    p.tool('fill')
    p.key('esc')
    p.tool('tool_subfield')
    p.double(80, 8)
    p.tool('fill')
    p.key('esc')
    p.key('esc')
    p.mark('prima del 3D')
    p.trigger('view_both')
    p.spin(2500)
    p.photo('tutte-e-due')
    p.trigger('view_3d')
    p.spin(2500)
    p.photo('solo-3d')
    p.mark('3D aperto')
    p.trigger('view_plan')
    p.spin(800)
    p.mark('pianta di nuovo')


@journey
def salva(p):
    """Save with the program's command on a file in the output folder, read it again, count again."""
    from meridiana import model
    target = p.out/f'salva-{p.engine}.meridiana'
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (40, 0), (40, 20), (0, 20))
    p.key('enter')
    p.polygon((55, 0), (85, 0), (85, 30), (55, 30))
    p.key('enter')
    p.key('esc')
    p.key('c')
    p.polygon((55, 15), (85, 15))
    p.key('esc')
    p.key('esc')
    p.key('x')
    p.polygon((10, 5), (15, 5), (15, 10), (10, 10))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.phase('plant')
    p.tool('tool_subfield')
    p.double(30, 10)
    p.tool('fill')
    p.key('esc')
    p.tool('tool_subfield')
    p.double(70, 8)
    p.tool('fill')
    p.key('esc')
    p.key('esc')
    p.tool('strings_auto')
    p.spin(800)
    p.button('Stringa')
    p.spin(6000)
    state = p.mark('prima di salvare')
    p.session.path = target
    if not p.quick:
        p.host.session.path = target
    p.trigger('save')
    p.spin(1500)
    p.say(f'file scritto: {target.exists()} {target.stat().st_size if target.exists() else 0} byte; path {p.session.path}')
    if not target.exists():
        p.say('il comando non ha scritto: salvataggio per funzione')
        p.project.save(target)
    project, notice = model.Project.load(target)
    results = {sf.id: project.fill(sf) for sf in project.subfields if sf.filled}
    runs = (project.energy.get('strings') or {}).get('runs') or []
    p.say(f'riaperto: avviso {notice!r}, edifici {len(project.buildings)}, esclusioni {len(project.exclusions)}, '
          f'moduli {sum(r.count for r in results.values())}, stringhe {len(runs)}, nel programma moduli {state["modules"]} stringhe {state["strings"]["runs"]}')
    p.undo()
    p.mark('annulla dopo il salvataggio')
    p.phase('production')
    p.phase('model')
    p.mark('fasi dopo il salvataggio')


@journey
def automatica(p):
    """Automatic stringing alone: how long, on which inputs, then replaced, then completed."""
    import time
    p.fit(-5, -5, 75, 40, .08)
    strings_setup(p)
    p.tool('strings_auto')
    p.spin(800)
    if not p.quick:
        from PySide6.QtWidgets import QAbstractButton, QApplication
        p.say(f"finestre {[(type(w).__name__, w.isVisible()) for w in QApplication.topLevelWidgets() if w.isVisible()]}")
        p.say(f"pulsanti {[b.text() for w in QApplication.topLevelWidgets() if w.isVisible() for b in w.findChildren(QAbstractButton) if b.isVisible() and b.text()][-12:]}")
    p.button('Stringa')
    start = time.perf_counter()
    while time.perf_counter()-start < 30 and not _strings_summary(p.project)['runs']:
        p.spin(300)
    p.say(f'stringhe automatiche dopo {time.perf_counter()-start:.1f} s')
    p.mark('prima proposta')
    p.tool('strings_auto')
    p.spin(800)
    p.button('Stringa')
    p.spin(800)
    p.say(f'finestre di domanda {getattr(p.host, "message_boxes", [])[-1:]}')
    p.button('Continua', 'Sì', 'Yes')
    p.spin(5000)
    p.mark('seconda proposta sopra la prima')
    p.undo()
    p.mark('annulla seconda proposta')
    p.key('esc')
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 20), (30, 20), (30, 30), (0, 30))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.phase('plant')
    p.tool('tool_subfield')
    p.double(15, 25)
    p.tool('fill')
    p.key('esc')
    p.key('esc')
    p.mark('sottocampo nuovo dopo le stringhe', 'i suoi moduli restano fuori stringa')
    p.trigger('strings_complete')
    p.spin(800)
    p.button('Stringa')
    p.spin(5000)
    p.mark('Completa: solo i moduli nuovi')
    p.compute()
    p.mark('calcolo')
    p.photo('fine')


@journey
def lunga(p):
    """A string too long and one too short, then the year: both programs must say the same in the Checks."""
    p.fit(-5, -5, 75, 40, .08)
    strings_setup(p)
    a, b = p.centres(0), p.centres(1)
    p.tool('strings_manual')
    for m in b[:78]:
        p.click(*m)
    p.key('enter')
    p.spin(4000)
    p.mark('stringa da 78 moduli, 4 secondi dopo')
    p.compute()
    p.mark('stringa da 78 moduli, calcolo')
    p.tool('strings_manual')
    for m in a[:2]:
        p.click(*m)
    p.key('enter')
    p.spin(4000)
    p.mark('stringa da 2 moduli, 4 secondi dopo')
    p.compute()
    p.mark('stringa da 2 moduli, calcolo')
    p.phase('production')
    p.spin(800)
    p.photo('producibilita')
    p.phase('plant')
    p.mark('fine')


@journey
def piccoli(p):
    """Small or odd outlines, as a distracted user draws them: what is kept, what is refused, and what the program says."""
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (60, 0), (60, 40), (0, 40))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.phase('plant')
    cases = [
        ('1 m per 1 m', [(2, 2), (3, 2), (3, 3), (2, 3)]),
        ('1,5 m per 1,5 m', [(6, 2), (7.5, 2), (7.5, 3.5), (6, 3.5)]),
        ('3 m per 3 m', [(10, 2), (13, 2), (13, 5), (10, 5)]),
        ('striscia 30 m per 0,4 m', [(15, 2), (45, 2), (45, 2.4), (15, 2.4)]),
        ('triangolo', [(50, 2), (58, 2), (54, 8)]),
        ('sporge dal tetto', [(50, 30), (70, 30), (70, 50), (50, 50)]),
        ('si incrocia', [(10, 10), (25, 25), (25, 10), (10, 25)]),
    ]
    for name, ring in cases:
        p.tool('tool_subfield')
        p.polygon(*ring)
        p.key('enter')
        p.spin(200)
        p.say(f'{name}: messaggio {_message(p)!r}')
        p.tool('fill')
        p.spin(200)
        p.key('esc')
        p.key('esc')
        p.key('esc')
        p.mark(f'sottocampo {name}')
    p.tool('tool_subfield')
    p.double(30, 35)
    p.mark('doppio clic: tutto il tetto sopra gli altri')
    p.key('esc')
    p.key('esc')
    p.mark('fine')
    p.photo('fine')


def _message(p):
    """What the status line says now."""
    if p.quick:
        item = p.item('statusHint')
        return str(item.property('text'))[:140] if item is not None else ''
    return p.host.statusBar().currentMessage()[:140] or str(p.host.hint.text())[:140]


def wait_layout(p, label, seconds=90):
    """How long from an edit to the modules on the plan being those of the edit; the count at 2 s tells what is seen."""
    import time
    start = time.perf_counter()
    at_two = None
    done = None
    while time.perf_counter()-start < seconds:
        p.spin(100)
        if at_two is None and time.perf_counter()-start >= 2:
            at_two = sum(c.count for c in p.session.results.values() if not isinstance(c, Exception))
        if done is None and all(sf.id in p.session.results and p.session.layout_keys.get(sf.id) == p.project.layout_key(sf)
                                for sf in p.project.subfields if sf.filled):
            done = time.perf_counter()-start
            break
    total = sum(c.count for c in p.session.results.values() if not isinstance(c, Exception))
    p.say(f'{label}: posa aggiornata dopo {"mai" if done is None else f"{done:.1f} s"}; moduli a 2 s {at_two}, alla fine {total}')
    return done


@journey
def ritardo(p):
    """After an edit, when do the modules follow? With the year being computed and without."""
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (60, 0), (60, 30), (0, 30))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.phase('plant')
    p.tool('tool_subfield')
    p.double(30, 15)
    p.tool('fill')
    p.key('esc')
    p.key('esc')
    p.settle(20)
    p.tool('strings_auto')
    p.spin(800)
    p.button('Stringa')
    p.spin(1500)
    p.mark('stringhe')
    wait_layout(p, 'dopo le stringhe')
    centres = p.centres(0)
    p.click(*centres[10])
    p.spin(150)
    p.key('delete')
    wait_layout(p, 'Canc su un modulo, subito')
    p.mark('Canc su un modulo')
    p.spin(30000)
    p.say(f'chiavi energia dopo 30 s: {sorted(p.session.energy)[:6]}')
    p.click(*p.centres(0)[20])
    p.spin(150)
    p.key('delete')
    wait_layout(p, 'Canc su un modulo, a calcolo finito')
    p.mark('Canc su un altro modulo')

    def change(project):
        project.subfields[0].params.update(tilt=30, azimuth=20, portrait=False)
    p.edit('inclinazione 30, azimut 20, orizzontale', change)
    wait_layout(p, 'parametri cambiati')
    p.mark('parametri cambiati')
    p.undo()
    wait_layout(p, 'annulla parametri')
    p.mark('annulla parametri')


def prop(p, key, value):
    """A value through the panel's own way in: the commit of the form, the signal of the inspector."""
    if p.quick:
        done = p.host.parts.controllers['properties'].commit(key, value)
    else:
        from meridiana.ui.properties import Properties
        inspector = next((o for o in p.host.findChildren(Properties)), None) if hasattr(Properties, 'edited') else None
        inspector.edited.emit(inspector.kind, inspector.oid, {key: value})
        done = True
    p.spin(200)
    p.say(f'  proprieta {key} = {value}: {done}')
    return done


@journey
def proprieta(p):
    """Everything the Properties panel changes on a roof and a sub-field: the values go in through the panel's function."""
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (60, 0), (60, 30), (0, 30))
    p.key('enter')
    p.polygon((70, 0), (110, 0), (110, 30), (70, 30))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.phase('plant')
    p.tool('tool_subfield')
    p.double(30, 15)
    p.tool('fill')
    p.key('esc')
    p.key('esc')
    p.mark('tetto piano posato')
    p.click(30, 3 if False else 0.4)
    p.spin(200)
    p.say(f'selezione {p.session.selection}')
    if p.session.selection[0] != 'subfield':
        p.session.select('subfield', p.project.subfields[0].id)
        p.spin(300)
        p.say('selezione per funzione')
    if p.quick:
        prop(p, 'automatic', False)
    for key, value in (('params.tilt', 30.0), ('params.azimuth', 20.0), ('params.portrait', False), ('params.stack', 2),
                       ('params.edge', 1.5), ('params.mounting', 'flush'), ('params.mounting', 'east_west'),
                       ('params.mounting', 'tilted_anchored')):
        prop(p, key, value)
        p.mark(f'sottocampo {key} {value}')
    p.phase('model')
    p.key('esc')
    p.key('esc')
    p.key('esc')
    p.click(90, 15)
    p.spin(200)
    p.say(f'selezione {p.session.selection}')
    prop(p, 'height', 12.5)
    p.mark('altezza di gronda 12,5')
    p.key('c')
    p.polygon((70, 15), (110, 15))
    p.key('esc')
    p.key('esc')
    p.mark('capanna')
    p.click(90, 7)
    p.spin(200)
    p.say(f'selezione {p.session.selection}')
    if p.session.selection[0] != 'building':
        p.session.select('building', p.project.buildings[1].id)
        p.spin(300)
    prop(p, 'roof.tilt', 35.0)
    p.mark('pendenza 35')
    prop(p, 'roof.ridge_height', 20.0)
    p.mark('quota di colmo 20')
    prop(p, 'roof.tilt', 0.0)
    p.mark('pendenza 0')
    prop(p, 'roof.tilt', 75.0)
    p.mark('pendenza 75')
    p.phase('plant')
    p.tool('tool_subfield')
    p.double(90, 7)
    p.tool('fill')
    p.key('esc')
    p.key('esc')
    p.mark('moduli sulla falda ripida')
    p.undo()
    p.undo()
    p.mark('due annulla')


@journey
def file(p):
    """Rows by hand and east-west inside a sub-field, then a change after the laying."""
    p.fit(-5, -5, 75, 40, .08)
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (60, 0), (60, 30), (0, 30))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.phase('plant')
    p.tool('tool_subfield')
    p.polygon((2, 2), (28, 2), (28, 28), (2, 28))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.mark('area senza moduli')
    p.trigger('tool_row')
    p.click(4, 5)
    p.click(25, 5)
    p.mark('prima fila a due clic')
    p.click(4, 9)
    p.at(25, 9)
    p.typed('15')
    p.key('enter')
    p.mark('seconda fila, lunghezza digitata 15')
    p.key('esc')
    p.key('esc')
    p.mark('Esc Esc')
    p.undo()
    p.mark('annulla fila')
    p.redo()
    p.mark('ripeti fila')
    p.tool('tool_subfield')
    p.polygon((32, 2), (58, 2), (58, 28), (32, 28))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.trigger('layout_east_west')
    p.click(34, 5)
    p.click(55, 5)
    p.mark('est-ovest a due clic')
    p.key('esc')
    p.key('esc')
    p.mark('Esc Esc')
    p.tool('tool_subfield')
    p.key('esc')
    p.key('esc')
    p.photo('fine')
    centres = p.centres(0)
    if centres:
        p.click(*centres[0])
        p.mark('clic su una fila')
        p.click(*centres[0])
        p.mark('secondo clic: fila')
        p.key('delete')
        p.mark('Canc sulla fila')
        p.undo()
        p.mark('annulla Canc')
    p.key('esc')
    p.key('esc')
    p.phase('model')
    p.key('x')
    p.polygon((5, 3), (10, 3), (10, 7), (5, 7))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.mark('esclusione sopra le file a mano')


@journey
def proposta(p):
    """The automatic proposal itself, through the button in Quick and through the button and then the function in Widgets."""
    import time
    if not p.quick:
        tell = p.host.tell
        p.host.tell = lambda text, *a, **k: (p.say(f'  messaggio: {text}'), tell(text, *a, **k))[1]
    p.fit(-5, -5, 75, 40, .08)
    strings_setup(p)
    p.tool('strings_auto')
    p.spin(800)
    p.button('Stringa')
    start = time.perf_counter()
    while time.perf_counter()-start < 12 and not _strings_summary(p.project)['runs']:
        p.spin(300)
    p.say(f'dopo il pulsante: {_strings_summary(p.project)["runs"]} stringhe in {time.perf_counter()-start:.1f} s')
    if not p.quick and not _strings_summary(p.project)['runs']:
        p.say(f'  posa ferma {p.host._layouts_settled()}, lavoro in corso {p.host.string_proposal_job}')
        p.settle(10)
        p.host._strings_propose('serpentine')
        start = time.perf_counter()
        while time.perf_counter()-start < 20 and not _strings_summary(p.project)['runs']:
            p.spin(300)
        p.say(f'per funzione: {_strings_summary(p.project)["runs"]} stringhe in {time.perf_counter()-start:.1f} s')
    p.mark('proposta')
    p.compute(90)
    p.mark('proposta con il calcolo')
    p.photo('fine')


@journey
def ritardo2(p):
    """The same delay with no strings: several sub-fields, one module deleted, a window of modules, a parameter."""
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (60, 0), (60, 30), (0, 30))
    p.key('enter')
    p.polygon((70, 0), (110, 0), (110, 30), (70, 30))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.phase('plant')
    p.tool('tool_subfield')
    p.double(30, 15)
    p.tool('fill')
    p.key('esc')
    p.tool('tool_subfield')
    p.double(90, 15)
    p.tool('fill')
    p.key('esc')
    p.key('esc')
    wait_layout(p, 'prima posa')
    if p.tool_name() != 'select':
        p.say(f'dopo Esc Esc lo strumento e {p.tool_name()}: Seleziona dal pulsante')
        p.tool('tool_select')
    p.mark('due sottocampi posati')
    for n in range(2):
        centres = p.centres(0)
        p.click(*centres[10+n])
        p.spin(150)
        p.say(f'selezione {p.session.selection} modulo {p.session.selected_module}')
        p.key('delete')
        wait_layout(p, f'Canc su un modulo, volta {n+1}')
        p.mark(f'Canc su un modulo {n+1}')
        p.key('esc')
        p.key('esc')
        p.spin(25000)
    p.drag((5, 3), (15, 8))
    p.key('delete')
    wait_layout(p, 'Canc sulla finestra')
    p.mark('Canc sulla finestra')
    p.key('esc')
    p.key('esc')
    p.undo()
    wait_layout(p, 'annulla finestra')
    p.mark('annulla finestra')

    def change(project):
        project.subfields[0].params.update(tilt=30, azimuth=20, portrait=False)
    p.edit('inclinazione 30, azimut 20, orizzontale', change)
    wait_layout(p, 'parametri')
    p.mark('parametri')


@journey
def esc(p):
    """Esc after each kind of tool button, in both phases: does it reach the plan? Every shortcut used twice is listed."""
    events = []
    if p.quick:
        listed = shortcut_objects(p)
        for o in listed:
            name = str(o.property('sequences') or o.property('sequence'))
            o.activated.connect(lambda n=name: events.append(('attivata', n)))
            o.activatedAmbiguously.connect(lambda n=name: events.append(('ambigua', n)))

        def duplicates(label):
            keys = {}
            for o in listed:
                if o.property('enabled'):
                    seen = o.property('sequences') or [o.property('sequence')]
                    for k in seen:
                        keys.setdefault(str(k), []).append(o.parent().metaObject().className()[:28])
            p.say(f'{label}: doppie {[(k, v) for k, v in keys.items() if len(v) > 1]}')
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (60, 0), (60, 30), (0, 30))
    p.key('enter')
    for phase, tools in (('model', ('tool_building', 'tool_pitch', 'tool_exclusion', 'tool_measure')),
                         ('plant', ('tool_subfield', 'strings_manual', 'tool_erase_string'))):
        p.phase(phase)
        if p.quick:
            duplicates(phase)
        for command in tools:
            p.tool(command)
            before = p.tool_name()
            for n in range(3):
                events.clear()
                p.key('esc')
                p.spin(120)
                p.say(f'{phase} {command}: prima {before}, Esc {n+1}: {p.tool_name()} segnali {events}')
            if p.tool_name() != 'select':
                p.say('  non torna a Seleziona: lo rimetto dal pulsante')
                p.tool('tool_select')
    p.mark('fine')


@journey
def popup(p):
    """Widgets only: why «Stringa» in the little window gives no strings. The window, the button by function, the signal."""
    import time
    tell = p.host.tell
    p.host.tell = lambda text, *a, **k: (p.say(f'  messaggio: {text}'), tell(text, *a, **k))[1]
    p.fit(-5, -5, 75, 40, .08)
    strings_setup(p)
    p.tool('strings_auto')
    p.spin(800)
    popup = p.host.stringing_popup
    p.host_calls = []
    original = p.host._strings_asked
    popup.asked.connect(lambda options: p.say(f'  segnale asked: {options}'))
    p.say(f'finestrella visibile {popup.isVisible()}, geometria {popup.geometry()}, pulsante {popup.go.text()!r} abilitato {popup.go.isEnabled()}')
    q = popup.go.mapToGlobal(popup.go.rect().center())
    p.say(f'centro del pulsante {q}')
    p.hand.click(q.x(), q.y(), popup=True)
    p.spin(500)
    p.say(f'dopo il clic: visibile {popup.isVisible()}, lavoro {p.host.string_proposal_job}')
    start = time.perf_counter()
    while time.perf_counter()-start < 8 and not _strings_summary(p.project)['runs']:
        p.spin(300)
    p.say(f'dopo il clic: {_strings_summary(p.project)["runs"]} stringhe')
    if not _strings_summary(p.project)['runs']:
        p.tool('strings_auto')
        p.spin(800)
        popup.go.click()
        p.spin(500)
        p.say(f'clic per funzione: visibile {popup.isVisible()}, lavoro {p.host.string_proposal_job}')
        start = time.perf_counter()
        while time.perf_counter()-start < 8 and not _strings_summary(p.project)['runs']:
            p.spin(300)
        p.say(f'dopo il clic per funzione: {_strings_summary(p.project)["runs"]} stringhe; {str(p.project.energy.get("strings"))[:200]}')


@journey
def falda5(p):
    """A pitch by corners: tool Pitch, R, five clicks, Enter."""
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (40, 0), (40, 20), (0, 20))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    p.key('p')
    p.key('r')
    p.polygon((3, 3), (37, 3), (37, 12), (20, 16), (3, 12))
    p.key('enter')
    p.mark('falda a 5 vertici')


@journey
def ingressi(p):
    """Three strings by hand, with Esc between them so that no string stays chosen: each must take a free input."""
    p.fit(-5, -5, 75, 40, .08)
    strings_setup(p)
    a = p.centres(0)
    for start in (0, 5, 10):
        p.tool('strings_manual')
        for m in a[start:start+4]:
            p.click(*m)
        p.key('enter')
        p.spin(300)
        p.key('esc')
        p.key('esc')
        p.key('esc')
        p.say(f'scelta dopo Esc: {p.host.plan.chosenString if p.quick else p.host.chosen_string}')
    p.mark('tre stringhe a mano')


def shortcut_objects(p):
    found = {}

    def visit(obj):
        if obj.metaObject().className().startswith('QQuickShortcut'):
            found[id(obj)] = obj
        for child in obj.children():
            visit(child)
    for root in p.host.engine.rootObjects():
        visit(root)
    for item in p.walk():
        visit(item)
    return list(found.values())


@journey
def scorciatoie(p):
    """Why Ctrl+Z may do nothing: every Shortcut of the window with its keys, and which signal a real press fires."""
    p.phase('model')
    p.tool('tool_building')
    p.polygon((0, 0), (40, 0), (40, 20), (0, 20))
    p.key('enter')
    p.key('esc')
    p.key('esc')
    if not p.quick:
        p.undo()
        p.mark('annulla')
        return
    events = []
    listed = shortcut_objects(p)
    for o in listed:
        keys = o.property('sequence') or o.property('nativeText') or o.property('sequences')
        name = str(keys)
        o.activated.connect(lambda n=name: events.append(('attivata', n)))
        o.activatedAmbiguously.connect(lambda n=name: events.append(('ambigua', n)))
    undo_like = [(str(o.property('sequence')), str(o.property('sequences')), o.property('enabled'),
                  o.parent().metaObject().className()[:40], str(o.parent().objectName()))
                 for o in listed if 'Ctrl+Z' in str(o.property('sequence'))+str(o.property('sequences'))+str(o.property('nativeText'))
                 or o.property('sequences') == [30] or 'Annulla' in str(o.property('nativeText'))]
    p.say(f'scorciatoie nella finestra: {len(listed)}; con Ctrl+Z: {undo_like}')
    for phase in ('model', 'plant', 'model'):
        p.phase(phase)
        for n in range(3):
            before = p.session.state_key()
            events.clear()
            p.key('z', 'ctrl')
            p.spin(300)
            changed = p.session.state_key() != before
            p.say(f'{phase}, Ctrl+Z numero {n+1}: stato cambiato {changed}, segnali {events}, '
                  f'edifici {len(p.project.buildings)}, si annulla {p.session.undo.can_undo()}, si ripete {p.session.undo.can_redo()}, '
                  f'chiamate {getattr(p.host.bridge, "calls", {}).get("slot:undo")}')
            if changed:
                p.key('y', 'ctrl')
                p.spin(300)
                p.say(f'   Ctrl+Y: segnali {events[-2:]}, stato tornato {p.session.state_key() == before}')
    p.mark('fine')


def dialog_text(p):
    if not p.quick:
        return getattr(p.host, 'message_boxes', [])[-3:]
    found = [i for i in p.walk() if p.shown(i) and i.property('text') and i.property('hovered') is not None
             and i.mapToGlobal(QPointF(0, 0)).y() > 100]
    return [str(i.property('text')) for i in found][-8:]


class NativeHand:
    """NativeInput of tools/quick_native_input.py behind the calls of the real hand: it takes client coordinates."""
    CODES = {'backspace': 0x08, ',': 0xBC, '.': 0xBE, '-': 0xBD, ';': 0xBC, 'f3': 0x72, 'f8': 0x77}
    inputs = 0

    def __init__(self, native, window):
        self.native, self.window = native, window

    def _client(self, x, y):
        origin = self.window.mapToGlobal(QPoint(0, 0))
        return x-origin.x(), y-origin.y()

    def spin(self, ms):
        self.native.spin(ms)

    def move(self, x, y, steps=10, gap_ms=10):
        self.native.move(*self._client(x, y), steps, gap_ms)

    def click(self, x=None, y=None, button='left', steps=10, settle=120, popup=False):
        if x is not None:
            self.move(x, y, steps)
        self.native.spin(settle)
        self.native.press(button)
        self.native.spin(50)
        self.native.release(button)
        self.native.spin(settle)

    def double_click(self, x, y, popup=False):
        self.native.double_click(*self._client(x, y))

    def drag(self, x0, y0, x1, y1, button='left', steps=14):
        self.native.drag(*self._client(x0, y0), *self._client(x1, y1), button, steps)

    def key(self, name, modifiers=(), settle=120, popup=False):
        self.native.key(self.CODES.get(name, name), tuple(modifiers), settle)

    def type_text(self, text):
        for character in text:
            self.key(character, settle=40)

    def front(self, popup=False):
        return True


def on_hidden(app, host, window, native, engine, journey, out):
    """Inside the program started by tools/quick_native_input.py: see modellazione_nascosto.py."""
    Path(out).mkdir(parents=True, exist_ok=True)
    with (Path(out)/f'{journey}-{engine}.log').open('w', encoding='utf8') as log:
        pilot = Pilot(engine, app, host if engine == 'quick' else host.window, window, NativeHand(native, window), out, journey, log)
        pilot.prepare()
        run(pilot, journey)
    print('fine', journey, engine, len(pilot.records))


def run(pilot, name):
    if name == 'all':
        for function in JOURNEYS.values():
            function(pilot)
    else:
        JOURNEYS[name](pilot)
