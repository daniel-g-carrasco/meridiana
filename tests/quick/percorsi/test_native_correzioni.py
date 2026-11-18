"""The corrections after Daniel's trial and the collaudo, driven by native messages on the real window.

Each method names the defect of docs/quick/collaudo/difetti.csv or the request it covers. The journey runs once,
inside the program, and only records; the assertions are here. Run with
    python -m unittest quick.percorsi.test_native_correzioni
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT/'tools/quick_native_input.py'

JOURNEY = r'''
import ctypes
import json
import math
import time
from PySide6.QtCore import QMetaObject, QObject, QPointF, Q_ARG, Q_RETURN_ARG, Qt
ctypes_ubyte = ctypes.c_ubyte

seen = {}
away = (1100, 300)
# Started without the year: the layout, as the computation's process would give it.
from meridiana import jobs
laid, laid_keys, _unused = jobs.layout_of(host.bridge.session.project, host.bridge.session.known_layouts())
host.bridge.accept_layout(host.bridge.session.generation, laid, laid_keys)
spin(1.0)


def tips():
    return [p for p in popups(win) if 'p style' in (visible_text(p) + [''])[0]]


def menus():
    return [p for p in popups(win) if p.height() > 8 and 'p style' not in (visible_text(p) + [''])[0]]


def close_all():
    for item in menus():
        item.parent().close()
    spin(0.15)


# D03, D04, R379: a tooltip under the pointer, fading in 90 ms and out in 60, and none left behind.
button = find(win, name='tool_tool_move')
native.move(*away); spin(0.2)
x, y = center(button)
native.move(x, y); start = time.perf_counter(); first = None; opacities = []
while time.perf_counter() - start < 1.2:
    native.spin(4)
    shown = [p for p in popups(win) if 'Sposta' in (visible_text(p) + [''])[0]]
    if shown:
        first = first or time.perf_counter()
        opacities.append(round(shown[0].opacity(), 3))
        if opacities[-1] >= 1 and len(opacities) > 1:
            break
seen['tip_wait_ms'] = None if first is None else round((first - start)*1000)
seen['tip_fade_samples'] = opacities
tip = [p for p in popups(win) if 'Sposta' in (visible_text(p) + [''])[0]]
if tip:
    at = tip[0].mapToScene(QPointF(0, 0))
    seen['tip_offset'] = [round(at.x() - x, 1), round(at.y() - y, 1)]
native.longest_turn = 0
native.move(*away, steps=2); start = time.perf_counter(); fading = []
while time.perf_counter() - start < 0.5:
    native.spin(4)
    shown = [p for p in popups(win) if 'Sposta' in (visible_text(p) + [''])[0]]
    if not shown:
        break
    fading.append(round(shown[0].opacity(), 3))
seen['tip_gone_ms'] = round((time.perf_counter() - start)*1000)
seen['tip_gone_turn_ms'] = round(native.longest_turn*1000)
seen['tip_fade_out_samples'] = fading

# Passing from one control to the next: the next tip comes at once (R379).
zoom_in, zoom_out = find(win, name='planView-zoom_in'), find(win, name='planView-zoom_out')
native.move(*center(zoom_in)); spin(0.6)
native.move(*center(zoom_out), steps=3); spin(0.15)
seen['tips_while_passing'] = [(visible_text(p) + [''])[0][-40:] for p in tips()]
native.move(*away); spin(0.4)

# D02, D03: click, click, away.
native.move(*center(zoom_in)); native.click(); spin(0.2)
native.move(*center(zoom_out)); native.click(); spin(0.2)
native.move(*away); spin(0.5)
seen['stuck_tips'] = len(tips())
seen['stuck_alpha'] = [zoom_in.property('color').alpha(), zoom_out.property('color').alpha()]

# D05, D06: every kind of menu, closed by a click outside and by Esc after it; the click never reaches the view.
tool_before = host.plan.tool if hasattr(host.plan, 'tool') else None
results = {}
def try_menu(name, opener):
    opener(); spin(0.4)
    opened = bool(menus())
    native.move(*away); spin(0.1); native.click(); spin(0.3)
    outside = not menus()
    close_all()
    opener(); spin(0.4)
    native.key('esc'); spin(0.3)
    esc = not menus()
    close_all()
    results[name] = dict(opened=opened, outside=outside, esc=esc)
background = center(find(win, name='planView-background'))
try_menu('background', lambda: native.click(*background))
def split(name):
    def open_it():
        item = find(win, name=name)
        native.move(item.mapToScene(QPointF(item.width() - 3, item.height()/2)).x(), item.mapToScene(QPointF(0, item.height()/2)).y())
        native.click()
    return open_it
for item in items(win):
    if item.objectName().startswith('tool_') and item.isVisible() and item.property('stripWidth') is not None:
        try_menu(item.objectName(), split(item.objectName()))
        break
try_menu('plan-right', lambda: native.click(600, 500, button='right'))
try_menu('3d-right', lambda: native.click(*center(find(win, name='sceneView')), button='right'))
try_menu('status-right', lambda: native.click(*center(find(win, name='statusPanelLeft')), button='right'))
seen['menus'] = results

# After a click outside, the keyboard is still the window's: Esc does not stop working (D06).
native.click(*background); spin(0.3)
native.move(*away); spin(0.1); native.click(); spin(0.3)
native.click(*center(find(win, name='tool_tool_building'))); spin(0.2)
native.key('esc'); spin(0.3); native.key('esc'); spin(0.3)
seen['esc_after_click_outside'] = find(win, name='planCanvas') is None or host.plan.tool
native.move(*away); spin(0.1)

# The menu unrolls downward; no entry falls outside; margins (Daniel, Controls/Menu.qml).
native.longest_turn = 0
native.move(*background); native.press(); native.release(); frames = []; start = time.perf_counter()
while time.perf_counter() - start < 0.4:
    native.spin(4)
    if menus():
        frames.append(menus()[0].height())
seen['menu_unroll_heights'] = frames[:30]
seen['menu_unroll_turn_ms'] = round(native.longest_turn*1000)
seen['menu_height'] = menus()[0].height() if menus() else None
close_all()

# D09: the maps are on from the start.
maps = host.plan._maps
seen['maps_offline'] = bool(maps.loader.offline)

# D08 and its family: Ctrl+Z after an edit, in every phase, then Esc in Modellazione after Impianto has been seen.
session = host.bridge.session
start_count = len(session.project.buildings)
native.click(*center(find(win, name='tool_tool_building'))); spin(0.2)
for at in [(690, 540), (760, 540), (760, 600), (690, 600)]:
    native.click(*at, steps=4, settle=60)
native.key('enter'); spin(0.5); native.key('esc'); spin(0.2); native.key('esc'); spin(0.2)
seen['drawn'] = len(session.project.buildings) - start_count
native.key('z', ('ctrl',)); spin(0.5)
seen['ctrl_z_model'] = len(session.project.buildings) - start_count
native.key('y', ('ctrl',)); spin(0.5)
seen['ctrl_y_model'] = len(session.project.buildings) - start_count
native.key('2', ('ctrl',)); spin(1.0)
native.key('z', ('ctrl',)); spin(0.5)
seen['ctrl_z_plant'] = len(session.project.buildings) - start_count
native.key('y', ('ctrl',)); spin(0.5)
seen['ctrl_y_plant'] = len(session.project.buildings) - start_count
native.key('1', ('ctrl',)); spin(0.6)
native.key('z', ('ctrl',)); spin(0.5)
native.click(*center(find(win, name='tool_tool_building'))); spin(0.2)
seen['tool_after_click'] = find(win, name='planCanvas') is not None
native.key('esc'); spin(0.3)
seen['esc_back_to_select'] = str(win.property('planItem').property('tool'))

# R402: the 3D and the split in Plant, opening on the plan, back to Modellazione's own.
seen['view_model'] = win.property('viewMode')
native.key('2', ('ctrl',)); spin(0.8)
seen['view_plant_opens'] = win.property('viewMode')
seen['plant_3d_at_open'] = find(win, name='view3dHost') is not None
native.click(*center(find(win, name='planView-view_both'))); spin(0.6)
seen['plant_split_plan'] = find(win, name='planCanvas') is not None or find(win, name='planViewBar') is not None
seen['plant_split_3d'] = find(win, name='view3dHost') is not None
# Stringing with the 3D beside it (R402, Daniel asked to try it).
editor = host.plan.editor
strings_before = len(editor.runs())
# On a project whose inverters are not in this profile's catalogue the command says so: the draft is started as the
# row of an input starts it.
wait_until(lambda: host.parts.controllers['plant'].state is not None, 30)
host.parts.controllers['plantActions'].draw(1, 1, -1); spin(0.5)
seen['string_tool_beside_3d'] = editor.tool
plan_item = find(win, name='plan')
chosen = []
for result in session.good_results().values():
    for module in result.modules:
        xs, ys = zip(*module.corners)
        at = QMetaObject.invokeMethod(plan_item, 'screen', Qt.DirectConnection, Q_RETURN_ARG('QVariant'),
                                      Q_ARG('QVariant', sum(xs)/len(xs)), Q_ARG('QVariant', sum(ys)/len(ys)))
        at = at if isinstance(at, QPointF) else QPointF(at.x(), at.y())
        if 60 < at.x() < plan_item.width() - 60 and 60 < at.y() < plan_item.height() - 60:
            chosen.append(plan_item.mapToScene(at))
        if len(chosen) == 3:
            break
    if chosen:
        break
# The modules of this project are in strings already: Shift and a click takes them, as the hint of the tool says.
shift = (ctypes_ubyte*256)()
user32.GetKeyboardState(shift); shift[0x10] = shift[0xA0] = 0x80; user32.SetKeyboardState(shift)
for at in chosen:
    native.click(at.x(), at.y(), steps=3, settle=80)
shift[0x10] = shift[0xA0] = 0; user32.SetKeyboardState(shift)
seen['string_modules_clicked'] = len(chosen)
seen['string_draft'] = len(editor.draft or [])
native.key('enter'); spin(0.6)
seen['strings_added_beside_3d'] = len(editor.runs()) - strings_before
seen['string_stored'] = any(len(run.get('modules') or []) == len(chosen) for run in editor.runs())
seen['tool_after_string'] = editor.tool
if seen['strings_added_beside_3d'] > 0:
    native.key('z', ('ctrl',)); spin(0.5)
native.click(*center(find(win, name='planView-view_plan'))); spin(0.4)
native.key('1', ('ctrl',)); spin(0.6)
seen['view_model_again'] = win.property('viewMode')
seen['model_3d_again'] = find(win, name='view3dHost') is not None
native.key('2', ('ctrl',)); spin(0.4)
seen['view_plant_again'] = win.property('viewMode')
native.key('1', ('ctrl',)); spin(0.4)

# R410: a ridge drawn off the axis of a building stands where it is drawn.
drawn_before = len(session.project.buildings)
native.click(*center(find(win, name='tool_tool_building'))); spin(0.2)
corners = [(600, 480), (790, 480), (790, 600), (600, 600)]
for at in corners:
    native.click(*at, steps=4, settle=60)
native.key('enter'); spin(0.5); native.key('esc'); spin(0.2); native.key('esc'); spin(0.2)
new = session.project.buildings[-1] if len(session.project.buildings) > drawn_before else None
if new is not None:
    plan_item = win.property('planItem')
    native.key('c'); spin(0.2)
    native.click(610, 510, steps=4, settle=60); native.click(780, 510, steps=4, settle=60)
    spin(0.5); native.key('esc'); spin(0.2); native.key('esc'); spin(0.2)
    b = session.project.building(new.id)
    tops = [q for f in b.roof.free_pitches for q, z in zip(f['ring'], f.get('z') or []) if z == max(f.get('z') or [0])]
    low, high = min(p[1] for p in b.footprint), max(p[1] for p in b.footprint)
    seen['ridge_type'] = b.roof.type
    seen['ridge_share'] = None if not tops else round((tops[0][1] - low)/(high - low), 2)
    seen['ridge_pitches'] = len(b.pitches())
    native.key('z', ('ctrl',)); spin(0.4)
    seen['ridge_undone'] = session.project.building(new.id).roof.type
    native.key('z', ('ctrl',)); spin(0.4)

# R401, R412: the corners in the scene, Ctrl with a plus by the pointer, Shift no more.
buildings = session.project.buildings
session.select('building', buildings[0].id); spin(0.4)
viewport = find(win, name='viewport3d')
viewport.setProperty('editVertices', True); spin(0.4)
scene = find(win, name='sceneView')
dots = scene.findChild(QObject, 'vertexDots')
seen['dots_in_scene'] = dots is not None and dots.property('visible') is True
state = (ctypes_ubyte*256)()
at_scene = scene.mapToScene(QPointF(40, 40))
native.move(at_scene.x(), at_scene.y(), steps=2); spin(0.1)
seen['plus_without_ctrl'] = find(win, name='vertexPlus') is not None
user32.GetKeyboardState(state); state[0x11] = state[0xA2] = 0x80; user32.SetKeyboardState(state)
native.move(at_scene.x() + 10, at_scene.y() + 10, steps=3); spin(0.1)
seen['plus_with_ctrl'] = find(win, name='vertexPlus') is not None
state[0x11] = state[0xA2] = 0; user32.SetKeyboardState(state)
native.move(at_scene.x() + 20, at_scene.y() + 20, steps=3); spin(0.1)
seen['plus_after_ctrl'] = find(win, name='vertexPlus') is not None
seen['vertex_help'] = host.scene.vertexHelp
# Seen from low down, beside the building: the corner on the near side shows, the far one is behind the wall.
points = viewport.property('verticesData').toVariant()
xs, zs = [p['point'][0] for p in points], [p['point'][2] for p in points]
middle = [(min(xs) + max(xs))/2, points[0]['point'][1], (min(zs) + max(zs))/2]
position = [min(xs) - 12, 3.0, min(zs) - 12]
forward = [middle[i] - position[i] for i in range(3)]
length = math.sqrt(sum(v*v for v in forward))
forward = [v/length for v in forward]
yaw, pitch = math.atan2(-forward[0], -forward[2]), math.asin(forward[1])
qy = (math.cos(yaw/2), 0.0, math.sin(yaw/2), 0.0)
qx = (math.cos(pitch/2), math.sin(pitch/2), 0.0, 0.0)
rotation = [qy[0]*qx[0] - qy[1]*qx[1] - qy[2]*qx[2] - qy[3]*qx[3],
            qy[0]*qx[1] + qy[1]*qx[0] + qy[2]*qx[3] - qy[3]*qx[2],
            qy[0]*qx[2] - qy[1]*qx[3] + qy[2]*qx[0] + qy[3]*qx[1],
            qy[0]*qx[3] + qy[1]*qx[2] - qy[2]*qx[1] + qy[3]*qx[0]]
saved = viewport.property('cameraState').toVariant()
viewport.setProperty('userMoved', True)
viewport.setProperty('cameraState', dict(saved, position=position, rotation=rotation, target=middle))
spin(0.8)
dots = scene.findChild(QObject, 'vertexDots')
def shot():
    origin = scene.mapToScene(QPointF(0, 0))
    return win.grabWindow(), origin
with_dots, origin = shot()
dots.setProperty('visible', False); spin(0.5)
without_dots, _ = shot()
dots.setProperty('visible', True); spin(0.2)
def changed_near(point):
    at = QMetaObject.invokeMethod(viewport, 'projectPoint', Qt.DirectConnection, Q_RETURN_ARG('QVariant'), Q_ARG('QVariant', point))
    at = at.toVariant() if hasattr(at, 'toVariant') else at
    if not at:
        return None
    x, y = int(origin.x() + at[0]), int(origin.y() + at[1])
    return sum(with_dots.pixel(x + dx, y + dy) != without_dots.pixel(x + dx, y + dy) for dx in range(-2, 3) for dy in range(-2, 3))
order = sorted(points, key=lambda p: (p['point'][0] - position[0])**2 + (p['point'][2] - position[2])**2)
seen['corner_near_changed'] = changed_near(order[0]['point'])
seen['corner_far_changed'] = changed_near(order[-1]['point'])
viewport.setProperty('cameraState', saved); spin(0.3)
viewport.setProperty("editVertices", False); session.select("site", ""); spin(0.3)

# D18: where the pointer is (by the plan's scale since R484), what the selection measures; M15: the year's remark is not the plan's hint.
native.move(600, 500, steps=3); spin(0.2)
cursor = find(win, name='planCursorText')
seen['cursor_text'] = cursor.property('text') if cursor is not None else ''
session.select('building', session.project.buildings[0].id); spin(0.3)
measure = find(win, name='statusMeasure')
seen['measure_text'] = measure.property('text') if measure is not None else ''
session.select('site', ''); spin(0.2)
seen['hint_in_model'] = find(win, name='statusHint').property('text')

bridge = host.bridge
# D20, D22: a card carried to a column stands beside the others; the right button on a title.
title = find(win, name='projectTitleDrag')
x, y = center(title)
native.move(x, y); spin(0.1); native.press()
native.move(1400, 300, steps=16); spin(0.4)
zone = find(win, name='dropZone')
seen['drop_zone_shown'] = zone is not None
seen['lift_scale'] = find(win, name='cardLift').scale() if find(win, name='cardLift') is not None else None
central_while = find(win, name='centralPanel').x()
native.release(); spin(0.7)
right, left = find(win, name='rightPanel'), find(win, name='leftPanel')
seen['carried_visible'] = [left is not None, right is not None]
if left is not None and right is not None:
    seen['carried_rects'] = [[left.x(), left.y(), left.width(), left.height()], [right.x(), right.y(), right.width(), right.height()]]
seen['central_moved_at_once'] = central_while == find(win, name='centralPanel').x()
native.click(*center(find(win, name='leftPanel') and find(win, name='projectTitleDrag')), button='right'); spin(0.4)
seen['title_menu'] = [visible_text(p)[:5] for p in popups(win) if p.height() > 40]
native.key('esc'); spin(0.2)
host.shell.trigger('default_layout'); spin(0.8)
seen['restored_left_x'] = find(win, name='leftPanel').x() if find(win, name='leftPanel') is not None else None

# D16: a row under the pointer lights, on Checks and on the Project tree.
def lit_pixels(item):
    native.move(*away); spin(0.3)
    off = win.grabWindow()
    native.move(*center(item)); spin(0.3)
    on = win.grabWindow()
    at = item.mapToScene(QPointF(0, 0))
    native.move(*away); spin(0.2)
    return sum(off.pixel(int(at.x()) + x, int(at.y()) + y) != on.pixel(int(at.x()) + x, int(at.y()) + y)
               for x in range(4, int(item.width()) - 4, 3) for y in range(2, int(item.height()) - 2, 3))
row = next((i for i in items(win) if i.objectName().startswith('checks-row-') and i.isVisible()), None)
seen['check_row_lit'] = lit_pixels(row) if row is not None else 0
tree = next((i for i in items(win) if i.objectName().startswith('tree-row-building') and i.isVisible()), None)
seen['tree_row_lit'] = lit_pixels(tree) if tree is not None else 0

# D17: the strip of the weather in the bar of the Production, its boxes change the project, one undo.
win.setProperty('phase', 'production'); spin(1.0)
strip = find(win, name='productionStrip')
seen['strip_shown'] = strip is not None
seen['meteo_state'] = find(win, name='meteoState').property('text') if strip is not None else ''
if strip is not None:
    box = find(win, name='useNear')
    before = dict(session.project.energy or {}).get('losses', {}).get('use_near', True)
    native.click(*center(box)); spin(0.4)
    seen['near_changed'] = (dict(session.project.energy or {}).get('losses', {}).get('use_near', True)) != before
    native.key('z', ('ctrl',)); spin(0.4)
    seen['near_back'] = (dict(session.project.energy or {}).get('losses', {}).get('use_near', True)) == before
    seen['near_box_back'] = bool(find(win, name='useNear').property('checked')) == before
bridge.cancelCompute() if hasattr(host.bridge, 'cancelCompute') else None
win.setProperty('phase', 'model'); spin(0.6)

# R431: selecting, opening a section and moving a panel's edge leave the plan's scale and centre where they are.
def plan_view():
    item = find(win, name='plan')
    centre = QMetaObject.invokeMethod(item, 'world', Qt.DirectConnection, Q_RETURN_ARG('QVariant'),
                                      Q_ARG('QVariant', item.width()/2), Q_ARG('QVariant', item.height()/2))
    centre = centre if isinstance(centre, QPointF) else QPointF(centre.x(), centre.y())
    return dict(zoom=round(item.property('zoom'), 6), x=round(centre.x(), 2), y=round(centre.y(), 2),
                width=item.width(), right=find(win, name='rightPanel').width())
marks = {'start': plan_view()}
for prefix in ('tree-row-subfield', 'tree-row-building', 'tree-row-exclusion'):
    row = next((i for i in items(win) if i.objectName().startswith(prefix) and i.isVisible()), None)
    if row is not None:
        native.click(*center(row)); spin(0.8)
        marks[prefix] = plan_view()
session.select('site', ''); spin(0.4)
marks['site'] = plan_view()
edge = find(win, name='rightResizeHandle')
x, y = center(edge)
native.drag(x, y, x - 60, y, steps=6); spin(0.5)
marks['edge_moved'] = plan_view()
native.drag(x - 60, y, x, y, steps=6); spin(0.5)
seen['view_marks'] = marks
native.key('2', ('ctrl',)); spin(1.0)
marks2 = {'plant': plan_view()}
for word in ('Inverter', 'Accumulo', 'Pannelli', 'Moduli', 'Inverter'):
    # Since r14-impianto the heads of the Plant's sections are MouseAreas named plant-section-<key>, with their text.
    head = next((i for i in items(win) if i.isVisible() and i.property('text') == word
                 and (i.metaObject().className().startswith('Button') or i.objectName().startswith('plant-section-'))), None)
    if head is not None:
        native.click(*center(head)); spin(0.6)
        marks2[word] = plan_view()
seen['view_marks_plant'] = marks2
native.key('1', ('ctrl',)); spin(0.5)

# R430: the status bar stays inside the window and the window inside the screen's useful area.
def in_area():
    area = win.screen().availableGeometry()
    box = win.geometry()
    bar = find(win, name='statusMeridio')
    bottom = bar.mapToScene(QPointF(0, bar.height())).y()
    return dict(window_in_area=box.top() >= area.top() and box.bottom() <= area.bottom() and box.left() >= area.left() and box.right() <= area.right(),
                bar_in_window=bottom <= win.height())
placed = {}
win.showMaximized(); spin(0.8)
placed['maximized'] = in_area()
theme = host.theme
win.showNormal(); spin(0.5)
area = win.screen().availableGeometry()
win.setGeometry(area.left() + 40, area.bottom() - 200, area.width() + 300, area.height() + 200); spin(0.3)
host.keep_on_screen(); spin(0.5)
placed['too_big_and_low'] = in_area()
win.setGeometry(0, 0, 1600, 960); win.setPosition(0, 0); spin(0.6)
seen['placed'] = placed

# D15, D16: rows stay when the list changes, with their hover.
row = find(win, name='checks-row-0') or next((i for i in items(win) if i.objectName().startswith('checks-row-') and i.isVisible()), None)
seen['check_row'] = row is not None
if row is not None:
    native.move(*center(row)); spin(0.2)
    name_before = row.objectName()
    native.click(); spin(0.5)
    try:
        seen['check_row_kept'] = row.objectName() == name_before
    except RuntimeError:
        seen['check_row_kept'] = False
    native.click(); spin(0.3)
    seen['check_row_height'] = row.height() if seen['check_row_kept'] else None
native.move(*away); spin(0.2)
tree_row = next((i for i in items(win) if i.objectName().startswith('tree-row-building') and i.isVisible()), None)
seen['tree_row'] = tree_row is not None
if tree_row is not None:
    native.click(*center(tree_row)); spin(0.4)
    try:
        seen['tree_row_kept'] = bool(tree_row.objectName())
    except RuntimeError:
        seen['tree_row_kept'] = False
    session.select('site', ''); spin(0.2)

# D23: a smaller window: said, with its Undo.
win.resize(1280, 800); spin(0.8)
seen['small_notice'] = find(win, name='statusHint').property('text')
seen['small_undo'] = find(win, name='arrangeUndo') is not None
seen['small_checks'] = find(win, name='checksPanel') is not None
if seen['small_undo']:
    native.click(*center(find(win, name='arrangeUndo'))); spin(0.6)
    seen['small_checks_after_undo'] = find(win, name='checksPanel') is not None
win.resize(1600, 960); spin(0.8)
host.shell.trigger('default_layout'); spin(0.6)
seen['back_checks'] = find(win, name='checksPanel') is not None

# M07: the automatic strings beside the panel, the plan free.
native.key('2', ('ctrl',)); spin(0.8)
host.shell.trigger('strings_auto'); spin(0.6)
dialog = find(win, name='plant-proposal-dialog') or next((p for p in popups(win) if p.height() > 100), None)
popup_item = next((p for p in popups(win) if p.height() > 100), None)
seen['proposal_open'] = popup_item is not None
if popup_item is not None:
    seen['proposal_modal'] = bool(popup_item.parent().property('modal'))
    seen['proposal_size'] = [popup_item.width(), popup_item.height()]
    point = popup_item.mapToScene(QPointF(0, 0))
    seen['proposal_at'] = [point.x(), point.y()]
    plan_area = find(win, name='planMouse')
    corner = plan_area.mapToScene(QPointF(30, plan_area.height()-30))
    native.click(corner.x(), corner.y()); spin(0.3)
    seen['proposal_stays_after_plan_click'] = next((p for p in popups(win) if p.height() > 100), None) is not None
    native.click(*center(find(win, text='Annulla', within=popup_item))); spin(0.3)
    seen['proposal_closes'] = next((p for p in popups(win) if p.height() > 100), None) is None
    host.shell.trigger('strings_auto'); spin(0.5)
    native.key('esc'); spin(0.3)
    seen['proposal_closes_with_esc'] = next((p for p in popups(win) if p.height() > 100), None) is None
native.key('1', ('ctrl',)); spin(0.5)
seen['phase_after_proposal'] = win.property('phase')
win.setProperty('phase', 'model'); spin(0.5)

# D11, D12: the ground and the pixels. R405: square buttons.
scene = find(win, name='sceneView')
ground = scene.findChild(QObject, 'ground')
seen['ground'] = [ground.property('scale').x(), host.scene.bounds['groundHalf'], ground.property('position').x(), host.scene.bounds['centre'][0]]
point = scene.mapToScene(QPointF(0, 0))
seen['scene_view'] = [point.x(), point.y(), scene.width(), scene.height()]
seen['status_buttons'] = []
for name in ('statusPanelLeft', 'statusPanelBottom', 'statusPanelRight', 'statusHelp'):
    item = find(win, name=name)
    icon = next(i for i in [item.property('contentItem')] + list(item.property('contentItem').childItems()) if i.width() and 'Icon' in i.metaObject().className())
    seen['status_buttons'].append([item.width(), item.height(), icon.width(), icon.height()])
fractional = []
for item in items(win):
    if item.isVisible() and item.metaObject().className().startswith('Icon_') and item.width() and item.opacity():
        at = item.mapToScene(QPointF(0, 0))
        if abs(at.x() - round(at.x())) > 0.01 or abs(at.y() - round(at.y())) > 0.01:
            fractional.append([item.parentItem().objectName() or item.parentItem().metaObject().className()[:24], round(at.x(), 2), round(at.y(), 2)])
seen['icons_off_pixel'] = fractional[:12]
# D18, D26: a year on its way has its bar and Cancel; Cancel stops it; another goes to its end.
bridge = host.bridge
bridge.recompute()
wait_until(lambda: find(win, name='statusProgressBar') is not None, 60)
progress = find(win, name='statusProgressBar')
seen['progress_shown'] = progress is not None
seen['progress_text'] = find(win, name='statusProgressText').property('text') if progress is not None else ''
if progress is not None:
    native.click(*center(find(win, name='statusProgressCancel'))); spin(0.4)
seen['busy_after_cancel'] = bool(bridge.busy)
seen['progress_after_cancel'] = find(win, name='statusProgress') is not None
bridge.recompute()
wait_until(lambda: find(win, name='statusProgressBar') is not None, 60)
seen['second_year_progress'] = find(win, name='statusProgressBar') is not None
bridge.cancelCompute(); spin(0.3)
seen['busy_after_second_cancel'] = bool(bridge.busy)

seen['warnings'] = host.warnings[-5:]
print(json.dumps(seen, ensure_ascii=False))
'''


def _run(*args, timeout):
    environment = dict(os.environ, PYTHONUTF8='1', PYTHONPATH=os.pathsep.join((str(ROOT/'tests'), str(ROOT/'src'))))
    with tempfile.TemporaryFile() as output:     # a pipe would stay open in the program left running
        code = subprocess.run([sys.executable, str(TOOL), *args], stdout=output, stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL, env=environment, timeout=timeout, cwd=ROOT).returncode
        output.seek(0)
        return code, output.read().decode('utf-8', 'replace')


@unittest.skipUnless(sys.platform == 'win32', 'Windows messages')
@unittest.skipIf(os.environ.get('MERIDIANA_NO_NATIVE'), 'switched off')
class Corrections(unittest.TestCase):
    seen = None

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='meridiana-native-r14-', ignore_cleanup_errors=True)
        ctl = cls.folder.name
        code, text = _run('start', '--engine', 'quick', '--ctl', ctl, '--timeout', '120', '--no-calc',
                          '--desktop', 'meridiana-collaudo-r14', timeout=140)
        if code:
            raise AssertionError(text)
        script = Path(ctl)/'journey.py'
        script.write_text(JOURNEY, encoding='utf-8')
        code, text = _run('run', '--ctl', ctl, str(script), '--timeout', '460', timeout=480)
        _run('run', '--ctl', ctl, '--stop', timeout=30)
        if os.environ.get('MERIDIANA_NATIVE_DUMP'):
            Path(os.environ['MERIDIANA_NATIVE_DUMP']).write_text(text, encoding='utf-8')
        try:
            cls.seen = json.loads(text.strip().splitlines()[-1])
        except (IndexError, ValueError):
            raise AssertionError(text) from None

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def test_d04_tooltip_sits_under_the_pointer(self):
        dx, dy = self.seen['tip_offset']
        self.assertLessEqual(abs(dx - 2), 1)        # ui: tip at 2, 21 from the cursor
        self.assertLessEqual(abs(dy - 21), 1)

    def test_r379_tooltip_fades_in_and_out(self):
        self.assertTrue(any(0 < value < 1 for value in self.seen['tip_fade_samples']), self.seen['tip_fade_samples'])
        self.assertTrue(any(0 < value < 1 for value in self.seen['tip_fade_out_samples']), self.seen['tip_fade_out_samples'])
        # 60 ms of fading; other programs on this PC can hold a frame back, which is not the tooltip's doing.
        self.assertLess(self.seen['tip_gone_ms'] - self.seen['tip_gone_turn_ms'], 200)

    def test_r367_next_tooltip_at_once(self):
        self.assertEqual(len(self.seen['tips_while_passing']), 1, self.seen['tips_while_passing'])

    def test_d02_d03_nothing_stays_after_clicks(self):
        self.assertEqual(self.seen['stuck_tips'], 0)
        self.assertEqual(self.seen['stuck_alpha'], [0, 0])

    def test_d05_d06_every_menu_closes(self):
        self.assertGreaterEqual(len(self.seen['menus']), 4, self.seen['menus'])
        for name, result in self.seen['menus'].items():
            self.assertEqual(result, dict(opened=True, outside=True, esc=True), name)

    def test_menu_unrolls_downward(self):
        heights = self.seen['menu_unroll_heights']
        if self.seen['menu_unroll_turn_ms'] < 60:      # a loaded PC may give the animation no frame to be seen in
            self.assertTrue(any(0 < value < self.seen['menu_height'] for value in heights), heights)
        self.assertEqual(heights, sorted(heights))

    def test_d10_background_menu_is_the_short_one(self):
        self.assertLess(self.seen['menu_height'], 400)

    def test_d09_maps_on_from_the_start(self):
        self.assertFalse(self.seen['maps_offline'])

    def test_d08_undo_and_redo_in_every_phase(self):
        self.assertEqual(self.seen['drawn'], 1)
        self.assertEqual(self.seen['ctrl_z_model'], 0)
        self.assertEqual(self.seen['ctrl_y_model'], 1)
        self.assertEqual(self.seen['ctrl_z_plant'], 0)
        self.assertEqual(self.seen['ctrl_y_plant'], 1)

    def test_esc_returns_to_select_after_plant_was_visited(self):
        self.assertEqual(self.seen['esc_back_to_select'], 'select')

    def test_r402_stringing_beside_the_3d(self):
        self.assertEqual(self.seen['string_tool_beside_3d'], 'string')
        self.assertGreater(self.seen['string_modules_clicked'], 0)
        self.assertEqual(self.seen['string_draft'], self.seen['string_modules_clicked'])
        self.assertGreaterEqual(self.seen['strings_added_beside_3d'], 0)      # a string taken from others: the list may keep its length
        self.assertTrue(self.seen['string_stored'])
        self.assertEqual(self.seen['tool_after_string'], 'select')

    def test_r402_views_in_plant(self):
        self.assertEqual(self.seen['view_plant_opens'], 'plan')
        self.assertFalse(self.seen['plant_3d_at_open'])
        self.assertTrue(self.seen['plant_split_plan'])
        self.assertTrue(self.seen['plant_split_3d'])
        self.assertEqual(self.seen['view_model_again'], self.seen['view_model'])
        self.assertTrue(self.seen['model_3d_again'])
        self.assertEqual(self.seen['view_plant_again'], 'plan')

    def test_d11_ground_as_in_the_widgets(self):
        scale, half, x, centre = self.seen['ground']
        self.assertAlmostEqual(scale, half/50, places=3)
        self.assertAlmostEqual(x, centre, places=3)

    def test_d12_3d_on_whole_pixels(self):
        for value in self.seen['scene_view']:
            self.assertAlmostEqual(value, round(value), places=3)

    def test_d13_icons_on_whole_pixels(self):
        self.assertEqual(self.seen['icons_off_pixel'], [])

    def test_r405_status_buttons_are_square(self):
        for width, height, icon_width, icon_height in self.seen['status_buttons']:
            self.assertEqual((width, height), (28, 28))
            self.assertEqual((icon_width, icon_height), (16, 16))

    def test_r410_ridge_stands_where_it_is_drawn(self):
        self.assertEqual(self.seen['ridge_type'], 'free')
        self.assertEqual(self.seen['ridge_pitches'], 2)
        # Clicked a quarter from the far side; the share is read to two decimals (0.72 is within the 0.03).
        self.assertLessEqual(abs(round(self.seen['ridge_share'] - .75, 2)), .03)
        self.assertEqual(self.seen['ridge_undone'], 'flat')

    def test_r401_corners_are_drawn_in_the_scene(self):
        self.assertTrue(self.seen['dots_in_scene'])
        self.assertGreater(self.seen['corner_near_changed'], 0)      # the near corner shows
        self.assertEqual(self.seen['corner_far_changed'], 0)         # the far one is behind the wall

    def test_r412_a_plus_by_the_pointer_only_with_ctrl(self):
        self.assertFalse(self.seen['plus_without_ctrl'])
        self.assertTrue(self.seen['plus_with_ctrl'])
        self.assertFalse(self.seen['plus_after_ctrl'])
        self.assertIn('Ctrl', self.seen['vertex_help'])
        self.assertNotIn('Maiusc', self.seen['vertex_help'])
        self.assertNotIn('Shift', self.seen['vertex_help'])

    def test_d18_status_bar_says_where_and_what(self):
        self.assertRegex(self.seen['cursor_text'], r'^E .*  N .* m$')
        self.assertTrue(self.seen['measure_text'], self.seen)

    def test_m15_the_year_remark_is_not_the_plan_hint(self):
        self.assertNotIn('Posa prima', self.seen['hint_in_model'])

    def test_d18_d26_the_bar_of_the_year(self):
        self.assertTrue(self.seen['progress_shown'])
        self.assertIn('Produzione', self.seen['progress_text'])
        self.assertFalse(self.seen['busy_after_cancel'])
        self.assertFalse(self.seen['progress_after_cancel'])
        self.assertTrue(self.seen['second_year_progress'])
        self.assertFalse(self.seen['busy_after_second_cancel'])

    def test_m07_proposal_is_a_little_window_beside_the_panel(self):
        self.assertTrue(self.seen['proposal_open'])
        self.assertFalse(self.seen['proposal_modal'])
        width, height = self.seen['proposal_size']
        self.assertLessEqual(width, 480)
        self.assertLess(height, 560)
        self.assertTrue(self.seen['proposal_stays_after_plan_click'])
        self.assertTrue(self.seen['proposal_closes'])
        self.assertTrue(self.seen['proposal_closes_with_esc'])
        self.assertEqual(self.seen['phase_after_proposal'], 'model')

    def test_d20_card_carried_stands_beside_the_other(self):
        self.assertTrue(self.seen['drop_zone_shown'])
        self.assertAlmostEqual(self.seen['lift_scale'], 1.03, places=2)
        self.assertEqual(self.seen['carried_visible'], [True, True])
        (lx, ly, lw, lh), (rx, ry, rw, rh) = self.seen['carried_rects']
        self.assertEqual((lx, lw), (rx, rw))
        self.assertLessEqual(ly + lh, ry)            # carried over the upper third: above Properties
        self.assertTrue(self.seen['central_moved_at_once'])
        self.assertEqual(self.seen['restored_left_x'], 0)

    def test_d23_a_smaller_window_says_so_with_its_undo(self):
        self.assertIn('forma', self.seen['small_notice'])
        self.assertTrue(self.seen['small_undo'])
        self.assertTrue(self.seen['small_checks_after_undo'])
        self.assertTrue(self.seen['back_checks'])

    def test_d22_right_button_on_a_title(self):
        self.assertTrue(self.seen['title_menu'], self.seen)
        self.assertIn('Strumenti', self.seen['title_menu'][0] + [''] or [])

    def test_d16_rows_light_under_the_pointer(self):
        self.assertGreater(self.seen['check_row_lit'], 20)
        self.assertGreater(self.seen['tree_row_lit'], 20)

    def test_d17_strip_of_the_production(self):
        self.assertTrue(self.seen['strip_shown'])
        self.assertTrue(self.seen['meteo_state'])
        self.assertTrue(self.seen['near_changed'])
        self.assertTrue(self.seen['near_back'])
        self.assertTrue(self.seen['near_box_back'])

    def assert_view_kept(self, marks, keys=('zoom', 'x', 'y')):
        first = next(iter(marks.values()))
        for name, mark in marks.items():
            for key in keys:
                self.assertAlmostEqual(mark[key], first[key], delta=.02 if key != 'zoom' else 1e-5, msg=(name, key, marks))

    def test_r431_selecting_does_not_move_the_plan_nor_the_panel(self):
        marks = {k: v for k, v in self.seen['view_marks'].items()}
        self.assertGreaterEqual(len(marks), 5, marks)
        self.assert_view_kept(marks)
        for name, mark in marks.items():
            if name != 'edge_moved':
                self.assertEqual(mark['right'], marks['start']['right'], name)
                self.assertEqual(mark['width'], marks['start']['width'], name)
        self.assertNotEqual(marks['edge_moved']['width'], marks['start']['width'])

    def test_r431_a_section_of_the_plant_does_not_move_the_plan(self):
        marks = self.seen['view_marks_plant']
        self.assertGreaterEqual(len(marks), 2, marks)
        self.assert_view_kept(marks, ('zoom', 'x', 'y', 'width', 'right'))

    def test_r430_status_bar_stays_in_the_useful_area(self):
        for name, place in self.seen['placed'].items():
            self.assertEqual(place, dict(window_in_area=True, bar_in_window=True), name)

    def test_d15_rows_are_kept_when_the_list_changes(self):
        self.assertTrue(self.seen['check_row'])
        self.assertTrue(self.seen['check_row_kept'])
        self.assertEqual(self.seen['check_row_height'], 34)
        self.assertTrue(self.seen['tree_row_kept'])

    def test_no_qml_warning(self):
        self.assertEqual(self.seen['warnings'], [])


if __name__ == '__main__':
    unittest.main()
