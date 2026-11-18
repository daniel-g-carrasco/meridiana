"""Parts share one session and publish their places before QML loads."""
import unittest
from types import SimpleNamespace

from meridiana.quick.backend.parts import Part, Parts


class PartsTest(unittest.TestCase):
    def test_install_bind_and_close(self):
        calls = []
        session, engine, cache = object(), object(), object()
        window = SimpleNamespace(shell=SimpleNamespace(register_command=lambda *args: calls.append(args)))

        def install(e, s, c, w):
            self.assertEqual((e, s, c, w), (engine, session, cache, window))
            return Part('example', sources={'project': 'Project.qml'},
                        commands={'open': lambda: None}, close=lambda: calls.append('closed'))

        parts = Parts(engine, session, cache, window)
        parts.install(install)
        self.assertEqual(parts.sources, {'project': 'Project.qml'})
        parts.bind()
        self.assertEqual(calls[0][0], 'open')
        parts.close()
        parts.close()
        self.assertEqual(calls.count('closed'), 1)

    def test_duplicate_place_is_rejected(self):
        parts = Parts(None, None, None, None)
        parts.install(lambda *a: Part('one', sources={'file': 'One.qml'}))
        with self.assertRaises(ValueError):
            parts.install(lambda *a: Part('two', sources={'file': 'Two.qml'}))
