"""Provider configuration must never imply credentials or disclose them."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import _setup  # noqa: F401
from meridiana.assistant import providers, speech


class Setup(unittest.TestCase):
    def test_seven_cloud_choices_require_model_and_key(self):
        from meridiana.assistant import setup
        self.assertEqual(set(setup.CLOUD), {'openai', 'anthropic', 'qwen', 'gemini', 'kimi', 'mistral', 'deepseek'})
        cfg = SimpleNamespace(assistant_cloud_profiles={}, assistant_cloud_model='legacy')
        self.assertEqual(setup.available(cfg, lambda _p: ''), [])
        cfg.assistant_cloud_profiles = {'mistral': {'model': 'mistral-small-latest'}}
        self.assertEqual(setup.available(cfg, lambda p: 'test' if p == 'mistral' else ''), ['mistral'])

    def test_factory_routes_cloud_and_hides_keys(self):
        from meridiana.assistant import setup
        for provider in setup.CLOUD:
            with self.subTest(provider=provider):
                result = setup.make(provider, {'model': 'example', 'endpoint': setup.CLOUD[provider].endpoint}, 'secret-test')
                self.assertTrue(result.cloud)
                self.assertNotIn('secret-test', repr(result))
                self.assertEqual(result.model, 'example')
        with self.assertRaises(ValueError):
            setup.make('openai', {'model':'example', 'endpoint':'http://bad.example/v1'}, 'secret')

    def test_the_two_claude_models_of_the_menu_keep_their_effort_and_a_typed_model_gets_the_defaults(self):
        """R07 review: the generic factory dropped what task 14 measured for the menu's models (Haiku low effort,
        Sonnet medium with the refusal fallback); only a model typed by the designer gets the API's defaults."""
        from meridiana.assistant import setup
        default = setup.CLOUD['anthropic'].endpoint
        haiku = setup.make('anthropic', {'model': 'claude-haiku-5-5', 'endpoint': default}, 'k')
        sonnet = setup.make('anthropic', {'model': 'claude-sonnet-5-5', 'endpoint': default}, 'k')
        typed = setup.make('anthropic', {'model': 'claude-future-1', 'endpoint': default}, 'k')
        proxied = setup.make('anthropic', {'model': 'claude-sonnet-5-5', 'endpoint': 'https://proxy.example.org'}, 'k')
        self.assertEqual((haiku.effort, haiku.fallbacks), ('low', False))
        self.assertEqual((sonnet.effort, sonnet.fallbacks), ('medium', True))
        self.assertEqual((typed.effort, typed.fallbacks), ('', False))
        self.assertEqual((proxied.effort, proxied.fallbacks), ('medium', False))   # a beta not promised by a proxy

    def test_one_place_writes_the_cloud_model(self):
        from meridiana.assistant import setup
        cfg = SimpleNamespace(assistant_cloud_profiles={'anthropic': {'model': 'claude-haiku-5-5',
                                                                      'endpoint': 'https://proxy.example.org'}},
                              assistant_cloud_model='claude-haiku-5-5')
        before = cfg.assistant_cloud_profiles
        setup.remember(cfg, 'claude', 'claude-sonnet-5-5')
        self.assertEqual(setup.profile(cfg, 'anthropic'), {'model': 'claude-sonnet-5-5',
                                                           'endpoint': 'https://proxy.example.org'})
        self.assertEqual(cfg.assistant_cloud_model, 'claude-sonnet-5-5')
        self.assertEqual(before['anthropic']['model'], 'claude-haiku-5-5')   # a copy of the settings is untouched

    def test_endpoint_cannot_store_query_credentials(self):
        from meridiana.assistant import setup
        for endpoint in ('https://user:pass@server/v1', 'https://server/v1?key=secret', 'https://server/v1#secret'):
            with self.assertRaises(ValueError):
                setup.validate_endpoint(endpoint)

    def test_kokoro_discovers_nested_model_and_valid_neighbour_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            root = home / '.local/opt/kokoro'
            models = root / 'models'
            models.mkdir(parents=True)
            for name in speech.MODEL_FILES:
                (models / name).write_bytes(b'model')
            python = root / 'venv' / ('Scripts/python.exe' if __import__('os').name == 'nt' else 'bin/python')
            python.parent.mkdir(parents=True)
            python.write_bytes(b'python')
            with patch.object(Path, 'home', return_value=home):
                self.assertEqual(speech.find_model(environ={}), models)
                self.assertEqual(speech.worker_python(model_dir=models), str(python))

    def test_kokoro_never_looks_in_a_test_folder_of_one_pc(self):
        """R07 review (A, H): ~/fvtest/kokoro-venv, a folder of Daniel's laptop, was looked in for every user. The
        environments next to the model stay; the bundle's own worker (frozen) is untouched."""
        import os
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            models = home / 'Voci' / 'kokoro'
            models.mkdir(parents=True)
            for name in speech.MODEL_FILES:
                (models / name).write_bytes(b'model')
            stray = home / 'fvtest' / 'kokoro-venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            stray.parent.mkdir(parents=True)
            stray.write_bytes(b'python')
            with patch.object(Path, 'home', return_value=home):
                self.assertNotEqual(speech.worker_python(model_dir=models, frozen=False), str(stray))
                self.assertEqual(speech.worker_python(model_dir=models, frozen=True), sys.executable)
                beside = models.parent / '.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
                beside.parent.mkdir(parents=True)
                beside.write_bytes(b'python')
                self.assertEqual(speech.worker_python(model_dir=models, frozen=False), str(beside))

    def test_cancelled_before_request_does_not_connect(self):
        for cls in (providers.Ollama, providers.OpenAICompatible):
            provider = cls(model='local-test')
            provider.cancel()
            class Transport:
                def post(self, *args, **kwargs):
                    raise AssertionError('cancelled request connected')
            provider.session = Transport()
            self.assertEqual(list(provider.stream('', [], [])), [providers.Done('stopped')])

    def test_unknown_ram_never_recommends_the_largest_download(self):
        from meridiana.assistant import local
        self.assertLess(local.suggested(local.Machine()).ollama_gb, 5)

    def test_cloud_tool_signature_and_reasoning_are_returned_unchanged(self):
        import json
        from meridiana.assistant.conversation import Conversation, collect
        chunks = [
            {'choices': [{'delta': {'reasoning_content': 'hidden', 'tool_calls': [
                {'index': 0, 'id': 'c1', 'function': {'name': 'ping', 'arguments': '{}'},
                 'extra_content': {'google': {'thought_signature': 'sig'}}}]}}]},
            {'choices': [{'delta': {}, 'finish_reason': 'tool_calls'}]}]
        class Response:
            status_code = 200
            def iter_lines(self):
                for chunk in chunks:
                    yield 'data: ' + json.dumps(chunk)
                    yield ''
            def close(self):
                pass
        class Transport:
            def post(self, *args, **kwargs):
                return Response()
        provider = providers.OpenAICompatible(model='example', local=False, cloud=True, session=Transport())
        result = collect(provider, '', [], [])
        conversation = Conversation()
        conversation.add_round(result, provider)
        message = providers.openai_messages('', conversation.messages)[0]
        self.assertEqual(message['reasoning_content'], 'hidden')
        self.assertEqual(message['tool_calls'][0]['extra_content']['google']['thought_signature'], 'sig')
