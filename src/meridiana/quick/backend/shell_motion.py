"""The transitions of File and of the phases (R471, R483), with all animation on the scene graph.

R483 (Daniel 06/11/2026: «l'apertura di File, così come il ripassaggio a una delle fasi, non ha praticamente animazione
e fluidità»; worst going back to a phase with the plan): one picture of the old page, the page changed under it at
once, and the picture fading out over the new one when that one has been drawn (Workbench.qml, fileVeil). Before,
File took two pictures (the second of the new page, a whole render more of waiting, and taken on the next turn of the
loop, before a page made late was there) and crossed them through the window's ground; the phases had nothing."""
from PySide6.QtCore import QObject, QTimer, Slot

PHASES = ['model', 'plant', 'production', 'consumption', 'economics', 'report']


class FileMotion(QObject):
    """R21 F6c, on the backend-QML contract (docs/studio/39-contratto-backend-qml.md): Python asks the window for a
    picture (Workbench.captureFileMotion; since r24-fasi, studio 41 S1, no picture: the window answers at once and the
    new page fades in from the window's ground, no more Item.grabToImage read back) and applies the change
    when the window answers (covered), or at once when a picture is not possible. Never grabWindow(): on lucciola it
    blocked the main thread for ever leaving Relazione (confronto-r20.md). The state read is what the QML passes."""
    def __init__(self, host):
        super().__init__(host.engine)
        self.host, self.serial = host, 0
        self.switching = False
        self._pending = {}
        self._fallback = QTimer(self)
        self._fallback.setSingleShot(True)
        self._fallback.setInterval(250)         # a picture that never comes (window hidden meanwhile): the change alone
        self._fallback.timeout.connect(lambda: self.covered(self.serial, False))

    def bind(self):
        self.host.shell.fileRequested.connect(self.change)

    def change(self, opened):
        """File opened or closed (Workbench.fileOpen)."""
        window = self.host.window
        if self.switching:                      # a phase chosen from File: one transition, the phase's
            window.applyFile(opened)
            return
        self.cover(lambda: window.applyFile(opened), 1 if opened else -1)

    @Slot(str, str, bool)
    def phase(self, value, before, file_open):
        """A phase chosen (Workbench.showPhase), from another or from File; the phase and File shown come with it."""
        window = self.host.window
        step = (PHASES.index(value) - PHASES.index(before)) if value in PHASES and before in PHASES else 1

        def switch():
            self.switching = True
            try:
                window.applyPhase(value)
            finally:
                self.switching = False
        if value == before and not file_open:
            # r21-unita: the phase on show asked again while another one waits for its picture (Ctrl+1 then Ctrl+2
            # then Ctrl+1 at once): the last one wins, the change on its way is dropped
            if self._pending:
                self._pending.clear()
                self._fallback.stop()
            return
        self.cover(switch, 1 if step >= 0 else -1)

    def cover(self, change, direction):
        """The old page as a picture over the window, the change under it, the picture fading when the new page has
        been drawn. Without a window shown or with less motion asked, the change alone."""
        window = self.host.window
        self.serial += 1
        if not window.isVisible() or self.host.theme.reducedMotion:
            self._pending.clear()
            change()
            window.stopFileMotion()
            return
        if self._pending:                       # a change asked while the picture before is still on its way
            previous = self._pending.pop(max(self._pending))
            previous()
        self._pending[self.serial] = change
        window.captureFileMotion(self.serial, direction)
        self._fallback.start()

    @Slot(int, bool)
    def covered(self, serial, pictured):
        """Workbench.captureFileMotion: the picture is there (the veil starts with the change) or could not be taken."""
        change = self._pending.pop(serial, None)
        if change is None:
            return
        self._fallback.stop()
        window = self.host.window
        if pictured:
            window.beginVeil()
        change()
        if not pictured:
            window.stopFileMotion()
