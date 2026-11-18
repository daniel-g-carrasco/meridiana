"""Quick catalogue adapter. No project or user-profile writes are implicit.

Launcher contract: create_page(engine, session=None) installs ``catalogBackend``
and returns it; load PAGE_URL in a QQuickView, or use CatalogPage as an Item.
``chosen(kind, record)`` transfers a deep copy to the caller. The caller owns
project edits. ``importRequested(kind)`` delegates PVsyst file selection.
"""
from __future__ import annotations

import copy
import json
import math
from collections import Counter
from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import (QAbstractListModel, QObject, Property, QRunnable,
                            Qt, QThreadPool, QTimer, QUrl, Signal, Slot)
from PySide6.QtGui import QDesktopServices

from meridiana import catalog
from meridiana.catalog import compat, personal, schema
from meridiana.catalog.audit import audit_record, unit_of
from meridiana.i18n import number
from meridiana.quick.backend.catalog_i18n import _, field_label

PAGE_URL = QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] /
                                  'qml/Meridiana/Catalog/CatalogPage.qml'))
_DEFAULT = dict(text='', source='', manufacturer='', low=0, high=0, family='', bifacial='',
                efficiency_min=0, length_max=0, market='', state='', fitting='')
_REMEMBERED = {}
STATE_COLUMN = '__state'
HIDDEN_NAMES = 4      # models named in the line of what the filters hide
EUROPE = 'europe'       # the market filter's default: what is sold for a European grid (R-US, Daniel 05/11/2026)


def labels():
    """Static gettext strings shared by records and the editor, without Widgets."""
    return dict(manufacturer=_("Manufacturer"), model=_("Model"), series=_("Series"),
                source=_("Origin"), cell_family=_("Cell family"), pmax=_("Power at STC (W)"),
                length=_("Length (m)"), width=_("Width (m)"), efficiency_pct=_("Efficiency (%)"),
                bifacial=_("Bifacial"), bifaciality=_("Bifaciality (%)"),
                gamma_pmax=_("γ Pmax (%/K)"), beta_voc=_("β Voc (%/K)"), alpha_isc=_("α Isc (%/K)"),
                ac_power_nominal_w=_("Nominal AC power (W)"), dc_voltage_max_v=_("Maximum DC voltage (V)"),
                mppt_voltage_min_v=_("MPPT from (V)"), mppt_voltage_max_v=_("MPPT to (V)"),
                mppt_count=_("MPPT"), phases=_("Phases"), technology=_("Technology"),
                usable_energy_kwh=_("Usable energy (kWh)"), nominal_energy_kwh=_("Nominal energy (kWh)"),
                rated_input_power_w=_("Rated input power (W)"), voltage_class=_("Voltage class"),
                modules_per_unit=_("Modules per unit"), notes=_("Notes"), chemistry=_("Chemistry"),
                datasheet_url=_("Source document or URL"), retrieved=_("Read on"),
                max_input_voltage_v=_("Maximum input voltage (V)"),
                max_input_isc_a=_("Maximum input Isc (A)"),
                max_output_current_a=_("Maximum output current (A)"),
                max_charge_power_w=_("Maximum charge power (W)"),
                max_discharge_power_w=_("Maximum discharge power (W)"),
                round_trip_efficiency_pct=_("Round-trip efficiency (%)"),
                depth_of_discharge_pct=_("Depth of discharge (%)"),
                warranty_years=_("Warranty (years)"), weight_kg=_("Weight (kg)"),
                vmp='Vmp (V)', imp='Imp (A)', voc='Voc (V)', isc='Isc (A)')


def display(value):
    if value is None or value == '' or value == []:
        return _("Unknown")
    if isinstance(value, bool):
        return _("yes") if value else _("no")
    if isinstance(value, (float, int)):
        return number(value, 3 if abs(value) < 10 else 1)
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def display_field(record, key):
    value = record.get(key)
    if key == 'source':
        return next((o['text'] for o in options()['origins'] if o['key'] == value), display(value))
    if key == 'cell_family':
        return next((o['text'] for o in options()['families'] if o['key'] == value), display(value))
    text = display(value)
    if key == 'efficiency_pct' and record.get('efficiency_derived'):
        text += ' (' + _("worked out from power and size") + ')'
    if key == 'bifaciality_estimated' and value:
        text += ' (' + _("estimated from the cell family, not on the datasheet") + ')'
    return text


def lifecycle_text(record):
    """The state of a product in words, with its date and source: what the row and the card say, never only a colour."""
    state = catalog.lifecycle_state(record)
    words = {catalog.CURRENT: _("Current"), catalog.PHASING_OUT: _("Phasing out"),
             catalog.DISCONTINUED: _("Out of production"), catalog.UNKNOWN: _("State unknown")}[state]
    return words


def lifecycle_detail(record):
    life = record.get('lifecycle') if isinstance(record.get('lifecycle'), dict) else {}
    if record.get('source') == 'cec':
        return _("From the CEC list: no word on whether it is still made.")
    if not life:
        return _("No written source read on whether it is still made.")
    lines = [_("Checked on {date}: {url}").format(date=life.get('checked', ''), url=life.get('url', ''))]
    if life.get('text'):
        lines.append(_("Read there: «{text}»").format(text=life['text']))
    if life.get('note'):
        lines.append(_(life['note']))
    if life.get('replacement'):
        lines.append(_("In its place: {model}").format(model=life['replacement']))
    return '\n'.join(lines)


def options():
    return {
        'states': [dict(key=k, text=t) for k, t in (
            ('current', _("Current, verified")), ('phasing_out', _("Phasing out")),
            ('discontinued', _("Out of production")), ('unknown', _("State unknown")), ('', _("Any state")))],
        'markets': [dict(key=k, text=t) for k, t in (
            (EUROPE, _("For Europe (230/400 V)")), ('US', _("USA (208/240/277/480 V)")), ('', _("Any market")))],
        'kinds': [dict(key=k, text=t) for k, t in zip(catalog.KINDS, (
            _("PV modules"), _("Inverters"), _("Microinverters"), _("Optimizers"), _("Batteries")), strict=True)],
        'origins': [dict(key=k, text=t) for k, t in (
            ('', _("All")), ('curated', _("Datasheets read for Meridiana")),
            ('cec', _("CEC list (USA)")), ('personal', _("Personal catalogue")))],
        'families': [dict(key=k, text=t) for k, t in (
            ('', _("Any cell")), ('topcon', _("TOPCon")), ('hjt', _("HJT (heterojunction)")),
            ('back_contact', _("Back contact")), ('perc', _("PERC")), ('thin_film', _("Thin film")),
            ('poly', _("Polycrystalline")), ('mono', _("Monocrystalline, cell not stated")),
            ('unknown', _("Cell not stated")))],
        'bifacial': [dict(key=k, text=t) for k, t in (
            ('', _("Monofacial and bifacial")), ('yes', _("Bifacial only")), ('no', _("Monofacial only")))]}


