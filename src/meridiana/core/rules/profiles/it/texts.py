"""Unchanged Italian layout messages."""
from meridiana.i18n import N_

BALLAST_WARNING = N_("Ballast alone is not a restraint on a roof slab (NTC 2018 7.2.4, recalled by CEI 82-25/3 6.2): "
                     "anchors or tie-downs are needed.")


from meridiana.i18n import _


def text(key):
    return {
        "exclusion_band": _("Free band (DCPREV 14030)"),
        'azimuth_label': _('azimuth from South, + West (CEI 82-25/1)'),
        'transposition_reference': _('Transposition: {model} (pvlib.irradiance). Irradiation terms: CEI 82-25/1:2026, 3.2.1.15-18, p. 13-14'),

        'manual_edge_0': _('Modules keep away from an exclusion and its clearance (1 m more for smoke vents, openings and roof plant under the fire-brigade rules). Move the rows, take the modules out, or lay the sub-field again automatically.'),
        'manual_edge_1': _('The modules stay 1 m from the roof edge under the fire-brigade rules (DCPREV 14030 of 01/09/2025, 3.3.5.1 point 2): a guide the designer may go over, his call. Move the side or take the modules out.'),
        'manual_edge_2': _('The modules stay inside the edge band of the sub-field (1 m from the roof edge under the fire-brigade rules). Move the rows inwards, or lay the sub-field again automatically.'),
    }[key]
