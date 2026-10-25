"""How the mouse moves the views: FreeCAD's navigation styles as tables of data (gesture -> action), plus «AutoCAD»
(FreeCAD's Revit style with a double middle click that fits the view, and the right button dragged to orbit, as
study 12a proposes) and «SketchUp» (study 15, 2.1-2.6). One state machine serves the plan and the 3D view: it
turns presses, moves, releases, double clicks and the wheel into actions; the plan ignores the orbit.

- A gesture is the set of buttons held and the modifiers held, matched exactly: «middle» pans in the CAD style,
  «middle + left» orbits, «Ctrl + right» pans.
- A press that does not move more than CLICK_PX before its release is a click: the left one selects (Ctrl adds),
  the middle one recentres the view on the point (FreeCAD's lookAtPoint), the right one opens the menu.
- The wheel zooms towards the cursor in every style.

Of FreeCAD's styles, what needs a keyboard while the mouse waits (Gesture's H, NX's Ctrl after the middle button)
or a touch screen is left out: the mouse part only. CAD's zoom «middle held, a short click of the left button,
then up and down» is not here either: Ctrl+Shift+right does the same in that style. No Qt here."""

from __future__ import annotations

from dataclasses import dataclass, field

CLICK_PX = 4.0          # a press that moves less than this is a click (FreeCAD and Qt use a few pixels too)
BUTTONS = ("left", "middle", "right")
MODIFIERS = ("ctrl", "shift", "alt")


def g(buttons: str, mods: str = "") -> tuple[frozenset, frozenset]:
    """A gesture written as words: g("middle left"), g("right", "ctrl shift")."""
    return frozenset(buttons.split()), frozenset(mods.split())


@dataclass(frozen=True)
class Style:
    name: str
    pan: tuple = ()
    orbit: tuple = ()
    zoom: tuple = ()                # zoom by dragging up and down
    select: tuple = (g("left"), g("left", "ctrl"))     # clicks that select (Ctrl: adds)
    middle_click: str = "recentre"  # "recentre" or ""
    middle_double: str = ""         # "fit" or ""
    right_click: str = "menu"
    notes: str = ""


# FreeCAD 26.3 / 1.1.4, study 15, table 2.2; AutoCAD and SketchUp from study 12a, 2.6
STYLES = {
    "autocad": Style("AutoCAD", pan=(g("middle"), g("left right")), orbit=(g("middle", "shift"), g("middle right"),
                                                                           g("right")),
                     zoom=(g("middle", "ctrl"), g("right", "ctrl shift")), middle_double="fit",
                     notes="FreeCAD's Revit style, a double middle click fits the view, the right button dragged orbits"),
    "cad": Style("CAD", pan=(g("middle"), g("right", "ctrl")),
                 orbit=(g("middle left"), g("middle right"), g("right", "shift")), zoom=(g("right", "ctrl shift"),)),
    "revit": Style("Revit", pan=(g("middle"), g("left right")), orbit=(g("middle", "shift"), g("middle right")),
                   zoom=(g("middle", "ctrl"), g("right", "ctrl shift"))),
    "blender": Style("Blender", pan=(g("middle", "shift"), g("left right")), orbit=(g("middle"),),
                     zoom=(g("middle", "ctrl"), g("right", "ctrl shift"))),
    "solidworks": Style("SolidWorks", pan=(g("middle", "ctrl"),), orbit=(g("middle"),), zoom=(g("middle", "shift"),)),
    "nx": Style("Siemens NX", pan=(g("middle", "shift"), g("middle right")), orbit=(g("middle"),),
                zoom=(g("middle left"),)),
    "openinventor": Style("OpenInventor", pan=(g("middle"), g("left", "ctrl shift")), orbit=(g("left"),),
                          zoom=(g("left middle"), g("middle", "ctrl")),
                          select=(g("left", "ctrl"), g("left", "shift"))),
    "opencascade": Style("OpenCascade", pan=(g("middle"), g("middle", "ctrl")),
                         orbit=(g("right", "ctrl"), g("middle right")), zoom=(g("left", "ctrl"),), middle_click=""),
    "openscad": Style("OpenSCAD", pan=(g("right"),), orbit=(g("left"),), zoom=(g("middle"), g("right", "shift")),
                      middle_click=""),
    "tinkercad": Style("TinkerCAD", pan=(g("middle"),), orbit=(g("right"),), middle_click=""),
    "touchpad": Style("Touchpad", pan=(g("", "shift"),), orbit=(g("", "alt"), g("left", "shift")),
                      zoom=(g("", "ctrl shift"),), middle_click=""),
    "gesture": Style("Gesture", pan=(g("right"),), orbit=(g("left"), g("left", "alt"))),
    "maya": Style("Maya-Gesture", pan=(g("middle", "alt"),), orbit=(g("left", "alt"),), zoom=(g("right", "alt"),)),
    "sketchup": Style("SketchUp", pan=(g("middle", "shift"), g("middle left")), orbit=(g("middle"),),
                      middle_click="", middle_double="recentre"),
}
DEFAULT_STYLE = "autocad"


