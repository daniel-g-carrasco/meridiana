"""The optional grid fields in the shared Site properties page."""

import unittest

import _setup

from meridiana import model

setUpModule = _setup.keep_global_state


class GridFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.look = _setup.meridiana_look()

    def test_fields_are_optional_and_emit_one_network_model(self):
        from meridiana.ui.properties import Properties
        project = model.Project()
        props = Properties()
        self.addCleanup(_setup.dispose, props)
        sent = []

        def apply(kind, oid, changes):
            sent.append(changes)
            project.network = changes["network"]
            project.sync_network()

        props.edited.connect(apply)
        props.show_site(project, False)
        self.assertEqual(props.grid_rule.text(), "")
        props.distributor.setText("E-distribuzione")
        props.distributor.editingFinished.emit()
        props.voltage.setValue(20000)
        props.level.setCurrentIndex(props.level.findData("MT"))
        props.connection.setCurrentIndex(props.connection.findData("new"))
        props.available.setValue(80)
        props.requested.setValue(65)
        props.pod.setText("IT001E12345678")
        props.pod.editingFinished.emit()
        props.practice.setText("PR-42")
        props.practice.editingFinished.emit()
        network = sent[-1]["network"]
        self.assertEqual(network.distributor, "E-distribuzione")
        self.assertEqual(network.voltage_v, 20000)
        self.assertEqual(network.technical_rule(), "CEI 0-16")
        self.assertEqual((network.level, network.connection), ("MT", "new"))
        self.assertEqual((network.available_kw, network.requested_kw), (80, 65))
        self.assertEqual((network.pod, network.practice_code), ("IT001E12345678", "PR-42"))


if __name__ == "__main__":
    unittest.main()
