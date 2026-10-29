"""The designer's local catalogue, explicitly reviewed and saved without changing shipped data."""
from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from pathlib import Path

from ..paths import Paths
from ..i18n import _

REQUIRED = {
    'modules': ('pmax', 'vmp', 'imp', 'voc', 'isc', 'length', 'width'),
    'inverters': ('ac_power_nominal_w',),
    'microinverters': ('ac_power_nominal_w',),
    'optimizers': ('rated_input_power_w',),
    'batteries': ('usable_energy_kwh',),
}


def location() -> Path:
    return Paths.from_env().data / 'catalog' / 'personal.json'


def _numeric_tree(value):
    """Ratings tables contain positive finite numbers under numeric selector keys."""
    if isinstance(value, dict):
        return bool(value) and all(str(key).isdigit() and int(key) > 0 and _numeric_tree(item)
                                   for key, item in value.items())
    if isinstance(value, list):
        return bool(value) and all(_numeric_tree(item) for item in value)
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def validate(kind: str, record: dict) -> dict:
    if kind not in REQUIRED or not isinstance(record, dict):
        raise ValueError(_('Unknown product kind or invalid record.'))
    out = json.loads(json.dumps(record, allow_nan=False))
    for key in ('manufacturer', 'model', 'datasheet_url'):
        if not isinstance(out.get(key), str) or not out[key].strip():
            raise ValueError(_('Required field: {field}').format(field=key))
        out[key] = out[key].strip()
    for key in REQUIRED[kind]:
        value = out.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(_('A positive stated value is required: {field}').format(field=key))
    if kind == 'modules' and (out['voc'] < out['vmp'] or out['isc'] < out['imp']):
        raise ValueError(_('Voc and Isc must not be smaller than Vmp and Imp.'))
    # Optional ratings still need a real finite number, not a word the model guessed.
    from .audit import unit_of, audit_record
    for key, value in out.items():
        numeric = bool(unit_of(key)) or key in ('gamma_pmax', 'beta_voc', 'alpha_isc', 'bifaciality',
                                                'first_year_loss', 'yearly_loss', 'noct')
        if value is not None and numeric:
            if key == 'voltage_range_by_phases_v':
                if not isinstance(value, dict) or not value or any(
                        str(phase) not in ('1', '3') or not isinstance(bounds, list) or len(bounds) != 2
                        or not _numeric_tree(bounds) or bounds[0] >= bounds[1]
                        for phase, bounds in value.items()):
                    raise ValueError(_('Invalid voltage range: {field}').format(field=key))
                continue
            if key in ('dc_current_max_per_mppt_a', 'dc_isc_max_per_mppt_a',
                       'dc_current_max_per_mppt_by_strings_a', 'dimensions_mm'):
                if not isinstance(value, list) or not _numeric_tree(value):
                    raise ValueError(_('Invalid numeric list: {field}').format(field=key))
                continue
            if key in ('voltage_range_v', 'battery_voltage_range_v', 'power_classes_w') and isinstance(value, list):
                if not value or any(isinstance(v, bool) or not isinstance(v, (int, float))
                                    or not math.isfinite(v) or v <= 0 for v in value):
                    raise ValueError(_('Invalid numeric list: {field}').format(field=key))
                if key.endswith('range_v') and (len(value) != 2 or value[0] > value[1]):
                    raise ValueError(_('Invalid voltage range: {field}').format(field=key))
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(_('A stated numeric value is required: {field}').format(field=key))
    # Imported anchors retain where the value came from, never the authority of
    # a previous verification after personal edits or an AI verification claim.
    anchors = out.get('field_sources')
    if anchors is not None:
        if not isinstance(anchors, dict) or any(not isinstance(anchor, dict) for anchor in anchors.values()):
            raise ValueError(_('Unknown product kind or invalid record.'))
        for anchor in anchors.values():
            anchor.pop('verified', None)
            anchor['status'] = 'unverified_personal'
    issues = audit_record(out, kind)["issues"]
    if issues:
        raise ValueError(_('Inconsistent product data: {issues}').format(issues="; ".join(issues)))
    out['source'], out['kind'] = 'personal', kind
    identity = f"{kind}:{out['manufacturer']}:{out['model']}"
    out['id'] = 'personal:' + hashlib.sha256(identity.casefold().encode()).hexdigest()[:20]
    return out


def _read(path: Path) -> list:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError(_('The personal catalogue is not a list.'))
    return data


def load(kind: str, *, path=None) -> list:
    return [validate(kind, row) for row in _read(Path(path) if path else location()) if row.get('kind') == kind]


def save(kind: str, record: dict, *, path=None) -> dict:
    """Add a new reviewed product atomically; an existing model is never overwritten."""
    row = validate(kind, record)
    path = Path(path) if path else location()
    rows = _read(path)
    if any(r.get('id') == row['id'] for r in rows):
        raise ValueError(_('This model already exists. Use a distinct model or revision name.'))
    rows.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='personal-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(rows, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    from . import load as catalog_load
    catalog_load.cache_clear()
    return row