def _in_market(row, market):
    """Whether a row is for a market. Europe: a row whose `markets` say EU, IT or global; the designer's own rows always
    (he knows where he sells them); a row that says nothing is taken as not for Europe only when it is from the CEC list."""
    markets = row.get('markets') or []
    if market != EUROPE:
        return market in markets
    if row.get('source') == 'personal':
        return True
    return bool(set(markets) & {'EU', 'IT', 'global'}) or (not markets and row.get('source') != 'cec')


def _verdicts(kind, records, context):
    """The verdict of every row for the context, on a worker: one check for the five kinds (catalog.compat). The CEC's rows
    are not judged: there are twenty-one thousand, they stay hidden by the market's filter, and their limits are mostly
    missing; shown, they are unknown."""
    if not context:
        return {}
    return {r.get('id'): compat.check(kind, r, context).as_dict() for r in records if r.get('source') != 'cec'}


def _search(records, kind, filters, sort, descending):
    words = filters['text'].casefold().split()
    result = []
    for row in records:
        haystack = ' '.join(str(row.get(k) or '') for k in ('manufacturer', 'model', 'series')).casefold()
        if any(word not in haystack for word in words):
            continue
        if any(filters[key] and str(row.get(key, '')).casefold() != str(filters[key]).casefold()
               for key in ('source', 'manufacturer')):
            continue
        power = catalog.power_of(row, kind)
        if filters['low'] and power < filters['low'] or filters['high'] and power > filters['high']:
            continue
        if filters['market'] and not _in_market(row, filters['market']):
            continue
        if filters['state'] and catalog.lifecycle_state(row) != filters['state']:
            continue
        if kind == 'modules':
            if filters['family'] and row.get('cell_family') != filters['family']:
                continue
            if filters['bifacial'] and bool(row.get('bifacial')) != (filters['bifacial'] == 'yes'):
                continue
            if filters['efficiency_min'] and (row.get('efficiency_pct') or 0) < filters['efficiency_min']:
                continue
            if filters['length_max'] and (not row.get('length') or row['length'] > filters['length_max']):
                continue
        result.append(row)
    return catalog.sorted_by(result, catalog.family_rank if sort == 'cell_family' else sort, descending) if sort else result


def grouped(rows, kind, expanded, narrowed=False):
    """The rows as the list shows them: a family of two or more rows is one row with the range of its powers, followed
    by its members when it is open; a search that leaves one member shows that member, plainly. The order is the order
    of the search: a family stands where its first member stands. What makes a family: catalog.family_key."""
    members = {}
    for row in rows:
        key = catalog.family_key(row, kind)
        if key:
            members.setdefault(key, []).append(row)
    out, seen = [], set()
    for row in rows:
        key = catalog.family_key(row, kind)
        if not key or len(members[key]) < 2:
            out.append(row)
        elif key not in seen:
            seen.add(key)
            family = members[key]
            central = catalog.central_class(family, kind)
            powers = sorted(catalog.power_of(r, kind) for r in family)
            head = {'id': 'family:' + key, 'family_row': True, 'family': key, 'members': family, 'central': central.get('id'),
                    'manufacturer': central.get('manufacturer'), 'model': catalog.family_name(family),
                    'source': central.get('source'), 'cell_family': central.get('cell_family'),
                    'phases': central.get('phases'), 'range': (powers[0], powers[-1]), 'lifecycle': central.get('lifecycle')}
            out.append(head)
            if key in expanded or narrowed:
                ordered = sorted(family, key=lambda r: catalog.power_of(r, kind))
                out.extend(dict(r, member_of=key) for r in ordered)
                for power in central.get('unread_classes') or []:
                    out.append({'id': f'unread:{key}:{power:g}', 'unread_class': True, 'member_of': key,
                                'manufacturer': central.get('manufacturer'),
                                'model': catalog.class_model(central, power), 'pmax': power, 'source': central.get('source'),
                                'lifecycle': central.get('lifecycle')})
    return out


class CatalogListModel(QAbstractListModel):
    """One row per product or family; only visible delegates request formatted cells."""
    CellsRole = Qt.ItemDataRole.UserRole + 1
    IdentityRole = CellsRole + 1
    SelectedRole = IdentityRole + 1
    KindRole = SelectedRole + 1     # "", "family", "member" or "unread"
    OpenRole = KindRole + 1
    StateRole = OpenRole + 1        # the lifecycle in words
    StateKeyRole = StateRole + 1
    FitRole = StateKeyRole + 1      # "ok", "no" or "unknown"
    WhyRole = FitRole + 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self.keys = []
        self.selection = set()
        self.expanded = set()
        self.verdicts = {}

    def rowCount(self, parent=None):
        return 0 if parent is not None and parent.isValid() else len(self.rows)

    def roleNames(self):
        return {self.CellsRole: b'cells', self.IdentityRole: b'identity', self.SelectedRole: b'selected',
                self.KindRole: b'rowKind', self.OpenRole: b'open', self.StateRole: b'stateText',
                self.StateKeyRole: b'stateKey', self.FitRole: b'fit', self.WhyRole: b'why'}

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.rows):
            return None
        row = self.rows[index.row()]
        if role == self.IdentityRole:
            return str(row.get('id', index.row()))
        if role == self.SelectedRole:
            if row.get('family_row'):
                return row.get('central') in self.selection and row.get('family') not in self.expanded
            return row.get('id') in self.selection
        if role == self.KindRole:
            return 'family' if row.get('family_row') else 'unread' if row.get('unread_class') else 'member' if row.get('member_of') else ''
        if role == self.OpenRole:
            return row.get('family') in self.expanded
        if role == self.StateRole:
            return lifecycle_text(row)
        if role == self.StateKeyRole:
            return catalog.lifecycle_state(row)
        if role == self.FitRole:
            return self._verdict(row).get('state', 'unknown')
        if role == self.WhyRole:
            if row.get('unread_class'):
                return _(catalog.UNREAD_CLASS)
            return '; '.join(self._verdict(row).get('reasons', [])[:2])
        if role == self.CellsRole:
            origins = {o['key']: o['text'] for o in options()['origins']}
            families = {o['key']: o['text'] for o in options()['families']}

            def cell(k):
                if k == STATE_COLUMN:
                    return lifecycle_text(row)
                if row.get('family_row') and row.get('range') and len(self.keys) > 2 and k == self.keys[2]:
                    low, high = row['range']
                    return number(low, 0) if low == high else f"{number(low, 0)}–{number(high, 0)}"
                if k == 'source':
                    return origins.get(row.get(k), display(row.get(k)))
                if k == 'cell_family':
                    return families.get(row.get(k), display(row.get(k)))
                if row.get('family_row') and k not in ('manufacturer', 'model') and row.get(k) is None:
                    return ''
                return number(row[k], 0) if isinstance(row.get(k), (int, float)) else display(row.get(k))
            return [cell(k) for k in self.keys]
        return None

    def _verdict(self, row):
        key = row.get('central') if row.get('family_row') else row.get('id')
        return self.verdicts.get(key, {})

    def refresh_row_states(self):
        if self.rows:
            self.dataChanged.emit(self.index(0), self.index(len(self.rows) - 1),
                                  [self.SelectedRole, self.OpenRole, self.FitRole, self.WhyRole])

    def replace(self, rows, keys):
        self.beginResetModel()
        self.rows, self.keys = list(rows), list(keys)
        self.endResetModel()

    def record(self, index):
        return copy.deepcopy(self.rows[index]) if 0 <= index < len(self.rows) else {}

    def set_selection(self, records, notify=True):
        self.selection = {r.get('id') for r in records}
        if notify and self.rows:
            self.dataChanged.emit(self.index(0), self.index(len(self.rows) - 1), [self.SelectedRole])

    def index_of(self, identity):
        return next((n for n, row in enumerate(self.rows) if row.get('id') == identity), -1)


