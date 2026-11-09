"""Field descriptions shared by the autonomous Quick properties page.

The computations come from the same core functions as ui/properties.py. A schema
contains presentation values only; edits belong to PropertiesBackend and Session.
"""
from __future__ import annotations

import math

from meridiana import help as help_text, layout, model, props, roofs, rules, sides, sun
from meridiana import vvf_activities as vvf
from meridiana.fields import mounting_names, pitch_mode_names
from meridiana.i18n import _, ngettext, number, pgettext


def roof_names():
    return {'flat': _('Flat'), 'mono': _('Mono-pitch'), 'gable': _('Gable'),
            'hip': _('Hip'), 'free': _('Pitches drawn by hand'), 'saddles': _('Saddle-backed bands')}


class Schema:
    def __init__(self):
        self.sections = []
        self.current = None

    def section(self, key, title, hid='', framed=True):
        hint = help_text.get(hid) if hid else None
        self.current = dict(key=key, title=title, help=hid, helpTip=hint.short if hint else '',
                            framed=framed, fields=[])
        self.sections.append(self.current)

    def field(self, key, label, value='', kind='text', **kw):
        item = dict(id=key, label=label, value=value, kind=kind, enabled=True,
                    visible=True, unit='', minimum=0., maximum=1e9, decimals=2,
                    step=0.1, options=[], help='', tip='', side=-1, special='', inlineWith='')
        item.update(kw)
        if kind == 'number':
            value = max(item['minimum'], min(item['maximum'], round(value, item['decimals'])))
            item['value'] = value
            item['display'] = item['special'] if item['special'] and value == item['minimum'] else (
                number(value, item['decimals']) + (('' if item['unit'] == '°' else ' ') + item['unit']
                                                 if item['unit'] else ''))
        else:
            item['display'] = str(value)
        self.current['fields'].append(item)
        return item

    def num(self, key, label, value, low, high, unit='', decimals=2, step=0.1, **kw):
        return self.field(key, label, value, 'number', minimum=low, maximum=high,
                          unit=unit, decimals=decimals, step=step, **kw)

    def choice(self, key, label, value, options, **kw):
        pairs = options.items() if isinstance(options, dict) else options
        return self.field(key, label, value, 'choice',
                          options=[dict(value=k, label=v, enabled=True) for k, v in pairs], **kw)

    def check(self, key, label, value, **kw):
        return self.field(key, label, bool(value), 'check', **kw)

    def note(self, key, text, **kw):
        return self.field(key, '', text, 'note', **kw)

    def action(self, key, label, **kw):
        return self.field(key, label, '', 'action', **kw)

    def outline(self, ring):
        self.section('sides', _('Sides'), 'sides')
        for i, length in enumerate(sides.lengths(ring)):
            self.num(f'side.{i}', _('Side {n}').format(n=i + 1), length,
                     0.1, 10000, 'm', side=i)


MANY_KINDS = ('text', 'number', 'choice', 'check')
MANY_OWN = ('name', 'automatic', 'side.', 'edge.', 'free.')     # what is each object's own: a name, its geometry


def _merged(fields):
    """One field for the same field of several objects: disabled or hidden if it is for one of them, with the choices
    and the range all can take, and «different values» where they differ."""
    item = dict(fields[0])
    item['enabled'] = all(f['enabled'] for f in fields)
    item['visible'] = all(f['visible'] for f in fields)
    if item['kind'] == 'number':
        item['minimum'] = max(f['minimum'] for f in fields)
        item['maximum'] = min(f['maximum'] for f in fields)
    if item['kind'] == 'choice':
        item['options'] = [dict(o, enabled=all(any(type(p['value']) is type(o['value']) and p['value'] == o['value']
                                                   and p['enabled'] for p in f['options']) for f in fields))
                           for o in item['options']]
    item['mixed'] = any(f['value'] != item['value'] for f in fields)
    if item['mixed']:
        item['display'] = ''
        item['mixedText'] = _('different values')
        if item['kind'] == 'choice':
            item['value'] = None
    return item


def common_schema(session, kind, objects):
    """What several objects of one kind have in common (R439), as the schema of one: a change applies to all."""
    schemas = [build_schema(session, kind, thing) for thing in objects]
    known = [{f['id']: f for section in schema for f in section['fields']} for schema in schemas]
    sections = []
    for section in schemas[0]:
        fields = []
        for f in section['fields']:
            same = [fields_of.get(f['id']) for fields_of in known]
            if (f['kind'] in MANY_KINDS and not f['id'].startswith(MANY_OWN)
                    and all(x is not None and x['kind'] == f['kind'] for x in same)):
                fields.append(_merged(same))
        kept = {f['id'] for f in fields}
        for f in fields:
            if f['inlineWith'] and f['inlineWith'] not in kept:
                f['inlineWith'] = ''
        if fields:
            sections.append({**section, 'fields': fields})
    s = Schema()
    s.section('many', '', framed=False)
    names = {'building': _('Buildings'), 'subfield': _('Sub-fields'), 'exclusion': _('Exclusions'), 'prop': _('3D objects')}
    s.note('many', _('{what}: {n} selected. A change applies to all of them; the name and the sides stay each one\'s.').format(
        what=names.get(kind, kind), n=len(objects)))
    return s.sections + sections


