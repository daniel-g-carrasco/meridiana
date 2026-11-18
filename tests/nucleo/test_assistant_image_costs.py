"""What a picture costs (R320): about width × height / 750 input tokens on Claude, sent again with every question;
the bill counts them when a provider says nothing, so that the line under the conversation stays honest."""
import unittest

import _setup  # noqa: F401
from meridiana.assistant import costs, providers
from meridiana.assistant.conversation import Conversation, Round

IMAGE = {"name": "vista.png", "media_type": "image/png", "data": "AAAA", "width": 1568, "height": 980}


class ImageCosts(unittest.TestCase):
    def test_pixels_over_750(self):
        self.assertEqual(costs.image_tokens(1568, 980), 2049)          # 1.536.640 / 750 = 2048,85
        self.assertEqual(costs.image_tokens(750, 1), 1)
        self.assertEqual(costs.image_tokens(0, 100), 0)
        # the newer models' limit (2576 px on the long side): about 4784 tokens, as the documentation says
        self.assertAlmostEqual(costs.image_tokens(2576, 1393), 4784, delta=5)
        self.assertEqual(costs.pictures_tokens([IMAGE, IMAGE]), 2 * 2049)

    def test_the_line_of_the_consent_says_tokens_and_dollars(self):
        line = costs.pictures_line([IMAGE], "claude-haiku-5-5")
        self.assertIn("2,049", line)
        self.assertIn("dollar cents", line)                             # 2049 × 0,10 $/M = 0,02 cents
        self.assertIn("price unknown", costs.pictures_line([IMAGE], "unknown-model"))
        self.assertAlmostEqual(costs.input_usd("claude-haiku-5-5", 2049), 2049 * 0.10 / 1e6)

    def test_a_provider_that_counts_is_believed_one_that_does_not_is_estimated(self):
        bill = costs.Bill()
        bill.add("claude-haiku-5-5", providers.Usage(input=2500, output=40), True, estimate=2049)
        self.assertEqual(bill.usage.input, 2500)
        self.assertFalse(bill.estimated)
        bill.add("claude-haiku-5-5", providers.Usage(), True, estimate=2049)
        self.assertEqual(bill.usage.input, 2500 + 2049)
        self.assertTrue(bill.estimated)
        self.assertIn("images estimated", costs.line(bill, True))

    def test_the_conversation_estimates_every_picture_it_sends_again(self):
        c = Conversation()
        c.ask("Cosa vedi?", images=[IMAGE])
        provider = providers.OpenAICompatible(model="claude-haiku-5-5", local=False, cloud=True)
        c.add_round(Round(text="Un tetto."), provider)                 # no usage told
        self.assertEqual(c.bill.usage.input, 2049)
        c.ask("E adesso?")
        c.add_round(Round(text="Sempre quello."), provider)
        self.assertEqual(c.bill.usage.input, 2 * 2049)                 # the picture went again


if __name__ == "__main__":
    unittest.main()