def style_names() -> dict:
    return {k: s.name for k, s in STYLES.items()}


def gesture_text(gesture: tuple) -> str:
    """A gesture in words: «Shift + middle», «middle + right», «Ctrl + Shift + right»."""
    from .i18n import _
    buttons, mods = gesture
    names = {"left": _("left"), "middle": _("middle"), "right": _("right"), "ctrl": _("Ctrl"), "shift": _("Shift"),
             "alt": _("Alt")}
    words = [names[m] for m in MODIFIERS if m in mods] + [names[b] for b in BUTTONS if b in buttons]
    return " + ".join(words) if buttons else " + ".join(words) + " " + _("and move")


def orbit_keys(style: Style) -> tuple[frozenset, ...]:
    """The keys that, held, make the next press of a button an orbit, one set of modifiers per way to do it: Shift in
    AutoCAD (Shift + middle) and in CAD (Shift + right). A gesture without a button orbits at once, with the keys
    alone (Touchpad's Alt): it has nothing to wait for. The 3D view shows where the orbit would turn while one of
    these is held (study 16, G2)."""
    return tuple(dict.fromkeys(mods for buttons, mods in style.orbit if buttons and mods))


def orbit_key_text(key: str) -> str:
    """The keys of orbit_keys in words, «Shift» or «Shift / Alt», for the preferences; empty when the style has none."""
    from .i18n import _
    names = {"ctrl": _("Ctrl"), "shift": _("Shift"), "alt": _("Alt")}
    style = STYLES.get(key, STYLES[DEFAULT_STYLE])
    return " / ".join(" + ".join(names[m] for m in MODIFIERS if m in mods) for mods in orbit_keys(style))


def table(key: str) -> list[tuple[str, str]]:
    """A style in words, for the preferences (Daniel, 23/10/2026: «nelle impostazioni deve essere spiegato bene cosa
    fa uno e cosa fa l'altro»): (what, how) for pan, orbit, zoom, recentre, fit, selection and menu, in this order,
    from the tables above."""
    from .i18n import _
    style = STYLES.get(key, STYLES[DEFAULT_STYLE])

    def words(gestures) -> str:
        return ", ".join(gesture_text(x) for x in gestures)
    zoom = _("the wheel, towards the cursor")
    if style.zoom:
        zoom += "; " + _("{gestures}, up and down").format(gestures=words(style.zoom))
    recentre = (_("a short click of the middle button") if style.middle_click == "recentre" else
                _("a double click of the middle button") if style.middle_double == "recentre" else
                _("not in this style"))
    fit = _("F, or «Fit» in the view's bar")
    if style.middle_double == "fit":
        fit = _("a double click of the middle button") + "; " + fit
    clicks = [x for x in style.select if x[0] == frozenset({"left"})]
    either = " " + _("or") + " "
    select = (_("a click of the left button") if clicks and not clicks[0][1] else
              _("a click with {gestures}").format(gestures=either.join(gesture_text(x) for x in clicks)))
    menu = _("a click of the right button, held still") if style.right_click == "menu" else _("not in this style")
    return [(_("Pan"), words(style.pan) or _("not in this style")),
            (_("Orbit (3D only)"), words(style.orbit) or _("not in this style")),
            (_("Zoom"), zoom), (_("Recentre on the point"), recentre), (_("Fit the view"), fit),
            (_("Select"), select), (_("Menu"), menu)]


