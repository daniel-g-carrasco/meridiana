"""Images to the models (R320): the body each provider sends, checked on a stand-in of the transport (the real
anthropic SDK over an httpx2 MockTransport, a requests stand-in for OpenAI's and Ollama's APIs); never a call to a
real service. A model without vision is said in words."""
import base64
import json
import typing
import unittest

import _setup  # noqa: F401
from meridiana.assistant import providers
from meridiana.assistant.conversation import Conversation, collect

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n-not-a-real-picture-").decode()
IMAGE = {"name": "vista.png", "media_type": "image/png", "data": PNG, "width": 1568, "height": 980}


def asked(text="Cosa vedi?", images=(IMAGE,)):
    c = Conversation()
    c.ask(text, images=list(images))
    return c.messages


class Response:
    def __init__(self, status=200, lines=(), body=None):
        self.status_code = status
        self.lines = list(lines)
        self.body = body or {}
        self.text = json.dumps(self.body)

    def iter_lines(self):
        yield from self.lines

    def json(self):
        return self.body

    def close(self):
        pass


class Transport:
    """requests.Session as the providers use it: each post noted, answered by `answer(url, body)`."""

    def __init__(self, answer):
        self.answer = answer
        self.posts = []
        self.trust_env = True

    def post(self, url, json=None, **_kwargs):
        self.posts.append((url, json))
        return self.answer(url, json)


def sse_text(text="Vedo un tetto."):
    return [f"data: {json.dumps({'choices': [{'delta': {'content': text}}]})}", "",
            f"data: {json.dumps({'choices': [{'delta': {}, 'finish_reason': 'stop'}]})}", "", "data: [DONE]", ""]


class OpenAI(unittest.TestCase):
    def test_the_picture_goes_as_an_image_url_part_with_a_data_url(self):
        http = Transport(lambda url, body: Response(lines=sse_text()))
        provider = providers.OpenAICompatible(model="gemma4:12b", session=http)
        r = collect(provider, "sys", asked(), [])
        self.assertEqual(r.text, "Vedo un tetto.")
        user = http.posts[0][1]["messages"][1]
        self.assertEqual(user["role"], "user")
        self.assertEqual(user["content"][0], {"type": "text", "text": "Cosa vedi?"})
        self.assertEqual(user["content"][1], {"type": "image_url",
                                              "image_url": {"url": "data:image/png;base64," + PNG}})

    def test_a_question_without_pictures_stays_plain_text(self):
        c = Conversation()
        c.ask("Ciao")
        self.assertEqual(providers.openai_messages("", c.messages), [{"role": "user", "content": "Ciao"}])
        self.assertNotIn("images", c.messages[0])

    def test_llama_server_without_its_projector_is_said_as_a_model_without_vision(self):
        for status, message in ((500, "image input is not supported - hint: you may need to provide the mmproj"),
                                (400, "unknown variant `image_url`, expected `text`")):
            http = Transport(lambda url, body, s=status, m=message: Response(s, body={"error": {"message": m}}))
            provider = providers.OpenAICompatible(model="qwen3.6:35b", session=http)
            with self.assertRaises(providers.ProviderError) as caught:
                collect(provider, "", asked(), [])
            self.assertEqual(caught.exception.kind, "vision", message)

    def test_other_refusals_stay_what_they_were(self):
        http = Transport(lambda url, body: Response(401, body={"error": {"message": "bad key"}}))
        with self.assertRaises(providers.ProviderError) as caught:
            collect(providers.OpenAICompatible(model="x", session=http, local=False, cloud=True), "", asked(), [])
        self.assertEqual(caught.exception.kind, "auth")
        http = Transport(lambda url, body: Response(400, body={"error": {"message": "Invalid image: too large"}}))
        with self.assertRaises(providers.ProviderError) as caught:
            collect(providers.OpenAICompatible(model="x", session=http, local=False, cloud=True), "", asked(), [])
        self.assertEqual(caught.exception.kind, "image")


class Ollama(unittest.TestCase):
    def answer(self, capabilities):
        def answer(url, body):
            if url.endswith("/api/show"):
                return Response(body={"capabilities": capabilities})
            return Response(lines=[json.dumps({"message": {"content": "Vedo un tetto."}}),
                                   json.dumps({"done": True, "done_reason": "stop", "prompt_eval_count": 700,
                                               "eval_count": 5})])
        return answer

    def test_the_picture_goes_in_the_images_list_of_the_question(self):
        http = Transport(self.answer(["completion", "vision", "tools"]))
        r = collect(providers.Ollama(model="gemma4:12b", session=http), "sys", asked(), [])
        self.assertEqual(r.text, "Vedo un tetto.")
        url, body = http.posts[-1]
        self.assertTrue(url.endswith("/api/chat"))
        self.assertEqual(body["messages"][1], {"role": "user", "content": "Cosa vedi?", "images": [PNG]})

    def test_a_model_that_ollama_says_has_no_vision_is_not_asked(self):
        http = Transport(self.answer(["completion", "tools"]))
        with self.assertRaises(providers.ProviderError) as caught:
            collect(providers.Ollama(model="qwen3.6:35b-a3b", session=http), "", asked(), [])
        self.assertEqual(caught.exception.kind, "vision")
        self.assertFalse([u for u, _b in http.posts if u.endswith("/api/chat")])


