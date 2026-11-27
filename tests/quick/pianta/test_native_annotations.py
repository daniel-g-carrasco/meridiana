"""The full native window must retain unselected geometry beside annotations."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QObject

import _setup
from meridiana.app.view.measure_tool import Measure, Probe
from meridiana.core.model.model import Building, Project, Roof
from quick.aiuti.view_grab import grab_item
from quick.vista3d._fidelity_support import js, pixels, settle
from quick.aiuti.avvisi import real

setUpModule = _setup.keep_global_state


class NativeAnnotations(unittest.TestCase):
    def test_unselected_building_is_drawn_in_the_full_window(self):
        from meridiana.gui.application import QuickWindow, create_app
        import numpy as np
        app = create_app()
        project = Project(name='Annotation fixture')
        project.buildings.extend([
            Building(id='a', name='First', height=6, footprint=[[0, 0], [40, 0], [40, 20], [0, 20]]),
            Building(id='b', name='Second', height=6, roof=Roof(type='gable', tilt=25),
                     footprint=[[100, 0], [140, 0], [140, 20], [100, 20]])])
        with tempfile.TemporaryDirectory() as tmp:
            host = QuickWindow(project, Path(tmp), real_views=True, theme={'reducedMotion': True})
            try:
                host.window.show()
                host.window.resize(1600, 1000)
                host.window.setProperty('viewMode', 'plan')
                settle(app, 1)
                plan = host.window.findChild(QObject, 'plan')
                plan.fit()
                host.plan.editor.select('building', 'a')
                host.measure.tool.measures[:] = [Measure(1, 'distance', (Probe((0, 0, 6)), Probe((40, 0, 6))))]
                host.measure._changed()
                settle(app, 1)
                point = js(plan, 'screen(120,0)')
                image = grab_item(plan)
                dpr = image.devicePixelRatio()
                x, y = round(point.x()*dpr), round(point.y()*dpr)
                drawn = pixels(image)[y-5:y+6, x-10:x+11].astype(int)
                world = plan.findChild(QObject, 'worldLayer')
                world.setVisible(False)
                settle(app, .1)
                blank = pixels(grab_item(plan))[y-5:y+6, x-10:x+11].astype(int)
                self.assertGreater(np.count_nonzero(np.any(np.abs(drawn-blank) > 20, axis=2)), 10)
                self.assertFalse(real(host.warnings), host.warnings)
            finally:
                host.close()
