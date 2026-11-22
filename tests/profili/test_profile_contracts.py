"""Profile identity is persisted and participates in all computation identities."""

import copy
import unittest

import _setup  # noqa: F401
from meridiana.core.model import model
from meridiana.app.session import ProjectSession, topics_of


class ProfileContracts(unittest.TestCase):
    def test_legacy_positional_project_arguments_keep_their_meaning(self):
        p = model.Project("Synthetic", "example-id", "example-series")
        self.assertEqual((p.job_id, p.series_id, p.regulatory_profile), ("example-id", "example-series", "it"))

    def test_initial_rule_adapter_preserves_legacy_results(self):
        from meridiana.core.rules import registry, rules, checks, vvf_activities
        from profili.fixtures import facts
        profile = registry.get("it")
        f = facts()
        self.assertEqual(profile.rules(), tuple(rules.RULES))
        self.assertEqual(profile.minimum(f), rules.minimum(f))
        self.assertEqual(profile.rule_items(f), checks.rule_items(f))
        self.assertEqual(profile.activity(1), vvf_activities.activity(1))

    def test_registry_is_explicit_and_immutable(self):
        from meridiana.core.rules import registry
        from dataclasses import FrozenInstanceError
        p = model.Project()
        profile = registry.for_project(p)
        self.assertEqual((profile.id, profile.revision), ("it", 1))
        self.assertEqual(registry.effective_timezone(p), "Europe/Rome")
        for bad in (None, "", "unknown", "IT"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                registry.get(bad)
        with self.assertRaises(FrozenInstanceError):
            profile.id = "other"

    def test_format_migration_and_internal_copy(self):
        raw = model.Project().to_json()
        self.assertEqual(raw["version"], model.FORMAT_VERSION)       # 31 added the profile; 32 the obstacles' base
        self.assertEqual(raw["regulatory_profile"], "it")
        raw["site"]["timezone"] = "Pacific/Auckland"
        self.assertEqual(model.Project.from_json(raw, check=False).site.timezone, "Pacific/Auckland")
        old = copy.deepcopy(raw)
        old["version"] = 30
        old.pop("regulatory_profile")
        old["site"].pop("timezone")
        p = model.Project.from_json(old)
        self.assertEqual((p.regulatory_profile, p.site.timezone), ("it", "Europe/Rome"))
        self.assertNotIn("regulatory_profile", model.DESIGN)
        self.assertNotIn("site", model.DESIGN)

    def test_invalid_identity_and_timezone_are_rejected(self):
        raw = model.Project().to_json()
        for bad in (None, "", "unregistered"):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "regulatory_profile"):
                model.Project.from_json({**raw, "regulatory_profile": bad})
        raw.pop("regulatory_profile", None)
        with self.assertRaisesRegex(ValueError, "regulatory_profile"):
            model.Project.from_json(raw)
        raw["regulatory_profile"] = "it"
        for bad in (None, 1, "MadeUp/Zone"):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "site.timezone"):
                model.Project.from_json({**raw, "site": {**raw["site"], "timezone": bad}})

    def test_profile_change_topics_and_timezone_cache_identity(self):
        p = model.Project()
        before = p.to_json()
        topics = topics_of(before, {**before, "regulatory_profile": "generic"})
        self.assertTrue({"project:rules", "project:site", "project:fire", "project:energy", "checks"} <= topics)
        session = ProjectSession(p)
        state, energy = session.state_key(), session.energy_key()
        p.site.timezone = "UTC"
        self.assertNotEqual(session.state_key(), state)
        self.assertNotEqual(session.energy_key(), energy)

    def test_profile_revision_participates_in_keys(self):
        from unittest.mock import patch
        from meridiana.core.rules import registry
        from profili.fixtures import projects
        from dataclasses import replace
        p = next(projects())[1]
        session = ProjectSession(p)
        sf = p.subfields[0]
        state, energy, layout = session.state_key(), session.energy_key(), p.layout_key(sf)
        with patch.dict(registry._PROFILES, it=replace(registry.get("it"), revision=2)):
            self.assertNotEqual(session.state_key(), state)
            self.assertNotEqual(session.energy_key(), energy)
            self.assertNotEqual(p.layout_key(sf), layout)

    def test_late_year_is_discarded_after_timezone_edit_and_undo(self):
        session = ProjectSession(model.Project())
        generation = session.energy_asked()
        session.edit("Timezone", lambda p: setattr(p.site, "timezone", "UTC"))
        self.assertFalse(session.energy_done(generation, {"stale": True}))
        session.undo.undo()
        self.assertEqual(session.project.site.timezone, "")

    def test_late_layout_is_discarded_after_timezone_edit(self):
        session = ProjectSession(model.Project())
        generation = session.generation
        session.edit("Timezone", lambda p: setattr(p.site, "timezone", "UTC"))
        self.assertFalse(session.layout_done(generation, {}, {}))
