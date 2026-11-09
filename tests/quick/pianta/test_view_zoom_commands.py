"""R538, Daniel 07/11/2026: «i comandi + e − sulla vista 3D agiscono sullo zoom della vista 2D mentre quelli nella vista
2D agiscono su entrambi. Da capire anche sul comando di inquadramento». Each view has its own +, - and Fit, and the
shortcuts act on the view that has the focus, also in the plan and 3D side by side of Plant; every combination."""
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

RHO = Path(os.environ.get('MERIDIANA_REAL_HOME') or Path.home()) / 'dev/meridiana-prove/Prova capannone Rho.meridiana'


@unittest.skipUnless(RHO.exists(), 'the Rho project of the trials')
@unittest.skipIf(os.environ.get('QT_QPA_PLATFORM') == 'offscreen',
                 'the 3D view is not shown offscreen: this test runs on a screen (r21-pianta, R538)')
class ViewZoomCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QObject, QTimer
        from meridiana import model
        from meridiana.quick.app import QuickWindow, create_app
        from meridiana.quick.sample import recorded_weather
        cls.work = Path(tempfile.mkdtemp(prefix='meridiana-r538-'))
        shutil.copy2(RHO, cls.work / RHO.name)
        cls.app = create_app()
        project, _notice = model.Project.load(cls.work / RHO.name)
        recorded_weather(project, cls.work)
        cls.host = QuickWindow(project, cls.work, real_views=True, path=cls.work / RHO.name)
        cls.window = cls.host.window
        cls.window.resize(1600, 960)
        cls.window.show()
        QTimer.singleShot(0, cls.host.bridge.recompute)
        cls.spin(4)
        cls.window.setProperty('phase', 'plant')
        cls.host.shell.trigger('view_both')
        cls.spin(3)
        cls.plan = cls.window.findChild(QObject, 'plan')
        end = time.monotonic() + 15        # the 3D view is made the first time it is shown
        while time.monotonic() < end:
            shown = [v for v in cls.window.findChildren(QObject, 'viewport3d') if v.property('visible')]
            if shown:
                break
            cls.spin(.2)
        cls.scene = shown[0] if shown else cls.window.findChild(QObject, 'viewport3d')
        cls.spin(1)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        shutil.rmtree(cls.work, ignore_errors=True)

    @classmethod
    def spin(cls, seconds):
        from _setup import turn_events      # the time itself is tested: the 300 ms the plan waits after a gesture
        turn_events(cls.app, seconds * 1000)

    def views(self):
        camera = self.scene.property('cameraState')
        camera = camera.toVariant() if hasattr(camera, 'toVariant') else camera
        return round(self.plan.property('zoom'), 6), json.dumps(camera, sort_keys=True, default=str)

    def act(self, action):
        from PySide6.QtCore import QMetaObject, Q_ARG
        # both views away from their framing first, so that a Fit shows which one it moved
        self.plan.setProperty('zoom', self.plan.property('zoom') * 1.3)
        QMetaObject.invokeMethod(self.scene, 'zoomBy', Q_ARG('QVariant', 1))
        self.spin(.3)
        before = self.views()
        action()
        self.spin(1.2)           # a Fit of the 3D view flies there
        after = self.views()
        return before[0] != after[0], before[1] != after[1]

    def plan_focus(self):
        self.plan.forceActiveFocus()
        self.spin(.1)

    def scene_focus(self):
        self.scene.forceActiveFocus()
        self.spin(.1)

    def test_every_button_and_shortcut_acts_on_one_view(self):
        from PySide6.QtCore import QMetaObject, Q_ARG
        self.assertTrue(self.plan.property('visible') and self.scene.property('visible'), ('plan and 3D side by side', self.window.property('viewMode'), self.plan.property('visible'), self.scene.property('visible'), self.window.property('phase')))
        backend = self.host.plan
        shell = self.host.shell
        results = {}
        for command in ('zoom_in', 'zoom_out', 'fit'):
            # the plan's buttons call its backend (ViewBar), the 3D view's call requestCommand (SceneToolbar)
            self.scene_focus()
            results[f'plan button {command}'] = (self.act(lambda c=command: backend.viewAction(c)), (True, False))
            self.plan_focus()
            results[f'3D button {command}'] = (self.act(lambda c=command: QMetaObject.invokeMethod(
                self.scene, 'requestCommand', Q_ARG('QVariant', c))), (False, True))
            for focus, name, expected in ((self.plan_focus, 'plan', (True, False)),
                                          (self.scene_focus, '3D', (False, True))):
                focus()
                results[f'shortcut {command}, focus on the {name}'] = (
                    self.act(lambda c=command: shell.trigger(c)), expected)
                focus()
                results[f'window command {command}, focus on the {name}'] = (
                    self.act(lambda c=command: QMetaObject.invokeMethod(self.window, 'runCommand',
                                                                        Q_ARG('QVariant', c))), expected)
        wrong = {k: v for k, v in results.items() if v[0] != v[1]}
        self.assertEqual(wrong, {}, json.dumps({k: [list(v[0]), list(v[1])] for k, v in results.items()}, indent=1))


if __name__ == '__main__':
    unittest.main()