def audience(key: str) -> str:
    """Whom a style suits, in a line next to its table."""
    from .i18n import _
    return {
        "autocad": _("As AutoCAD and Revit: for whoever draws in AutoCAD. Meridiana's default."),
        "cad": _("FreeCAD's default style: for whoever comes from FreeCAD."),
        "revit": _("As Revit: AutoCAD's hands without the double click that fits the view."),
        "blender": _("As Blender: for whoever models in Blender."),
        "solidworks": _("As SolidWorks: for whoever models parts in SolidWorks."),
        "nx": _("As Siemens NX: for whoever works in NX."),
        "openinventor": _("As OpenInventor: the left button orbits, so a click selects with Ctrl or Shift."),
        "opencascade": _("As the viewers of OpenCascade."),
        "openscad": _("As OpenSCAD: for whoever writes models in OpenSCAD."),
        "tinkercad": _("As TinkerCAD: few gestures, for whoever begins."),
        "touchpad": _("For a laptop without a mouse: the touchpad with Shift, Alt or Ctrl and Shift held."),
        "gesture": _("FreeCAD's Gesture style, the mouse part: the left button orbits, the right one pans."),
        "maya": _("As Maya: every gesture with Alt held."),
        "sketchup": _("As SketchUp: for whoever draws buildings in SketchUp."),
    }.get(key, "")


@dataclass(frozen=True)
class Action:
    kind: str           # "pan", "orbit", "zoom" (drag), "wheel", "select", "recentre", "fit", "menu"
    phase: str          # "begin", "move", "end" for a drag; "once" for the rest
    x: float = 0.0      # where the pointer is (pixels of the view)
    y: float = 0.0
    dx: float = 0.0     # what it moved since the last action of the drag; for the wheel, dy is the steps
    dy: float = 0.0
    mods: frozenset = frozenset()


