"""R478, Windows: the process of the computation on a pipe, with nothing more coming on it while a year runs.

On 06/11/2026 the live process stood still for hours on the PC at its first year (`calcolo_vivo.py`, mode `vivo`) and
at its second in the Quick's trials, while on Linux every trial passed. The cause: the workers of the year's pool
are children of the process of the computation, and on Windows a child that inherits the console gets a copy of its
standard handles, the commands' pipe included; the main thread of the process is in a synchronous read of that pipe
for the whole year, and a worker starting up stops on that handle (Windows serializes synchronous I/O on the same
file object) until the next line arrives: the pool never starts, the year never ends. A single line sent on the pipe
made such a year end within a second (docs/prestazioni/2026-11-06/calcolo-vivo-r20.md). Here a year that uses the
pool (two workers asked) must end with nothing sent after its `job`, twice in the same process with the same kWh,
and nothing must outlive the process. Before the correction this trial stood still until its limit (150 s)."""
import os
import pickle
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from _fixtures import capannone, inverter_record
from meridiana.quick.sample import recorded_weather
from nucleo.test_pool_orphans import alive, wait_gone

SRC = Path(__file__).resolve().parents[3] / "src"
LIMIT = 150         # seconds for a year of the shed: both take 6 s on the loaded PC; stuck, it never ends


def kill_tree(process):
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    else:
        process.kill()
    process.wait(30)


class LivePipe(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="live-pipe-"))
        project = capannone()
        # inverters, so that the modules have strings and the year has an electrical network for its pool
        project.energy["inverters"] = [{"record": inverter_record(), "count": 3, "name": ""}]
        project.energy["strings"] = {"auto": True}
        recorded_weather(project, self.folder)
        self.input = pickle.dumps((project, {}, self.folder, "", True, {}), protocol=5)
        env = dict(os.environ, MERIDIANA_WORKERS="2", PYTHONPATH=str(SRC), PYTHONUTF8="1")
        self.serve = subprocess.Popen([sys.executable, "-m", "meridiana.quick.backend.shell_compute", "--serve",
                                       "--parent", str(os.getpid())],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
        self.addCleanup(self._close_pipes)
        self.addCleanup(kill_tree, self.serve)
        self.lines = []
        threading.Thread(target=self._read, daemon=True).start()

    def _close_pipes(self):
        for pipe in (self.serve.stdin, self.serve.stdout):
            try:
                pipe.close()
            except OSError:
                pass

    def _read(self):
        for line in self.serve.stdout:
            self.lines.append(line.decode("utf-8", "replace").strip())

    def expect(self, word, seconds=LIMIT):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            for i, line in enumerate(self.lines):
                if line.split(" ", 1)[0] == word:
                    del self.lines[:i + 1]
                    return line
            if self.serve.poll() is not None:
                self.fail(f"the process of the computation ended ({self.serve.returncode}) waiting for {word!r}")
            time.sleep(0.05)
        self.fail(f"no {word!r} within {seconds} s: the year stood still (last lines: {self.lines[-3:]})")

    def year(self, name):
        folder = self.folder / name
        folder.mkdir()
        (folder / "input.bin").write_bytes(self.input)
        self.serve.stdin.write(f"job {folder}\n".encode())
        self.serve.stdin.flush()
        self.expect("done")             # nothing more is sent while the year runs
        energy, metrics = pickle.loads((folder / "result.bin").read_bytes())
        self.assertIsNone(metrics.get("error"), metrics.get("error"))
        return energy["sim"].energy_kwh, metrics

    def test_two_years_that_use_the_pool_end_with_nothing_more_on_the_pipe(self):
        pid = int(self.expect("ready").split()[1])
        first, metrics = self.year("01")
        self.assertGreater(metrics["network_parts_made"], 0)
        second, metrics = self.year("02")
        self.assertEqual(repr(second), repr(first))
        self.assertGreater(metrics["network_parts_kept"], 0)
        self.assertEqual(metrics["pid"], pid)
        self.serve.stdin.write(b"warm\n")
        self.serve.stdin.flush()
        workers = [int(p) for p in self.expect("warm", 60).split()[1:]]
        self.assertEqual(len(workers), 2, "the year's pool did not have its two processes")
        self.assertTrue(all(alive(p) for p in workers))
        self.serve.stdin.write(b"quit\n")
        self.serve.stdin.close()
        self.serve.wait(30)
        self.assertEqual(wait_gone([pid, *workers], 20), [], "the process of the computation or its pool outlived it")


if __name__ == "__main__":
    unittest.main()
