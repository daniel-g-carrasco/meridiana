"""The journey of R426, R427 and R432: a sub-field astride a ridge, its corners, Tab, the two phases, copy and paste.

Runs inside the program through tools/quick_native_input.py, on its own desktop, on a synthetic project. It only
records what it sees: the assertions are in test_native_selezione.py.
"""
from meridiana import model


def synthetic(path):
    """A shed with a gable roof, a sub-field astride the ridge, another on the South pitch, a skylight, a tree."""
    p = model.Project(name="Prova due falde")
    p.buildings.append(model.Building(id="b1", name="Capannone", footprint=[[0, 0], [40, 0], [40, 20], [0, 20]],
                                      height=8.0, roof=model.Roof(type="gable", tilt=15.0)))
    b = p.buildings[0]
    south = next(i for i, q in enumerate(b.pitches()) if q.ring[0][1] < 10 and q.ring[2][1] <= 10.01)
    p.subfields.append(model.SubField(id="s1", name="A cavallo", ring=[[8, 6], [22, 6], [22, 13], [8, 13]],
                                      building="b1", pitch=b.pitch_ref(south), filled=True,
                                      params={"mounting": "coplanar"}))
    p.subfields.append(model.SubField(id="s2", name="Sud", ring=[[26, 1], [38, 1], [38, 9], [26, 9]], building="b1",
                                      pitch=b.pitch_ref(south), filled=True, params={"mounting": "coplanar"}))
    p.exclusions.append(model.ExclusionItem(id="e1", ring=[[2, 2], [5, 2], [5, 5], [2, 5]], kind="skylight",
                                            building="b1"))
    p.props.append(model.Prop(id="o1", kind="broadleaf", at=[-8.0, 10.0]))
    p.save(path)


def three_buildings(path):
    """Three sheds of different heights, a sub-field on each of two: R439."""
    p = model.Project(name="Prova tre edifici")
    for i, height in enumerate((8.0, 6.0, 6.0)):
        x = 45 * i
        p.buildings.append(model.Building(id=f"b{i+1}", name=f"Corpo {i+1}", height=height,
                                          footprint=[[x, 0], [x+40, 0], [x+40, 20], [x, 20]]))
    p.subfields.append(model.SubField(id="s1", name="Uno", ring=[[2, 2], [30, 2], [30, 18], [2, 18]], building="b1",
                                      pitch=0, params={"mounting": "tilted_anchored"}))
    p.save(path)


# R439: more buildings chosen in the tree, one change for all.
MANY = r'''
import ctypes
import json
from PySide6.QtCore import QPointF

seen = {}
session = host.bridge.session
controller = host.plan
spin(1.0)
state = (ctypes.c_ubyte*256)()


def held(names, action):
    codes = {'ctrl': (0x11, 0xA2), 'shift': (0x10, 0xA0)}
    user32.GetKeyboardState(state)
    for name in names:
        for code in codes[name]:
            state[code] = 0x80
    user32.SetKeyboardState(state)
    action()
    for name in names:
        for code in codes[name]:
            state[code] = 0
    user32.SetKeyboardState(state)


def row(kind, oid):
    return center(find(win, name=f'tree-row-{kind}-{oid}'))


def lit():
    return sorted({o['oid'] for o in controller.highlights if o.get('kind') == 'building'})


native.click(*row('building', 'b1')); spin(0.3)
seen['one'] = list(session.selection)
held(['ctrl'], lambda: native.click(*row('building', 'b2'))); spin(0.3)
seen['ctrl'] = list(session.many)
seen['lit_two'] = lit()
held(['shift'], lambda: native.click(*row('building', 'b3'))); spin(0.3)
seen['shift'] = list(session.many)
held(['ctrl'], lambda: native.click(*row('building', 'b1'))); spin(0.3)
seen['all'] = sorted(session.many)
seen['lit_all'] = lit()
seen['grips'] = len(controller.grips)
seen['rows_selected'] = sum(1 for oid in ('b1', 'b2', 'b3')
                            if find(win, name=f'tree-row-building-{oid}').property('selected'))
height = find(win, name='editor:height')
seen['height_text'] = height.property('text')
seen['height_placeholder'] = height.property('placeholderText')
grab('molti.png')
box = find(win, name='editor:fire.subject')
for _step in range(30):
    y = center(box)[1]
    if 100 < y < 660:
        break
    native.wheel(*center(height), notches=-2); spin(0.15)
seen['box_state_before'] = box.property('checkState').value
undos = session.undo.count()
native.click(*center(box)); spin(0.4)
seen['subject'] = [b.fire.subject for b in session.project.buildings]
seen['undo_steps'] = session.undo.count()-undos
seen['box_state_after'] = box.property('checkState').value
grab('molti-soggetta.png')
session.undo.undo(); spin(0.3)
seen['undone'] = [b.fire.subject for b in session.project.buildings]
session.undo.redo(); spin(0.3)
held(['ctrl'], lambda: native.click(*row('subfield', 's1'))); spin(0.3)
seen['other_kind'] = [list(session.selection), list(session.many)]
native.click(*row('building', 'b2')); spin(0.3)
seen['plain'] = [list(session.selection), list(session.many)]
seen['warnings'] = host.warnings[-5:]
print(json.dumps(seen, ensure_ascii=False))
'''