class _Signals(QObject):
    done = Signal(int, object, str)


class _Job(QRunnable):
    def __init__(self, generation, operation):
        super().__init__()
        self.generation, self.operation = generation, operation
        self.signals = _Signals()

    def run(self):
        try:
            value, error = self.operation(), ''
        except Exception as exc:  # Worker boundary; displayed by the page.
            value, error = None, f'{type(exc).__name__}: {exc}'
        self.signals.done.emit(self.generation, value, error)


class CatalogBackend(QObject):
    changed = Signal()
    editorChanged = Signal()
    chosen = Signal(str, 'QVariantMap')
    importRequested = Signal(str)
    saved = Signal('QVariantMap')
    reviewFinished = Signal(str, bool)      # a proposal under review (Meridio's): its id, whether it was saved
    fileRequested = Signal(str)             # "datasheet" or "pvsyst": the page asks the user for a file
    positioned = Signal(int)                # the row to bring into view

    def __init__(self, session=None, parent=None, *, records=None, safe_root=None):
        super().__init__(parent)
        self.session = session
        self._provided = records
        # With no explicit folder the entries go to the personal catalogue the program loads (catalog.personal.location);
        # an explicit folder (the proofs, a test) keeps the old rule of a destination named inside it.
        self._explicit_root = safe_root is not None
        self._safe_root = Path(safe_root or Path.cwd() / 'build/catalog').resolve()
        self._context = {}
        self._current_id = ''
        self._confirm = ''
        self._hidden = {}
        self._review_id = ''
        self._editor_groups = []
        self._editor_checks = []
        self._editor_note = ''
        self._editor_classes = []
        self._editor_proposals = []
        self._anchors = {}
        self._model = CatalogListModel(self)
        self._kind = 'modules'
        self._states = _REMEMBERED if records is None else {}
        # R434: it opens on what is current and sold for Europe (Daniel, 06/11/2026, after R458 voce 7), with «Show all
        # (n)» beside the filters for the rest; each row says its own state, an optimizer hides what does not fit.
        self._initial = dict(_DEFAULT, state='current', market=EUROPE) if records is None else dict(_DEFAULT)
        self._filters = dict(self._states.get('modules', self._initial))
        self._sort, self._descending = '', False
        self._all, self._brands, self._selected = [], [], []
        self._draft, self._editor_fields, self._types = {}, [], {}
        self._extra_json = '{}'
        self._schema = {}
        self._anchor_index = 0
        self._destination, self._error = '', ''
        self._busy, self._editing = False, False
        self._generation = 0
        self._jobs = {}
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(160)
        self._timer.timeout.connect(self._search)
        self._load()

    def dispose(self):
        """Ignore outstanding searches after the owning workbench closes."""
        self._timer.stop()
        self._generation += 1
        self._busy = False

    model = Property(QObject, lambda self: self._model, constant=True)
    kind = Property(str, lambda self: self._kind, notify=changed)
    filters = Property('QVariantMap', lambda self: dict(self._filters), notify=changed)
    brands = Property('QStringList', lambda self: list(self._brands), notify=changed)
    busy = Property(bool, lambda self: self._busy, notify=changed)
    error = Property(str, lambda self: self._error, notify=changed)
    destination = Property(str, lambda self: self._destination, notify=changed)
    destinationFolder = Property(str, lambda self: str(self._safe_root), constant=True)
    editing = Property(bool, lambda self: self._editing, notify=editorChanged)
    editorFields = Property('QVariantList', lambda self: copy.deepcopy(self._editor_fields), notify=editorChanged)
    editorExtra = Property(str, lambda self: self._extra_json, notify=editorChanged)
    selectedRecord = Property('QVariantMap', lambda self: copy.deepcopy(self._selected[0]) if self._selected else {},
                              notify=changed)
    selectedIds = Property('QStringList', lambda self: [str(r.get('id', '')) for r in self._selected], notify=changed)
    selectedCount = Property(int, lambda self: len(self._selected), notify=changed)
    selectedNames = Property('QStringList', lambda self: [str(r.get('model', '')) for r in self._selected[:4]], notify=changed)
    choices = Property('QVariantMap', lambda self: options(), constant=True)
    def _make_texts(self):
        return {
                'title': _("Catalogue"), 'search': _("Maker, model, series: every word must appear"),
                'clear': _("Clear filters"), 'maker': _("All the makers"), 'choose': _("Choose"),
                'new': _("New personal product"), 'copy': _("Review personal product"), 'save': _("Save"),
                'cancel': _("Cancel"), 'empty': _("No products match these filters."),
                'from': _("Power from"), 'to': _("Power up to"), 'efficiency': _("Efficiency from (%)"),
                'length': _("Length up to (m)"), 'destination': _("Personal catalogue destination (.json)"),
                'note': _("Check every value against the source. Empty values are unknown. "
                          "Saving adds a local catalogue entry; it does not change the project."),
                'json': _("Additional fields (JSON). Units: W, V, A, m, kWh"),
                'import': _("Import PVsyst"), 'details': _("Product details"), 'loading': _("Loading…"),
                'compare': _("Compare up to four selected products."),
                'compareButton': _("Compare selected products"), 'compareClose': _("Close the comparison"),
                'compareHint': _("Select two to four products to compare (Ctrl or Shift)."),
                'cec': _("From the CEC list: a model for the US market, with the values tested "
                         "for the California Energy Commission."),
                'required': _("Required stated value"), 'state': _("State"), 'fitting': _("Only what goes with it"),
                'showAll': _("Show them"), 'showAllTip': _("Also the products out of production, of unknown state, for other markets or "
                "that do not go with it."), 'anyway': _("Use it anyway"), 'keep': _("Go back"), 'open': _("Open the family"),
                'close': _("Close the family"), 'dropTitle': _("Drag the datasheet here, or choose the file"),
                'dropHelp': _("Meridiana reads the PDF on this PC, without sending it anywhere. Nothing is saved before you check it."),
                'chooseFile': _("Choose the datasheet…"), 'importPvsyst': _("Import a .PAN or .OND…"), 'classes': _("Power classes"),
                'classesHelp': _("One row for each class, with its own values from the table of the datasheet."),
                'addClass': _("Add a class"), 'removeClass': _("Remove"), 'fromSheet': _("read on the sheet"),
                'sources': _("Source"), 'required2': _("Required for the calculations"), 'pick': _("Which product of this sheet?"),
                'noSelection': _("Select a product to see its card.")}

    def _texts_kept(self):
        # Read 400 times entering Plant (06/11/2026, R465): sixty translations each read, now once.
        if not hasattr(self, '_texts'):
            self._texts = self._make_texts()
        return self._texts

    texts = Property('QVariantMap', lambda self: self._texts_kept(), constant=True)
    countText = Property(str, lambda self: self._count_text(), notify=changed)
    hiddenText = Property(str, lambda self: self._hidden_text(), notify=changed)
    hiddenCount = Property(int, lambda self: self._hidden_count(), notify=changed)
    showAllText = Property(str, lambda self: self._show_all_text(), notify=changed)
    confirmation = Property(str, lambda self: self._confirm, notify=changed)
    hasContext = Property(bool, lambda self: bool(self._context), notify=changed)
    contextText = Property(str, lambda self: self._context_text(), notify=changed)
    canChoose = Property(bool, lambda self: bool(self._selected) and not self._selected[0].get('unread_class'), notify=changed)
    selectedState = Property('QVariantMap', lambda self: self._selected_state(), notify=changed)
    editorGroups = Property('QVariantList', lambda self: copy.deepcopy(self._editor_groups), notify=editorChanged)
    editorClasses = Property('QVariantList', lambda self: copy.deepcopy(self._editor_classes), notify=editorChanged)
    editorProposals = Property('QVariantList', lambda self: copy.deepcopy(self._editor_proposals), notify=editorChanged)
    editorNote = Property(str, lambda self: self._editor_note, notify=editorChanged)
    checksChanged = Signal()
    editorChecks = Property('QVariantList', lambda self: copy.deepcopy(self._editor_checks), notify=checksChanged)
    needsDestination = Property(bool, lambda self: self._explicit_root, constant=True)

    def _count_text(self):
        rows = self._model.rows
        products = sum(len(r['members']) for r in rows if r.get('family_row')) + sum(
            1 for r in rows if not r.get('family_row') and not r.get('member_of'))
        families = sum(1 for r in rows if r.get('family_row'))
        text = _("{n} products").format(n=number(products, 0, grouping=True))
        return text if not families else text + ' · ' + _("{n} families").format(n=number(families, 0, grouping=True))

    def _hidden_count(self):
        """The products the state, the market and what goes with the context leave out: what «Show all» brings in."""
        return sum(int(self._hidden.get(k, 0) or 0) for k in ('state', 'market', 'fit'))

    def _show_all_text(self):
        count = self._hidden_count()
        return _("Show all ({n})").format(n=number(count, 0, grouping=True)) if count else ''

    def _hidden_text(self):
        """What the filters leave out, said so that it can be found: how many, in which state, which models, and what
        they do not go with (R458 voce 8: «4 in un altro stato» said too little)."""
        parts = []
        state = self._hidden.get('state', 0)
        if state:
            states = self._hidden.get('states') or {}
            words = {catalog.CURRENT: _("current"), catalog.PHASING_OUT: _("phasing out"),
                     catalog.DISCONTINUED: _("out of production"), catalog.UNKNOWN: _("state unknown")}
            detail = ', '.join(f"{number(n, 0, grouping=True)} {words.get(k, k)}" for k, n in states.items() if n)
            text = _("{n} in another state").format(n=number(state, 0, grouping=True))
            parts.append(f"{text} ({detail})" if detail else text)
        unfit = self._hidden.get('fit', 0)
        if unfit:
            what = self._context_text().removeprefix(_("For: {what}").format(what='')).strip()
            parts.append((_("{n} that do not go with {what}").format(n=number(unfit, 0, grouping=True), what=what)
                          if what else _("{n} that do not go with it").format(n=number(unfit, 0, grouping=True))))
        if not parts:
            return ''
        names = [n for n in self._hidden.get('names', []) if n]
        total = state + unfit
        shown = ', '.join(names) + (', …' if total > len(names) else '')
        text = _("Hidden by the filters: {what}").format(what='; '.join(parts))
        return text + (' · ' + _("among them {models}").format(models=shown) if names else '')

    def _context_text(self):
        parts = []
        for key, word in (('module', _("module")), ('inverter', _("inverter")), ('optimizer', _("optimizer"))):
            record = self._context.get(key)
            if record:
                parts.append(f"{word} {record.get('manufacturer', '')} {record.get('model', '')}".strip())
        return _("For: {what}").format(what=', '.join(parts)) if parts else ''

    def _selected_state(self):
        if not self._selected:
            return {}
        row = self._selected[0]
        verdict = self._model.verdicts.get(row.get('id'), {})
        return dict(state=catalog.lifecycle_state(row), text=lifecycle_text(row), detail=lifecycle_detail(row),
                    fit=verdict.get('state', 'unknown'), reasons=verdict.get('reasons', []), passed=verdict.get('passed', []),
                    unread=_(catalog.UNREAD_CLASS) if row.get('unread_class') else '')

    @Property('QVariantList', notify=changed)
    def columns(self):
        power = {'modules': 'pmax', 'batteries': 'usable_energy_kwh', 'optimizers': 'rated_input_power_w'}.get(
            self._kind, 'ac_power_nominal_w')
        extra = {'modules': 'cell_family', 'batteries': 'voltage_class', 'optimizers': 'max_input_voltage_v',
                 'microinverters': 'modules_per_unit', 'inverters': 'phases'}[self._kind]
        return [dict(key=k, title=labels().get(k, k).removesuffix(f' ({unit_of(k)})'), unit=unit_of(k)) for k in
                ('manufacturer', 'model', power, extra, 'source')] + [dict(key=STATE_COLUMN, title=_("State"), unit='')]

    @Property('QVariantList', notify=changed)
    def details(self):
        keys = dict.fromkeys(k for row in self._selected[:4] for k in row if k not in (
            'id', 'lifecycle', 'classes', 'family_id', 'class_of', 'unread_classes', 'classes_read', 'member_of', 'unread_class'))
        return [dict(key=k, label=field_label(k, labels()),
                     values=[display_field(row, k) for row in self._selected[:4]]) for k in keys]

    def _submit(self, operation, callback):
        self._generation += 1
        generation = self._generation
        self._busy, self._error = True, ''
        job = _Job(generation, operation)
        self._jobs[generation] = (job, callback)
        job.signals.done.connect(self._done)
        QThreadPool.globalInstance().start(job)
        self.changed.emit()

    @Slot(int, object, str)
    def _done(self, generation, value, error):
        entry = self._jobs.pop(generation, None)
        if generation != self._generation or entry is None:
            return
        self._busy, self._error = False, error
        if not error:
            entry[1](value)
        self.changed.emit()

    def _load(self):
        kind = self._kind
        def read():
            if self._provided is not None:
                records = copy.deepcopy(self._provided.get(kind, []))
            else:
                records = catalog.search(kind, limit=None)
            schema = {}
            for row in records:
                for key, value in row.items():
                    if key not in schema or schema[key] is None:
                        schema[key] = value
            return records, schema, _verdicts(kind, records, context)
        context = dict(self._context)
        self._submit(read, self._loaded)

    def _loaded(self, result):
        self._all, self._schema, self._model.verdicts = result
        self._search()

    def _judge(self):
        records, kind, context = self._all, self._kind, dict(self._context)

        def judged(verdicts):
            self._model.verdicts = verdicts
            self._search()
        self._submit(lambda: _verdicts(kind, records, context), judged)

    def _search(self):
        self._timer.stop()
        records, kind = self._all, self._kind
        filters, sort, descending = dict(self._filters), self._sort, self._descending
        verdicts = dict(self._model.verdicts)

        def work():
            everything = dict(filters, state='', market='')
            widest = _search(records, kind, everything, sort, descending)
            market = filters['market']
            wide = [r for r in widest if _in_market(r, market)] if market else widest
            rows = [r for r in wide if not filters['state'] or catalog.lifecycle_state(r) == filters['state']]
            out = [r for r in wide if filters['state'] and catalog.lifecycle_state(r) != filters['state']]
            hidden = {'state': len(out), 'states': dict(Counter(catalog.lifecycle_state(r) for r in out)),
                      'names': [str(r.get('model', '')) for r in out[:HIDDEN_NAMES]],
                      'market': len(widest) - len(wide)}       # counted for «Show all (n)», not in the line
            # An inverter or a module that does not go with the context is shown last with its reason; an optimizer
            # that does not fit the module is hidden unless asked for (the Plant proposes among those that fit).
            fitting_all = filters['fitting'] == 'all' or (kind != 'optimizers' and filters['fitting'] != 'only')
            if verdicts:
                fitting = [r for r in rows if verdicts.get(r.get('id'), {}).get('state') != compat.NOT_OK]
                unfit = [r for r in rows if verdicts.get(r.get('id'), {}).get('state') == compat.NOT_OK]
                if fitting_all:
                    rows = fitting + unfit      # those that do not go with it last, with their reason
                else:
                    rows, hidden['fit'] = fitting, len(unfit)
                    hidden['names'] += [str(r.get('model', '')) for r in unfit[:max(0, HIDDEN_NAMES-len(hidden['names']))]]
            return rows, hidden
        self._submit(work, self._results)

    def _results(self, result):
        rows, self._hidden = result
        ids = {r.get('id') for r in rows}
        # Never a row at random (R421): what is in use or proposed, what the search left alone, or nothing at all.
        self._selected = [r for r in self._selected if r.get('id') in ids]
        if not self._selected and self._current_id in ids:
            self._selected = [next(r for r in rows if r.get('id') == self._current_id)]
            key = catalog.family_key(self._selected[0], self._kind)
            if key:
                self._model.expanded.add(key)
        if not self._selected and len(rows) == 1:
            self._selected = [rows[0]]
        self._anchor_index = 0
        self._model.set_selection(self._selected, notify=False)
        narrowed = bool(self._filters['text'].split()) and len(rows) <= 12
        shown = grouped(rows, self._kind, self._model.expanded, narrowed)
        self._model.replace(shown, [c['key'] for c in self.columns])
        if self._selected:
            at = self._model.index_of(self._selected[0].get('id'))
            if at >= 0:
                self._anchor_index = at
                self.positioned.emit(at)
        names = {}
        for row in self._all:
            if not self._filters['source'] or row.get('source') == self._filters['source']:
                name = str(row.get('manufacturer', ''))
                names.setdefault(name.casefold(), name)
        self._brands = sorted(names.values(), key=str.casefold)

    @Slot(str)
    def setKind(self, kind):
        if kind not in catalog.KINDS or kind == self._kind:
            return
        self._timer.stop()
        self._states[self._kind] = dict(self._filters)
        self._kind, self._selected, self._all = kind, [], []
        self._filters = dict(self._states.get(kind, self._initial))
        self._model.expanded = set()
        self._confirm = ''
        self._sort, self._descending = '', False
        self._model.replace([], [c['key'] for c in self.columns])
        self.cancelEdit()
        self._load()

    @Slot(str, 'QVariant')
    def setFilter(self, key, value):
        if key not in _DEFAULT:
            return
        if key in ('low', 'high', 'efficiency_min', 'length_max'):
            try:
                value = max(0, float(str(value).replace(',', '.')))
            except (TypeError, ValueError):
                return
        else:
            value = str(value or '')
        self._filters[key] = value
        self._states[self._kind] = dict(self._filters)
        # Keep a pending catalogue read alive; the latest filters apply when it finishes.
        if self._all or not self._busy:
            self._generation += 1
            self._timer.start()
        self._busy = True
        self.changed.emit()

    @Slot()
    def showAll(self):
        """Every product of the kind: any state, any market, those that do not go with the context too (last, with
        their reason). One search; «Clear» goes back to the opening filters (R434)."""
        self._filters.update(state='', market='', fitting='all')
        self._states[self._kind] = dict(self._filters)
        if self._all or not self._busy:
            self._generation += 1
            self._timer.start()
        self._busy = True
        self.changed.emit()

    @Slot()
    def clearFilters(self):
        self._filters = dict(self._initial)
        self._states[self._kind] = dict(self._filters)
        self._timer.stop()
        if self._all or not self._busy:
            self._search()
        self.changed.emit()

    @Slot(str, bool)
    def sortBy(self, key, descending=False):
        self._sort, self._descending = key, descending
        if self._all or not self._busy:
            self._search()

    @Slot(str, 'QVariantMap', str)
    def setContext(self, kind, context, current=''):
        """What the catalogue is opened for: the module and the inverter in hand, the coldest temperature. `current` is the
        id of the product in use; what Meridiana would propose takes its place when nothing is in use (R421)."""
        self._context = {k: v for k, v in dict(context).items() if v not in (None, {}, '')}
        self._confirm = ''
        proposed = compat.proposed(kind, self._context) if not current and self._context else None
        self._current_id = current or (f"cur:{proposed.get('manufacturer', '')}:{proposed.get('model', '')}" if proposed else '')
        self._selected = []
        self._filters = dict(self._states.get(kind, self._initial), fitting='')
        if kind != self._kind:
            self.setKind(kind)
            self._filters['fitting'] = ''
        elif self._all:
            self._judge()
        self.changed.emit()

    @Slot()
    def clearContext(self):
        self.setContext(self._kind, {}, '')

    @Slot(int)
    def toggleFamily(self, index):
        row = self._model.record(index)
        key = row.get('family') or row.get('member_of')
        if not key:
            return
        if key in self._model.expanded:
            self._model.expanded.discard(key)
        else:
            self._model.expanded.add(key)
        self._search()

    def _member(self, row):
        """The record a list row stands for: a family's central class, or the row itself."""
        if row.get('family_row'):
            central = next((m for m in row['members'] if m.get('id') == row.get('central')), row['members'][0])
            return copy.deepcopy(central)
        return {k: v for k, v in row.items() if k != 'member_of'}

    @Slot(int, bool)
    def select(self, index, extend=False):
        row = self._model.record(index)
        if not row:
            return
        row = self._member(row)
        self._confirm = ''
        if extend:
            kept = [r for r in self._selected if r.get('id') != row.get('id')]
            self._selected = kept if len(kept) < len(self._selected) else self._selected + [row]
        else:
            self._selected = [row]
            self._anchor_index = index
        self._model.set_selection(self._selected)
        self.changed.emit()

    @Slot(int)
    def selectRange(self, index):
        start, end = sorted((self._anchor_index, index))
        self._selected = self._model.rows[max(0, start):end + 1]
        self._model.set_selection(self._selected)
        self.changed.emit()

    @Slot()
    def choose(self):
        """OK on a product that does not go with what is there, or is out of production, does not pass in silence: it is
        said, and a second, explicit step takes it (R421)."""
        if not self._selected:
            return
        row = self._selected[0]
        if row.get('unread_class'):
            self._error = _(catalog.UNREAD_CLASS)
            self.changed.emit()
            return
        reasons = []
        verdict = self._model.verdicts.get(row.get('id'), {})
        if verdict.get('state') == compat.NOT_OK:
            reasons.append(_("{name} does not go with what you have: {why}").format(
                name=row.get('model', ''), why='; '.join(verdict.get('reasons', [])[:2])))
        if catalog.lifecycle_state(row) == catalog.DISCONTINUED:
            life = row.get('lifecycle') or {}
            reasons.append(_("{name} is out of production.").format(name=row.get('model', '')) + (
                ' ' + _("In its place: {model}").format(model=life['replacement']) if life.get('replacement') else ''))
        if reasons:
            self._confirm = ' '.join(reasons)
            self.changed.emit()
            return
        self._take(row)

    @Slot()
    def chooseAnyway(self):
        if self._selected and not self._selected[0].get('unread_class'):
            self._take(self._selected[0])

    @Slot()
    def keepLooking(self):
        self._confirm = ''
        self.changed.emit()

    def _take(self, row):
        self._confirm = ''
        issues = audit_record(row, self._kind)['issues']
        if issues:
            self._error = _("Product not selected: inconsistent data. {issues}").format(issues='; '.join(issues))
            self.changed.emit()
            return
        self.chosen.emit(self._kind, copy.deepcopy(row))

    @Slot()
    def requestImport(self):
        if self._kind in ('modules', 'inverters'):
            self.importRequested.emit(self._kind)

    @Slot(str, result=bool)
    def openSource(self, source):
        url = QUrl.fromUserInput(source)
        allowed = url.scheme().lower() in ('http', 'https')
        if url.isLocalFile():
            allowed = Path(url.toLocalFile()).suffix.lower() == '.pdf'
        if not allowed or not url.isValid():
            self._error = _("The source must be an HTTP(S) address or a PDF document.")
            self.changed.emit()
            return False
        if not QDesktopServices.openUrl(url):
            self._error = _("The source document could not be opened.")
            self.changed.emit()
            return False
        return True

    # The review window (R415): the fields of the kind in groups, each with its name, its unit and, when it came from a
    # document, where it was read. No JSON: what a list holds is typed as numbers.

    @Slot(bool)
    def beginEdit(self, copy_selected=False):
        draft = self.selectedRecord if copy_selected else {}
        for key in ('id', 'kind', 'source', 'family_id', 'class_of', 'unread_classes', 'lifecycle', 'classes_read',
                    'efficiency_derived', 'bifaciality_estimated', 'unread_class', 'member_of'):
            draft.pop(key, None)
        self._open_editor(draft, {}, '')

    def _open_editor(self, record, anchors, note, review_id=''):
        self._draft = copy.deepcopy(record)
        self._anchors = copy.deepcopy(anchors)
        self._editor_note = note
        self._review_id = review_id
        self._editor_classes = [self._class_row(c) for c in record.get('classes') or []]
        self._editor_proposals = []
        self._build_editor()
        self._editing, self._error = True, ''
        self.editorChanged.emit()
        self.changed.emit()
        self._check_editor()

    def _class_row(self, entry):
        return {key: self._number_text(entry.get(key)) for key in ('pmax', 'vmp', 'imp', 'voc', 'isc', 'efficiency_pct')}

    @staticmethod
    def _number_text(value):
        if value is None or value == '':
            return ''
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            if float(value).is_integer():
                return number(value, 0)
            return number(value, max(0, -Decimal(str(value)).as_tuple().exponent))
        return str(value)

    def _value_text(self, field, value):
        if value is None or value == [] or value == '':
            return ''
        if field.type == 'yesno':
            return 'yes' if value else 'no'
        if field.type in ('per_mppt', 'dimensions'):
            items = value if isinstance(value, list) else [value]
            return ' '.join(self._number_text(item) for item in items)
        if field.type in ('number', 'integer'):
            return self._number_text(value)
        return str(value)

    def _build_editor(self):
        groups = []
        for title, members in schema.groups(self._kind):
            rows = []
            for field in members:
                anchor = self._anchors.get(field.key) or {}
                rows.append(dict(key=field.key, label=_(field.label), unit=field.unit, type=field.type, required=field.required,
                                 value=self._value_text(field, self._draft.get(field.key)), hint=_(field.hint) if field.hint else '',
                                 choices=[dict(key=k, text=_(t)) for k, t in field.choices],
                                 visible=schema.visible(field, self._draft), page=anchor.get('page', 0),
                                 line=anchor.get('text', ''), confidence=anchor.get('confidence', ''),
                                 sourceText=self._anchor_text(anchor)))
            groups.append(dict(title=_(title), fields=rows))
        self._editor_groups = groups
        known = {f.key for f in schema.fields(self._kind)}
        self._types = {f.key: f.type for f in schema.fields(self._kind)}
        self._extra_json = '{}'
        # the fields of the record that have no box (a file's own, the one-diode parameters) go through as they are
        self._kept = {k: v for k, v in self._draft.items() if k not in known and k != 'classes'}
        self._editor_fields = [f for group in groups for f in group['fields']]

    @staticmethod
    def _anchor_text(anchor):
        if not anchor:
            return ''
        words = {'high': _("sure, checked"), 'medium': _("to check"), 'low': _("doubtful")}.get(anchor.get('confidence'), '')
        where = _("p. {page}").format(page=anchor['page']) if anchor.get('page') else str(anchor.get('source') or '')
        return ' · '.join(part for part in (where, words) if part)

    def _parse_field(self, field, text):
        text = (text or '').strip()
        if not text:
            return '' if field.type == 'text' else None
        if field.type in ('number', 'integer'):
            value = float(text.replace(' ', '').replace('.', '').replace(',', '.') if ',' in text else text)
            return int(value) if field.type == 'integer' and value.is_integer() else value
        if field.type == 'yesno':
            return text == 'yes'
        if field.type == 'per_mppt':
            values = [float(v.replace(',', '.')) for v in text.replace(';', ' ').replace('/', ' ').split()]
            return values
        if field.type == 'dimensions':
            values = [float(v.replace(',', '.')) for v in text.replace('x', ' ').replace('×', ' ').split()]
            return values
        if field.type == 'choice' and field.key == 'phases':
            return int(text)
        return text

    def _editor_record(self):
        """The record the window holds. ValueError names the field whose text is not a number."""
        values = dict(getattr(self, '_kept', {}))
        by_key = {f.key: f for f in schema.fields(self._kind)}
        for row in self._editor_fields:
            field = by_key[row['key']]
            try:
                value = self._parse_field(field, row['value'])
            except ValueError:
                raise ValueError(_("{field}: «{text}» is not a number.").format(field=row['label'], text=row['value'])) from None
            # An empty box is a value only for a field the record had: what nobody said stays out of the record.
            if value not in (None, '') or row['key'] in self._draft:
                values[row['key']] = value
        if self._kind == 'inverters':
            count = values.get('mppt_count')
            for key in ('dc_current_max_per_mppt_a', 'dc_isc_max_per_mppt_a', 'strings_per_mppt'):
                value = values.get(key)
                if isinstance(value, list) and len(value) == 1 and count.__class__ is int and count > 1:
                    values[key] = value * count
        if self._kind == 'modules':
            classes = []
            for row in self._editor_classes:
                entry = {}
                for key, text in row.items():
                    text = (text or '').strip()
                    if text:
                        try:
                            entry[key] = float(text.replace(',', '.'))
                        except ValueError:
                            raise ValueError(_("A class: «{text}» is not a number.").format(text=text)) from None
                if entry:
                    classes.append(entry)
            if classes:
                values['classes'] = classes
                values['power_classes_w'] = [c.get('pmax') for c in classes if c.get('pmax')]
        sources = {}
        for key, anchor in self._anchors.items():
            sources[key] = {k: anchor[k] for k in ('source', 'page', 'text', 'confidence') if k in anchor}
        if sources:
            values['field_sources'] = sources
        return values

    def _check_editor(self):
        try:
            record = self._editor_record()
        except ValueError as error:
            self._editor_checks = [dict(level='error', field='', text=str(error))]
            self.checksChanged.emit()
            return
        checks = []
        for item in schema.coherence(self._kind, record):
            values = {k: (_(v) if k == 'field' else self._number_text(v)) for k, v in item['values'].items()}
            checks.append(dict(level=item['level'], field=item['field'], text=_(item['text']).format(**values) if values else _(item['text'])))
        absent = schema.missing(self._kind, record)
        if absent:
            checks.insert(0, dict(level='required', field=absent[0].key, text=_("Still needed for the calculations: {fields}").format(
                fields=', '.join(_(f.label) for f in absent))))
        self._editor_checks = checks
        self.checksChanged.emit()

    @Slot(str, str)
    def setEditorField(self, key, value):
        if key not in self._types:
            return
        # Do not reset the editor model on each keystroke: the active delegate keeps focus.
        rebuild = False
        for field in self._editor_fields:
            if field['key'] == key:
                field['value'] = value
                self._anchors.pop(key, None)        # typed by hand: it no longer comes from the sheet
                rebuild = key in ('dc_architecture', 'bifacial', 'type')
                break
        if rebuild:
            kept = {f['key']: f['value'] for f in self._editor_fields}
            try:
                self._draft = self._editor_record()
            except ValueError:
                pass
            self._build_editor()
            for field in self._editor_fields:
                if field['key'] in kept:
                    field['value'] = kept[field['key']]
            self.editorChanged.emit()
        self._check_editor()

    @Slot(int, str, str)
    def setEditorClass(self, index, key, value):
        if 0 <= index < len(self._editor_classes) and key in self._editor_classes[index]:
            self._editor_classes[index][key] = value
            self._check_editor()

    @Slot()
    def addEditorClass(self):
        self._editor_classes.append(dict(pmax='', vmp='', imp='', voc='', isc='', efficiency_pct=''))
        self.editorChanged.emit()
        self._check_editor()

    @Slot(int)
    def removeEditorClass(self, index):
        if 0 <= index < len(self._editor_classes):
            del self._editor_classes[index]
            self.editorChanged.emit()
            self._check_editor()

    @Slot(str)
    def setEditorExtra(self, value):
        self._extra_json = value

    @Slot(str, result=bool)
    def setDestination(self, path):
        try:
            target = Path(path).expanduser()
            if not target.is_absolute():
                raise ValueError(_("Choose an absolute catalogue destination."))
            target = target.resolve()
            if not target.is_relative_to(self._safe_root) or target.suffix.lower() != '.json':
                raise ValueError(_("Choose a JSON destination inside the allowed catalogue folder."))
            self._destination, self._error = str(target), ''
        except (ValueError, OSError) as exc:
            self._destination, self._error = '', str(exc)
            self.changed.emit()
            return False
        self.changed.emit()
        return True

    # Filling the window from a document: the reader, a PVsyst file or Meridio. Nothing here saves anything.

    @staticmethod
    def _local(url):
        text = str(url)
        return Path(QUrl(text).toLocalFile() if text.startswith('file:') else text)

    @Slot(str)
    def readDatasheet(self, url):
        """Read a PDF on a worker and fill the window with what it says, each field with its page and how sure."""
        path = self._local(url)
        kind = self._kind
        self._editor_note = _("Reading {file}…").format(file=path.name)
        self.editorChanged.emit()

        def read():
            from meridiana.catalog import datasheet
            return path, datasheet.read(path, kind)
        self._submit(read, self._datasheet_read)

    def _datasheet_read(self, result):
        path, reading = result
        if reading.scanned:
            self._editor_note = _("{file} has no text: it is a scanned sheet. Meridio can read its pictures if you allow it, "
                                  "or type the values here.").format(file=path.name)
            self.editorChanged.emit()
            return
        if not reading.proposals:
            self._editor_note = _("Nothing in {file} could be read as a product of this kind. Type the values, or try Meridio.").format(file=path.name)
            self.editorChanged.emit()
            return
        self._readings = reading
        self._editor_proposals = [dict(index=n, model=str(p.record.get('model') or ''), fields=len(p.record))
                                  for n, p in enumerate(reading.proposals)]
        self._use_proposal(0)

    @Slot(int)
    def useProposal(self, index):
        self._use_proposal(index)

    def _use_proposal(self, index):
        reading = getattr(self, '_readings', None)
        if reading is None or not 0 <= index < len(reading.proposals):
            return
        proposal = reading.proposals[index]
        proposals = self._editor_proposals
        record = dict(self._draft)
        record.update(proposal.record)
        notes = list(proposal.notes) + list(reading.notes)
        note = _("Read from {file}: check every value against the sheet.").format(file=reading.file)
        if notes:
            note += ' ' + ' '.join(notes)
        self._open_editor(record, proposal.sources(reading.file), note, self._review_id)
        self._editor_proposals = proposals
        self.editorChanged.emit()

    @Slot(str)
    def importPvsystInto(self, url):
        """A .PAN or .OND in the same window, as the Widgets' import did with its dialog."""
        path = self._local(url)
        from meridiana.catalog import panond
        reader = panond.module if path.suffix.lower() == '.pan' else panond.inverter

        def read():
            return path, reader(path)

        def done(result):
            source, (record, notes) = result
            anchors = {key: dict(source=source.name, page=0, text='', confidence='high') for key in record}
            self._open_editor({k: v for k, v in record.items() if k not in ('source', 'file')}, anchors,
                              _("Read from {file}: {what}.").format(file=source.name, what='; '.join(notes)), self._review_id)
        self._submit(read, done)

    @Slot(str, str, 'QVariantMap')
    def reviewProposal(self, review_id, kind, record):
        """A record proposed from outside (Meridio) in the review window. It is the same window: nothing is saved here, and
        the words of whoever proposed it are data."""
        if kind in catalog.KINDS and kind != self._kind:
            self.setKind(kind)
        record = schema.normalised(self._kind, dict(record))
        anchors = record.pop('field_sources', None) or {}
        self._open_editor(record, anchors if isinstance(anchors, dict) else {},
                          _("Proposed by Meridio: check every value against the sheet."), review_id)

    @Slot(result=bool)
    def saveEditor(self):
        try:
            if self._explicit_root:
                if not self._destination:
                    raise ValueError(_("Choose an explicit personal catalogue destination before saving."))
                target = Path(self._destination)
                if target.exists():
                    existing = json.loads(target.read_text(encoding='utf8'))
                    if not isinstance(existing, list) or any(
                            not isinstance(row, dict) or row.get('source') != 'personal' or
                            row.get('kind') not in catalog.KINDS or not str(row.get('id', '')).startswith('personal:')
                            for row in existing):
                        raise ValueError(_("The destination is not a personal catalogue. Choose a new JSON file."))
            else:
                self._destination = str(personal.location())
            values = self._editor_record()
            blocking = [c for c in self._editor_checks if c['level'] == 'error']
            if blocking:
                raise ValueError(blocking[0]['text'])
            absent = schema.missing(self._kind, values)
            if absent:
                raise ValueError(_("Still needed for the calculations: {fields}").format(
                    fields=', '.join(_(f.label) for f in absent)))
            row = personal.save(self._kind, values, path=self._destination)
        except (ValueError, OSError, TypeError) as exc:
            self._error = _("Not saved: {reason}").format(reason=exc)
            self.changed.emit()
            return False
        self._error = ''
        rows = catalog.expand_classes(row) if self._kind == 'modules' else [row]
        self._all = rows + self._all
        self._schema.update({key: value for key, value in row.items() if value is not None})
        self._filters['source'] = 'personal'
        self._filters['state'] = ''
        self._search()
        self.saved.emit(copy.deepcopy(row))
        review, self._review_id = self._review_id, ''
        if review:
            self.reviewFinished.emit(review, True)
        self.cancelEdit()
        return True

    @Slot()
    def cancelEdit(self):
        review, self._review_id = self._review_id, ''
        if review:
            self.reviewFinished.emit(review, False)
        self._editing = False
        self.editorChanged.emit()


def create_page(engine, session=None):
    """Install the page's context and retain its backend for the engine lifetime."""
    from meridiana.quick.backend.controls import install_controls
    install_controls(engine)
    backend = CatalogBackend(session, engine)
    engine.rootContext().setContextProperty('catalogBackend', backend)
    engine._catalog_backend = backend
    return backend
