"""Starting on Windows: the program's identity (the mutex an update looks for, the AppUserModelID of its shortcuts)
and what the installer writes for it. (The theme of a Linux desktop Qt does not know is no longer chosen here:
tried on Niri on 10/11/2026, the Flatpak follows the system's dark preference and opens the system's file dialogs
by itself.)"""

import unittest
from unittest import mock

import _setup

from meridiana.gui import startup as app


class WindowsIdentity(unittest.TestCase):
    """The mutex the installer looks for to start the program again after an update, and the AppUserModelID of its
    shortcuts (task 18f)."""

    @unittest.skipUnless(_setup.WINDOWS, "Windows only")
    def test_the_program_holds_a_mutex_named_as_its_id_while_it_runs(self):
        import ctypes
        name = "io.github.daniel_g_carrasco.meridiana.test"            # not the program's: it may be running
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenMutexW.restype = ctypes.c_void_p
        synchronize = 0x00100000
        self.assertFalse(kernel32.OpenMutexW(synchronize, False, name))
        handle = app.windows_identity(name)
        self.assertTrue(handle)
        other = kernel32.OpenMutexW(synchronize, False, name)        # what Setup's CheckForMutexes does
        self.assertTrue(other)
        kernel32.CloseHandle(ctypes.c_void_p(other))
        app._RUNNING.remove(handle)
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        self.assertFalse(kernel32.OpenMutexW(synchronize, False, name))
        got = ctypes.c_wchar_p()
        ctypes.windll.shell32.GetCurrentProcessExplicitAppUserModelID(ctypes.byref(got))
        self.assertEqual(got.value, name)

    def test_nothing_elsewhere(self):
        with mock.patch.object(app.sys, "platform", "linux"):
            self.assertEqual(app.windows_identity("x"), 0)

    def test_the_installer_looks_for_that_mutex_and_associates_the_project_files(self):
        import meridiana
        iss = (_setup.ROOT / "build-aux" / "windows" / "meridiana.iss").read_text(encoding="utf-8")
        self.assertIn(f'#define AppId "{meridiana.APP_ID}"', iss)
        self.assertIn("CheckForMutexes('{#AppId}')", iss)
        self.assertIn(r'Software\Classes\.mer"', iss)
        self.assertIn('application/x-meridiana-project+zip', iss)
        self.assertIn('"%1"', iss)
        manifest = (_setup.ROOT / "build-aux" / "windows" / "meridiana.manifest").read_text(encoding="utf-8")
        self.assertNotIn("<dpiAware", manifest)         # Qt makes itself per monitor V2: never decided before it

    def test_an_isolated_install_can_skip_shortcuts_and_every_association_entry(self):
        iss = (_setup.ROOT / "build-aux" / "windows" / "meridiana.iss").read_text(encoding="utf-8")
        self.assertIn("AllowNoIcons=yes", iss, "/NOICONS needs the optional checkbox even with its page hidden")
        registry = iss.split("[Registry]", 1)[1].split("[Run]", 1)[0]
        for line in registry.splitlines():
            if line.startswith("Root:"):
                self.assertIn("Tasks: associate", line, "An unchecked association task must write no class keys")
        supported = next(line for line in registry.splitlines() if "SupportedTypes" in line)
        self.assertIn("uninsdeletevalue", supported)
        self.assertIn("uninsdeletekeyifempty", supported)
        self.assertNotIn("Flags: uninsdeletekey;", supported, "Other registered types must survive uninstall")


if __name__ == "__main__":
    unittest.main()
