"""Set the language before importing any producer with translated module constants."""

import json
from pathlib import Path
import sys

import _setup  # noqa: F401
from meridiana import i18n


def main():
    bank, lang, folder = sys.argv[1:]
    i18n.setup(lang)
    from profili.snapshot import encoded
    import numpy as np
    data, arrays = encoded(bank, lang)
    path = Path(folder) / f"{bank}-{lang}.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    if arrays:
        np.savez_compressed(path.with_suffix(".npz"), **arrays)


if __name__ == "__main__":
    main()
