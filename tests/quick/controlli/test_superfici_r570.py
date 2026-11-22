"""R570: every surface that floats over the window keeps the pointer for itself (Daniel 09/11 and 14/11/2026).

«Tutte le finestre e i pannelli flottanti (Meridio, schede staccate, popup) devono fermare il passaggio del puntatore e
i clic verso ciò che sta sotto, in un solo posto»: the panel attached to a button (M.Popup, the jobs' list of the
status bar and the object picker are one), a menu (M.Menu), the help's bubble (M.HelpBubble), a window (M.Dialog)
and a card carried off its column (DockPanel floating), each over the stand-ins of quick/aiuti/sonde_puntatore.py,
where it has no control of its own: nothing behind reacts to the gestures given there. Meridio's bubble and character
are in quick/meridio/test_pointer_shield.py.
"""
import unittest

from PySide6.QtCore import QObject, QPointF

from quick.aiuti.sonde_puntatore import PointerProbes

HOST = 'M.Button { id: host; x: 120; y: 120; text: "host" }'
SURFACES = {
    'popup': HOST + '''
        M.Popup { objectName: "surface"; parent: host
            contentItem: Item { implicitWidth: 260; implicitHeight: 180 }
            Component.onCompleted: open() }''',
    'menu': HOST + '''
        M.Menu { objectName: "surface"; parent: host; y: host.height
            M.MenuItem { text: "Prima voce" }
            M.MenuItem { text: "Seconda voce" }
            Component.onCompleted: open() }''',
    'help': HOST + '''
        M.HelpBubble { objectName: "surface"; parent: host
            entry: ({text: "Una spiegazione lunga abbastanza da andare a capo, con le sue righe e i suoi spazi."})
            Component.onCompleted: open() }''',
    'dialog': '''
        M.Dialog { objectName: "surface"; title: "Finestra"; rejectText: "Chiudi"
            Item { implicitWidth: 300; implicitHeight: 160 }
            Component.onCompleted: open() }''',
    'card': '''
        DockPanel { objectName: "surface"; panelId: "carried"; zone: "floating"; title: "Scheda"
            floatX: 120; floatY: 120; floatWidth: 320; floatHeight: 240
            // what the workspace answers a card alone (Workbench.qml)
            workspace: QtObject { property bool settling: false; property string draggedPanel: ""
                property bool ghostReady: false
                function tabMembers(zone) { return [] } function stackedHere(panel) { return false }
                function activePanel(zone) { return "" } function arrangementChanged() {} } }''',
}


class SurfacesTest(PointerProbes, unittest.TestCase):
    def surface_scene(self, kind, name):
        text = ('import Meridiana.Shell\n' if name == 'card' else '') + 'Item {\n' + SURFACES[name] + '\n}'
        window, layer, probe, made = self.scene(kind, text, opened=False)
        surface = made.findChild(QObject, 'surface')
        self.assertIsNotNone(surface, name)
        if name != 'card':
            self.assertTrue(surface.property('opened'), name)
        # where the surface has no control: the middle of its frame for the popup, the window and the card (their
        # content draws nothing there), the left padding of the menu's frame, the words of the help
        if name == 'card':
            item = surface
            pos = item.mapToScene(QPointF(item.width() / 2, item.height() * 0.7))
        elif name == 'menu':
            item = surface.property('background')
            pos = item.mapToScene(QPointF(2, item.height() / 2))
        else:
            item = surface.property('contentItem')
            pos = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
        return window, probe, pos

    def test_nothing_behind_a_floating_surface_reacts(self):
        for name in SURFACES:
            for kind in ('handlers', 'mouse', 'button'):
                window, probe, pos = self.surface_scene(kind, name)
                # the two drags of KNOWN below
                self.check_blocked(window, probe, pos, f'{kind} under the {name}',
                                   skip_drag=(kind, name) in (('mouse', 'popup'), ('handlers', 'menu')))

    # KNOWN, not closed (r35-meridio, 14/11/2026), both inside Qt's popups (they stand in the overlay, which takes the
    # press for itself and not for what is drawn in it): after a drag begun on an M.Popup's frame, the hover goes on
    # through it to what is behind until the next click; a drag begun on a menu's frame (its padding) is taken over by a
    # DragHandler behind (only the order of the inverters, PlantPage, has one). Stated in docs/quick/stato/r35-meridio.md.
    @unittest.expectedFailure
    def test_after_a_drag_on_a_popup_nothing_behind_is_hovered(self):
        window, probe, pos = self.surface_scene('mouse', 'popup')
        self.move(window, pos)
        self.drag(window, pos)
        self.move(window, pos + QPointF(5, 5))
        self.assertFalse(probe.property('hovered'))

    @unittest.expectedFailure
    def test_a_drag_handler_behind_a_menu_does_not_take_its_drag(self):
        window, probe, pos = self.surface_scene('handlers', 'menu')
        self.move(window, pos)
        self.drag(window, pos)
        self.assertEqual(probe.property('drags'), 0)


if __name__ == '__main__':
    unittest.main()