def activity_note(fire):
    activity = vvf.activity(fire.activity)
    if activity is not None:
        text = _('{label}. Threshold: {threshold}.').format(
            label=activity.label(), threshold=activity.threshold or _('none, every one is subject'))
        if activity.category_text(fire.category):
            text += ' ' + _('Category {category}: {text}.').format(
                category=fire.category, text=activity.category_text(fire.category).rstrip('.'))
        return text + ' ' + _('Source: DPR 151/2011 Annex I, GU no. 221 of 22/09/2011, p. {page}.').format(
            page=activity.page)
    return _('Choose the activity of Annex I: the category and the report notes follow from it.') if fire.subject else ''


def site_schema(s, p):
    s.section('site', _('Site'), 'site')
    s.field('name', _('Project'), p.name)
    s.field('latitude', _('Latitude'), number(p.site.lat, 6), 'read')
    s.field('longitude', _('Longitude'), number(p.site.lon, 6), 'read')
    if p.site.address:
        s.field('address', _('Address'), p.site.address, 'read')
    s.check('reserved', _('Reserved: never sent to a cloud model'), p.reserved,
            tip=_('Meridio answers about this project only with the local model, whatever his settings say'))
    if p.reserved:
        s.check('consent.tiles', _('Allow online maps: the area shown leaves this PC'), 'tiles' in p.network_consent)
        s.check('consent.pvgis', _('Allow PVGIS weather: the site coordinates leave this PC'), 'pvgis' in p.network_consent)
    s.section('site_actions', '', framed=False)
    s.action('site', _('Find the site…'), enabled=not (p.buildings or p.subfields),
             tip=_('Search an address or type coordinates.') if not (p.buildings or p.subfields) else
             _('The site can be moved only before anything is drawn: the drawing is measured from it.'))
    s.section('network', _('Grid connection (optional)'), 'site.network')
    n = p.network
    for key, label in [('distributor', _('Distributor')), ('pod', 'POD')]:
        s.field('network.' + key, label, getattr(n, key))
    s.num('network.voltage_v', _('Supply voltage'), n.voltage_v, 0, 1000000, 'V', 0, 1, special=_('not stated'))
    s.field('technical_rule', _('Technical rule from voltage'), n.technical_rule(), 'read')
    s.choice('network.phases', _('Phases'), n.phases,
             [('', _('not stated')), ('1', _('Single phase')), ('3', _('Three phase'))])
    s.choice('network.level', _('Connection level'), n.level,
             [('', _('not stated')), *[(k, v) for k, v in rules.level_names().items() if k != 'auto']])
    s.choice('network.connection', _('Connection'), n.connection,
             [('', _('not stated')), ('existing', _('Existing connection')), ('new', _('New connection')),
              ('modification', _('Modification of the connection'))])
    s.num('network.available_kw', _('Available or contracted power'), n.available_kw, 0, 1e9, 'kW', 1, .5,
          special=_('not stated'))
    s.num('network.requested_kw', _('Power requested for the new plant'), n.requested_kw, 0, 1e9, 'kW', 1, .5,
          special=_('not stated'))
    s.field('network.practice_code', _('Connection practice code'), n.practice_code)
    s.section('rules', _('Connection and obligations'), 'site.rules')
    r = p.rules or {}
    s.choice('rules.obligation', _('Minimum renewable capacity'), r.get('obligation') or '', rules.obligation_names())
    s.check('rules.public', _('Public building (+10%)'), r.get('public'))
    s.choice('rules.use', _('Use of the building'), r.get('use') or 'other', rules.use_names())
    s.check('rules.permit_2027', _('Permit requested from 01/01/2027'), r.get('permit_2027'))
    s.num('rules.floor_m2', _('Floor area of the premises'), float(r.get('floor_m2') or 0), 0, 1e6, 'm²', 0, 10,
          special=_('not stated'), tip=_('The floor area of the premises: above 200 m² (production, commerce, services) '
                                         'or 400 m² (a dwelling) the design is a professional\'s (DM 37/2008 art. 5 par. 2).'))
    s.choice('rules.premises', _('Premises'), r.get('premises') or '', rules.premises_names())
    s.check('rules.risk', _('Higher fire risk, medical use or explosion hazard'), r.get('risk'),
            tip=_('Environments subject to specific CEI rules (for the fire risk, CEI 64-8/7 sect. 751.03): '
                  'the design is always a professional\'s (DM 37/2008 art. 5 par. 2 d).'))
    region = rules.region_of(p.site.address)
    s.note('region', _('Region from the address: {region}. Lombardy raises k for permits from 01/01/2027.').format(
        region=region) if region else _('The address does not name a region with rules of its own: the national ones apply.'))


