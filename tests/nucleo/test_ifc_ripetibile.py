"""Two readings of one model give the same answer. A body made of elements that are as many in one storey as in
another took its storey from a set of names, whose order changes with every process (the hash of a string is salted):
one reading said «Piano 6», the next «Piano 7», and the body's name in the project with it. Now the storey is the most
frequent one and, of two as frequent, the first met.

The sample `tests/data/ifc/piani-pari.ifc` (made by hand): one roof of two slabs, one in each of two storeys. Each
reading runs in a process of its own with its own hash seed, as two openings of the program do."""

import os
import subprocess
import sys
import unittest
from pathlib import Path

import _setup  # noqa: F401

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "ifc" / "piani-pari.ifc"
SRC = Path(__file__).resolve().parents[2] / "src"
CODE = ("import json, sys\n"
        "from meridiana.app.exchange import ifc_read\n"
        "found = ifc_read.read(sys.argv[1])\n"
        "found.pop('times', None)\n"
        "print(json.dumps(found, sort_keys=True, default=float))\n")


def reading(seed: int) -> str:
    env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONPATH=str(SRC), PYTHONUTF8="1")
    done = subprocess.run([sys.executable, "-c", CODE, str(SAMPLE)], env=env, capture_output=True, text=True,
                          encoding="utf-8", check=True)
    return done.stdout.strip().splitlines()[-1]


class SameAnswerEveryTime(unittest.TestCase):
    def test_the_storey_of_a_body_does_not_change_with_the_process(self):
        import json
        answers = [reading(seed) for seed in (1, 2, 3, 4)]
        storeys = [[b["storey"] for b in json.loads(a)["buildings"]] for a in answers]
        self.assertEqual(storeys, [["Piano 6 ala est"]] * 4)
        self.assertEqual(len(set(answers)), 1, "the whole answer, times apart, is the same in every process")


if __name__ == "__main__":
    unittest.main()
