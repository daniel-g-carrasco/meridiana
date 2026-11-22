"""What can be read of a Revit file (.rvt, .rfa, .rte) without Revit: a Revit file is an OLE2 compound file whose streams
hold a line of text with its version and build, an XML with its title and a PNG preview. The geometry is in a proprietary
format, compressed, and is not read here (study 32, which compares the ways of getting it). Without Qt and without
dependencies; the file is opened for reading only, and nothing is written beside it.

`read(path)` gives {"format": "2023", "build": ..., "title": ..., "central": ..., "preview": b"PNG...", "streams": n, "size": n};
RvtError with the reason when it is not such a file. A file larger than any stream read costs nothing: only
the directory and the three small streams are read."""

from __future__ import annotations

import os
import re
import struct
from pathlib import Path

SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
MAX_STREAM = 64 * 1024 * 1024       # what is read of one stream: the three wanted are far smaller
FREE, END, FAT_SECTOR, DIFAT_SECTOR = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFC
PNG = bytes.fromhex("89504E470D0A1A0A")


class RvtError(ValueError):
    """A file that is not a readable Revit file: said in words."""


class _Compound:
    """The little of the compound file format needed (MS-CFB): the FAT, the mini FAT, the directory, a stream."""

    def __init__(self, fh, size: int):
        self.fh, self.size = fh, size
        head = fh.read(512)
        if len(head) < 512 or head[:8] != SIGNATURE:
            raise RvtError("not an OLE2 compound file")
        self.sector = 1 << struct.unpack_from("<H", head, 30)[0]
        self.mini = 1 << struct.unpack_from("<H", head, 32)[0]
        if self.sector not in (512, 4096) or self.mini != 64:
            raise RvtError("an OLE2 file of an unknown layout")
        fat_count, self.directory_start = struct.unpack_from("<II", head, 44)[0], struct.unpack_from("<I", head, 48)[0]
        self.cutoff = struct.unpack_from("<I", head, 56)[0]
        mini_start, mini_count = struct.unpack_from("<II", head, 60)
        difat_start, difat_count = struct.unpack_from("<II", head, 68)
        difat = list(struct.unpack_from("<109I", head, 76))
        sect = difat_start
        for _i in range(difat_count):
            if sect in (FREE, END):
                break
            data = self._sector(sect)
            n = self.sector // 4
            values = struct.unpack(f"<{n}I", data)
            difat += values[:-1]
            sect = values[-1]
        self.fat: list[int] = []
        for s in difat[:fat_count] if fat_count <= len(difat) else difat:
            if s in (FREE, END):
                continue
            self.fat += struct.unpack(f"<{self.sector // 4}I", self._sector(s))
        self.minifat: list[int] = []
        s, count = mini_start, 0
        while s not in (FREE, END) and count <= mini_count:
            self.minifat += struct.unpack(f"<{self.sector // 4}I", self._sector(s))
            s, count = self._next(s), count + 1
        self.entries = self._directory()
        root = self.entries[0] if self.entries else None
        self.ministream = self._chain(root[1], root[2]) if root else b""

    def _sector(self, s: int) -> bytes:
        offset = (s + 1) * self.sector
        if offset + self.sector > self.size + self.sector:
            raise RvtError("a sector beyond the end of the file: the file is cut short")
        self.fh.seek(offset)
        return self.fh.read(self.sector).ljust(self.sector, b"\0")

    def _next(self, s: int) -> int:
        if s >= len(self.fat):
            raise RvtError("a damaged file allocation table")
        return self.fat[s]

    def _chain(self, start: int, size: int) -> bytes:
        out = bytearray()
        s, seen = start, 0
        limit = size if size else MAX_STREAM
        while s not in (FREE, END, FAT_SECTOR, DIFAT_SECTOR) and len(out) < limit:
            out += self._sector(s)
            s = self._next(s)
            seen += 1
            if seen > (self.size // self.sector) + 2:
                raise RvtError("a loop in the file allocation table")
        return bytes(out[:size]) if size else bytes(out)

    def _directory(self) -> list:
        data = self._chain(self.directory_start, 0)
        out = []
        for k in range(0, len(data) - 127, 128):
            e = data[k:k + 128]
            length = struct.unpack_from("<H", e, 64)[0]
            if not 2 <= length <= 64 or e[66] == 0:
                continue
            name = e[:length - 2].decode("utf-16-le", "replace")
            start = struct.unpack_from("<I", e, 116)[0]
            size = struct.unpack_from("<Q", e, 120)[0] if self.sector == 4096 else struct.unpack_from("<I", e, 120)[0]
            out.append((name, start, size, e[66]))
        return out

    def names(self) -> list[str]:
        return [e[0] for e in self.entries if e[3] == 2]

    def stream(self, name: str) -> bytes | None:
        for entry_name, start, size, kind in self.entries:
            if entry_name == name and kind == 2:
                if size > MAX_STREAM:
                    return None
                if size < self.cutoff:
                    out = bytearray()
                    s, seen = start, 0
                    while s not in (FREE, END) and len(out) < size and s < len(self.minifat):
                        out += self.ministream[s * self.mini:(s + 1) * self.mini]
                        s = self.minifat[s]
                        seen += 1
                        if seen > len(self.minifat):
                            raise RvtError("a loop in the mini allocation table")
                    return bytes(out[:size])
                return self._chain(start, size)
        return None


def _basic_info(data: bytes) -> dict:
    """The version, the build and the central model's path from BasicFileInfo. Recent versions (seen: 2021-2026) write
    length-prefixed UTF-16 strings, among them the year alone; older ones lines of text («Format: 2018»)."""
    out = {"format": "", "build": "", "central": ""}
    m = re.search(rb"\x04\x00\x00\x00(2\x000\x00[0-9]\x00[0-9]\x00)", data)
    if m:
        out["format"] = m.group(1).decode("utf-16-le")
    texts = [data.decode("utf-16-le", "ignore"), data[1:].decode("utf-16-le", "ignore"), data.decode("utf-8", "ignore")]
    for text in texts:
        if not out["format"]:
            found = re.search(r"Format\s*:\s*(20[0-9]{2})", text) or re.search(r"Autodesk Revit (20[0-9]{2})", text)
            if found:
                out["format"] = found.group(1)
        if not out["build"]:
            found = re.search(r"([0-9]{8}_[0-9]{4}\(x64\))", text)
            if found:
                out["build"] = found.group(1)
        if not out["central"]:
            found = re.search(r"(\\\\[^\x00\r\n]{3,300}?\.rvt)", text, re.IGNORECASE)
            if found:
                out["central"] = found.group(1)
    return out


def read(path) -> dict:
    """What the file says of itself (the module's docstring)."""
    path = Path(path)
    try:
        size = os.path.getsize(path)
        with path.open("rb") as fh:
            cf = _Compound(fh, size)
            info = cf.stream("BasicFileInfo")
            atom = cf.stream("PartAtom")
            preview = cf.stream("RevitPreview4.0")
            names = cf.names()
    except (OSError, struct.error, IndexError) as error:
        raise RvtError(f"not a readable Revit file: {error}") from None
    if info is None and atom is None:
        raise RvtError("an OLE2 file, but not a Revit one: it has no BasicFileInfo")
    out = {"size": size, "streams": len(names), "title": "", "preview": b"", **_basic_info(info or b"")}
    if atom:
        xml = atom.decode("utf-8", "ignore")
        title = re.search(r"<title>([^<]*)</title>", xml)
        out["title"] = title.group(1).strip() if title else ""
        if not out["format"]:
            year = re.search(r"Revit[^<]*?(20[0-9]{2})", xml)
            out["format"] = year.group(1) if year else ""
    if preview:
        at = preview.find(PNG)
        if at >= 0:
            out["preview"] = preview[at:]
    return out


def installed_revit(root=None) -> list[int]:
    """The years of Revit installed on this PC, from its usual folders: nothing is started, nothing is written."""
    base = Path(root) if root is not None else Path(os.environ.get("ProgramW6432") or r"C:\Program Files") / "Autodesk"
    out = []
    try:
        for entry in base.iterdir():
            m = re.fullmatch(r"Revit (20[0-9]{2})", entry.name)
            if m and (entry / "Revit.exe").is_file():
                out.append(int(m.group(1)))
    except OSError:
        return []
    return sorted(out)


def can_open(file_format: str, years: list[int]) -> int | None:
    """The oldest installed Revit that opens a file of this format: a Revit opens what its version or an older one
    saved, and upgrades it; never what a later one saved."""
    try:
        wanted = int(file_format)
    except ValueError:
        return None
    usable = [y for y in years if y >= wanted]
    return min(usable) if usable else None