# What every run does: the corners at three zooms.
HEAD = r'''
import json
from pathlib import Path
import tempfile
from PySide6.QtCore import QPointF, Qt

from meridiana import model

seen = {}
plan = find(win, name='plan')
session = host.bridge.session
controller = host.plan


def at(x, y):
    z, px, py = plan.property('zoom'), plan.property('panX'), plan.property('panY')
    p = plan.mapToScene(QPointF(px+z*x, py-z*y))
    return p.x(), p.y()


def off(point, dx, dy):
    return point[0]+dx, point[1]+dy


def sf(oid):
    return session.subfield(oid)


def module_of(oid):
    return next(m for m in session.results[oid].modules if m.key not in sf(oid).removed)


def laid(oid):
    return oid in session.results and not isinstance(session.results[oid], Exception) and bool(session.results[oid].modules)


def settle():
    wait_until(lambda: not controller.busy, 30)
    spin(0.25)


def hint():
    return plan.property('statusText')


wait_until(lambda: controller is not None and laid('s1') and laid('s2'), 60)
spin(0.5)
native.key('2', ('ctrl',)); spin(0.8)
seen['phase'] = win.property('phase')
# The same view whatever the panels leave: 12 pixels a metre, the shed in the middle.
plan.setProperty('fitted', False)
plan.setProperty('zoom', 12.0)
plan.setProperty('panX', plan.width()/2-20*12.0)
plan.setProperty('panY', plan.height()/2+10*12.0)
spin(0.3)
seen['dpr'] = win.devicePixelRatio()

# The corners: the same gesture at the view's zoom, closer, and further away.
corner = (26.0, 1.0)
native.click(*at(*module_of('s2').centre)); spin(0.2)
seen['corner_select'] = list(session.selection)
seen['corners_with_a_module'] = len(controller.grips)
native.key('esc'); spin(0.2)
results = []
for notches in (0, 3, -6):
    if notches:
        native.wheel(*at(32.0, 5.0), notches=notches); spin(0.3)
    before = [list(q) for q in sf('s2').ring]
    start = off(at(*corner), 10, -6)            # 11,7 pixels from the corner, over the modules
    native.move(*start); spin(0.1)
    native.press(); native.move(*off(start, 18, -14), steps=8); native.release(); spin(0.2)
    settle()
    results.append(dict(zoom=plan.property('zoom'), moved=sf('s2').ring[0] != before[0],
                        others_still=sf('s2').ring[1:] == before[1:], selection=list(session.selection),
                        swept=len(controller.editor.swept)))
    session.undo.undo() if sf('s2').ring[0] != before[0] else None
    settle()
seen['corners'] = results
native.wheel(*at(32.0, 5.0), notches=3); spin(0.3)
seen['corner_click_changes_nothing'] = None
before = [list(q) for q in sf('s2').ring]
undos = session.undo.count()
native.click(*off(at(*corner), 6, -3)); spin(0.2)
seen['corner_click_changes_nothing'] = sf('s2').ring == before and session.undo.count() == undos
seen['warnings_head'] = host.warnings[-5:]
'''

