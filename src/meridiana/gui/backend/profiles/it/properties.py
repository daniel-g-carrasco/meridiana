"""Italian property fields, preserved in their original order."""
from meridiana.core.rules import rules
from meridiana.core.rules import vvf_activities as vvf
from meridiana.i18n import _, ngettext

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


def site(s, p, obj, session):
    s.section('network', _('Grid connection (optional)'), 'site.network')
    n = p.network
    for key, label in [('distributor', _('Distributor')), ('pod', 'POD')]:
        s.field('network.' + key, label, getattr(n, key))
    s.num('network.voltage_v', _('Supply voltage'), n.voltage_v, 0, 1000000, 'V', 0, 1, special=_('not stated'))
    s.field('technical_rule', _('Technical rule from voltage'), n.technical_rule(profile_id=p.regulatory_profile), 'read')
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


def building(s, p, obj, session):
    b = obj
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


def defaults(s, p, obj, session):
    s.section('defaults_fire', _('Fire brigade'), 'subfield')
    s.check('fire_bands', _('Add the 1 m bands as obstacles on the subject buildings'),
            p.layout_defaults.get('fire_bands') is True,
            tip=_('When a sub-field is drawn on a building subject to the fire-brigade rules, the free band of 1 m '
                  'along its roof edges (DCPREV 14030, 3.3.5.1 point 2) is added first, if it is not there.'))


def exclusion(s, p, obj, session):
    s.note('fire_note', _('Smoke vents, openings and roof plant get 1 m more by themselves where the fire-brigade rules apply '
                         '(DCPREV 14030/2025, 3.3.5.1).'))


def subfield_groups(s, p, obj, session):
    result = obj
    if result.groups:
        s.note('groups', ngettext('{n} fire-brigade group', '{n} fire-brigade groups', len(result.groups)).format(n=len(result.groups)))

