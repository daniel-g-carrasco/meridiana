"""Run a JSON list of fluidity probes sequentially, preserving logs and failures."""

import json
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
wait_for = spec.get("wait_for")
if wait_for:
    deadline = time.monotonic() + 600
    while not (ROOT / wait_for).exists():
        if time.monotonic() > deadline:
            raise TimeoutError(wait_for)
        time.sleep(1)
for commit in spec.get("archive_commits", []):
    destination = ROOT / "build/speed" / commit
    if not destination.exists():
        destination.mkdir(parents=True)
        tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["git", "archive", commit], cwd=ROOT))).extractall(
            destination, filter="data")
for tree in spec.get("compile_trees", []):
    subprocess.run([sys.executable, str(ROOT / tree / "tools/compile_po.py"), "--python"], check=True,
                   stdout=subprocess.DEVNULL)
if spec.get("prepare_weather"):
    subprocess.run([sys.executable, str(HERE / "prepare_weather.py")], check=True)
for run in spec["runs"]:
    name = run["name"]
    for repeat in range(1, run.get("repeats", 3) + 1):
        out = HERE / f"{name}-{repeat}.json"
        if out.exists():
            if spec.get("resume"):
                json.loads(out.read_text(encoding="utf-8"))
                print("retained", out.name, flush=True)
                continue
            raise FileExistsError(out)
        cmd = [sys.executable, str(HERE / "probe.py"), "--out", str(out), *run["args"]]
        start = time.monotonic()
        log = ROOT / "build/speed" / f"{name}-{repeat}.log"
        attempt = 1
        while log.exists():
            attempt += 1
            log = ROOT / "build/speed" / f"{name}-{repeat}-attempt{attempt}.log"
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(cmd, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=360)
        print(name, repeat, "exit", result.returncode, "seconds", round(time.monotonic() - start), flush=True)
        if result.returncode or not out.exists():
            raise RuntimeError(f"Probe failed, inspect {log}")
