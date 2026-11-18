"""What the system says of the look (ui/theme.py, SystemAccent): on Linux the portal's accent and its reduced motion
read with gdbus without waiting. PySide6 and a display (offscreen will do)."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class PortalAccent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    @unittest.skipUnless(sys.platform.startswith("linux"), "the portal is Linux's")
    def test_the_portals_accent_is_read_without_waiting(self):
        from _setup import wait_until

        from meridiana.ui.theme import SystemAccent
        folder = Path(tempfile.mkdtemp())
        fake = folder / "gdbus"                             # what gdbus prints on Lucciola: GNOME's yellow
        fake.write_text("#!/bin/sh\ncase \"$*\" in *reduced-motion*) echo '(<uint32 1>,)';; "
                        "*) echo '(<(0.78431372549019607, 0.53333333333333333, 0.0)>,)';; esac\n")
        fake.chmod(0o755)
        heard = []
        with mock.patch.dict(os.environ, {"PATH": f"{folder}{os.pathsep}{os.environ.get('PATH', '')}"}):
            reader = SystemAccent(self.app)
            reader.changed.connect(heard.append)
            reader.motion.connect(heard.append)
            self.assertEqual(reader.value, "")                  # not waited for
            self.assertTrue(wait_until(self.app, lambda: sorted(map(str, heard)) == ["#c88800", "True"], 5))
        self.assertEqual((reader.value, reader.reduced_motion), ("#c88800", True))
        reader.deleteLater()


if __name__ == "__main__":
    unittest.main()
