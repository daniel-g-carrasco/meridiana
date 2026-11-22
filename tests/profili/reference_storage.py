"""Deterministic, exact fingerprints of frozen JSON lists and numeric vectors.

Only calendar/pipeline long lists are hashed. Every other JSON value remains
readable after decompression. Acquisition and conversion never run in a test.
"""

import gzip
import hashlib
import io
import json

import numpy as np


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _compact(value):
    if isinstance(value, list):
        if len(value) > 64:
            return {"$snapshot_list": {"sha256": hashlib.sha256(canonical(value)).hexdigest(),
                                      "length": len(value), "first": value[:2], "last": value[-2:]}}
        return [_compact(item) for item in value]
    if isinstance(value, dict):
        if "$snapshot_list" in value:
            raise ValueError("Reserved snapshot key in source JSON")
        return {key: _compact(item) for key, item in value.items()}
    return value


def document(data, arrays, *, compact=False):
    sources = set()

    def inventory(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"source", "reference"} and isinstance(item, str):
                    sources.add((key, item))
                inventory(item)
        elif isinstance(value, list):
            for item in value:
                inventory(item)

    inventory(data)
    vectors = {}
    for name, array in arrays.items():
        if array.dtype.hasobject:
            raise ValueError("Object arrays must be encoded as JSON")
        vectors[name] = {"dtype": str(array.dtype), "shape": list(array.shape),
                         "sha256": hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest(),
                         "first": repr(array.ravel()[:2].tolist()),
                         "last": repr(array.ravel()[-2:].tolist())}
    return {"version": 1, "compact_lists": compact, "sha256": hashlib.sha256(canonical(data)).hexdigest(),
            "data": _compact(data) if compact else data, "arrays": vectors,
            "source_fields": [{key: value} for key, value in sorted(sources)]}


def pack(value):
    stream = io.BytesIO()
    with gzip.GzipFile(filename="", fileobj=stream, mode="wb", compresslevel=9, mtime=0) as zipped:
        zipped.write(canonical(value))
    return stream.getvalue()


def unpack(raw):
    return json.loads(gzip.decompress(raw))


def differences(expected, actual, limit=8):
    """Return the first differing JSON pointers, bounded even for hourly vectors."""
    found = []

    def visit(left, right, path):
        if len(found) >= limit:
            return
        if type(left) is not type(right):
            found.append(f"{path}: expected {type(left).__name__}, got {type(right).__name__}")
        elif isinstance(left, dict):
            for key in sorted(left.keys() | right.keys()):
                pointer = path + "/" + key.replace("~", "~0").replace("/", "~1")
                if key not in left or key not in right:
                    if len(found) < limit:
                        found.append(f"{pointer}: {'unexpected' if key not in left else 'missing'} key")
                else:
                    visit(left[key], right[key], pointer)
        elif isinstance(left, list):
            if len(left) != len(right):
                found.append(f"{path}: expected length {len(left)}, got {len(right)}")
            for i, (a, b) in enumerate(zip(left, right, strict=False)):
                visit(a, b, f"{path}/{i}")
                if len(found) >= limit:
                    break
        elif left != right:
            found.append(f"{path}: expected {repr(left)[:180]}, got {repr(right)[:180]}")

    visit(expected, actual, "$")
    return found
