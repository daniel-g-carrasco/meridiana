"""R575: what the import made of an IFC model (its placement planes, its obstacles) is not drawn over the model's true
geometry in the 3D.

Daniel (13/11/2026, model A): on the roofs, two surfaces in the same plane took turns in jagged stripes; beside the shed
glazing, full rectangular «walls» with a diagonal. Neither was the simplified body (its faces were already unseen):
- the stripes were the import's placement planes (`ifc_import._offer_support`: a roof plane that the body's roof
  cannot reproduce, offered as a sub-field with its own plane, drawn by `mesh.support_triangles`), lying exactly on
  the model's own roof since its place and height were corrected (4fd7f4cc);
- the walls were the obstacles read from the model, drawn as upright prisms of their plan outline from the roof to
  their top: a sloping mullion of 5 x 5 cm made a wall 4 m high (model A, IfcMember of the shed's curtain wall).

The sample (tests/data/ifc/r575-falda-montante.ifc) has a roof slab falling towards no side of its outline (the import
offers its plane), a sloping mullion 2.8 m long standing on it and a chimney of 1 x 1 x 1.8 m (the import makes the
chimney an obstacle). Since 13/11/2026 a slender element leaning over a roof is no obstacle at all (ifc_read._leans): the
mullion's wall is gone, and the obstacle not drawn over the model is the chimney's prism. Off screen Qt Quick 3D draws
nothing: the tests read what goes to the GPU, the drawn mesh and the unseen one that is still picked."""
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PySide6.QtWidgets import QApplication

from meridiana.app import jobs
from meridiana.app.exchange import ifc_import, ifc_mesh, ifc_worker
from meridiana.app.session import ProjectSession
from meridiana.core.geometry import mesh
from meridiana.core.model import model
from meridiana.gui.backend.scene import SceneBackend

SAMPLE = Path(__file__).resolve().parents[2] / 'data' / 'ifc' / 'r575-falda-montante.ifc'
MULLION = 51                         # the record of «MONTANTE»
SUPPORT = (0.30, 0.60, 0.65)         # mesh.support_triangles' colour


def imported(folder: Path) -> tuple[model.Project, dict]:
    found = ifc_worker.read(str(SAMPLE), 'direct', lambda f, w: None, None, str(folder / 'cache'))
    project = model.Project()
    plan = ifc_import.plan(found, project, 'origin', None, name='t', source_name='t.ifc')
    ifc_import.apply(project, plan)
    return project, found


def vertices(geometry) -> np.ndarray:
    """The vertices given to the GPU: x, y, z (Qt axes), normal, rgba; none for an empty mesh (one dummy triangle)."""
    data = np.frombuffer(bytes(geometry.vertexData()), '<f4').reshape(-1, 10)
    return data if np.abs(data).sum() else data[:0]


