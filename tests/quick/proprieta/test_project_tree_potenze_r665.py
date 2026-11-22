"""R665 (Daniel 16/11/2026: «in scheda Project si può eliminare l'indicazione 1-subfields, no subfields? e mantenere solo
la potenza? per i sottocampi mettiamoci anche la potenza. Se la scheda si restringe troppo, i nomi scompaiono e si
vedono solo potenze»): in the Project tree a building shows its kWp, a sub-field its modules and kWp; the value is
never cut: the name gives way to it, cut at its end, and goes when not even ControlMetrics.treeNameLeast of its
characters fit (the value alone, the name in the tooltip).

    python -m unittest quick.proprieta.test_project_tree_potenze_r665
"""
import copy
import unittest

import _setup
from _fixtures import capannone_rho


def setUpModule():
    _setup.keep_global_state()


class NarrowTree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_value_stays_whole_and_the_name_gives_way(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtQuick import QQuickView
        from meridiana import i18n
        from meridiana.app import jobs
        from meridiana.app.session import ProjectSession
        from meridiana.core.model import model
        from meridiana.gui.backend.controls import install_controls
        from meridiana.gui.backend.project_tree import ProjectTreeBackend
        from quick.gestures import pump
        self.addCleanup(i18n.setup, i18n.language())
        i18n.setup('en')
        project = model.Project.from_json(copy.deepcopy(capannone_rho().to_json()))
        backend = ProjectTreeBackend(ProjectSession(project))
        self.addCleanup(backend.close)
        backend.trigger('fill', 'subfield', 's1')
        results, keys, _laid = jobs.layout_of(backend.session.project)
        backend.session.results, backend.session.layout_keys = results, keys
        backend.session.changed('layout:s1')
        for _ in range(3):
            for row in list(backend.rows):
                if row.get('fold') and not row.get('open'):
                    backend.setOpen(row['fold'], True)
        view = QQuickView()
        install_controls(view.engine(), dict(theme='dark', reducedMotion=True))
        view.rootContext().setContextProperty('treeBackend', backend)
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.setInitialProperties({'backend': backend})
        view.setSource(QUrl.fromLocalFile(str(_setup.ROOT / 'src/meridiana/gui/qml/Meridiana/ProjectTree/ProjectTreePage.qml')))
        self.assertIsNotNone(view.rootObject(), view.errors())
        view.resize(320, 600)
        view.show()
        pump(300)
        self.addCleanup(view.close)
        rows = {r['oid']: r for r in backend.rows if r['kind'] in ('building', 'subfield') and r['value']}
        self.assertTrue(rows, 'buildings and sub-fields with a value')
        building = next(r for r in rows.values() if r['kind'] == 'building')
        self.assertTrue(building['value'].endswith('kWp') and 'sub-field' not in building['tail'])
        subfield = next(r for r in rows.values() if r['kind'] == 'subfield')
        self.assertRegex(subfield['value'], r'^\d[\d ,.]* · [\d,.]+ kWp$')

        def labels(oid, kind):
            row = self.find(view.rootObject(), f'tree-row-{kind}-{oid}')
            texts = [t for t in self.items(row) if t.inherits('QQuickText') and t.property('text') and t.isVisible()]
            return texts
        seen = {}
        for width in (320, 230, 190, 160, 320):     # and wide again: a name hidden comes back whole
            view.resize(width, 600)
            pump(200)
            for oid, row in rows.items():
                texts = labels(oid, row['kind'])
                value = texts[-1]
                room = value.parentItem().width()           # the row's text, after its icon
                with self.subTest(width=width, row=oid):
                    if room >= value.property('implicitWidth'):  # where the value alone fits, it is never cut
                        self.assertGreaterEqual(value.width() + .5, value.property('implicitWidth'), 'the value is never cut')
                    if width == 320:                            # wide: the whole name before its value
                        self.assertEqual(len(texts), 2)
                        self.assertGreaterEqual(texts[0].width() + .5, texts[0].property('implicitWidth'))
                        self.assertGreater(texts[0].width(), 0, 'the name is drawn')
                    seen.setdefault(oid, []).append((len(texts), value.property('text')))
        # wide, the name and the value after it; narrow, at least one name goes and its value stands alone
        for oid, row in rows.items():
            self.assertEqual(seen[oid][0], (2, ' · ' + row['value']))
        gone = [oid for oid, s in seen.items() if s[-2] == (1, rows[oid]['value'])]
        self.assertTrue(gone, seen)

    @staticmethod
    def items(item):
        yield item
        for child in item.childItems():
            yield from NarrowTree.items(child)

    @classmethod
    def find(cls, root, name):
        return next(it for it in cls.items(root) if it.objectName() == name)


if __name__ == '__main__':
    unittest.main()
