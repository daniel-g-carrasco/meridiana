"""Query PyPI for the wheels of each dependency, per platform tag family.

Usage: python pypi_wheels.py <name>[==version] ...
Prints a markdown table: package, version, wheel found for each platform family (or "-").
"""
import json
import sys
import urllib.request

FAMILIES = {
    "win_amd64": lambda f: "win_amd64" in f,
    "win_arm64": lambda f: "win_arm64" in f,
    "manylinux_x86_64": lambda f: ("manylinux" in f and "x86_64" in f),
    "manylinux_aarch64": lambda f: ("manylinux" in f and "aarch64" in f),
    "musllinux_aarch64": lambda f: ("musllinux" in f and "aarch64" in f),
    "macos_arm64": lambda f: ("macosx" in f and ("arm64" in f or "universal2" in f)),
    "android": lambda f: "android" in f,
    "ios": lambda f: "ios" in f,
    "pure": lambda f: f.endswith("none-any.whl"),
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "meridiana-study-21/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main(argv):
    pyver = "cp312"
    rows = []
    for spec in argv:
        if "==" in spec:
            name, ver = spec.split("==", 1)
        else:
            name, ver = spec, None
        try:
            data = fetch(f"https://pypi.org/pypi/{name}/json") if ver is None else fetch(f"https://pypi.org/pypi/{name}/{ver}/json")
        except Exception as exc:  # noqa: BLE001
            rows.append((name, ver or "?", {k: f"ERR {exc}" for k in FAMILIES}))
            continue
        ver = data["info"]["version"]
        files = [u["filename"] for u in data["urls"] if u["filename"].endswith(".whl")]
        found = {}
        for fam, test in FAMILIES.items():
            hits = [f for f in files if test(f)]
            # prefer cp312 / abi3 / py3 wheels
            pref = [f for f in hits if pyver in f or "abi3" in f or "py3-none" in f or "py2.py3" in f]
            chosen = pref or hits
            found[fam] = chosen[0] if chosen else "-"
            if len(chosen) > 1 and fam != "pure":
                found[fam] += f" (+{len(chosen) - 1})"
        rows.append((name, ver, found))
    fams = list(FAMILIES)
    print("| pacchetto | versione | " + " | ".join(fams) + " |")
    print("|---|---|" + "|".join("---" for _ in fams) + "|")
    for name, ver, found in rows:
        print(f"| {name} | {ver} | " + " | ".join(found[f] for f in fams) + " |")


if __name__ == "__main__":
    main(sys.argv[1:])
