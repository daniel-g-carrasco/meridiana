"""A building with very many hand-drawn pitches or sides: Properties says how many there are instead of a group of
controls for each one, and the forms made ahead after the opening never take a form too big to make at once (an
imported roof of 158 pitches on 191 sides asked for 1627 controls and froze the window)."""
import unittest
from unittest import mock

from meridiana.core.model import model
from meridiana.gui.backend import properties, properties_schema
from meridiana.gui.backend.properties_schema import MAX_LISTED_PITCHES, MAX_LISTED_SIDES


def rect(x0, y0, x1, y1):
    return [[float(x0), float(y0)], [float(x1), float(y0)], [float(x1), float(y1)], [float(x0), float(y1)]]


def jagged(sides):
    """An outline of so many sides: a toothed bottom edge, closed by three straight sides over it."""
    teeth = sides - 3
    bottom = [[float(i), 0.0 if i % 2 == 0 else 0.2] for i in range(teeth + 1)]
    return [*bottom, [float(teeth), 10.0], [0.0, 10.0]][:sides]


def free_roof(pitches):
    return model.Roof(type='free', joined=False, free_pitches=[
        {"id": f"p{i + 1}", "ring": rect(i, 0.5, i + 1, 10), "eave_side": 0, "eave": 6.0, "tilt": 10.0}
        for i in range(pitches)])


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import _setup
        from meridiana import i18n
        cls.app = _setup.qt_or_skip()
        cls.language = i18n.language()
        i18n.setup("en")

    @classmethod
    def tearDownClass(cls):
        from meridiana import i18n
        i18n.setup(cls.language)

    def start(self, pitches=1, sides=4, buildings=1):
        from _fixtures import capannone
        from meridiana.app.session import ProjectSession
        self.project = capannone()
        first = self.project.buildings[0]
        first.footprint, first.height = (rect(0, 0, 40, 20) if sides == 4 else jagged(sides)), 6.0
        first.roof = free_roof(pitches)
        for n in range(1, buildings):
            twin = model.Building(id=self.project.new_id("b"), name=f"Corpo {n + 1}", footprint=jagged(sides),
                                  height=6.0, roof=free_roof(pitches))
            self.project.buildings.append(twin)
        self.session = ProjectSession(self.project)
        self.backend = properties.PropertiesBackend(self.session)
        self.addCleanup(self.backend.close)
        self.building = first

    def select(self):
        self.session.select("building", self.building.id)
        self.app.processEvents()

    def data(self, key):
        field = self.backend.field(key)
        return None if field is None else field.data


class ManyPitches(Base):
    def test_pitches_over_the_limit_are_one_note(self):
        self.start(pitches=MAX_LISTED_PITCHES + 1)
        self.select()
        self.assertIsNone(self.data('free.0.tilt'))
        self.assertIsNone(self.data(f'free.{MAX_LISTED_PITCHES}.eave_side'))
        self.assertIsNone(self.data('pick_free_eave:0'))
        self.assertIn(str(MAX_LISTED_PITCHES + 1), self.data('free_many')['value'])
        self.assertEqual(self.data('roof.type')['value'], 'free')     # the building's and the roof's own fields stay
        self.assertIsNotNone(self.data('roof.joined'))
        self.assertIsNotNone(self.data('height'))

    def test_pitches_up_to_the_limit_are_listed_as_before(self):
        self.start(pitches=MAX_LISTED_PITCHES)
        self.select()
        self.assertIsNone(self.data('free_many'))
        for i in (0, MAX_LISTED_PITCHES - 1):
            for part in ('eave_side', 'eave', 'tilt', 'percent', 'ridge', 'depth', 'swap'):
                self.assertIsNotNone(self.data(f'free.{i}.{part}'), f'free.{i}.{part}')

    def test_what_names_a_pitch_not_shown_changes_nothing_and_raises_nothing(self):
        self.start(pitches=MAX_LISTED_PITCHES + 1)
        self.select()
        before = self.session.undo.count()
        self.assertFalse(self.backend.commit('free.0.eave_side', 2))      # as a pick on the plan would send it
        self.assertFalse(self.backend.commit('free.0.tilt', '30'))
        self.backend.trigger('free.0.swap')
        self.assertEqual(self.session.undo.count(), before)
        self.assertEqual(self.session.project.building(self.building.id).roof.free_pitches[0]['tilt'], 10.0)


class ManySides(Base):
    def test_sides_over_the_limit_are_one_note(self):
        self.start(sides=MAX_LISTED_SIDES + 1)
        self.select()
        self.assertEqual(len(self.session.project.building(self.building.id).footprint), MAX_LISTED_SIDES + 1)
        self.assertIsNone(self.data('side.0'))
        self.assertIn(str(MAX_LISTED_SIDES + 1), self.data('sides_many')['value'])
        self.assertFalse(self.backend.commit('side.0', '5'))

    def test_sides_up_to_the_limit_are_listed_as_before(self):
        self.start(sides=MAX_LISTED_SIDES)
        self.select()
        self.assertIsNone(self.data('sides_many'))
        self.assertIsNotNone(self.data('side.0'))
        self.assertIsNotNone(self.data(f'side.{MAX_LISTED_SIDES - 1}'))

    def test_a_sub_field_and_an_exclusion_follow_the_same_limit(self):
        self.start()
        ring = jagged(MAX_LISTED_SIDES + 1)
        s = properties_schema.Schema()
        s.outline(ring)
        self.assertEqual([f['id'] for f in s.sections[0]['fields']], ['sides_many'])

    def test_several_such_buildings_chosen_together_have_their_common_fields(self):
        self.start(pitches=MAX_LISTED_PITCHES + 1, sides=MAX_LISTED_SIDES + 1, buildings=2)
        schema = properties_schema.common_schema(self.session, 'building', self.session.project.buildings[:2])
        ids = {f['id'] for section in schema for f in section['fields']}
        self.assertIn('roof.joined', ids)
        self.assertFalse(any(i.startswith(('free.', 'side.')) for i in ids))


class WarmForms(Base):
    def made(self):
        """The forms one call of warmForms makes (its names and its fields), and the timer it would start."""
        made, before = [], set(self.backend._forms)
        self.backend.formAdded.connect(made.append)
        with mock.patch.object(properties.QTimer, 'singleShot') as later:
            self.backend.warmForms()
        self.backend.formAdded.disconnect(made.append)
        self.fields = [form[2] for shape, form in self.backend._forms.items() if shape not in before]
        return made, later

    def test_a_huge_imported_roof_is_made_ahead_small_and_at_once(self):
        self.start(pitches=200, sides=200)
        made, later = self.made()
        self.assertEqual(len(made), 1)
        fields, = self.fields
        self.assertLessEqual(len(fields), properties.MAX_WARM_FIELDS)
        self.assertNotIn('free.0.tilt', fields)
        self.assertNotIn('side.0', fields)
        later.assert_called_once()                  # the next form, if any, in a later turn of the window
        made, later = self.made()                   # that later turn: nothing left to make, nothing scheduled
        self.assertEqual(made, [])
        later.assert_not_called()

    def test_a_form_over_the_limit_is_left_for_when_it_is_chosen(self):
        self.start(pitches=MAX_LISTED_PITCHES)
        with mock.patch.object(properties, 'MAX_WARM_FIELDS', 20):
            made, later = self.made()
        self.assertEqual(made, [])
        self.assertEqual(self.fields, [])
        later.assert_not_called()                   # passed over, not tried again and again
        self.select()                               # chosen, it is made as always
        self.assertIsNotNone(self.data('free.0.tilt'))


if __name__ == '__main__':
    unittest.main()
