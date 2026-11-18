"""The shared pilot, accepting QWidget text properties as well as methods."""
import sys
import os
import pickle
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
import quick_pilot as pilot
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QTabBar, QWidget


original = pilot.find_target
original_perform = pilot.perform


def calculated_perform(app, window, engine, step, last):
    path = os.environ.get('MERIDIANA_PHOTO_YEAR')
    if path and not getattr(window, '_photo_year_ready', False):
        with Path(path).open('rb') as file:
            fixture = pickle.load(file)  # Only the output of calculated_rho, never a user file.
        if engine == 'quick':
            host = window._photo_host
            host.bridge._finished(host.bridge.session.generation, fixture['energy'], [], {})
        else:
            window._abandon_year()
            generation = window.session.energy_asked()
            window._energy_done(generation, fixture['energy'])
        window._photo_year_ready = True
        pilot.pump(1800)
    return original_perform(app, window, engine, step, last)


def find_target(window, text, engine):
    if engine != 'widgets':
        return original(window, text, engine)
    for tab in window.findChildren(QTabBar):
        if tab.isVisible():
            for i in range(tab.count()):
                label = pilot.normal(tab.tabText(i))
                if label == text or label.partition(' ')[2] == text:
                    return tab, QPointF(tab.tabRect(i).center())
    for obj in window.findChildren(QWidget):
        value = getattr(obj, 'text', '')
        label = value() if callable(value) else value
        if obj.isVisible() and (obj.objectName() == text or pilot.normal(label) == text):
            return obj, QPointF(obj.rect().center())
    raise AssertionError(f'{engine}: no visible control with label {text!r}')


if __name__ == '__main__':
    if os.environ.get('MERIDIANA_PHOTO_YEAR'):
        from meridiana.quick import app as quick_app
        base = quick_app.QuickWindow
        class CaptureWindow(base):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Settings installs the saved profile; restore the explicitly requested photo theme.
                if kwargs.get('theme'):
                    self.theme.configure(kwargs['theme'])
                self.window._photo_host = self
        quick_app.QuickWindow = CaptureWindow
        pilot.perform = calculated_perform
    pilot.find_target = find_target
    pilot.__file__ = __file__
    pilot.main()
