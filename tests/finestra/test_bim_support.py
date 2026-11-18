"""The support controls use the ordinary session edit/undo path, with the original roof kept."""
import unittest
import _setup
from _fixtures import capannone
setUpModule = _setup.keep_global_state


class SupportControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_support_controls_enable_move_and_undo_the_plane_without_changing_the_roof(self):
        from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox
        from meridiana import model, move
        win = _setup.window(self, capannone())
        sf = win.project.subfields[0]
        roof = win.project.buildings[0].geometry_key()
        host = sf.building
        win._select('subfield', sf.id)
        on = win.props.findChild(QCheckBox, 'support-enabled')
        self.assertIsNotNone(on)
        self.assertFalse(win.props.findChild(QDoubleSpinBox, 'support-z0').isEnabled())
        on.click()
        self.assertIsInstance(win.project.subfields[0].support, model.SupportPlane)
        for field, value in [('z0', 18.0), ('tilt', 23.0), ('azimuth', 37.0)]:
            control = win.props.findChild(QDoubleSpinBox, 'support-'+field)
            self.assertTrue(control.isEnabled())
            control.setValue(value)
        sf = win.project.subfields[0]
        point = move.centre(win.project, 'subfield', sf.id)
        self.assertAlmostEqual(win.project.surface_of(sf).z(*point), 18.0)
        self.assertEqual(sf.support.azimuth, 37.0)
        self.assertEqual(sf.building, host)
        self.assertEqual(win.project.buildings[0].geometry_key(), roof)
        win.undo.undo()
        self.assertEqual(win.project.subfields[0].support.azimuth, 0.0)
        on = win.props.findChild(QCheckBox, 'support-enabled')
        on.click()
        self.assertFalse(win.project.subfields[0].support.enabled)
        self.assertEqual(win.project.subfields[0].support.tilt, 23.0)