class Anthropic(unittest.TestCase):
    def client(self, handler):
        try:
            import anthropic
            import httpx2 as httpx
        except ImportError:
            self.skipTest("anthropic")
        return anthropic.Anthropic(api_key="test-key", base_url="https://api.anthropic.test", max_retries=0,
                                   http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    @staticmethod
    def stream_body(text="Vedo un tetto."):
        events = [
            ("message_start", {"type": "message_start", "message": {
                "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-haiku-5-5", "content": [],
                "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 2100, "output_tokens": 1}}}),
            ("content_block_start", {"type": "content_block_start", "index": 0,
                                     "content_block": {"type": "text", "text": ""}}),
            ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                     "delta": {"type": "text_delta", "text": text}}),
            ("content_block_stop", {"type": "content_block_stop", "index": 0}),
            ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                               "usage": {"output_tokens": 6}}),
            ("message_stop", {"type": "message_stop"})]
        return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events).encode()

    def test_the_sdk_sends_an_image_block_with_a_base64_source_before_the_words(self):
        import httpx2 as httpx
        sent = []

        def handler(request):
            sent.append(json.loads(request.content))
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=self.stream_body())
        provider = providers.Anthropic(model="claude-haiku-5-5", client=self.client(handler))
        r = collect(provider, "sys", asked(), [])
        self.assertEqual(r.text, "Vedo un tetto.")
        self.assertEqual(r.usage.input, 2100)
        content = sent[0]["messages"][0]["content"]
        self.assertEqual(content[0], {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                                  "data": PNG}})
        self.assertEqual(content[1], {"type": "text", "text": "Cosa vedi?"})

    def test_the_blocks_are_the_shape_the_installed_sdk_declares(self):
        try:
            from anthropic.types import Base64ImageSourceParam, ImageBlockParam
        except ImportError:
            self.skipTest("anthropic")
        block = providers.anthropic_messages(asked())[0]["content"][0]
        self.assertTrue(ImageBlockParam.__required_keys__ <= set(block) <= set(ImageBlockParam.__annotations__))
        source = block["source"]
        self.assertTrue(Base64ImageSourceParam.__required_keys__ <= set(source)
                        <= set(Base64ImageSourceParam.__annotations__))
        media = typing.get_args(typing.get_type_hints(Base64ImageSourceParam)["media_type"])
        self.assertIn("image/png", media)
        self.assertIn("image/jpeg", media)                  # the two kinds images.py writes
        self.assertIn(source["media_type"], media)

    def test_an_image_refused_by_the_service_is_said_as_such(self):
        import httpx2 as httpx

        def handler(request):
            return httpx.Response(400, json={"type": "error", "error": {
                "type": "invalid_request_error",
                "message": "messages.0.content.0.image.source.base64: image exceeds 5 MB maximum"}})
        provider = providers.Anthropic(model="claude-haiku-5-5", client=self.client(handler))
        with self.assertRaises(providers.ProviderError) as caught:
            collect(provider, "", asked(), [])
        self.assertEqual(caught.exception.kind, "image")


class Sight(unittest.TestCase):
    def test_which_models_see(self):
        see = lambda model, **kw: providers.sees_images(  # noqa: E731
            providers.OpenAICompatible(model=model, **kw))
        for model in ("gemma4:26b-a4b-it-qat", "gemma3:12b", "qwen2.5vl:7b", "qwen3-vl:8b", "llava:13b",
                      "llama3.2-vision", "minicpm-v", "unsloth/gemma-4-12b-it-GGUF:Q4_K_M"):
            self.assertIs(see(model), True, model)
        for model in ("qwen3:8b", "gpt-oss:20b", "llama3.1:8b", "gemma3:1b", "deepseek-r1:14b"):
            self.assertIs(see(model), False, model)
        for model in ("qwen3.6:35b-a3b", "", "my-model"):
            self.assertIsNone(see(model), model)
        self.assertIsNone(see("qwen3-max", local=False, cloud=True))        # a cloud model is tried
        self.assertIs(providers.sees_images(providers.Anthropic(model="claude-haiku-5-5")), True)

    def test_drop_images_leaves_the_questions(self):
        c = Conversation()
        c.ask("uno", images=[IMAGE])
        c.drop_images()
        self.assertEqual(c.messages, [{"role": "user", "content": "uno"}])
        self.assertFalse(providers.has_images(c.messages))


if __name__ == "__main__":
    unittest.main()