def building_schema(s, b, p):
    s.section('building', _('Building'), 'building')
    s.field('name', _('Name'), b.name)
    s.num('height', _('Clear height') if b.canopy else _('Ridge of the bands') if b.roof.type == 'saddles'
          else _('Eave height'), b.height, .5, 300, 'm')
    others = [x for x in p.buildings if x.id != b.id and x.on != b.id and x.part_of != b.id]
    if b.canopy is None:
        s.num('base', _('Base height'), b.base, 0, 300, 'm', special=_('the ground'),
              tip=_('Where the walls start, above the ground: 0 on the ground; the height of the roof it stands on for '
                    'a plant room (R453). Heights stay measured from the ground.'))
        s.choice('on', _('Stands on'), b.on if p.building(b.on) else '',
                 [('', _('the ground')), *[(x.id, x.name) for x in others]],
                 tip=_('A building chosen: the base goes to its roof under this outline, this body moves with it and keeps '
                       'its modules off this outline.'))
    s.choice('part_of', _('Part of'), b.part_of if p.building(b.part_of) else '',
             [('', _('a building of its own')), *[(x.id, x.name) for x in others if not x.part_of]],
             tip=_('Bodies of one building (an imported model, R440): one name, one fire activity, one entry in the '
                   'report; each keeps its outline and roof.'))
    if b.part_of and p.building(b.part_of):
        s.note('part_note', _('A body of {name}: its name and fire data are those.').format(name=p.whole_of(b).name))
    if b.group and len([x for x in p.buildings if x.group == b.group]) > 1 and not b.part_of:
        s.action('bodies_as_one', _('The bodies of the model are one building'),
                 tip=_('Every body of the imported model becomes a part of this one.'))
    if b.group:
        s.check('in_group', _('Moves with the imported model'), True,
                tip=_('Its bodies move and turn together. Take it off to move this one alone.'))
    if b.canopy:
        s.num('canopy.bays', _('Spaces per row'), b.canopy.bays, 1, 100, decimals=0, step=1)
        s.choice('canopy.pillars', _('Columns'), b.canopy.pillars,
                 [('cantilever', _('Cantilever, one line')), ('two_rows', _('Two lines'))])
        s.num('canopy.columns', _('Columns per line'), b.canopy.columns, 0, 200, decimals=0, step=1,
              special=_('Proposed'))
    s.section('roof', _('Roof'), 'building.roof')
    s.choice('roof.type', _('Type'), b.roof.type, roof_names())
    if b.roof.type in ('mono', 'free', *model.PITCHED) and b.canopy is None:
        s.check('roof.keep_ridge', _('Keep the ridge height when the slope changes'), not b.roof.keep_eave,
                tip=_('On: writing the slope moves the eave, writing the eave changes the slope, the ridge stays where it is. '
                      'Off: the eave stays, and the ridge goes up or down with the slope.'))
    if b.roof.type in ('mono', *model.PITCHED):
        names = roofs.covering_names()
        s.choice('roof.covering', _('Covering'), b.roof.covering or roofs.DEFAULT_COVERING,
                 [(k, _('{covering} ({p} %)').format(covering=names[k], p=number(pct, 0)))
                  for k, pct in roofs.COVERINGS.items()])
        s.num('roof.tilt', _('Slope'), b.slope(), 0, 80, '°', 1, 1)
        s.num('roof.percent', _('Slope (percent)'), math.tan(math.radians(b.slope())) * 100, 0, 600, '%', 1, 1)
        s.note('covering_note', _('Proposed for {covering}: {p} %, from {source}.').format(
            covering=names.get(b.roof.covering or roofs.DEFAULT_COVERING, ''),
            p=number(roofs.COVERINGS.get(b.roof.covering or roofs.DEFAULT_COVERING, 35.), 0),
            source=roofs.covering_source(b.roof.covering)))
    if b.roof.type in model.PITCHED:
        s.num('roof.ridge_height', _('Ridge height'), b.ridge(), .5, 1000, 'm',
              tip=_('The height of the ridge above the ground: written, it sets the slope (the highest point of the roof stands there)'))
        for i, kind in enumerate(b.sides_kind()):
            s.choice(f'edge.{i}', _('Side {n}').format(n=i + 1), kind,
                     [('eave', _('Eave')), ('gable', _('Gable end'))])
        s.action('pick_gable', _('Pick on the plan'))
        problem, indices = b.roof_problem()
        if problem == 'gables':
            s.note('roof_problem', ngettext('Side {sides} cannot be a gable end on this outline: it is an eave.',
                'Sides {sides} cannot be gable ends on this outline: they are eaves.', len(indices)).format(
                    sides=', '.join(str(i + 1) for i in indices)))
        elif problem == 'outline':
            s.note('roof_problem', _('The outline crosses itself: the roof stays flat until it is put right.'))
    if b.roof.type == 'mono':
        s.num('roof.eave_side', _('Eave on side'), b.roof.eave_side + 1, 1, len(b.footprint), decimals=0, step=1)
        s.action('pick_eave', _('Pick on the plan'), inlineWith='roof.eave_side')
    if b.roof.type == 'flat':
        plane = b.plane()
        if plane is not None:               # R455: tilted by its corners, still flat
            pitch = b.pitches()[0]
            s.note('plane_note', _('Inclined plane: slope {t} °, from {low} to {high} m, facing {az} °.').format(
                t=number(pitch.tilt, 1), low=number(min(plane)), high=number(max(plane)), az=number(pitch.azimuth, 0)))
            s.action('flatten', _('Make it level'), tip=_('All the corners at the eave height.'))
        s.num('parapet', _('Parapet'), b.parapet, 0, 5, 'm',
              tip=_('Height of the parapet above the roof, all round: it casts shadows on the modules'))
    if b.roof.type == 'saddles':
        spec = roofs.saddle_spec(b.roof.saddles)
        s.num('saddles.direction', _('Direction of the bands'), spec['direction'], 0, 359.9, '°', 1, 1,
              tip=_('Bearing of the bands, degrees from North: 0 north-south, 90 east-west.'))
        s.action('trace_saddles', _('Trace on the plan'), inlineWith='saddles.direction',
                 tip=_('Two clicks on the plan: the bands run along the line between them.'))
        s.num('saddles.band', _('Width of a band'), spec['band'], 0.2, 100, 'm')
        s.num('saddles.tilt', _('Slope of the bands'), spec['tilt'], 0, 80, '°', 1, 1)
        s.num('saddles.channel', _('Width of a channel'), spec['channel'], 0, 20, 'm')
        s.num('saddles.depth', _('Depth of a channel'), spec['depth'], 0, 5, 'm',
              tip=_('Under the edges of the bands beside it.'))
        s.num('saddles.offset', _('Offset of the pattern'), spec['offset'], 0, 1000, 'm')
        s.note('saddles_note', ngettext('{n} pitch: each band two, each channel one.',
                                        '{n} pitches: each band two, each channel one.', len(b.pitches())).format(
            n=len(b.pitches())))
    if b.roof.type == 'free':
        s.check('roof.joined', _('Join the pitches into one roof'), b.roof.joined,
                tip=_('Pitches side by side meet on the line between them: the ridge or the valley is worked out and '
                      'the heights follow. Untick it for pitches that stay separate, each on its own plane'))
        solved = b.solved()
        for i, f in enumerate(b.roof.free_pitches):
            prefix = f'free.{i}.'
            s.field(prefix + 'heading', '', _('Pitch {n}').format(n=i + 1), 'heading')
            if solved and i < len(solved.heights):
                values = dict(t=number(solved.pitches[i].tilt, 1), low=number(min(solved.heights[i])),
                              high=number(max(solved.heights[i])))
                if any(fold.pitch == i for fold in solved.folds):
                    s.note(prefix + 'solved', _('Corners off one plane: folded into {n} pitches, each corner at its height.').format(
                        n=sum(p.whole == i for p in solved.pitches)))
                elif f.get('z') is not None:
                    s.note(prefix + 'solved', _('By the heights of its corners: slope {t} °, from {low} to {high} m.').format(**values))
                elif i in solved.moved:
                    s.note(prefix + 'solved', _('Joined to the pitches beside it: slope {t} °, from {low} to {high} m.').format(**values))
            s.num(prefix + 'eave_side', _('Eave on side'), f['eave_side'] % len(f['ring']) + 1,
                  1, len(f['ring']), decimals=0, step=1)
            s.action(f'pick_free_eave:{i}', _('Pick on the plan'), inlineWith=prefix + 'eave_side')
            s.num(prefix + 'eave', _('Eave height'), f['eave'], 0, 1000, 'm')
            s.num(prefix + 'tilt', _('Slope'), f['tilt'], 0, 80, '°', 1, 1)
            s.num(prefix + 'percent', _('Slope (percent)'), math.tan(math.radians(f['tilt'])) * 100, 0, 600, '%', 1, 1)
            s.num(prefix + 'ridge', _('Ridge height'), roofs.free_ridge(f['ring'], f['eave_side'], f['eave'], f['tilt']), 0, 1000, 'm')
            s.note(prefix + 'depth', _('Depth from the eave: {v} m').format(v=number(roofs.free_depth(f['ring'], f['eave_side']))))
            s.action(prefix + 'swap', _('Swap eave and ridge'))
    s.outline(b.footprint)
    s.section('fire', _('Fire brigade'), 'building.fire')
    s.choice('fire.activity', _('Activity (DPR 151/2011)'), vvf.shown(b.fire.subject, b.fire.activity),
             [(0, _('No activity subject to control')), (vvf.NOT_SPECIFIED, _('Subject, activity not specified')),
              *[(a.number, a.label()) for a in vvf.ACTIVITIES]], searchable=True,
             tip=_('Number or words of the activity'))
    a = vvf.activity(b.fire.activity)
    category = s.choice('fire.category', _('Category'), b.fire.category,
                        [('', _('not stated')), *[(c, f'{c}: {a.category_text(c)}' if a and a.category_text(c) else c)
                                                  for c in vvf.CATEGORIES]])
    for option in category['options']:
        option['enabled'] = not option['value'] or a is None or bool(a.category_text(option['value']))
    s.note('activity_note', activity_note(b.fire))
    s.check('fire.subject', _('Activity subject to control (DPR 151/2011)'), b.fire.subject)
    s.check('fire.roof_fire_resistant', _('Fire-resistant roof slab'), b.fire.roof_fire_resistant)
    s.note('fire_note', _('For an activity subject to control, the sub-fields keep 1 m from the edge, groups of at most '
                         '20 m and 2 m corridors (DCPREV 14030/2025, 3.3.5.1).'))


