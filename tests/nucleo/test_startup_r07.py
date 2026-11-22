"""Which argument of the command line is the project to open (R07): a document, never an option."""
import unittest
from pathlib import Path

import _setup  # noqa: F401
from meridiana.gui import startup


class Startup(unittest.TestCase):
    def test_only_a_document_argument_is_an_explicit_project(self):
        self.assertIsNone(startup.explicit_project(["meridiana"]))
        self.assertIsNone(startup.explicit_project(["meridiana", "--verbose"]))
        self.assertEqual(startup.explicit_project(["Meridiana.exe", "C:/Lavori/tetto è.mer"]),
                         Path("C:/Lavori/tetto è.mer"))


if __name__ == "__main__":
    unittest.main()
