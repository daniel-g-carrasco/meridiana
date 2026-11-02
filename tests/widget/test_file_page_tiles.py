"""The File page's tiles made congruent (R315, Daniel 02/11/2026: «questi gruppi di elementi non hanno dimensioni
armonizzate e congruenti»): the tiles of a row as tall as each other, the description with the room of two lines, the
formats and the button at the foot, at most three a row and never one alone under a full row; and the PVsyst files
of a module or an inverter imported from their catalogue. PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class RowSizes(unittest.TestCase):
    def test_no_tile_stands_alone_under_a_full_row(self):
        from meridiana.ui.file_page import row_sizes
        three = {0: [], 1: [1], 2: [2], 3: [3], 4: [2, 2], 5: [3, 2], 6: [3, 3], 7: [3, 2, 2], 8: [3, 3, 2],
                 9: [3, 3, 3], 10: [3, 3, 2, 2]}
        for count, sizes in three.items():
            self.assertEqual(row_sizes(count, 3), sizes, count)
        self.assertEqual(row_sizes(4, 2), [2, 2])
        self.assertEqual(row_sizes(5, 2), [2, 2, 1])               # two columns: an odd count leaves one
        self.assertEqual(row_sizes(3, 1), [1, 1, 1])
        self.assertEqual(row_sizes(2, 0), [1, 1])                  # never less than a column


class Tiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look("light")

    def section(self, tiles: list, width: int = 1400):
        from meridiana.ui.file_page import Section
        section = Section("Save and revisions", "Keep the current project.")
        section.group("Project", tiles)
        section.finish()
        section.resize(width, 800)
        section.show()
        self.addCleanup(_setup.dispose, section)
        _setup.wait_until(self.app, lambda: all(t.isVisible() for t in tiles), 5)
        self.app.processEvents()
        return section

    def tile(self, what: str, formats: tuple = ()):
        from meridiana.ui.file_page import Tile
        return Tile("save", "Save", what, formats, "Save", lambda: None)

    def foot(self, tile) -> int:
        """Where the button ends, from the tile's bottom edge."""
        return tile.height() - tile.button.geometry().bottom()

    def test_the_tiles_of_a_row_are_as_tall_and_their_buttons_stand_at_the_foot(self):
        """As the Save page: two tiles of one line and one of two, then a row with a long one; once a tile with
        no formats, which had a shorter foot."""
        tiles = [self.tile("Update the current project file."),
                 self.tile("Choose another name or location for the project.", (".mer",)),
                 self.tile("Keep this version in a new numbered file next to the project, with a longer sentence "
                           "that takes two lines at this width and maybe a third one.", ("_R01", "_R02")),
                 self.tile("One more.", ("PDF",)), self.tile("And the last.")]
        self.section(tiles)
        rows: dict = {}
        for t in tiles:
            rows.setdefault(t.y(), []).append(t)
        self.assertEqual([len(r) for r in rows.values()], [3, 2])             # 5 tiles: 3 + 2
        for row in rows.values():
            self.assertEqual({t.height() for t in row}, {row[0].height()}, "the tiles of a row are as tall")
            self.assertEqual({self.foot(t) for t in row}, {self.foot(row[0])}, "the buttons at the same height")
            for t in row:                   # every column as wide (the stretch shares the odd pixel out)
                self.assertLessEqual(abs(t.width() - tiles[0].width()), 1)
        first, second = rows.values()
        # the foot is anchored: the button is as far from the bottom in the tall row as in the short one
        self.assertEqual(self.foot(first[0]), self.foot(second[0]))
        self.assertLess(first[0].text.geometry().bottom(), first[0].button.geometry().top())

    def test_the_description_keeps_the_room_of_two_lines(self):
        from meridiana.ui.file_page import DESCRIPTION_LINES
        short, long = self.tile("Short."), self.tile("Short, with its formats.", ("PNG",))
        self.section([short, long])
        line = short.text.fontMetrics().lineSpacing()
        self.assertEqual(DESCRIPTION_LINES, 2)
        for t in (short, long):
            self.assertGreaterEqual(t.text.height(), 2 * line)
            self.assertTrue(t.text.alignment() & t.text.alignment().AlignTop)
        self.assertEqual(short.height(), long.height())

    def test_after_a_reflow_a_tile_that_changes_is_measured_again(self):
        """The rows laid out again for a new width (two columns, then three) still follow a tile whose text grows:
        the items taken out with takeAt stayed alive as the tiles' own, the new ones kept the old heights, and
        Help's first row stood a line taller than its tiles once Open and Save had been shown."""
        tiles = [self.tile("Short."), self.tile("Short too."), self.tile("And short.")]
        section = self.section(tiles, width=700)
        section.resize(1400, 800)
        _setup.wait_until(self.app, lambda: tiles[2].y() == tiles[0].y(), 5)
        before = tiles[0].height()
        tiles[1].text.setText(" ".join(["A sentence that grows to take many lines in its tile."] * 6))
        _setup.wait_until(self.app, lambda: tiles[1].height() > before, 5)
        self.assertEqual(tiles[1].height(), tiles[1].heightForWidth(tiles[1].width()))
        self.assertEqual({t.height() for t in tiles}, {tiles[1].height()})
        tiles[1].text.setText("Short again.")
        _setup.wait_until(self.app, lambda: tiles[1].height() == before, 5)
        self.assertEqual({t.height() for t in tiles}, {before})

    def test_four_tiles_go_two_and_two(self):
        tiles = [self.tile(f"Tile {n}.") for n in range(4)]
        self.section(tiles)
        self.assertEqual(len({t.y() for t in tiles}), 2)
        self.assertEqual(tiles[0].y(), tiles[1].y())
        self.assertEqual(tiles[2].y(), tiles[3].y())
        self.assertEqual(tiles[2].x(), tiles[0].x())