def support_now(p, sf):
    return sf.support or model.SupportPlane(enabled=False, **vars(p.surface_of(sf)))


def support_reference(p, sf):
    from meridiana.move import centre
    return centre(p, 'subfield', sf.id) or (0., 0.)


def alignment_names(current):
    names = [('aligned', _('Aligned')), ('staggered', _('Staggered by half a module')), ('free', _('Free'))]
    if current == layout.LEGACY_ALIGNMENT:     # a sub-field saved before keeps its modules until it is changed (R418)
        names.append((layout.LEGACY_ALIGNMENT, _('As it was saved')))
    return names


def target_from_names():
    return [('best', _('Least in shadow, then from the front')), ('front', _('From the front (the eave)')),
            ('back', _('From the back (the ridge)'))]


def target_rule(target_from):
    """The rule of the power asked in words (R417): which rows, from where, which one in part."""
    return {'front': _('Whole rows from the front row (the eave on a pitch), the last one in part.'),
            'back': _('Whole rows from the back row (the ridge on a pitch), the last one in part.')}.get(
        target_from, _('Whole rows next to each other, the set least in the shadows of the obstacles and of those '
                       'alike the one nearest the front (the eave on a pitch); the last row in part.'))


def placement_fields(s, p, sf, raw, result):
    """How the modules stand and how many: R417, R418. A sub-field laid by hand keeps its own rows; one drawn as its
    modules (flush) lays the power asked out of them."""
    automatic = dict(enabled=not sf.manual, tip=_('A sub-field laid by hand keeps its rows.')) if sf.manual else {}
    target_open = {} if not sf.manual or sf.flush else automatic
    s.section('placement', _('Module placement'), 'subfield.placement')
    s.choice('params.alignment', _('Alignment'), raw.alignment, alignment_names(raw.alignment), **automatic)
    s.num('params.target_kwp', _('Power asked'), raw.target_kwp, 0, 1e6, 'kWp', step=1., special=_('as many as fit'),
          **target_open)
    if raw.target_kwp > 0:
        s.choice('params.target_from', _('Rows taken'), raw.target_from, target_from_names(), **target_open)
        s.note('target_rule', target_rule(raw.target_from))
    if (sf.manual and not sf.flush) or raw.target_kwp <= 0 or result is None or not sf.filled:
        return
    power = p.module_of(sf).power_kw
    if result.target_missing:
        s.note('target', ngettext('{n} module short: this sub-field holds at most {m} modules, {kw} kWp',
                                  '{n} modules short: this sub-field holds at most {m} modules, {kw} kWp',
                                  result.target_missing).format(n=result.target_missing, m=result.capacity,
                                                                kw=number(result.capacity * power)))
    else:
        s.note('target', ngettext('{n} module, {kw} kWp, of the {m} this sub-field holds',
                                  '{n} modules, {kw} kWp, of the {m} this sub-field holds',
                                  result.count).format(n=result.count, kw=number(result.count * power), m=result.capacity))