# The rest, at scale 1.
JOURNEY = HEAD + r'''
# Hover, where the pointer reaches the plan (r14-correzioni).
button = find(win, name='tool_tool_move')
native.move(*center(button)); spin(0.2)
seen['hover_works'] = bool(button.property('hovered'))
grip = find(win, name='vertexGrip0')
overlay = find(win, name='selectionOverlay')
seen['grip_width_away'] = grip.width()
native.move(*off(at(*corner), 10, -6), steps=8); spin(0.25)
seen['grip_width_near'] = grip.width()
seen['hover_on_corner'] = overlay.property('hovered') is not None
seen['corner_area_cursor'] = find(win, name='vertexMouse').property('cursorShape') == Qt.SizeAllCursor
seen['corner_hint'] = hint()
grab('corner.png')
native.move(*at(32.0, 5.0), steps=8); spin(0.25)
seen['grip_width_back'] = grip.width()
seen['hover_on_module'] = overlay.property('hovered') is not None
native.key('esc'); spin(0.1); native.key('esc'); spin(0.2)

# R426: the sub-field astride the ridge moves, passes to the other pitch, says it.
native.click(*at(*module_of('s1').centre)); spin(0.2)
native.key('esc'); spin(0.2)
seen['astride_selected'] = list(session.selection)
pitch_before = sf('s1').pitch
ring_before = [list(q) for q in sf('s1').ring]
native.click(*center(find(win, name='tool_tool_move'))); spin(0.2)
seen['move_tool'] = controller.tool
native.click(*at(10.0, 8.0)); spin(0.15)
native.click(*at(10.0, 10.5)); spin(0.3); settle()
seen['moved_by'] = sf('s1').ring[0][1]-ring_before[0][1]
seen['pitch_changed'] = sf('s1').pitch != pitch_before
seen['move_error'] = controller.error
seen['move_hint'] = hint()
grab('astride.png')
native.key('esc'); spin(0.2)
if controller.tool != 'select':
    controller.setTool('select'); spin(0.1)

# «Split on the ridge», from the right button; one undo; redo; together; saved and opened.
ring_astride = [list(q) for q in sf('s1').ring]
native.click(*at(ring_astride[0][0]+2, ring_astride[0][1]+2), button='right'); spin(0.4)
entry = find(win, name='planContext-split_pitches')
row = next((r for r in controller.contextItems if r['command'] == 'split_pitches'), None)
if row is not None and row.get('menu'):          # R533: on a module, the sub-field's commands are in its submenu
    head = find(win, text=row['menu'])
    if head is not None:
        native.move(*center(head)); spin(0.8)
    entry = find(win, name='planContext-split_pitches')
seen['split_in_menu'] = entry is not None
if entry is not None:
    ex, ey = center(entry)
    native.move(ex, native.at[1]); spin(0.2)   # across into the submenu, not over the other heads
    native.click(ex, ey); spin(0.3)
else:
    native.key('esc'); spin(0.2)
    controller.contextCommand('split_pitches')
settle()
seen['after_split'] = len(session.project.subfields)
seen['split_groups'] = sorted({s.group for s in session.project.subfields if s.id != 's2'})
seen['split_pitches'] = sorted({str(s.pitch) for s in session.project.subfields if s.id != 's2'})
session.undo.undo(); spin(0.2); settle()
seen['after_split_undo'] = len(session.project.subfields)
session.undo.redo(); spin(0.2); settle()
seen['after_split_redo'] = len(session.project.subfields)
grab('split.png')
parts = [s.id for s in session.project.subfields if s.id != 's2']
rings = {i: [list(q) for q in sf(i).ring] for i in parts}
native.click(*center(find(win, name='tool_tool_move'))); spin(0.2)
native.click(*at(19.0, 12.0)); spin(0.15)
native.click(*at(17.0, 12.0)); spin(0.3); settle()
seen['parts_moved'] = [round(sf(i).ring[0][0]-rings[i][0][0], 3) for i in parts]
native.key('esc'); spin(0.2)
if controller.tool != 'select':
    controller.setTool('select'); spin(0.1)
with tempfile.TemporaryDirectory() as folder:
    path = Path(folder)/'split.meridiana'
    session.project.save(path)
    again = model.Project.load(path)[0]
    seen['reopened_groups'] = [s.group for s in again.subfields] == [s.group for s in session.project.subfields]
    seen['reopened_rings'] = [s.ring for s in again.subfields] == [s.ring for s in session.project.subfields]

# The two phases.
native.key('esc'); spin(0.1); native.key('esc'); spin(0.2)
native.move(*at(4.0, 18.0)); spin(0.25)
seen['plant_hover_roof'] = overlay.property('hovered') is not None
native.click(*at(4.0, 18.0)); spin(0.2)             # a bare roof, in Plant
seen['plant_click_roof'] = list(session.selection)
seen['plant_click_roof_hint'] = hint()
native.click(*at(3.5, 3.5)); spin(0.2)              # the skylight, in Plant
seen['plant_click_exclusion'] = list(session.selection)
native.key('1', ('ctrl',)); spin(0.8)
seen['phase_model'] = win.property('phase')
native.move(*at(*module_of('s2').centre)); spin(0.25)
lit = overlay.property('hovered')
seen['model_hover_module'] = lit.toVariant()['record']['kind'] if hasattr(lit, 'toVariant') and lit.toVariant() else (lit['record']['kind'] if lit else None)
native.click(*at(*module_of('s2').centre)); spin(0.2)
seen['model_click_module'] = list(session.selection)
seen['model_module_key'] = list(session.selected_module)
native.click(*at(3.5, 3.5)); spin(0.2)              # anchored: the skylight lies inside the building selected
seen['anchored'] = list(session.selection)
native.move(*at(3.7, 3.7)); spin(0.25)
seen['anchored_hover'] = overlay.property('hovered') is not None
native.move(*at(3.5, 3.5)); spin(0.2)
walk = []
for _step in range(3):
    native.key('tab'); spin(0.2)
    walk.append(list(session.selection))
seen['tab_walk'] = walk
seen['tab_hint'] = hint()
native.key('tab', ('shift',)); spin(0.2)
seen['shift_tab'] = list(session.selection)
native.key('esc'); spin(0.1); native.key('esc'); spin(0.2)
seen['esc_lets_go'] = list(session.selection)
native.click(*at(3.5, 3.5)); spin(0.2)
seen['after_esc_click'] = list(session.selection)
native.key('s'); spin(0.5)
seen['s_in_modelling'] = [win.property('phase'), controller.tool]
native.key('esc'); spin(0.2)
if win.property('phase') != 'model':
    native.key('1', ('ctrl',)); spin(0.8)
if controller.tool != 'select':
    controller.setTool('select'); spin(0.1)
if session.selection != ('exclusion', 'e1'):
    native.click(*at(3.5, 3.5)); spin(0.2)

# R432: copy and paste in Modelling, then a sub-field in Plant.
native.key('c', ('ctrl',)); spin(0.2)
native.move(*at(14.0, 17.0)); spin(0.1)
native.key('v', ('ctrl',)); spin(0.2)
seen['paste_tool_model'] = controller.tool
native.click(*at(14.0, 17.0)); spin(0.3)
seen['exclusions_after_paste'] = len(session.project.exclusions)
native.key('2', ('ctrl',)); spin(0.8)
native.click(*at(*module_of('s2').centre)); spin(0.2)
native.key('esc'); spin(0.2)
native.key('c', ('ctrl',)); spin(0.2)
seen['copied'] = controller.editor.clip.kind if controller.editor.clip else None
native.move(*at(32.0, 15.0)); spin(0.1)
native.key('v', ('ctrl',)); spin(0.3)
native.move(*at(32.0, 15.2), steps=3); spin(0.2)
seen['paste_tool'] = controller.tool
seen['paste_rings'] = len(controller.preview.get('rings', []))
seen['paste_hint'] = hint()
seen['paste_preview_drawn'] = len(controller.draftObjects)
grab('paste.png')
native.move(*at(32.0, 18.5), steps=4); spin(0.2)
seen['paste_refused'] = controller.preview.get('refused', '')
count = len(session.project.subfields)
native.click(*at(32.0, 18.5)); spin(0.3)
seen['paste_refused_count'] = len(session.project.subfields)-count
seen['paste_refused_said'] = hint()
grab('paste-refused.png')
undos = session.undo.count()
native.click(*at(32.0, 15.0)); spin(0.3); settle()
new = session.project.subfields[-1]
seen['pasted'] = len(session.project.subfields)-count
wait_until(lambda: laid(new.id), 30)
seen['pasted_on_north'] = session.project.surface_of(new).azimuth != session.project.surface_of(sf('s2')).azimuth
seen['pasted_undo_steps'] = session.undo.count()-undos
seen['pasted_hint'] = hint()
seen['pasted_modules'] = len(session.results[new.id].modules) if new.id in session.results else None
seen['pasted_keeps_module'] = new.module == sf('s2').module
strings = (session.project.energy.get('strings') or {}).get('runs') or []
seen['pasted_in_a_string'] = any(m.startswith(new.id+'/') for r in strings for m in r.get('modules', []))
# Cut and paste, one undo.
state = session.snapshot()
undos = session.undo.count()
oid = new.id
native.key('x', ('ctrl',)); spin(0.3); settle()
seen['cut_gone'] = session.subfield(oid) is None
native.move(*at(32.0, 4.0)); spin(0.1)
native.key('v', ('ctrl',)); spin(0.2)
native.click(*at(32.0, 15.0)); spin(0.3); settle()
seen['cut_pasted'] = len(session.project.subfields)-count
seen['cut_paste_undo_steps'] = session.undo.count()-undos
session.undo.undo(); spin(0.2); settle()
seen['cut_paste_undone'] = session.snapshot() == state
seen['warnings'] = host.warnings[-5:]
print(json.dumps(seen, ensure_ascii=False))
'''

# At scale 2 only the corners: what is asked is a reach in logical pixels.
SCALED = HEAD + r'''
seen['warnings'] = host.warnings[-5:]
print(json.dumps(seen, ensure_ascii=False))
'''
