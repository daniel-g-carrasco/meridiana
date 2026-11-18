"""The Plant's small windows (R458 voci 9 e 10, «scelte sì/no» difetto 6; 06/11/2026).

- The inverter sized by itself: the list of the Widgets window (ui/brand_picker.py), the favourites under their
  heading then every manufacturer, rows and not buttons, and its buttons in Italian («Scegli», not «Choose»).
- No double border: a content that draws its own frame (the strings' form, the optimizer groups) is the window's frame;
  the others keep the dialog's frame.
- The automatic stringing says «proposto» where the modules in series are left to Meridiana, never «0».

    python -m unittest quick.impianto.test_plant_dialogs
"""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from meridiana import i18n, jobs
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import pump, wait_for
from quick.parity.differential import connected_fixture

setUpModule = _setup.keep_global_state

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def descendants(item):
    pending = [item]
    while pending:
        current = pending.pop()
        yield current
        pending.extend(current.childItems())


def texts(item):
    return [t for t in (c.property('text') for c in descendants(item)) if isinstance(t, str) and t]


class PlantDialogs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True,
                               theme={'theme': 'light', 'accent': 'indigo', 'backgrounds': 'grey'})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1600, 960)
        cls.win.show()
        cls.plant = cls.host.parts.controllers['plant']
        cls.actions = cls.host.parts.controllers['plantActions']
        cls.host.shell.trigger('phase_plant')
        wait_for(lambda: not cls.plant.busy and cls.plant.units, 60)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def tearDown(self):
        self.actions.dismiss()
        pump(150)

    def dialog(self, kind, name):
        self.actions.open(kind)
        pump(300)
        # A popup's item lies in the overlay while it is open, its QObject parent is the Dialog itself.
        found = next((i.parent() for i in descendants(self.win.contentItem())
                      if i.metaObject().className().startswith('QQuickPopupItem') and i.isVisible()
                      and i.parent() is not None and i.parent().objectName() == name), None)
        self.assertIsNotNone(found, name)
        self.assertTrue(found.property('visible'), name)
        return found

    def test_the_maker_list_is_the_widgets_one_in_italian(self):
        dialog = self.dialog('sizing', 'plant-maker-dialog')
        wait_for(lambda: len(self.plant.makers) > 3, 60)
        pump(200)
        popup = dialog.property('contentItem').parentItem()
        shown = texts(popup)
        self.assertIn('Scegli', shown)
        self.assertNotIn('Choose', shown)
        listing = next(i for i in descendants(popup) if i.objectName() == 'maker-list')
        rows = [i for i in descendants(listing) if i.objectName().startswith('maker-row-')]
        self.assertTrue(rows)
        self.assertFalse([r for r in rows if r.metaObject().className().startswith('Button')])
        # A favourite: its heading above it, then «all the manufacturers» in alphabetical order, the dimmed last.
        makers = self.plant.makers
        first = next(m['label'] for m in makers if m['sizable'])
        if not any(m['favourite'] for m in makers):
            self.plant.toggleFavourite(first)
            self.addCleanup(self.plant.toggleFavourite, first)
        pump(200)
        shown = texts(popup)
        self.assertIn('Preferiti', shown)
        self.assertIn('Tutte le marche', shown)
        rest = [m for m in self.plant.makers if not m['favourite']]
        sizable = [m['label'] for m in rest if m['sizable']]
        self.assertEqual(sizable, sorted(sizable, key=str.casefold))
        self.assertTrue(all(m['sizable'] for m in rest[:len(sizable)]))

    def test_a_framed_content_leaves_its_frame_to_the_window(self):
        # R518: one frame and one set of margins, the window's (before R518 the card was the frame, R458 voce 10, with
        # margins of its own: «quella della stringatura in automatico non ha gli stessi margini che hanno le altre»)
        clear = self.dialog('clear', 'plant-clear-dialog')
        sides = [clear.property(side) for side in ('leftPadding', 'rightPadding', 'topPadding', 'bottomPadding')]
        self.actions.dismiss()
        pump(150)
        for kind, name in (('proposal', 'plant-proposal-dialog'),):
            dialog = self.dialog(kind, name)
            self.assertFalse(dialog.property('contentFramed'), name)
            self.assertEqual([dialog.property(side) for side in ('leftPadding', 'rightPadding', 'topPadding', 'bottomPadding')], sides, name)
            self.assertGreater(dialog.property('frameWidth'), 0, name)
            card = dialog.property('contentItem')
            self.assertTrue(card.property('bare'), name)
            self.assertEqual(card.property('color').alpha(), 0, name)          # no ground of its own
            self.assertNotEqual(dialog.property('title'), '', name)
            self.assertNotEqual(dialog.property('acceptText'), '', name)
            self.actions.dismiss()
            pump(150)

    def test_a_plain_content_keeps_the_dialog_frame(self):
        dialog = self.dialog('clear', 'plant-clear-dialog')
        self.assertFalse(dialog.property('contentFramed'))
        self.assertGreater(dialog.property('frameWidth'), 0)
        self.assertGreater(dialog.property('leftPadding'), 0)

    def test_modules_in_series_left_to_meridiana_say_proposto(self):
        dialog = self.dialog('proposal', 'plant-proposal-dialog')
        field = next(i for i in descendants(dialog.property('contentItem')) if i.objectName() == 'plant-propose-series')
        if self.plant.settings.get('n_series'):
            self.skipTest('the fixture asks for a number of modules in series')
        self.assertEqual(field.property('text'), 'proposto')
        self.assertFalse(field.property('invalid'))
        self.assertEqual(field.property('currentValue'), 0)


if __name__ == '__main__':
    unittest.main()