def subfield_schema(s, session, sf):
    p = session.project
    params = p.fill_params(sf)
    raw = sf.layout_params()
    result = session.results.get(sf.id)
    error = str(result) if isinstance(result, Exception) else ''
    result = None if isinstance(result, Exception) else result
    s.section('subfield', _('Sub-field'), 'subfield')
    s.field('name', _('Name'), sf.name)
    s.choice('params.mounting', _('Mounting'), params.mounting, mounting_names(), help='subfield.mounting')
    s.choice('module', _('Module'), sf.module, [(k, f"{m['manufacturer']} {m['model']}") for k, m in p.modules.items()])
    s.action('catalog_module', _('Catalogue…'), inlineWith='module',
             tip=_('Choose the module among the datasheets and the CEC list'))
    s.choice('params.portrait', _('Orientation'), params.portrait, [(True, _('Portrait')), (False, _('Landscape'))])
    s.num('params.stack', _('Modules per table, across'), params.stack, 1, 6, decimals=0, step=1, help='subfield.stack')
    flush = raw.mounting in layout.FLUSH
    if not flush or raw.mounting == 'canopy':
        s.num('params.tilt', _('Module tilt'), params.tilt, 0, 60, '°', 1, 1)
    azimuth = result.azimuth if result is not None and params.azimuth is None else (params.azimuth or 0.)
    s.num('params.azimuth', _('Azimuth (from South, + West)'), azimuth, -180, 180, '°', 1, 1,
          enabled=params.azimuth is not None, tip=_('Uncheck «Automatic» to enter the azimuth.'))
    s.check('automatic', _('Automatic'), params.azimuth is None, inlineWith='params.azimuth')
    s.section('support', _('Auxiliary support plane'), 'subfield.support')
    support = support_now(p, sf)
    s.check('support.enabled', _('Use an independent placement plane'), support.enabled)
    for key, label, low, high, unit in [
        ('z0', _('Elevation at area centre'), -model.HEIGHT_LIMIT, model.HEIGHT_LIMIT, 'm'),
        ('tilt', _('Plane tilt'), 0, 89, '°'), ('azimuth', _('Plane azimuth (from South, + West)'), -180, 180, '°')]:
        value = support.surface().z(*support_reference(p, sf)) if key == 'z0' else getattr(support, key)
        s.num('support.' + key, label, value, low, high, unit, enabled=support.enabled,
              tip=_('Enable the independent placement plane to edit it.'))
    s.note('support_note', _('The building and pitch remain as references; the received model is unchanged.'))
    placement_fields(s, p, sf, raw, result)
    s.section('gaps', _('Gaps and margins'), 'subfield.gaps')
    for key, label, high in [('gap', _('Between modules'), 1.), ('edge', _('From the edge of the area'), 20.)]:
        s.num('params.' + key, label, getattr(params, key), 0, high, 'm', step=.01 if high <= 1 else .1,
              help='subfield.edge' if key == 'edge' else '')
    if flush:
        s.num('params.flush_row_gap', _('Between rows'), params.flush_row_gap, 0, 2, 'm', step=.01, help='subfield.row_gap')
        s.note('row_gap_hint', help_text.texts()['subfield.row_gap'].short)
    s.num('params.table_modules', _('Modules per table, along'), params.table_modules, 0, 200, decimals=0, step=1,
          special=_('continuous rows'))
    s.num('params.table_gap', _('Between tables'), params.table_gap, 0, 5, 'm', step=.05)
    s.check('params.shade_free', _("Out of the obstacles' shadows"), params.shade_free, help='subfield.shade_free')
    s.note('shade_hint', help_text.texts()['subfield.shade_free'].short)
    if not flush:
        s.section('pitch', _('Row pitch'), 'subfield.pitch')
        s.choice('params.pitch_mode', pgettext('rows', 'Pitch'), params.pitch_mode, pitch_mode_names())
        if raw.pitch_mode == 'value':
            s.num('params.pitch', pgettext('rows', 'Pitch'), params.pitch or 3., .5, 30, 'm', step=.05)
        elif raw.pitch_mode == 'gcr':
            s.num('params.gcr', _('Ratio'), params.gcr, .1, 1., step=.01)
        elif raw.pitch_mode == 'sun':
            s.note('sun_source', _("This sub-field's own") if 'window' in sf.params else _('Project default'), help='subfield.sun_window')
            for key, label, low, high, unit, decimals, step in [
                ('day', _('Day'), 1, 31, '', 0, 1), ('month', _('Month'), 1, 12, '', 0, 1),
                ('start', _('From (solar time)'), 0, 24, 'h', 1, .5), ('end', _('To (solar time)'), 0, 24, 'h', 1, .5)]:
                s.num('window.' + key, label, getattr(params.window, key), low, high, unit, decimals, step, help='subfield.sun_window')
                if key == 'month':
                    s.current['fields'][-1]['inlineWith'] = 'window.day'
            s.action('sun_all', _('Use for all sub-fields'))
            s.note('sun_note', _('No row shades the next one on that day between those hours. The standards leave this choice to the designer.'))
    s.outline(sf.ring)
    s.section('defaults_own', _('Defaults for the next sub-fields'), 'subfield')
    s.action('defaults_take', _('Use as defaults'),
             tip=_('The next sub-fields start from the module and the layout of this one.'))
    s.action('defaults_apply', _('Apply the defaults'),
             tip=_('This sub-field takes the module and the layout of the defaults; Undo brings it back.'))
    s.section('layout', '', framed=False)
    if sf.manual and sf.filled:
        s.action('relayout', _('Lay again automatically'))
    else:
        s.action('fill', _('Lay again') if sf.filled else _('Lay the modules'))
    if sf.filled:
        s.action('empty', _('Take them out'), inlineWith='relayout' if sf.manual else 'fill')
    state = session.layout_state(sf)
    if state == 'stale':
        s.note('state', _('To lay out again: the layout is on its way, the figures below are the previous ones.'))
    elif state == 'error':
        s.note('state', _('The layout failed: {why}').format(why=error))
    if result is not None and sf.filled:
        s.note('summary', ngettext('<b>{n} module</b>, Po,cc {kw} kW', '<b>{n} modules</b>, Po,cc {kw} kW', result.count).format(
            n=result.count, kw=number(result.count * p.module_of(sf).power_kw)).replace('<b>', '').replace('</b>', ''))
        s.note('orientation', _('azimuth {a}°, tilt {t}°').format(a=number(result.azimuth, 1, sign=True), t=number(result.tilt, 1)))
        if params.mounting not in layout.FLUSH:
            s.note('pitch_summary', _('row pitch {p} m, clear gap {g} m, limit angle {l}°').format(
                p=number(result.pitch), g=number(result.clearance), l=number(result.limit_angle, 1)))
        if result.groups:
            s.note('groups', ngettext('{n} fire-brigade group', '{n} fire-brigade groups', len(result.groups)).format(n=len(result.groups)))
        if getattr(result, 'manual', False):
            count = sum(bool(row.places) for row in result.rows)
            s.note('manual', ngettext('Rows by hand: {n} row, kept as it is; the pitch and the rules are checked, not applied',
                'Rows by hand: {n} rows, kept as they are; the pitch and the rules are checked, not applied', count).format(n=count))
        for i, note in enumerate(result.notes):
            s.note(f'layout_note.{i}', _(note))


