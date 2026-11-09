"""The Widgets context_actions and row actions expressed as native Quick menu data."""
from meridiana import manual, move, sides

from .plan_locale import _


def entries(controller):
    e = controller.editor
    kind, oid = e.selection
    key = e.selected_module[1]
    result = []

    def add(command, text, enabled=True):
        result.append(dict(command=command, text=_(text), enabled=enabled, separator=False, header=False, menu=''))

    def separator():
        result.append(dict(command='', text='', enabled=False, separator=True, header=False, menu=''))

    if e.draft is not None:
        # R508: a string drawn by hand ends here as with its keys, the plan's own commands after it is closed
        add('finish_string', 'Close the string (Enter)', bool(e.draft))
        add('back_module', 'Take back the last module (Backspace)', bool(e.draft))
        separator()
        add('cancel_string', 'Give up the string (Esc)')  # the words of ui/window.py, translated
        coordinates(controller, result)
        return result
    if controller.tool not in ('select', 'move', 'rotate', 'string', 'draw_string') and controller.drawing.points:
        add('close_outline', 'Close the outline', len(controller.drawing.points) >= 3)
        add('back', 'Remove the last point (Backspace)')
        separator()
        add('cancel_outline', 'Cancel the drawing (Esc)')
        coordinates(controller, result)
        return result
    # R533: the menu looks at the selection. What it acts on comes first, under a title (the modules selected, the
    # module, the row); the levels above it (the sub-field, the roof) and the point's coordinates go in submenus, so
    # a menu opened on modules does not mix the commands of one module, of its row and of its sub-field.
    sfid = oid.partition('/')[0] if kind == 'row' else oid
    sf = e.session.subfield(sfid) if kind in ('row', 'subfield') else None
    swept = list(getattr(e, 'swept', None) or [])
    many = e.phase == 'plant' and len(swept) > 1
    part = kind in ('row', 'subfield') and (kind == 'row' or bool(key) or many)    # the sub-field is a level above
    menu = ['']

    def add(command, text, enabled=True, **values):
        result.append(dict(command=command, text=_(text).format(**values), enabled=enabled, separator=False,
                           header=False, menu=menu[0]))

    def separator():
        if result and not result[-1]['separator'] and result[-1]['menu'] == menu[0]:
            result.append(dict(command='', text='', enabled=False, separator=True, header=False, menu=menu[0]))

    def header(text, **values):
        # a title: a separator for whoever reads the commands, a line of muted words in the menu
        if result and not result[-1]['separator']:
            result.append(dict(command='', text='', enabled=False, separator=True, header=False, menu=menu[0]))
        result.append(dict(command='', text=_(text).format(**values), enabled=False, separator=True, header=True,
                           menu=menu[0]))

    if many:
        header('{n} modules selected', n=len(swept))
        add('frame', 'Frame it')
        add('select_rows', 'Select their rows')
        add('remove_selected', 'Take the {n} selected modules out', n=len(swept))
    elif kind == 'subfield' and key:
        header('Module')
        add('properties', 'Properties')
        add('frame', 'Frame it')
        add('remove', 'Take this module out')
    else:
        add('properties', 'Properties')
        add('frame', 'Frame it')
    if e.phase == 'plant' and (key or swept):
        # R456, answer 6: optimizers on some modules only, by hand or on the modules in the obstacles' shadow
        separator()
        add('optimizer_on', 'Optimizer on these modules')
        add('optimizer_off', 'No optimizer on these modules')
        add('optimizer_shaded', 'Optimizers only on the modules in the obstacles\' shadow')
    if e.phase == 'plant':
        # R522: the sizing window on the modules in no string only, the strings and inverters there are
        # kept; with R533's menu at its first level, after what acts on the selection, never in a submenu
        separator()
        add('propose_free', 'Propose inverters and strings for the modules in no string')
    rid = oid.partition('/')[2] if kind == 'row' else e._rid(sfid, key)
    row = next((r for r in getattr(e.results.get(sfid), 'rows', []) if r.id == rid), None)
    if row is not None and not many and (kind == 'row' or key):
        header('Row')
        if kind != 'row':
            add('select_row', 'Select the row')
        add('remove_row', 'Take the row away')
        add('append_row', 'Add a row at the back')
        add('resize_row', 'Shorten or lengthen…')
        add('explode_row' if row.count > 1 else 'turn_row', 'Explode the row' if row.count > 1 else 'Turn by 90°')
    if part and sf is not None:
        menu[0] = _('Sub-field «{name}»').format(name=sf.name or sf.id)
        if many:
            add('properties', 'Properties of the sub-field')
    if kind in ('building', 'subfield', 'row') and subfield_at(controller) and not many:
        # one module where the menu was opened, never a whole row (06/11/2026)
        add('add_module', 'Add a module here')
    if kind in ('subfield', 'row') and sf is not None:
        if not part:
            separator()
        add('relayout' if sf.manual else 'lay',
            'Lay again automatically' if sf.manual else 'Lay again' if sf.filled else 'Lay the modules')
        if sf.filled:
            add('explode_all', 'Explode the rows')
            add('empty', 'Take the modules out')
        if move.can_split(e.project, sf) and move.straddle(e.project, sf):
            add('split_pitches', 'Split on the ridge')
        if len(move._group_of(e.project, sf.id)) > 1:
            add('leave_group', 'Leave the group')
    roof = kind == 'building' or (e.phase == 'plant' and controller._context_host)
    if roof and kind != 'building':
        menu[0] = _('Roof')
    elif roof:
        separator()
    if roof:
        add('pitches', 'A sub-field on each pitch')
        if e.phase == 'plant':
            # R445, decision 4: the sub-field of before, an area the layout fills with its margins and the rules
            add('fill_area', 'Fill an area with the automatic layout')
        # R445, decision 2: the free bands of DCPREV 14030 as obstacles, on this roof or on every roof
        add('fire_bands', 'Add the 1 m fire-brigade bands as obstacles (this roof)')
        add('fire_bands_all', 'Add the 1 m fire-brigade bands as obstacles (every roof)')
    menu[0] = ''
    if e.clip_target() or e.can_paste():
        separator()
        if e.clip_target():
            add('cut', 'Cut')
            add('copy', 'Copy')
        if e.can_paste():
            add('paste', 'Paste')
    owner = 'subfield' if part else kind
    if owner in ('building', 'subfield', 'exclusion', 'prop'):
        menu[0] = _('Sub-field «{name}»').format(name=sf.name or sf.id) if part and sf is not None else ''
        separator()
        if owner not in ('exclusion', 'prop'):
            add('rename', 'Rename…')
        add('duplicate', 'Duplicate')
        if owner != 'prop':
            add('square', 'Square the corners')
        separator()
        # what «Delete» deletes, in its words: never a bare «Delete» beside the modules selected
        add('delete_subfield' if part else 'remove', {'building': 'Delete the building', 'subfield': 'Delete the sub-field',
            'exclusion': 'Delete the exclusion', 'prop': 'Delete the object'}[owner])
    menu[0] = ''
    if controller._context_side:
        separator()
        add('align_side', 'Align the view to this side')
        if abs(controller._view_bearing % 360) > .05:
            add('north', 'North up')
        if side_owner(controller):
            # R356: more vertices at once, on the side under the right click of what is selected
            menu[0] = _('Add vertices on this side')
            add('add_vertex_here', 'One vertex here')
            add('add_vertices_2', 'One in the middle')
            add('add_vertices_3', 'Two, in three equal parts')
            add('add_vertices_4', 'Three, in four equal parts')
            menu[0] = ''
    coordinates(controller, result)
    return result


