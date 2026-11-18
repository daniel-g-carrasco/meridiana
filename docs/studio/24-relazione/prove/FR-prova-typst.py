"""Typst compiling FR-prova-typst.typ (same forty rows, Inter from data/fonts, a page with big numbers): time of
the compile, weight of the PDF; the pages as PNG come from FR_pdf_png.py run with Meridiana's venv. The Typst
compiler is the `typst` wheel installed in a scratch venv, not in the project. Usage:
    <scratch venv python> FR-prova-typst.py compile
    <meridiana venv python> FR-prova-typst.py png"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
ROWS = "\n".join(f"[{n}], [Tensione a vuoto della stringa alla temperatura minima del sito, confrontata con la "
                 f"tensione massima ammessa dall'inverter (CEI 64-8/7, art. 712.512.1.1)], [{900 + n * 3} V su "
                 f"1.000 V], [conforme]," for n in range(1, 41))


def main() -> None:
    out = HERE / "FR-prova-typst.pdf"
    if sys.argv[1:] == ["png"]:
        from FR_pdf_png import pages_to_png
        print(pages_to_png(str(out), str(HERE / "FR-prova-typst"), pages=(0, 1, 2)))
        return
    t0 = time.perf_counter()
    import typst
    t1 = time.perf_counter()
    src = (HERE / "FR-prova-typst.typ").read_text(encoding="utf-8").replace("//ROWS", ROWS)
    work = HERE / "FR-prova-typst-filled.typ"
    work.write_text(src, encoding="utf-8")
    fonts = HERE.parents[1] / "data" / "fonts" / "inter"
    typst.compile(str(work), output=str(out), font_paths=[str(fonts)], ignore_system_fonts=True)
    t2 = time.perf_counter()
    typst.compile(str(work), output=str(out), font_paths=[str(fonts)], ignore_system_fonts=True)
    t3 = time.perf_counter()
    print(f"Typst: import {(t1 - t0) * 1000:.0f} ms, prima compilazione {(t2 - t1) * 1000:.0f} ms, seconda "
          f"{(t3 - t2) * 1000:.0f} ms, {out.stat().st_size / 1024:.0f} kB")


if __name__ == "__main__":
    main()
