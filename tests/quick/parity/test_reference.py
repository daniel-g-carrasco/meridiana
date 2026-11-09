"""The Widgets reference must describe pixels and visible controls faithfully."""
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _setup

setUpModule = _setup.keep_global_state


class ReferenceTest(unittest.TestCase):
    def test_capture_retains_named_text_geometry_font_and_palette(self):
        from PySide6.QtGui import QFont, QFontDatabase
        from PySide6.QtWidgets import QLabel, QWidget
        from tools.quick_rif import widget_snapshot
        app = _setup.qt_or_skip()
        root = QWidget()
        self.addCleanup(_setup.dispose, root)
        root.resize(300, 200)
        label = QLabel('Visible reference', root)
        font_id = QFontDatabase.addApplicationFont(str(_setup.ROOT / 'data/fonts/ibm-plex/IBMPlexSans-Regular.ttf'))
        self.assertGreaterEqual(font_id, 0)
        label.setFont(QFont('IBM Plex Sans', 10))
        label.setObjectName('caption')
        label.setGeometry(17, 29, 220, 31)
        hidden = QLabel('Must not leak', root)
        hidden.hide()
        root.show()
        app.processEvents()
        shot = widget_snapshot(root)
        row = next(w for w in shot['widgets'] if w['name'] == 'caption')
        self.assertEqual(row['rect'], [17, 29, 220, 31])
        self.assertEqual(row['text'], 'Visible reference')
        self.assertTrue(row['font']['family'])
        self.assertIn('WindowText', row['colors'])
        self.assertFalse(any(w['text'] == 'Must not leak' for w in shot['widgets']))
        self.assertEqual(len({w['id'] for w in shot['widgets']}), len(shot['widgets']))

    def test_canonical_gzip_is_repeatable_and_never_overwrites(self):
        from tools.quick_rif import write_canonical
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder) / 'a.json.gz', Path(folder) / 'b.json.gz'
            value = {'schema': 1, 'widgets': [], 'meta': {'text': 'Proprietà'}}
            write_canonical(a, value)
            write_canonical(b, value)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(json.loads(gzip.decompress(a.read_bytes())), value)
            with self.assertRaises(FileExistsError):
                write_canonical(a, {'wrong': True})

    def test_list_view_private_model_is_captured_as_visible_cells(self):
        from PySide6.QtWidgets import QListWidget
        from tools.quick_rif import widget_snapshot
        app = _setup.qt_or_skip()
        view = QListWidget()
        self.addCleanup(_setup.dispose, view)
        view.addItems(['First', 'Second'])
        view.resize(300, 200)
        view.show()
        app.processEvents()
        row = widget_snapshot(view)['widgets'][0]
        self.assertEqual([c['text'] for c in row['cells']], ['First', 'Second'])

    def test_matrix_contains_every_requested_combination_and_real_state(self):
        from tools.quick_rif import capture_matrix, state_names
        matrix = capture_matrix()
        self.assertEqual(len(matrix), 24)
        self.assertEqual({m['scale'] for m in matrix}, {1, 2})
        self.assertEqual({tuple(m['size']) for m in matrix}, {(1366, 900), (1600, 960), (1920, 1080)})
        self.assertTrue({'phase-production', 'phase-report', 'plant-strings', 'plant-inverters',
                         'file-open', 'settings-appearance', 'meridio', 'menu-file'} <= set(state_names()))

    def test_resume_requires_matching_states_and_unmodified_photo(self):
        from tools import quick_rif
        with tempfile.TemporaryDirectory() as folder, patch.object(quick_rif, 'ROOT', Path(folder)):
            root = Path(folder)
            photo = root / 'image.png'
            photo.write_bytes(b'original image bytes')
            snapshot = root / 'snapshot.json.gz'
            quick_rif.write_canonical(snapshot, {'meta': {
                'png_sha256': hashlib.sha256(photo.read_bytes()).hexdigest()}})
            self.assertFalse(quick_rif.capture_complete('run', 'case', ['model']))
            quick_rif.write_canonical(root / 'docs/quick/compat/riferimento/run/case/manifest.json.gz', {
                'captures': [{'state': 'model', 'png': 'image.png', 'json': 'snapshot.json.gz'}]})
            self.assertTrue(quick_rif.capture_complete('run', 'case', ['model']))
            with self.assertRaisesRegex(ValueError, 'different states'):
                quick_rif.capture_complete('run', 'case', ['plant'])
            photo.write_bytes(b'altered image')
            with self.assertRaisesRegex(ValueError, 'Damaged capture'):
                quick_rif.capture_complete('run', 'case', ['model'])

    def test_strings_state_scrolls_the_actual_diagram_into_the_viewport(self):
        from quick.parity.differential import connected_fixture
        from tools.quick_rif import present, settle
        project = connected_fixture()
        project.energy['inverters'][0]['count'] = 7
        app = _setup.qt_or_skip()
        window = _setup.window(self, project)
        window.setFixedSize(1366, 900)
        # Keep this a display test: no annual calculation or late plant refresh may
        # change the diagram's size while its viewport visibility is being checked.
        with patch.object(window, '_compute_energy'):
            self.assertTrue(_setup.wait_until(app, lambda: not window.plant_pending(), 30))
            present(window, 'plant-inverters')
            settle(app, window)
            inspector = window.plant_inspector
            inspector.verticalScrollBar().setValue(0)
            self.assertTrue(inspector.list.visibleRegion().isEmpty())

            # Negative control: selecting the real diagram alone must leave it
            # clipped. Removing ensureWidgetVisible from present fails below.
            with patch.object(inspector, 'ensureWidgetVisible'):
                present(window, 'plant-strings')
                settle(app, window)
            self.assertEqual(inspector.view, 'diagram')
            diagram = inspector.list.front()
            self.assertTrue(diagram.visibleRegion().isEmpty())

            # The mode is already diagram: only bringing it into the viewport can
            # make its painted contents visible. Scrollbar values are not evidence.
            present(window, 'plant-strings')
            settle(app, window)
            self.assertIs(inspector.list.front(), diagram)
            visible = diagram.visibleRegion().boundingRect()
            self.assertFalse(visible.isEmpty())
            self.assertTrue(diagram.rect().contains(visible))