COORDINATES = (('copy_degrees', 'degrees', 'Copy latitude and longitude: {text}'),
               ('copy_decimal', 'decimal', 'Copy for maps and GIS: {text}'),
               ('copy_utm', 'utm', 'Copy in UTM: {text}'),
               ('copy_local', 'local', 'Copy the local coordinates: {text}'))


def point_texts(controller):
    """The point where the menu was opened, written as geo.point_texts writes it; {} before any right click."""
    from meridiana import geo
    point = getattr(controller, '_context_coords', None)
    if not point:
        return {}
    site = controller.session.project.site
    return geo.point_texts(geo.Origin(site.lat, site.lon), *point)


def coordinates(controller, result):
    """R487: the point under the right click, on an object or on nothing, in four forms for the clipboard."""
    texts = point_texts(controller)
    if not texts:
        return
    # R533: in a submenu of their own, after what the menu acts on
    title = _('Coordinates of this point')
    for command, key, text in COORDINATES:
        result.append(dict(command=command, text=_(text).format(text=texts[key]), enabled=True, separator=False,
                           header=False, menu=title))


def near_side(controller, point):
    """The side under a right click: (its ring, its index, the kind and the id of its object), the selected object's
    first; None away from every side."""
    preferred = controller.editor.selection
    objects = sorted(controller._scene['objects'], key=lambda o: (o['kind'], o['oid']) != preferred)
    for obj in objects:
        if obj['kind'] not in ('building', 'pitch', 'subfield', 'exclusion'):
            continue
        ring = [(x, -y) for x, y in obj['points']]
        side = sides.nearest(ring, point, 12*controller._mpp)
        if side is not None:
            return ring, side, obj['kind'], obj['oid']
    return None


