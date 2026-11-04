"""Verify the evidence used in the R372 report, including repeats and input integrity."""

import hashlib
import json
from pathlib import Path
import subprocess


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
specs = ("batch-initial.json", "batch-ab.json", "batch-data-history.json", "batch-final.json", "batch-concurrent.json")
manifest = []
errors = []
for spec_name in specs:
    spec = json.loads((HERE / spec_name).read_text(encoding="utf-8"))
    for run in spec["runs"]:
        files = []
        summaries = []
        for repeat in range(1, run.get("repeats", 3) + 1):
            path = HERE / f"{run['name']}-{repeat}.json"
            if not path.exists():
                errors.append(f"Missing {path.name}")
                continue
            raw = path.read_bytes()
            data = json.loads(raw)
            assert data["on_screen"] and data["platform"] == "windows", path
            assert data["qt"] == "6.12.0", path
            assert data["results"], path
            for row in data["results"]:
                assert row["blocked_ms"] >= row["worst_ms"] >= 0, (path, row)
                assert (row["blocks"] == 0) == (row["blocked_ms"] == 0), (path, row)
            project = data.get("probe", {}).get("project_summary")
            if project:
                assert project == {"buildings": 4, "subfields": 2, "module_count": 778}, (path, project)
            files.append({"name": path.name, "sha256": hashlib.sha256(raw).hexdigest(),
                          "commit": data["commit"], "when": data["when"], "project": project})
            summaries.append([(row["gesture"]) for row in data["results"]])
        if summaries:
            assert all(rows == summaries[0] for rows in summaries), run["name"]
        manifest.append({"series": run["name"], "args": run["args"], "files": files})

original = Path.home() / "dev/meridiana-prove/Prova capannone Rho.meridiana"
conversion = json.loads((HERE / "sample-conversion_R02.json").read_text(encoding="utf-8"))
assert hashlib.sha256(original.read_bytes()).hexdigest() == conversion["original_sha256"]
assert hashlib.sha256((ROOT / "build/speed/sample-v13-R02.meridiana").read_bytes()).hexdigest() == conversion["copy_sha256"]
product = subprocess.run(["git", "diff", "--exit-code", "--", "src", "tests", "tools", "po"],
                         cwd=ROOT, capture_output=True, text=True, check=False)
assert product.returncode == 0, product.stdout + product.stderr
report = (ROOT / "docs/revisioni/codex-velocita-esito.md").read_text(encoding="utf-8")
summary = json.loads((HERE / "summary.json").read_text(encoding="utf-8"))
labels = {"phase plant #1": "Impianto, primo ingresso", "phase production #1": "Produzione, primo ingresso",
          "phase consumption #1": "Consumi, primo ingresso", "File: close (Esc) #1": "File, prima chiusura",
          "right panel: edge dragged #1": "Bordo destro, trascinato in Modellazione",
          "window: resized, 15 steps #1": "Finestra ridimensionata, sequenza base"}


def formatted(row):
    return f"{row['median']:.1f} [{row['min']:.1f}; {row['max']:.1f}]".replace(".", ",")


for series in ("it-screen-current-all", "it-screen-weather-all"):
    assert summary[series]["n"] == 3
    for gesture, label in labels.items():
        metrics = summary[series]["gestures"][gesture]
        expected = "| " + label + " | " + " | ".join(formatted(metrics[key]) for key in (
            "action_ms", "worst_ms", "blocked_ms")) + " |"
        assert expected in report, expected
for before, after, gesture in (
    ("it-screen-weather-edges", "it-screen-weather-chartless-edges", "consumption: right edge dragged #1"),
    ("it-screen-current-edges", "it-screen-no-plan-paint-edges", "model: right edge dragged #1"),
    ("it-screen-current-edges", "it-screen-no-tools-edges", "model: right edge dragged #1"),
    ("it-screen-current-all", "it-screen-instant-file-close-base", "File: close (Esc) #1"),
):
    difference = summary[before]["gestures"][gesture]["action_ms"]["median"] - summary[after]["gestures"][gesture][
        "action_ms"]["median"]
    assert f"{difference:.1f}".replace(".", ",") in report, (before, after, difference)
files_to_scan = [*HERE.glob("*.py"), *HERE.glob("*.json"), ROOT / "docs/revisioni/codex-velocita-esito.md"]
for path in files_to_scan:
    assert chr(0x2014) not in path.read_text(encoding="utf-8"), path
result = {"series": len(manifest), "expected_runs": sum(len(run["files"]) for run in manifest),
          "input_unchanged": True, "product_sources_unchanged": True,
          "report_reference_tables_and_gains_match_raw_data": True, "errors": errors, "manifest": manifest}
(HERE / "verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({key: value for key, value in result.items() if key != "manifest"}, indent=2))
if errors:
    raise SystemExit(1)
