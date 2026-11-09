"""R389: edit the real Widgets fields and the Quick adapter, compare whole projects."""
import copy
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone_rho
from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QLineEdit, QSpinBox

from meridiana import config, i18n
from meridiana.paths import Paths
from meridiana.quick.backend.properties import PropertiesBackend
from meridiana.session import ProjectSession
from quick.parity.differential import Adapter, canonical_project, run_scenario, undo_snapshot


setUpModule = _setup.keep_global_state


class PropertyDifferentialTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        i18n.setup('en')
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        paths = Paths(**{key: Path(tmp.name) / key for key in ('config', 'state', 'data', 'cache')})
        self.window = _setup.window(self, capannone_rho(), paths=paths, cfg=config.Config(background='none'))
        self.backend = PropertiesBackend(ProjectSession(copy.deepcopy(self.window.project)))
        self.addCleanup(self.backend.close)

    def widget(self, label, typ):
        page = self.window.props.widget()
        for form in page.findChildren(QFormLayout):
            for row in range(form.rowCount()):
                title = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
                item = form.itemAt(row, QFormLayout.ItemRole.FieldRole)
                if not title or not title.widget() or title.widget().text() != label or not item:
                    continue
                holder = item.widget()
                if isinstance(holder, typ):
                    return holder
                if holder:
                    candidates = [child for cls in (typ if isinstance(typ, tuple) else (typ,))
                                  for child in holder.findChildren(cls)]
                    if candidates:
                        return candidates[0]
        if typ is QCheckBox:
            for field in page.findChildren(QCheckBox):
                if field.text() == label or field.accessibleName() == label:
                    return field
        self.fail(f'Widgets field missing: {label} ({typ})')

    def edit_widget(self, key, label, value, kind='number'):
        if kind == 'choice':
            field = self.widget(label, QComboBox)
            index = field.findData(value)
            self.assertGreaterEqual(index, 0, (label, value))
            # Category and activity commit on activated, ordinary combos on index changed.
            field.setCurrentIndex(index)
            if key.startswith('fire.'):
                field.activated.emit(index)
        elif kind == 'text':
            field = self.widget(label, QLineEdit)
            field.setText(value)
            field.editingFinished.emit()
        elif kind == 'check':
            self.widget(label, QCheckBox).setChecked(value)
        else:
            field = self.widget(label, (QDoubleSpinBox, QSpinBox))
            field.setValue(value)

    def test_widgets_and_quick_edit_full_project_identically(self):
        w, b = self.window, self.backend
        # R413 keeps the ridge by default, in Quick only: compared with the eave kept, what the Widgets do.
        for session in (w.session, b.session):
            for building in session.project.buildings:
                building.roof.keep_eave = True

        def widget_select(kind, oid):
            w._select(kind, oid)

        def snapshot(session):
            return dict(project=canonical_project(session.project), undo=undo_snapshot(session))

        widgets = Adapter('Widgets', dict(select=widget_select, edit=self.edit_widget,
            undo=w.session.undo.undo, redo=w.session.undo.redo), lambda: snapshot(w.session))

        def quick_edit(key, label, value, kind='number'):
            self.assertTrue(b.commit(key, value), b.error)
        quick = Adapter('Quick', dict(select=b.session.select, edit=quick_edit, undo=b.undo, redo=b.redo),
                        lambda: snapshot(b.session))
        steps = []

        def select(kind, oid):
            steps.append(dict(command='select', args=dict(kind=kind, oid=oid)))

        def edit(key, label, value, kind='number'):
            steps.append(dict(command='edit', args=dict(key=key, label=label, value=value, kind=kind)))

        select('site', '')
        edit('name', 'Project', '  Rho modificato  ', 'text')
        edit('network.pod', 'POD', 'IT001234567890', 'text')
        edit('network.voltage_v', 'Supply voltage', 20000)
        edit('network.phases', 'Phases', '3', 'choice')
        edit('rules.public', 'Public building (+10%)', True, 'check')
        select('building', 'b1')
        edit('height', 'Eave height', 11)
        edit('side.0', 'Side 1', 44)
        edit('roof.type', 'Type', 'gable', 'choice')
        edit('roof.tilt', 'Slope', 25)
        edit('roof.percent', 'Slope (percent)', 35)
        edit('roof.ridge_height', 'Ridge height', 15)
        edit('fire.activity', 'Activity (DPR 151/2011)', 75, 'choice')
        edit('fire.category', 'Category', 'B', 'choice')
        select('subfield', 's1')
        edit('name', 'Name', 'Ovest', 'text')
        edit('params.stack', 'Modules per table, across', 3)
        edit('params.gap', 'Between modules', .04)
        edit('params.pitch_mode', 'Pitch', 'gcr', 'choice')
        edit('params.gcr', 'Ratio', .6)
        edit('params.pitch_mode', 'Pitch', 'value', 'choice')
        edit('params.pitch', 'Pitch', 4.2)
        select('exclusion', 'e1')
        edit('height', 'Height', 2.1)
        edit('clearance', 'Extra clearance', .7)
        steps.extend([dict(command='undo'), dict(command='redo')])
        result = run_scenario(dict(id='properties-all-fields-journey', steps=steps), widgets, quick)
        self.assertEqual(result['status'], 'equal', result)


if __name__ == '__main__':
    unittest.main()