def side_owner(controller):
    """The selected object whose side is under the right click, when vertices can be added on it (R356): a building,
    a sub-field or an exclusion, as (kind, id, side); None otherwise."""
    found = controller._context_side
    if not found or len(found) < 4:
        return None
    _ring, side, kind, oid = found
    if kind not in ('building', 'subfield', 'exclusion') or (kind, oid) != tuple(controller.editor.selection[:2]):
        return None
    return kind, oid, side


def building_under(controller, point):
    """The building under a right click: Plant cannot select it, and still lays a sub-field on each of its pitches."""
    hit = next(controller.editor._hits(point, frozenset({'building'})), None)
    return hit[1] if hit else None


def subfield_at(controller):
    """The laid sub-field under the point where the menu was opened (the one chosen first): where «Add a module here»
    puts it, also on a place left empty, where the click finds the building."""
    from shapely.geometry import Point, Polygon
    point = getattr(controller, '_context_point', None)
    if not point:
        return ''
    e = controller.editor
    kind, oid = e.selection
    chosen = oid.partition('/')[0] if kind in ('row', 'subfield') else ''
    here = Point(*point)
    found = [sf.id for sf in e.project.subfields if sf.filled and len(sf.ring) >= 3
             and Polygon([tuple(map(float, q)) for q in sf.ring]).buffer(1e-6).contains(here)]
    return chosen if chosen in found else (found[0] if found else '')


