"""The three icons the catalogue of 07/11/2026 found missing (meridiana-prove/icone-meridiana.html): «table» (the
Table view of the strings), «message-circle» (the tile «Report a problem»), «chevron-down» (Meridio's selector, which
now uses the chevron drawn for every menu, control:chevron-down). Lucide's, ISC (data/icons/lucide/LICENSE)."""
import unittest
from pathlib import Path

import _setup  # noqa: F401

ROOT = Path(__file__).resolve().parents[3]


class MissingIcons(unittest.TestCase):
    def test_table_and_message_circle_are_drawn(self):
        from meridiana.ui import icons
        for name in ("table", "message-circle"):
            data = icons.svg(name)
            self.assertTrue(data, name)
            self.assertIn(b'stroke="currentColor"', data)        # the theme's colour, as the others
            self.assertIn(b'viewBox="0 0 24 24"', data)           # the same grid

    def test_meridio_s_selector_uses_the_menu_s_chevron(self):
        # r22-unita: r22-f2 took Assistant/Selector.qml away; Meridio's choices are M.ComboBox, whose chevron is the
        # one drawn for every field (field:open). No QML asks any more for the missing «chevron-down» by name.
        qml = ROOT / "src/meridiana/quick/qml/Meridiana"
        self.assertFalse((qml / "Assistant/Selector.qml").exists())
        for page in ("ManualPage.qml", "SetupPage.qml"):
            self.assertIn("M.ComboBox", (qml / "Assistant" / page).read_text(encoding="utf-8"))
        self.assertIn('"field:open"', (qml / "Controls/ComboBox.qml").read_text(encoding="utf-8"))
        for path in qml.rglob("*.qml"):
            self.assertNotIn('iconName: "chevron-down"', path.read_text(encoding="utf-8"), path.name)

if __name__ == "__main__":
    unittest.main()
