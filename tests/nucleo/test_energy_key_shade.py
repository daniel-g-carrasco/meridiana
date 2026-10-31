"""The energy year is no longer good when what shades its modules changes (31/10/2026): an obstacle made taller,
another building raised, even for a sub-field that does not keep out of the shadows."""
import unittest

import _setup  # noqa: F401
from _fixtures import capannone


class ShadeInTheKey(unittest.TestCase):
    def test_an_obstacle_or_a_building_changed_changes_the_key(self):
        from meridiana import model
        from meridiana.session import ProjectSession as Session
        session = Session(capannone())
        p = session.project
        before = session.energy_key()
        b = p.buildings[0]
        p.exclusions.append(model.ExclusionItem(id="e9", ring=[(1.0, 1.0), (2.0, 1.0), (2.0, 2.0), (1.0, 2.0)],
                                                kind="chimney", building=b.id, height=1.0))
        with_chimney = session.energy_key()
        self.assertNotEqual(before, with_chimney)
        p.exclusions[-1].height = 3.0
        self.assertNotEqual(with_chimney, session.energy_key())
        raised = session.energy_key()
        b.height += 2.0
        self.assertNotEqual(raised, session.energy_key())


if __name__ == "__main__":
    unittest.main()