def execute(controller, command):
    e = controller.editor
    kind, oid = e.selection
    sfid = oid.partition('/')[0] if kind == 'row' else oid
    rid = oid.partition('/')[2] if kind == 'row' else e._rid(sfid, e.selected_module[1])
    if command in {c for c, _k, _t in COORDINATES}:
        from PySide6.QtGui import QGuiApplication
        text = point_texts(controller)[next(k for c, k, _t in COORDINATES if c == command)]
        QGuiApplication.clipboard().setText(text)
        controller.notice.emit(_('In the clipboard: {text}').format(text=text))
    elif command in ('optimizer_on', 'optimizer_off', 'optimizer_shaded'):
        from meridiana.energy import plant
        results = {k: v for k, v in e.results.items() if not isinstance(v, Exception)}
        if command == 'optimizer_shaded':
            keys, only = plant.shaded_keys(e.project, results), True
            if not keys:
                controller.notice.emit(_('No module is in the shadow of an obstacle in the design window.'))
                return
        else:
            keys = [f'{s}/{k}' for s, k in (getattr(e, 'swept', None) or [])] or [f'{sfid}/{e.selected_module[1]}']
            only = False
        found, text = plant.optimized_after(e.project, results, keys, command != 'optimizer_off', only=only)
        if found is None:
            controller.notice.emit(text)
            return
        controller.session.edit(text, lambda p: plant.set_optimized(p.energy, found))
        controller.notice.emit(text)
    elif command == 'add_module':
        target = subfield_at(controller)
        if target:
            controller.session.edit(_('Add a module'), manual.add_module(
                e.project, target, controller._context_point, e.results.get(target)))
    elif command in ('select_row', 'resize_row'):
        controller.setTool('select')
        e.select('row', sfid+'/'+rid)
    elif command in ('remove_row', 'append_row', 'explode_row', 'turn_row'):
        fn = dict(remove_row=manual.remove, append_row=manual.append, explode_row=manual.explode, turn_row=manual.turn)[command]
        controller.session.edit(_('Change a row'), fn(e.project, sfid, rid, e.results.get(sfid)))
    elif command in ('lay', 'relayout', 'empty', 'explode_all'):
        sf = e.session.subfield(oid)
        if sf is None:
            return
        if command == 'explode_all':
            change = manual.explode(e.project, oid, None, e.results.get(oid))
        else:
            def change(p):
                target = next(s for s in p.subfields if s.id == oid)
                target.filled = command != 'empty'
                if command == 'relayout':
                    target.manual = False
                    target.rows = []
                    target.removed = []
                elif command == 'lay' and not target.manual:
                    target.removed = []
        controller.session.edit(_('Lay modules') if command != 'empty' else _('Take the modules out'), change)
    elif command in ('cut', 'copy', 'paste'):
        e.apply_command(dict(type={'cut': 'cut', 'copy': 'copy', 'paste': 'paste_start'}[command]))
        controller._tool = e.tool
    elif command in ('split_pitches', 'leave_group'):
        e.apply_command(dict(type=command, oid=oid))
    elif command == 'pitches':
        b = e.project.building(oid if kind == 'building' else controller._context_host)
        if b:
            from shapely.geometry import Polygon
            rings = [p.ring for p in b.pitches() if len(p.ring) >= 3 and Polygon(p.ring).area >= .5] or [b.footprint]
            for ring in rings:
                # an area to lay, as before R445: whole pitches are filled with «Lay», with the margins and the rules
                e.apply_command(dict(type='polygon', tool='subfield', ring=ring, spec={'fill': 'area'}))
    elif command == 'square':
        e.apply_command(dict(type='square'))
    elif command == 'fill_area':
        controller.activateTool('subfield', {'fill': 'area'})
    elif command in ('fire_bands', 'fire_bands_all'):
        host = oid if kind == 'building' else controller._context_host
        e.apply_command(dict(type='fire_bands', building=None if command == 'fire_bands_all' else host))
    elif command in ('remove', 'remove_selected'):
        controller.key('Delete', '', 0)
    elif command == 'select_rows':
        # R533: the modules selected grow to the whole of their rows, still a selection of modules
        rows = {(s, e._rid(s, k)) for s, k in e.swept}
        grown = []
        for s in sorted({s for s, _r in rows}):
            gone = set(e.session.subfield(s).removed)
            grown += [(s, m.key) for m in getattr(e.results.get(s), 'modules', [])
                      if (s, m.rid) in rows and m.key not in gone]
        e.swept = grown
        e.session.select(*e.selection)
        e._hint()
    elif command == 'delete_subfield':
        e.select('subfield', sfid)
        e.swept = []
        controller.key('Delete', '', 0)
    elif command == 'propose_free':
        controller.viewCommand.emit(command)            # plan_part: the plant's sizing window (R522)
    elif command in ('properties', 'frame', 'north', 'rename'):
        controller.viewCommand.emit(command)
    elif command.startswith(('add_vertex_here', 'add_vertices_')) and side_owner(controller):
        kind, oid, side = side_owner(controller)
        found = dict(type='add_vertices', kind=kind, oid=oid, index=side)
        if command == 'add_vertex_here':
            found['point'] = controller._context_point
        else:
            found['parts'] = int(command.rpartition('_')[2])
        for event in e.apply_command(found):
            if event.get('type') == 'error':
                controller.notice.emit(event.get('message', ''))
        if e.notice:
            controller.notice.emit(e.notice)
    elif command == 'align_side' and controller._context_side:
        from .plan_collect import align_angle
        ring, side = controller._context_side[:2]
        controller.alignRequested.emit(align_angle(ring, side))
    elif command == 'close_outline':
        controller.key('Enter', '', 0)
    elif command == 'back':
        controller.key('Backspace', '', 0)
    elif command in ('finish_string', 'back_module', 'cancel_string'):
        controller.key({'finish_string': 'Enter', 'back_module': 'Backspace', 'cancel_string': 'Escape'}[command], '', 0)
    elif command == 'cancel_outline':
        controller.drawing._reset()
    else:
        raise ValueError('Unknown plan context command: '+command)
