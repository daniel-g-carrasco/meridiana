"""One long journey through the real window with native messages, measured once and read by the tests.

Runs inside the program through tools/quick_native_input.py, on its own desktop. It only records what it
sees, in a dictionary: the assertions are in test_native.py, so a defect found here does not stop the journey.
"""
JOURNEY = r'''
import json
from PySide6.QtCore import QObject, QPointF

seen = {}
near_away = (1100, 300)


def tips():
    return [p for p in popups(win) if 'p style' in (visible_text(p) + [''])[0]]


def menus():
    return [p for p in popups(win) if p.height() > 40 and 'p style' not in (visible_text(p) + [''])[0]]


def press_item(name, **kw):
    native.click(*center(find(win, name=name)), **kw)
    spin(0.4)


# Wait for the plan: the same steps as the real start, with the layout done.
wait_until(lambda: host.plan is not None and len(host.plan.modules or []) >= 700, 60)
spin(1.0)

# Hover and tooltips, before any click.
native.move(*near_away); spin(0.2)
button = find(win, name='tool_tool_move')
native.move(*center(button)); spin(0.2)
seen['hover_on_button'] = bool(button.property('hovered'))
spin(1.0)
seen['tip_on_button'] = bool([p for p in popups(win) if 'Sposta' in (visible_text(p) + [''])[0]])
native.move(*near_away); spin(0.3)
seen['hover_off_button'] = not button.property('hovered')

# A click on a button of the view bar, then away: nothing may stay lit.
zoom_in, zoom_out = find(win, name='planView-zoom_in'), find(win, name='planView-zoom_out')
native.move(*center(zoom_in)); native.click(); spin(0.2)
native.move(*center(zoom_out)); native.click(); spin(0.2)
native.move(*near_away); spin(0.5)
seen['stuck_tips'] = len(tips())
seen['stuck_hover_alpha'] = [zoom_in.property('color').alpha(), zoom_out.property('color').alpha()]
image = grab('tips.png')

# The background menu: size, and every way of closing it.
background = center(find(win, name='planView-background'))
overlay = None
native.move(*background); native.click(); spin(0.4)
open_menus = menus()
seen['menu_opens'] = bool(open_menus)
if open_menus:
    menu = open_menus[0]
    overlay = menu.parentItem()
    seen['background_menu_height'] = menu.height()
    native.move(*near_away); spin(0.1); native.click(); spin(0.3)
    seen['closes_outside'] = not menus()
    for item in menus():
        item.parent().close()
    spin(0.2)
native.move(*background); native.click(); spin(0.4)
native.key('esc'); spin(0.3)
seen['closes_esc'] = not menus()
for item in menus():
    item.parent().close()
spin(0.2)
native.move(*background); native.click(); spin(0.4)
if menus():
    entry = find(win, name='backgroundAutomatic')
    native.move(*center(entry)); spin(0.2)
    seen['entry_hover'] = bool(entry.property('hovered'))
    native.click(); spin(0.4)
    seen['closes_option'] = not menus()
for item in menus():
    item.parent().close()
spin(0.2)

# Meridio's provider menu: on top of its bubble?
native.click(*center(find(win, name='assistantCharacter'))); spin(0.8)
provider = next((i for i in items(win) if i.isVisible() and i.property('iconName') == 'house' and i.property('text')), None)
if provider is not None:
    native.click(*center(provider)); spin(0.6)
    opened = menus()
    if opened:
        menu = opened[-1]
        bubble = find(win, name='assistantBubble')
        corner = bubble.mapToScene(QPointF(bubble.width() - 8, 60))
        inside = menu.contains(menu.mapFromScene(corner))
        # childAt ignores z: compare the stacking of the two as the scene graph paints them.
        layer = find(win, name='assistantHost')
        seen['provider_menu_overlaps_bubble'] = bool(inside)
        seen['provider_menu_on_top'] = layer.parentItem() != menu.parentItem() or menu.z() > layer.z()
    native.key('esc'); spin(0.2)
    for item in menus():
        item.parent().close()
native.key('esc'); spin(0.3)
if find(win, name='assistantLayer').property('opened'):
    find(win, name='assistantLayer').setProperty('opened', False); spin(0.3)

# Maps and ground as a fresh profile starts them.
maps = host.plan._maps
seen['maps_offline_at_start'] = bool(maps.loader.offline)
scene = find(win, name='sceneView')
ground = scene.findChild(QObject, 'ground')
scale = ground.property('scale')
seen['ground_scale'] = scale.x()
seen['ground_half'] = find(win, name='viewport3d') and host.scene.bounds['groundHalf']
point = scene.mapToScene(QPointF(0, 0))
seen['scene_view'] = [point.x(), point.y(), scene.width(), scene.height()]

# Editing: draw, undo, redo, delete.
session = host.bridge.session
start = len(session.project.buildings)
native.click(*center(find(win, name='tool_tool_building'))); spin(0.2)
for at in [(690, 540), (760, 540), (760, 600), (690, 600)]:
    native.click(*at, steps=4, settle=60)
native.key('enter'); spin(0.5); native.key('esc'); spin(0.2); native.key('esc'); spin(0.2)
seen['drawn'] = len(session.project.buildings) - start
native.key('z', ('ctrl',)); spin(0.5)
seen['after_ctrl_z'] = len(session.project.buildings) - start
if seen['after_ctrl_z'] == seen['drawn']:
    session.undo.undo(); spin(0.3)
native.key('y', ('ctrl',)); spin(0.5)
seen['after_ctrl_y'] = len(session.project.buildings) - start
if seen['after_ctrl_y'] == 0:
    session.undo.redo(); spin(0.3)
native.click(725, 570, settle=300)
seen['selected'] = list(session.selection)
native.key('delete'); spin(0.5)
seen['after_delete'] = len(session.project.buildings) - start

# Keys of the phases.
native.key('2', ('ctrl',)); spin(0.6); seen['ctrl_2'] = win.property('phase')
native.key('1', ('ctrl',)); spin(0.6); seen['ctrl_1'] = win.property('phase')
native.key('tab', ('ctrl',)); spin(0.6); seen['ctrl_tab'] = win.property('phase')
native.key('1', ('ctrl',)); spin(0.4)

# The checks table.
rows = [find(win, name=f'checks-row-{i}') for i in range(3)]
seen['check_row_heights'] = [r.height() for r in rows if r is not None]

# A panel carried onto the right column: stacked as in the Widgets, or in tabs?
title = find(win, name='projectTitleDrag')
x, y = center(title)
native.move(x, y); spin(0.1); native.press()
native.move(1400, 300, steps=16); spin(0.25)
native.release(); spin(0.6)
# Under a tab the other panel is not visible: find only sees visible items.
seen['carried_panels_overlap'] = find(win, name='leftPanel') is None or find(win, name='rightPanel') is None

# A smaller window and back: the checks must come back.
win.resize(1280, 800); spin(0.8)
seen['checks_when_small'] = find(win, name='checksPanel') is not None
win.resize(1600, 960); spin(0.8)
seen['checks_after_back'] = find(win, name='checksPanel') is not None
seen['warnings'] = host.warnings[-5:]
print(json.dumps(seen, ensure_ascii=False))
'''
