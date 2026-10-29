"""Registered settings use real controls and Meridio only reveals them, without editing or taking focus."""

import copy
import unittest
from types import SimpleNamespace
from unittest import mock

import _setup

from meridiana import config, model, phases

setUpModule = _setup.keep_global_state


class Targets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def window(self):
        from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget
        from meridiana.assistant.local import Survey
        from meridiana.ui.phasebar import Phases
        from meridiana.ui.preferences import Preferences
        from meridiana.ui.properties import Properties
        from meridiana.ui.theme import Theme
        window = QWidget()
        window.cfg = config.Config(network_tiles=False, network_pvgis=False)
        window.project = model.Project()
        window.theme = Theme(window.cfg, app=self.app)
        window.assistant_chat = SimpleNamespace(survey=lambda **_kwargs: Survey())
        window.tabs = Phases()
        for phase in phases.phases():
            window.tabs.add_phase(phase, QWidget())
        window.props = Properties()
        window.props.show_site(window.project, True)
        settings = Preferences(window.cfg, {}, window.theme, window)
        window.file_page = SimpleNamespace(settings=settings, close_page=lambda: None)
        window._preferences = settings.show_page
        def navigate(target):
            if target[0] == "phase":
                window.tabs.setCurrentIndex(window.tabs.index_of_phase(target[1]))
            else:
                window.props.show_site(window.project, True)
        window._navigate = navigate
        window.docks = (QWidget(window), QWidget(window))
        layout = QVBoxLayout(window)
        layout.addWidget(window.tabs.header)
        field = QLineEdit("Meridio's question stays here")
        layout.addWidget(field)
        layout.addWidget(settings)
        layout.addWidget(window.props)
        window.resize(800, 750)
        window.show()
        self.app.processEvents()
        field.setFocus()
        self.app.processEvents()
        self.addCleanup(_setup.dispose, window)
        self.addCleanup(window.theme.deleteLater)
        return window, field

    def test_every_registered_control_resolves_to_an_existing_widget(self):
        from PySide6.QtWidgets import QWidget
        from meridiana.ui import navigation_targets
        window, _field = self.window()
        for target in navigation_targets.controls():
            with self.subTest(id=target.id):
                self.assertIsInstance(target.widget(window), QWidget)
        ids = {row["id"] for row in navigation_targets.catalogue(window)}
        self.assertTrue({"navigation.mouse_style", "navigation.orbit", "navigation.pivot", "appearance.theme",
                         "appearance.text_size", "privacy.tiles", "assistant.voice", "report.profile",
                         "maps.background", "site.pod"}.issubset(ids))

    def test_window_host_opens_the_requested_section_and_highlights_without_editing(self):
        from meridiana.ui import motion, spotlight
        from meridiana.ui.assistant_chat import WindowHost
        window, field = self.window()
        before = copy.deepcopy(window.cfg.to_json())
        with mock.patch.object(motion, "reduced", return_value=True):
            WindowHost(window).go_to(("setting", "navigation.pivot"))
            self.assertIs(window.file_page.settings.pages.currentWidget(), window.file_page.settings.navigation)
            self.assertTrue(_setup.wait_until(self.app, lambda: bool(window.findChildren(spotlight.Spotlight))))
            shown = window.findChildren(spotlight.Spotlight)[0]
            self.assertIs(shown.target, window.file_page.settings.navigation.pivot)
            self.assertIs(self.app.focusWidget(), field)
            self.assertEqual(window.cfg.to_json(), before)

    def test_a_missing_control_does_not_silently_claim_navigation_succeeded(self):
        from meridiana.ui import navigation_targets
        window, _field = self.window()
        del window.file_page.settings.navigation.pivot
        with self.assertRaisesRegex(ValueError, "unavailable"):
            navigation_targets.show(window, ("setting", "navigation.pivot"))

    def test_a_phase_is_shown_and_its_tab_is_highlighted_without_changing_the_project(self):
        from meridiana.ui import motion, spotlight
        from meridiana.ui.assistant_chat import WindowHost
        window, field = self.window()
        before = copy.deepcopy(window.project.to_json())
        with mock.patch.object(motion, "reduced", return_value=True):
            WindowHost(window).go_to(("phase", "plant"))
            self.assertEqual(window.tabs.phase_id(), "plant")
            self.assertTrue(_setup.wait_until(self.app, lambda: bool(window.findChildren(spotlight.Spotlight))))
            shown = window.findChildren(spotlight.Spotlight)[0]
            self.assertIs(shown.target, window.tabs.tabBar())
            self.assertEqual(shown.region(), window.tabs.tabBar().tabRect(1))
            self.assertEqual(window.project.to_json(), before)
            self.assertIs(self.app.focusWidget(), field)

    def test_a_site_property_is_revealed_without_editing_it(self):
        from meridiana.ui import motion, spotlight
        from meridiana.ui.assistant_chat import WindowHost
        window, field = self.window()
        before = copy.deepcopy(window.project.to_json())
        with mock.patch.object(motion, "reduced", return_value=True):
            WindowHost(window).go_to(("property", "site.available_power"))
            self.assertTrue(_setup.wait_until(self.app, lambda: bool(window.findChildren(spotlight.Spotlight))))
            self.assertIs(window.findChildren(spotlight.Spotlight)[0].target, window.props.available)
            self.assertEqual(window.project.to_json(), before)
            self.assertIs(self.app.focusWidget(), field)

    def test_hidden_phases_are_not_offered_and_navigation_reports_the_reason(self):
        from meridiana.ui import navigation_targets
        window, _field = self.window()
        window.tabs.tabBar().setTabVisible(window.tabs.index_of_phase("plant"), False)
        self.assertNotIn({"kind": "phase", "id": "plant", "label": "Plant"}, navigation_targets.catalogue(window))
        with self.assertRaisesRegex(ValueError, "hidden"):
            navigation_targets.show(window, ("phase", "plant"))


if __name__ == "__main__":
    unittest.main()
