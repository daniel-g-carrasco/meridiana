"""The editable report beside the PDF (R506): the same document as PDF, ODT and DOCX, the two editable files turned into
PDF by LibreOffice (and by Word, when asked), the same key pages drawn at 100 dpi and set side by side.

    python tools/editable_compare.py prepare NAME PROJECT OUT [--year FILE.pkl]   # the year once, the document, the PDF
    python tools/editable_compare.py export OUT                                  # ODT and DOCX from the document
    python tools/editable_compare.py convert OUT                                 # both through LibreOffice to PDF
    python tools/editable_compare.py word OUT [--seconds 240]                    # the DOCX through Word to PDF
    python tools/editable_compare.py pages OUT TARGET [--prefix rho]             # the key pages side by side

The project is read from a copy in a temporary folder; the original is never written. LibreOffice runs headless with a
profile of its own (it does not join a LibreOffice the user has open); Word runs invisible in a process of its own with a
time limit, Quit() in its finally, and is ended by its process id when it hangs (only the Word this script started)."""

from __future__ import annotations

import argparse
import json
import os
import pickle
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "rhi")

PROFILE = {"name": "Studio", "firm": "Studio Tecnico Rossi e Associati", "signer": "Ing. Mario Rossi",
           "register": "Ordine degli Ingegneri di Milano n. A00000", "address": "Via Esempio 1, 20100 Milano",
           "phone": "+39 02 000 0000", "email": "studio@esempio.it", "web": "", "logo": "", "accent": "#1c6e8c"}
REPORT = {"template": "complete", "register": True, "client": "Committente S.r.l. (segnaposto)", "revision": "Rev. 01"}
SOFFICE = Path(r"C:\Program Files\LibreOffice\program\soffice.com")
# the key pages: a name and the words that find it in each PDF (the first page that has all of them, after `after`)
PAGES = [("copertina", [], None), ("indice", ["Indice"], None), ("sintesi", ["Energia mese per mese", "Indice di prestazione"], "Indice"),
         ("mensile", ["Mese per mese", "Producibilità"], "Indice"), ("passo", ["dove:", "Riferimento"], "Indice"),
         ("simboli", ["resistenza parallelo", "fattore di diodo"], "Indice"), ("tabella", ["Registro"], "Indice")]


def year(name: str, source: Path, out: Path, cached: Path | None):
    cached = cached or out / f"{name}.pkl"
    if cached.exists():
        with open(cached, "rb") as f:
            return pickle.load(f)
    from meridiana import checks, jobs, model, rules
    from meridiana.energy import pipeline, system
    folder = Path(tempfile.mkdtemp(prefix=f"confronto-{name}-"))
    copy = folder / source.name
    shutil.copy2(source, copy)
    cache = Path(r"C:\Users\Grasso\dev\meridiana-prove\cache\pvgis")
    project, _notice = model.Project.load(copy, cache)
    results, _keys, _laid = jobs.layout_of(project)
    t = time.time()
    energy = pipeline.compute(project, results, cache, fetch=True).as_dict()
    print("year in %.0f s" % (time.time() - t), flush=True)
    data = {**energy, "results": results}
    if energy.get("sim") is not None:
        arrays = system.arrays_of(project, results)
        inverter = system.combined(system.inverters_of(project, sum(a.p_stc for a in arrays)))
        items = checks.gather(project, results, energy, inverter, True)
        if energy.get("plant") is not None:
            items += checks.plant_items(energy["plant"])
        items.sort(key=lambda item: checks.LEVELS.index(item.level))
        data.update({"checks": items, "rules_facts": rules.facts(project, results, energy, inverter)})
    saved = {"project": project, "data": data}
    with open(cached, "wb") as f:
        pickle.dump(saved, f, protocol=pickle.HIGHEST_PROTOCOL)
    return saved


