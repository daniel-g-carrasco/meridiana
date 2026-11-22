"""Geometry views use the common stroke and label contracts, never local copies."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[3] / 'src/meridiana/gui/qml/Meridiana'


class AnnotationGuard(unittest.TestCase):
    def test_geometric_paths_only_use_the_shared_components(self):
        # Filled masks have no geometric stroke; the view cube is a separate control.
        exceptions = {'Plan/SunMapLayer.qml', 'Plan/ViewCorners.qml',
                      'View3D/SceneCorners.qml', 'View3D/ViewCube.qml'}
        names = [str(path.relative_to(ROOT)).replace('\\', '/')
                 for folder in ('Plan', 'Measure', 'View3D')
                 for path in (ROOT / folder).rglob('*.qml')]
        names += ['Controls/LitSide.qml', 'Dialogs/GeometryPreview.qml']
        for name in names:
            if name in exceptions:
                continue
            text = (ROOT / name).read_text(encoding='utf-8')
            with self.subTest(name=name):
                self.assertNotRegex(text, r'\bShapePath\s*\{')
                self.assertNotRegex(text, r'\b(?:strokeWidth|dashPattern|lineWidth|setLineDash)\s*[:=(]')

    def test_labels_and_counter_have_no_local_typography(self):
        for name in ('Controls/LengthPill.qml', 'Controls/CountBadge.qml', 'Controls/SpanLabel.qml',
                     'Plan/SidePills.qml', 'Plan/StringLabels.qml', 'Controls/CheckMark.qml'):
            text = (ROOT / name).read_text(encoding='utf-8')
            with self.subTest(name=name):
                self.assertNotRegex(text, r'font\.(?:pixelSize|weight):\s*(?:\d|Font\.)')
                self.assertNotIn('Text.Outline', text)

    def test_common_path_reads_theme_for_every_style_value(self):
        text = (ROOT / 'Controls/ViewPath.qml').read_text(encoding='utf-8')
        for token in ('STROKE', 'HALO_EXTRA', 'HALO_ALPHA', 'DASH_ON', 'DASH_OFF'):
            self.assertIn('Theme.annotation.' + token, text)
        self.assertIsNone(re.search(r'dashPattern:\s*\[\s*\d', text))

    def test_native_ribbons_share_the_theme_style(self):
        viewport = (ROOT / 'View3D/Viewport.qml').read_text(encoding='utf-8')
        self.assertNotIn('property real ribbonWidth:', viewport)
        self.assertNotIn('property vector4d ribbonColor:', viewport)
        ribbon = (ROOT / 'View3D/ViewRibbon.qml').read_text(encoding='utf-8')
        for token in ('STROKE', 'HALO_EXTRA', 'HALO_ALPHA'):
            self.assertIn('Theme.annotation.' + token, ribbon)
        self.assertIn('layer.samples: Theme.annotation.SAMPLES',
                      (ROOT / 'Measure/MeasureLayer.qml').read_text(encoding='utf-8'))
        # R706: the plan's geometry is drawn once, into its retained image, which holds the theme's samples
        self.assertRegex((ROOT / 'Plan/Plan.qml').read_text(encoding='utf-8'),
                         r'(?m)^\s+samples: Theme\.annotation\.SAMPLES$')
