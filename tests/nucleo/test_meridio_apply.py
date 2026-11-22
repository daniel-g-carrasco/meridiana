"""«Apply» checks again the values a proposal was made on (study 50, 4.1 and 7.2 point 3): between the card and the
click the project can change, and a change computed on a value that is no longer there is not applied. No Qt."""

import unittest
from unittest import mock

import _setup  # noqa: F401
from _fakes import Host, with_problems
from _fixtures import capannone_rho

from meridiana.app.assistant import tools


def problems_host(**more) -> Host:
    p = capannone_rho()
    p.subfields[0].filled = True
    return with_problems(Host(p, **more))


class StillValid(unittest.TestCase):
    def test_an_edit_whose_field_changed_meanwhile_is_not_applied_and_the_reason_names_the_field(self):
        host = problems_host()
        made = tools.run("propose_edit", {"kind": "subfield", "id": "s1", "changes": {"params.tilt": 20},
                                          "reason": "meno ombra"}, host, tools.State())
        self.assertEqual(tools.changed_since(made.proposal, host), "")
        host.project.subfields[0].params["tilt"] = 25.0          # the designer typed another tilt meanwhile
        why = tools.changed_since(made.proposal, host)
        self.assertIn("tilt", why)
        self.assertIn("25", why)
        self.assertIn("15", why)

    def test_a_section_edit_and_an_object_gone_are_seen(self):
        host = problems_host()
        made = tools.run("propose_edit", {"kind": "economics", "changes": {"capex_per_kwp": 1100},
                                          "reason": "preventivo"}, host, tools.State())
        self.assertEqual(tools.changed_since(made.proposal, host), "")
        host.project.economics["capex_per_kwp"] = 1000.0
        self.assertNotEqual(tools.changed_since(made.proposal, host), "")
        gone = tools.run("propose_edit", {"kind": "subfield", "id": "s1", "changes": {"params.tilt": 20},
                                          "reason": "x"}, host, tools.State())
        host.project.subfields.clear()
        self.assertIn("no longer", tools.changed_since(gone.proposal, host))

    def test_a_fix_is_refused_when_its_check_is_gone_or_its_value_changed(self):
        host = problems_host()
        state = tools.State()
        tools.run("read_checks", {"min_level": "warn"}, host, state)
        energy = tools.run("propose_fix", {"check_id": "c1"}, host, state)       # strings.auto: True
        edit = tools.run("propose_fix", {"check_id": "c2"}, host, state)         # params.shade_free: True
        self.assertEqual(tools.changed_since(energy.proposal, host), "")
        self.assertEqual(tools.changed_since(edit.proposal, host), "")
        host.project.subfields[0].params["shade_free"] = True                     # done by hand meanwhile
        self.assertNotEqual(tools.changed_since(edit.proposal, host), "")
        host.project.energy.setdefault("strings", {})["auto"] = True
        self.assertNotEqual(tools.changed_since(energy.proposal, host), "")

    def test_an_undo_whose_step_changed_is_refused(self):
        host = problems_host()
        host.history_text = mock.Mock(return_value="Meridio: tilt")
        made = tools.run("propose_undo", {"action": "undo"}, host, tools.State())
        self.assertEqual(tools.changed_since(made.proposal, host), "")
        host.history_text.return_value = "Rename"
        self.assertIn("Rename", tools.changed_since(made.proposal, host))


if __name__ == "__main__":
    unittest.main()