@dataclass
class Navigator:
    style: Style = field(default_factory=lambda: STYLES[DEFAULT_STYLE])
    held: set = field(default_factory=set)
    mods: frozenset = frozenset()
    start: tuple | None = None          # where the first button went down
    last: tuple | None = None
    gesture: str = ""                   # the drag going on: "pan", "orbit", "zoom", or ""
    moved: bool = False                 # the press moved past CLICK_PX: no click at its release
    swallow: str = ""                   # the button whose release ends a double click: no click there
    before: str = ""                    # the gesture going on when a second button joined it
    spent: bool = False                 # a chord ended by letting a button go: nothing more until all are up

    def chorded(self, button: str) -> bool:
        """`button` makes a gesture with another button in this style (AutoCAD's left + right pan): pressed first,
        it may be the start of that gesture and not a click of its own."""
        return any(button in buttons and len(buttons) > 1
                   for buttons, _mods in self.style.pan + self.style.orbit + self.style.zoom)

    def previews_orbit(self, mods) -> bool:
        """The orbit's keys, exactly these, are held and nothing else is going on: no button held, no drag. The next
        press of the button is an orbit, and the 3D view may show where it would turn (study 16, G2)."""
        return not self.held and not self.gesture and frozenset(mods) in orbit_keys(self.style)

    def set_style(self, key: str) -> None:
        self.style = STYLES.get(key, STYLES[DEFAULT_STYLE])
        self.reset()

    def reset(self) -> None:
        self.held, self.start, self.last, self.gesture, self.moved = set(), None, None, "", False
        self.swallow, self.before, self.spent = "", "", False

    def _match(self, buttons, mods) -> str:
        key = (frozenset(buttons), frozenset(mods))
        for kind in ("orbit", "pan", "zoom"):
            if key in getattr(self.style, kind):
                return kind
        return ""

    def _switch(self, x: float, y: float) -> list[Action]:
        """The buttons or the modifiers changed while dragging: end one gesture, maybe begin another."""
        out = []
        kind = self._match(self.held, self.mods) if (self.moved or not self.held) and not self.spent else ""
        if kind != self.gesture:
            if self.gesture:
                out.append(Action(self.gesture, "end", x, y, mods=self.mods))
            self.gesture = kind
            if kind:
                out.append(Action(kind, "begin", x, y, mods=self.mods))
        return out

    def press(self, button: str, mods, x: float, y: float) -> list[Action]:
        self.mods = frozenset(mods)
        if not self.held:
            self.start, self.moved = (x, y), False
        else:
            self.before = self.gesture
        self.held.add(button)
        self.last = (x, y)
        return self._switch(x, y) if self.gesture else []

    def move(self, x: float, y: float, mods=None) -> list[Action]:
        """The pointer moved; with no button held only the modifier gestures (Touchpad: Shift pans) move."""
        if mods is not None:
            self.mods = frozenset(mods)
        out: list[Action] = []
        if self.last is None:
            self.last = (x, y)
        if self.held and not self.moved and self.start is not None:
            if abs(x - self.start[0]) + abs(y - self.start[1]) > CLICK_PX:
                self.moved = True
        if not self.held and not self._match(set(), self.mods) and not self.gesture:
            self.last = (x, y)
            return out
        if self.moved or not self.held:
            out += self._switch(x, y)
        if self.gesture:
            out.append(Action(self.gesture, "move", x, y, x - self.last[0], y - self.last[1], self.mods))
        self.last = (x, y)
        return out

    def release(self, button: str, mods, x: float, y: float) -> list[Action]:
        self.mods = frozenset(mods)
        out: list[Action] = []
        was = set(self.held)
        self.held.discard(button)
        if self.gesture:
            if not self.held:
                out.append(Action(self.gesture, "end", x, y, mods=self.mods))
                self.gesture = ""
            elif self._match(self.held, self.mods) not in ("", self.before):
                # what the buttons left would start on their own is not a way back: AutoCAD's pan with left and
                # right turned into an orbit when the left one went first (review, 23/10/2026)
                out.append(Action(self.gesture, "end", x, y, mods=self.mods))
                self.gesture, self.spent = "", True
            else:
                out += self._switch(x, y)
        elif button == self.swallow:
            self.swallow = ""
        elif not self.moved and was == {button}:
            out += self._click(button, x, y)
        if not self.held:
            self.start, self.moved, self.spent, self.before = None, False, False, ""
        return out

    def _click(self, button: str, x: float, y: float) -> list[Action]:
        if button == "left" and (frozenset({"left"}), self.mods) in self.style.select:
            return [Action("select", "once", x, y, mods=self.mods)]
        if button == "middle" and self.style.middle_click:
            return [Action(self.style.middle_click, "once", x, y, mods=self.mods)]
        if button == "right" and self.style.right_click:
            return [Action(self.style.right_click, "once", x, y, mods=self.mods)]
        return []

    def double(self, button: str, mods, x: float, y: float) -> list[Action]:
        """A double click. Qt sends press, release, press, double click, release: the release after the double
        is not a click of its own, or the fit of AutoCAD's double middle click was stopped at once by a recentre
        (review, 23/10/2026)."""
        if button == "middle" and self.style.middle_double:
            self.swallow = button
            return [Action(self.style.middle_double, "once", x, y, mods=frozenset(mods))]
        return []

    def wheel(self, steps: float, mods, x: float, y: float) -> list[Action]:
        """`steps` of the wheel, positive away from the user (zoom in), as Qt's angleDelta / 120."""
        return [Action("wheel", "once", x, y, 0.0, steps, frozenset(mods))]