def prepare(args) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    from meridiana import i18n
    i18n.setup("it")
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication([])
    saved = year(args.name, Path(args.project), out, Path(args.year) if args.year else None)
    project, data = saved["project"], saved["data"]
    project.report = {**(getattr(project, "report", None) or {}), **REPORT}
    from meridiana.ui import report, report_3d
    steps = report._prepared(project, data, dict(PROFILE))
    while True:
        try:
            next(steps)
        except StopIteration as done:
            build, document, _attached = done.value
            break
    try:
        root = out / "root"
        if root.exists():
            shutil.rmtree(root)
        shutil.copytree(build.root, root)
        (out / "document.json").write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
        result = build.compile(document)
        (out / "relazione.pdf").write_bytes(result.pdf)
        worked = sum(1 for b in walk(document.get("body", [])) if b.get("k") == "step" and b.get("worked"))
        print("pdf", len(result.pdf) // 1024, "kB; steps with the numbers:", worked, flush=True)
    finally:
        build.close()
        report_3d.release()
        app.quit()


def walk(blocks):
    for b in (x for x in blocks if isinstance(x, dict)):
        yield b
        for key in ("left", "right", "items"):
            if isinstance(b.get(key), list) and b.get("k") != "list":
                yield from walk(b[key])


def export(args) -> None:
    out = Path(args.out)
    from meridiana import i18n
    i18n.setup("it")
    from meridiana.report_typst import editable
    document = json.loads((out / "document.json").read_text(encoding="utf-8"))
    for kind in ("odt", "docx"):
        stats = editable.export(json.loads(json.dumps(document)), out / "root", out / f"relazione.{kind}", kind)
        print(kind, stats, flush=True)


def convert(args) -> None:
    out = Path(args.out)
    lo = out / "lo"
    lo.mkdir(exist_ok=True)
    profile = Path(tempfile.gettempdir()) / "meridiana-lo-profile"
    for kind in ("odt", "docx"):
        source = out / f"relazione.{kind}"
        copy = lo / f"relazione-{kind}.{kind}"
        shutil.copy2(source, copy)
        t = time.time()
        subprocess.run([str(SOFFICE), f"-env:UserInstallation={profile.as_uri()}", "--headless", "--invisible",
                        "--norestore", "--convert-to", "pdf", "--outdir", str(lo), str(copy)],
                       check=True, timeout=300, capture_output=True)
        print(kind, "->", copy.with_suffix(".pdf").name, "%.1f s" % (time.time() - t), flush=True)


WORD_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$word = $null
$fresh = $false
try {
  $word = New-Object -ComObject Word.Application
  # a Word of its own: one that has documents open is the user's, it is left alone
  $fresh = ($word.Documents.Count -eq 0)
  if (-not $fresh) { throw 'a Word with documents open answered: left alone' }
  $word.Visible = $false
  $word.DisplayAlerts = 0
  $doc = $word.Documents.Open('%(docx)s', $false, $true, $false)
  $doc.Fields.Update() | Out-Null
  foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
  $doc.Repaginate()
  foreach ($toc in $doc.TablesOfContents) { $toc.UpdatePageNumbers() }
  $doc.ExportAsFixedFormat('%(pdf)s', 17)
  $doc.Close(0)
  'ok'
} finally {
  if ($word -ne $null) {
    if ($fresh) { $word.Quit() }
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
  }
}
"""


def word_pids() -> set[int]:
    found = subprocess.run(["tasklist", "/FI", "IMAGENAME eq WINWORD.EXE", "/FO", "CSV", "/NH"], capture_output=True,
                           text=True).stdout
    return {int(line.split('","')[1]) for line in found.splitlines() if line.startswith('"WINWORD')}


def word(args) -> None:
    out = Path(args.out)
    target = out / "word"
    target.mkdir(exist_ok=True)
    docx = target / "relazione-word.docx"
    shutil.copy2(out / "relazione.docx", docx)
    pdf = target / "relazione-word.pdf"
    script = target / "word.ps1"
    script.write_text(WORD_SCRIPT % {"docx": str(docx), "pdf": str(pdf)}, encoding="utf-8-sig")
    before = word_pids()
    process = subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-File", str(script)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t = time.time()
    try:
        stdout, stderr = process.communicate(timeout=args.seconds)
        print("word:", stdout.strip(), stderr.strip()[-600:], "%.0f s" % (time.time() - t), flush=True)
    except subprocess.TimeoutExpired:
        process.kill()
        print("word: no answer in", args.seconds, "s, ended", flush=True)
    finally:
        for pid in word_pids() - before:     # only the Word this script started
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
            print("word: ended the hanging process", pid, flush=True)


def page_texts(pdf: Path) -> list[str]:
    from pypdf import PdfReader
    # without any space: a PDF of LibreOffice may space the letters of a line or join its words
    return ["".join((p.extract_text() or "").split()) for p in PdfReader(str(pdf)).pages]


def find(texts: list[str], words: list, after) -> int:
    start = 0
    if after:
        start = next((i + 1 for i, t in enumerate(texts) if "".join(after.split()) in t), 0)
    for i in range(start, len(texts)):
        if all("".join(w.split()) in texts[i] for w in words):
            return i
    return -1


def render(pdf: Path, index: int, dpi: int = 100):
    from PySide6.QtCore import QSize
    from PySide6.QtPdf import QPdfDocument
    doc = QPdfDocument()
    doc.load(str(pdf))
    size = doc.pagePointSize(index)
    image = doc.render(index, QSize(round(size.width() * dpi / 72), round(size.height() * dpi / 72)))
    doc.close()
    return image


def pages(args) -> None:
    from PIL import Image, ImageDraw
    from PySide6.QtGui import QGuiApplication, QImage
    app = QGuiApplication([])
    out, target = Path(args.out), Path(args.target)
    target.mkdir(parents=True, exist_ok=True)
    files = [("PDF", out / "relazione.pdf"), ("ODT", out / "lo" / "relazione-odt.pdf"),
             ("DOCX", out / "lo" / "relazione-docx.pdf")]
    if (out / "word" / "relazione-word.pdf").exists():
        files.append(("DOCX in Word", out / "word" / "relazione-word.pdf"))
    texts = {label: page_texts(path) for label, path in files}
    for name, words, after in PAGES:
        shots = []
        for label, path in files:
            index = 0 if not words else find(texts[label], words, after)
            if index < 0:
                print(name, label, "not found", flush=True)
                continue
            image = render(path, index).convertToFormat(QImage.Format.Format_RGBA8888)
            drawn = Image.frombuffer("RGBA", (image.width(), image.height()), bytes(image.constBits()), "raw", "RGBA",
                                     image.bytesPerLine(), 1)
            shot = Image.new("RGB", drawn.size, (255, 255, 255))
            shot.paste(drawn, mask=drawn.getchannel("A"))
            shots.append((f"{label}, pagina {index + 1} di {len(texts[label])}", shot))
        if not shots:
            continue
        gap, top = 16, 26
        width = sum(s.width for _l, s in shots) + gap * (len(shots) - 1)
        height = max(s.height for _l, s in shots) + top
        sheet = Image.new("RGB", (width, height), (96, 96, 96))
        draw = ImageDraw.Draw(sheet)
        x = 0
        for label, shot in shots:
            draw.text((x + 4, 6), label, fill=(255, 255, 255))
            sheet.paste(shot, (x, top))
            x += shot.width + gap
        path = target / f"{args.prefix}-{name}.png"
        sheet.save(path, optimize=True)
        print(path.name, flush=True)
    app.quit()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("name")
    p.add_argument("project")
    p.add_argument("out")
    p.add_argument("--year")
    p.set_defaults(run=prepare)
    for name, run in (("export", export), ("convert", convert)):
        q = sub.add_parser(name)
        q.add_argument("out")
        q.set_defaults(run=run)
    w = sub.add_parser("word")
    w.add_argument("out")
    w.add_argument("--seconds", type=int, default=240)
    w.set_defaults(run=word)
    g = sub.add_parser("pages")
    g.add_argument("out")
    g.add_argument("target")
    g.add_argument("--prefix", default="rho")
    g.set_defaults(run=pages)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    sys.exit(main())
