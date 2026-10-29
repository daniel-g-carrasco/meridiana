"""Starting on Linux: on a desktop Qt has no theme for (niri, sway, Hyprland) the portal's theme is used,
so the dark preference and the desktop's file dialogs are followed; elsewhere nothing is touched."""

import unittest
from unittest import mock

import _setup

from meridiana import app


class LinuxTheme(unittest.TestCase):
    def theme(self, environ: dict, platform: str = "linux") -> str | None:
        with mock.patch.object(app.sys, "platform", platform):
            app.linux_theme(environ)
        return environ.get("QT_QPA_PLATFORMTHEME")

    def test_niri_and_other_compositors_get_the_portal(self):
        for desktop in ("niri", "sway", "Hyprland", ""):
            self.assertEqual(self.theme({"XDG_CURRENT_DESKTOP": desktop}), "xdgdesktopportal", desktop)

    def test_desktops_with_a_qt_theme_keep_it(self):
        for desktop in ("KDE", "GNOME", "ubuntu:GNOME", "X-Cinnamon", "XFCE", "LXQt"):
            self.assertIsNone(self.theme({"XDG_CURRENT_DESKTOP": desktop}), desktop)

    def test_a_theme_chosen_by_the_user_stays(self):
        self.assertEqual(self.theme({"XDG_CURRENT_DESKTOP": "niri", "QT_QPA_PLATFORMTHEME": "gtk3"}), "gtk3")

    def test_windows_is_left_alone(self):
        self.assertIsNone(self.theme({"XDG_CURRENT_DESKTOP": "niri"}, platform="win32"))


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


if __name__ == "__main__":
    unittest.main()