class CatalogueImports(unittest.TestCase):
    """R315: «Import from PVsyst…» in the catalogues of the modules and of the inverters, which closes the catalogue
    and asks the window for the file (_import_pvsyst); not in the others, nor without a window that imports."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def host(self):
        from PySide6.QtWidgets import QWidget

        class Host(QWidget):
            def __init__(self):
                super().__init__()
                self.asked = []

            def _import_pvsyst(self, kind, path=""):
                self.asked.append(kind)
        host = Host()
        self.addCleanup(_setup.dispose, host)
        return host

    def dialog(self, kind, parent):
        from meridiana.ui.catalog_dialog import CatalogDialog
        dialog = CatalogDialog(kind, parent, browse=True)
        self.addCleanup(_setup.dispose, dialog)
        _setup.wait_until(self.app, lambda: not dialog.reading, 20)     # the list read in a worker at the first time
        return dialog

    def test_the_modules_and_the_inverters_import_from_pvsyst(self):
        for kind, which in (("modules", "module"), ("inverters", "inverter")):
            host = self.host()
            dialog = self.dialog(kind, host)
            self.assertIsNotNone(dialog.import_pvsyst, kind)
            self.assertEqual(dialog.import_pvsyst.text(), "Import from PVsyst…")
            self.assertIn(".PAN" if kind == "modules" else ".OND", dialog.import_pvsyst.toolTip())
            dialog.show()
            self.app.processEvents()
            dialog.import_pvsyst.click()
            self.assertFalse(dialog.isVisible())                     # the catalogue closes first
            self.assertTrue(_setup.wait_until(self.app, lambda h=host: h.asked, 5))
            self.assertEqual(host.asked, [which])

    def test_the_other_catalogues_and_a_host_that_does_not_import_have_no_button(self):
        host = self.host()
        for kind in ("batteries", "optimizers", "microinverters"):
            self.assertIsNone(self.dialog(kind, host).import_pvsyst, kind)
        self.assertIsNone(self.dialog("modules", None).import_pvsyst)


if __name__ == "__main__":
    unittest.main()