def exclusion_schema(s, e):
    s.section('exclusion', _('Exclusion'), 'exclusion')
    s.choice('kind', _('Kind'), e.kind, model.exclusion_names())
    s.num('clearance', _('Extra clearance'), e.clearance, 0, 10, 'm')
    s.num('height', _('Height'), e.obstacle_height(), 0, 60, 'm',
          tip=_('How high it rises above the roof (or the ground): it casts shadows on the modules'))
    s.section('exclusion_notes', '', framed=False)
    if e.height is None:
        s.note('default', _('Height: the default for this kind, indicative; measure it on the site.'))
    else:
        s.action('default_height', _('Use the default height of this kind'))
    s.note('fire_note', _('Smoke vents, openings and roof plant get 1 m more by themselves where the fire-brigade rules apply '
                         '(DCPREV 14030/2025, 3.3.5.1).'))
    s.outline(e.ring)


def prop_schema(s, x):
    s.section('prop', _('3D object'), framed=False)
    family, measures = props.family(x.kind), x.measures()
    s.choice('kind', _('Kind'), x.kind, model.prop_names())
    from .models3d import ASSET_FOR_KIND, choices           # R374, R376: the model drawn, where the kind has more
    models = choices(x.kind)
    if len(models) > 1:
        s.choice('asset', _('Model'), x.asset if any(k == x.asset for k, _n in models) else ASSET_FOR_KIND.get(x.kind), models)
    s.num('height', _('Height'), measures['height'], .05, 100, 'm')
    if family == 'tree':
        s.num('width', _('Crown diameter'), measures['crown_diameter'], .05, 60, 'm')
        if x.kind == 'hedge':
            s.num('length', _('Length'), measures['length'], .1, 200, 'm', step=.5)
    elif family in ('obstacle', 'car', 'site'):
        if family == 'car':
            s.num('length', _('Length'), measures['length'], .05, 100, 'm')
        s.num('width', _('Thickness') if x.kind == 'fence' else _('Width'), measures['width'], .05, 100, 'm')
        if family in ('obstacle', 'site') and x.path is None:
            s.num('length', _('Depth'), measures['depth'], .05, 100, 'm')
    s.num('rotation', _('Rotation'), x.rotation, -360, 360, '°', 1, 15)
    if x.kind == 'walkway':
        s.check('railing', _('With railing'), x.railing)
    if any(v is not None for v in (x.height, x.width, x.length)):
        s.action('default_measures', _('Use the default measures'))
    else:
        s.note('default', _('Measures: the defaults for this kind, indicative; measure them on the site.'))
    s.note('shadow', _('It casts its shadow on the modules in the calculation.') if x.casts_shadow() else
           _('A person is drawn for scale: it casts no shadow in the calculation.') if family == 'person' else
           _('It is drawn for the picture: it casts no shadow in the calculation.'))