def coloured(data: np.ndarray, rgb) -> int:
    """How many triangles of `data` have the colour `rgb`."""
    return int(np.all(np.abs(data[:, 6:9] - np.asarray(rgb, np.float32)) < 1e-3, axis=1).sum() // 3)


class DerivedPartsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.tmp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.tmp.name)
        cls.project, cls.found = imported(cls.folder)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def scene(self, project):
        session = ProjectSession(project)
        results, keys, _ = jobs.layout_of(session.project, {})
        session.layout_done(session.generation, results, keys)
        scene = SceneBackend(session, self.folder / 'scene')
        self.addCleanup(scene.close)
        self.assertTrue(scene.contextModels, 'the true geometry of the model is shown')
        return session, scene

    def copy(self):
        return model.Project.from_json(self.project.to_json())

    def test_the_sample_has_a_placement_plane_and_an_obstacle_from_the_model(self):
        p = self.project
        body = p.buildings[0]
        made = p.resources['ifc_reference']['derived']
        supports = [sf for sf in p.subfields if sf.support is not None]
        self.assertEqual([sf.id for sf in supports], made['supports'])
        self.assertEqual([e.id for e in p.exclusions], made['exclusions'])
        self.assertEqual(len(made['exclusions']), 1)
        self.assertEqual(supports[0].building, body.id)
        # the one obstacle is the chimney's upright prism, 1 x 1 m in plan and some 1.5 m above the roof ...
        prism = next(o for o in p.obstacle_prisms() if o['id'] == made['exclusions'][0])
        ring = np.asarray(prism['ring'])
        self.assertEqual(np.ptp(ring, axis=0).round(2).tolist(), [1.0, 1.0])
        self.assertAlmostEqual(p.exclusions[0].height, 1.5, delta=0.05)

    def test_the_sloping_mullion_is_no_obstacle(self):
        """The mullion was an upright prism some 2 m high on a strip 2.8 m long, a wall of about 5.9 m² a side, where
        the model has a bar of 5 x 5 cm: a slender element leaning over a roof is now left out and said."""
        p = self.project
        self.assertEqual(self.found['counts'].get('leaning'), 1)
        self.assertEqual([o['name'] for o in self.found['obstacles']], ['CAMINO'])
        self.assertEqual([e.kind for e in p.exclusions], ['chimney'])
        # the model has a bar of 5 x 5 cm: under 0.6 m² of faces in all, still in its true geometry
        m = ifc_mesh.load(p.resources['ifc_reference']['context']['mesh'])
        k = [int(e[0]) for e in m['elements']].index(MULLION)
        piece = int(m['piece_of'][k])
        v, f, _c = ifc_mesh.piece(m, piece)
        first, n = int(m['elements'][k][1]), int(m['elements'][k][2])
        t = v[f[first:first + n]].astype(float)
        area = float(np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum() / 2)
        self.assertLess(area, 0.6)

    def test_the_placement_plane_on_the_model_roof_is_not_drawn_and_its_modules_are(self):
        """Defect 1 (the stripes): the plane offered by the import lies on the model's roof and is not drawn over it;
        it is still picked, and the modules laid on it are drawn above the roof."""
        p = self.copy()
        sf = next(s for s in p.subfields if s.support is not None)
        sf.filled = True
        session, scene = self.scene(p)
        drawn, unseen = vertices(scene.geometry), vertices(scene.ghost_geometry)
        self.assertEqual(coloured(drawn, SUPPORT), 0, 'the placement plane drawn over the model\'s roof')
        self.assertGreater(coloured(unseen, SUPPORT), 0, 'the placement plane is still picked')
        self.assertGreater(scene.moduleCount, 0)
        surface = session.project.surface_of(sf)
        table = scene.module_table[:, :12].reshape(-1, 3, 4)
        for x, up, z in table[:, :, 3]:              # every module's middle above the plane, which is the model's roof
            self.assertGreater(up - surface.z(x, -z), 0.02)
        session.select('subfield', sf.id)
        self.assertTrue(scene._segments, 'the selection draws its outline')

    def test_the_obstacle_read_from_the_model_is_not_drawn_over_it(self):
        """Defect 2 (the walls): the obstacle read from the model (the chimney's prism) is not drawn over it; it stays
        in the calculation (the layout leaves it out) and is still picked."""
        p = self.copy()
        session, scene = self.scene(p)
        drawn, unseen = vertices(scene.geometry), vertices(scene.ghost_geometry)
        self.assertEqual(coloured(drawn, mesh.OBSTACLE), 0, 'the chimney\'s prism drawn over the model')
        self.assertGreater(coloured(unseen, mesh.OBSTACLE), 0)
        eid = p.exclusions[0].id
        self.assertIn(eid, {o['id'] for o in session.project.obstacle_prisms()})
        session.select('exclusion', eid)
        self.assertTrue(scene._segments)

    def test_what_the_designer_adds_on_the_model_is_drawn(self):
        p = self.copy()
        body = p.buildings[0]
        p.exclusions.append(model.ExclusionItem(id='e-mine', ring=[[-5, -3], [-4, -3], [-4, -2], [-5, -2]],
                                                kind='chimney', building=body.id, height=1.0))
        p.subfields.append(model.SubField('s-mine', 'Mine', [[1, -3], [5, -3], [5, 3], [1, 3]], building=body.id,
                                          support=model.SupportPlane(enabled=True, tilt=10, azimuth=0, z0=9.0)))
        _session, scene = self.scene(p)
        drawn = vertices(scene.geometry)
        self.assertGreater(coloured(drawn, mesh.OBSTACLE), 0)
        self.assertGreater(coloured(drawn, SUPPORT), 0)

    def test_a_project_imported_before_takes_what_stands_on_the_bodies_as_the_model_s(self):
        """No list of what the import made (`derived`, since R575): the obstacles and the planes on the model's bodies
        are its own, as they were in every such project."""
        p = self.copy()
        del p.resources['ifc_reference']['derived']
        _session, scene = self.scene(model.Project.from_json(p.to_json()))
        drawn = vertices(scene.geometry)
        self.assertEqual(coloured(drawn, mesh.OBSTACLE), 0)
        self.assertEqual(coloured(drawn, SUPPORT), 0)


if __name__ == '__main__':
    unittest.main()
