"""Explicit optimizer partitions survive the project archive and reject malformed input."""
import tempfile
import unittest
from pathlib import Path
import _setup  # noqa: F401
from meridiana import model


class Groups(unittest.TestCase):
    def project(self, sizes):
        p = model.Project(name='Optimizer groups')
        p.energy = {'strings': {'auto': False, 'runs': [{'inverter': 1, 'mppt': 1,
                    'modules': ['field/' + str(n) for n in range(5)], 'optimizer_group_sizes': sizes}]}}
        return p

    def test_archive_preserves_groups(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'groups.mer'
            self.project([2, 1, 2]).save(path)
            q, notice = model.Project.load(path)
            self.assertIsNone(notice)
            self.assertEqual(q.energy['strings']['runs'][0]['optimizer_group_sizes'], [2, 1, 2])

    def test_invalid_partitions_are_rejected_with_the_field_path(self):
        for sizes in ([2, 2], [3, 2], [2, True, 2], '2,1,2'):
            with self.subTest(sizes=sizes), self.assertRaisesRegex(ValueError, 'optimizer_group_sizes'):
                model.Project.from_json(self.project(sizes).to_json())