def defaults_values(p):
    """What the defaults of the next sub-fields hold, field by field (R523): their own values over layout.Params's,
    the alignment of a sub-field drawn now, the project's design window unless the defaults have their own."""
    raw = p.default_params()
    values = layout.Params()
    for key, value in raw.items():
        if key == 'window':
            values.window = sun.DesignWindow(**value)
        elif hasattr(values, key):
            setattr(values, key, value)
    if 'alignment' not in raw:
        values.alignment = layout.NEW_ALIGNMENT
    if 'window' not in raw:
        values.window = sun.DesignWindow(**p.sun_window)
    return raw, values


def defaults_schema(s, session):
    """The layout the next sub-fields start from (R523, Daniel 07/11/2026: «se non ci sono stringhe selezionate allora
    lì si selezionano le impostazioni che valgono nelle stringature successive»): the fields of a sub-field that are
    chosen before drawing, with the commands that keep them in the profile or bring back the program's."""
    p = session.project
    raw, params = defaults_values(p)
    s.section('defaults', _('Mounting and module'), 'subfield')      # the panel's heading says what they are
    s.note('defaults_hint', _('No sub-field is selected: these settings hold for the sub-fields you draw from now on, '
                              'for «Fill an area» and for «A sub-field on each pitch». The sub-fields already drawn '
                              'do not change; select one to change it.'))
    s.choice('params.mounting', _('Mounting'), raw.get('mounting', ''),
             [('', _('As the surface'))] + list(mounting_names().items()), help='subfield.mounting',
             tip=_('As the surface: coplanar on a sloping pitch, tilted rows on a flat roof, rows on the ground.'))
    s.choice('module', _('Module'), p.default_module(),
             [(k, f"{m['manufacturer']} {m['model']}") for k, m in p.modules.items()])
    s.choice('params.portrait', _('Orientation'), params.portrait, [(True, _('Portrait')), (False, _('Landscape'))])
    s.num('params.stack', _('Modules per table, across'), params.stack, 1, 6, decimals=0, step=1, help='subfield.stack')
    s.num('params.tilt', _('Module tilt'), params.tilt, 0, 60, '°', 1, 1,
          tip=_("Of the tilted rows, the east-west pairs, the ground rows and the canopies: the coplanar modules "
                "take the pitch's."))
    s.num('params.azimuth', _('Azimuth (from South, + West)'), params.azimuth or 0., -180, 180, '°', 1, 1,
          enabled=params.azimuth is not None, tip=_('Uncheck «Automatic» to enter the azimuth.'))
    s.check('automatic', _('Automatic'), params.azimuth is None, inlineWith='params.azimuth')
    s.choice('params.alignment', _('Alignment'), params.alignment, alignment_names(params.alignment))
    s.num('params.target_kwp', _('Power asked'), params.target_kwp, 0, 1e6, 'kWp', step=1., special=_('as many as fit'),
          tip=_('Each sub-field drawn from now on lays only the modules of this power.'))
    if params.target_kwp > 0:
        s.choice('params.target_from', _('Rows taken'), params.target_from, target_from_names())
        s.note('target_rule', target_rule(params.target_from))
    s.section('defaults_gaps', _('Gaps and margins'), 'subfield.gaps')
    s.num('params.gap', _('Between modules'), params.gap, 0, 1., 'm', step=.01)
    s.num('params.flush_row_gap', _('Between rows'), params.flush_row_gap, 0, 2, 'm', step=.01, help='subfield.row_gap',
          tip=_('Of the coplanar and integrated mountings and of the canopies.'))
    s.num('params.edge', _('From the edge of the area'), params.edge, 0, 20., 'm', step=.1, help='subfield.edge',
          tip=_('Of the areas laid automatically («Fill an area»): a sub-field drawn as modules has no band inside it.'))
    s.num('params.table_modules', _('Modules per table, along'), params.table_modules, 0, 200, decimals=0, step=1,
          special=_('continuous rows'))
    s.num('params.table_gap', _('Between tables'), params.table_gap, 0, 5, 'm', step=.05)
    s.check('params.shade_free', _("Out of the obstacles' shadows"), params.shade_free, help='subfield.shade_free')
    s.section('defaults_pitch', _('Row pitch'), 'subfield.pitch')
    s.choice('params.pitch_mode', pgettext('rows', 'Pitch'), params.pitch_mode, pitch_mode_names())
    if params.pitch_mode == 'value':
        s.num('params.pitch', pgettext('rows', 'Pitch'), params.pitch or 3., .5, 30, 'm', step=.05)
    elif params.pitch_mode == 'gcr':
        s.num('params.gcr', _('Ratio'), params.gcr, .1, 1., step=.01)
    else:
        s.note('sun_source', _('Their own') if 'window' in raw else _('Project default'), help='subfield.sun_window')
        for key, label, low, high, unit, decimals, step in [
                ('day', _('Day'), 1, 31, '', 0, 1), ('month', _('Month'), 1, 12, '', 0, 1),
                ('start', _('From (solar time)'), 0, 24, 'h', 1, .5), ('end', _('To (solar time)'), 0, 24, 'h', 1, .5)]:
            s.num('window.' + key, label, getattr(params.window, key), low, high, unit, decimals, step,
                  help='subfield.sun_window')
            if key == 'month':
                s.current['fields'][-1]['inlineWith'] = 'window.day'
    s.section('defaults_fire', _('Fire brigade'), 'subfield')
    s.check('fire_bands', _('Add the 1 m bands as obstacles on the subject buildings'),
            p.layout_defaults.get('fire_bands') is True,
            tip=_('When a sub-field is drawn on a building subject to the fire-brigade rules, the free band of 1 m '
                  'along its roof edges (DCPREV 14030, 3.3.5.1 point 2) is added first, if it is not there.'))
    s.section('defaults_keep', '', framed=False)
    s.action('defaults_profile', _('Keep in the profile'), tip=_('A new project starts from these defaults.'))
    s.action('defaults_reset', _("Back to the program's"),
             enabled=bool(p.layout_defaults))


def build_schema(session, kind, obj):
    s = Schema()
    if kind == 'defaults':
        defaults_schema(s, session)
        return s.sections
    if kind == 'building':
        building_schema(s, obj, session.project)
    elif kind == 'subfield':
        subfield_schema(s, session, obj)
    elif kind == 'exclusion':
        exclusion_schema(s, obj)
    elif kind == 'prop':
        prop_schema(s, obj)
    else:
        site_schema(s, session.project)
    return s.sections
