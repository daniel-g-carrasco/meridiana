"""Result inspectors: the fields and defaults of ui/energy_pages, without Widgets."""
from meridiana.core.energy import system
from meridiana.gui.backend.profiles import registry as profiles
from meridiana.core.energy.simulate import Losses, thermal_names
from meridiana.core.model.settings import LID_FALLBACK
from meridiana.i18n import _, number
from .properties_schema import Schema


def production(editor):
    p = editor.session.project
    s = Schema(profile_id=p.regulatory_profile)
    e = p.energy
    losses = Losses.from_dict(e.get('losses'))
    s.section('arrays', _('Arrays (the modules laid, by orientation)'))
    arrays = system.arrays_of(p, editor.session.good_results())
    if not arrays:
        s.note('no_modules', _('No module laid yet.'))
    for i, a in enumerate(arrays):
        s.note(f'array_{i}', a.name + '\n' + _('{n} modules · {kwp} kWp · tilt {tilt}° · azimuth {az}°').format(
            n=a.modules, kwp=number(a.p_stc / 1000, 2), tilt=number(a.tilt, 1), az=number(a.azimuth, 1)))
    s.note('thermal_intro', _("Cooling of the modules' back (thermal model):"))
    seen = set()
    for a in arrays:
        sfid = a.key.split('.')[0]
        if sfid not in seen:
            seen.add(sfid)
            s.choice('thermal.' + sfid, a.name, a.thermal, thermal_names())
    s.section('inverter', _('Inverter'), framed=False)
    # window.py installs LazyReference: the legacy fields are hidden in the real window.
    s.note('inverters', _('Plant: {what}').format(what=system.describe(e)))
    s.action('phase_plant', _('Go to the Plant'))
    s.section('losses', _('Losses'), 'production.losses')
    s.choice('losses.transposition', _('Transposition model'), losses.transposition,
             [('perez', 'Perez 1990'), ('haydavies', 'Hay e Davies'), ('isotropic', _('isotropic'))])
    for key, label, lo, hi, dec, unit in (
        ('albedo', _('Ground reflectance (albedo)'), 0, 1, 2, ''),
        ('soiling', _('Soiling'), 0, 20, 1, '%'), ('quality', _('Module quality'), -5, 5, 1, '%'),
        ('mismatch', _('Mismatch'), 0, 10, 1, '%'), ('dc_wiring', _('DC wiring at STC'), 0, 10, 1, '%'),
        ('ac_wiring', _('AC wiring at nominal power'), 0, 10, 1, '%'),
        ('unavailability', _('Unavailability'), 0, 20, 1, '%'),
        ('iam_b0', _('ASHRAE b0 (reflection)'), 0, .2, 3, ''),
    ):
        s.num('losses.' + key, label, getattr(losses, key), lo, hi, unit, dec, .1 if dec <= 1 else .01)
    s.check('lid_auto', _("LID from the module's datasheet"), losses.lid is None)
    s.num('losses.lid', _('Light-induced degradation'), losses.lid if losses.lid is not None else LID_FALLBACK,
          0, 10, '%', 1, .1, enabled=losses.lid is not None)
    s.check('losses.use_horizon', _('Shading of the far horizon'), losses.use_horizon)
    s.check('losses.use_near', _('Shading of the obstacles of the scene'), losses.use_near)
    return s


def consumption(editor, *, profile_id: str = "it"):
    from types import SimpleNamespace
    s = Schema(profile_id=editor.session.project.regulatory_profile)
    profiles.get(editor.session.project.regulatory_profile).append_chart_fields("consumption", SimpleNamespace(editor=editor, schema=s))
    return s

def economics(editor, *, profile_id: str = "it"):
    from types import SimpleNamespace
    s = Schema(profile_id=editor.session.project.regulatory_profile)
    profiles.get(editor.session.project.regulatory_profile).append_chart_fields("economics", SimpleNamespace(editor=editor, schema=s))
    return s

def build(editor):
    schema = {'production': production, 'consumption': consumption, 'economics': economics}[editor.phase](editor)
    schema.section('compute', '', framed=False)
    schema.action('compute', _('Compute'))
    return schema.sections
