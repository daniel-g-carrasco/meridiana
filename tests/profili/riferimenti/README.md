# Italian parity references, study 44

Acquired from `236dcc12101869a291653423cf1e8187cffc47eb` before changing any production source.
The environment and acquisition command are recorded in `it/metadata.json`.

Each bank runs in a fresh process with its language set **before** importing the producers.
This matters: some legacy descriptions are translated at import time and Meridio caches its passages.
The preliminary acquisition in one process did not repeat reliably and was archived outside these references,
before freezing this baseline. No production code was changed to make the snapshots repeatable.

The test command is `python -m unittest discover -s tests/profili -t tests` with the environment of the assignment.
Acquisition was a separate, explicit command: `python -m profili.snapshot --capture`.
It refuses to overwrite a reference. Tests never call acquisition or update a reference.

## Banks

- `rules`: all 26 existing rules, ordered paragraphs, sources, Item fields, report filters, notes and actions;
  powers just below, at and above every threshold, AC/DC ordering, design and renewable obligation cases,
  installations, storage, activities and connection combinations. The baseline has no N17: none is invented.
- `layouts`: four shared fixture projects, automatic and deterministic manual rows, complete projects,
  effective parameters, ordered placed modules with keys and corners, exclusions, guides, bands and checks.
- `electrical`: temperature known/missing, missing module coefficients and limits, MPPT/current/series/fuse
  cases, suggestions and manufacturer/market advice. Full plans and provenance records are frozen.
- `optimizers`: four inverter models crossed with four optimizer models, one/two modules per optimizer,
  one/two/three strings, short/valid/long strings, market restrictions and complete checks/provenance.
- `calendar`: every hourly timestamp in UTC and local time, band masks, leap-year and normal-year holidays,
  every synthetic consumption profile, annual/monthly/band/measured curves and their figures;
  ordinary/community economics in all three zones, with/without storage, grant, TRASE, deduction,
  complete hourly/monthly/yearly flows, KPIs and size/storage sensitivities.
- `pipeline`: synthetic cached weather, with/without a chimney and with/without a catalogue inverter.
  The two connected cases must produce positive energy. Complete pipeline output and composed reports.
- `reports_geometry`: complete and compact report documents for each geometry fixture, including manual rows.
- `pdf`: extracted text, page by page, of the actual complete and compact PDFs at a fixed date.
  An unavailable renderer is reported as a skipped test, never as a verified PDF.
- `interface`: property schemas, tool specifications and responses, every individual rule, activity catalogue,
  assistant persona, passages and help. No model or network request.
- `charts`: consumption modes and economic schemas, with/without community membership.
- `persistence`: every historical project file, migrated, serialized and reopened; malformed/future files
  retain their exact exception type/message. `historical-sha256.json` also guards all format fixtures, ignoring
  Git's normal LF/CRLF checkout conversion for text; archive bytes are hashed without normalization.

Every bank was acquired in both Italian and English. The frozen JSON/NPZ outputs were converted without
calling any producer on 12/11/2026. Each `it/<bank>-<language>.json.gz` contains canonical UTF-8 JSON
(sorted keys, fixed `(',', ':')` separators, no NaN), compressed with gzip level 9, `mtime=0`,
no embedded filename and a fixed OS header byte of 255.
The complete canonical JSON has a SHA-256 fingerprint. No tolerance is used.

## Lightweight storage and diagnostics

- `rules`, `layouts`, `electrical`, `optimizers`, `interface`, `persistence`, `charts`, `reports_geometry`,
  `pdf`: complete JSON values remain in gzip, including every text and list in its original order.
- `calendar`, `pipeline`: lists longer than 64 elements are replaced with the SHA-256 of their complete
  canonical form, their length and their first/last two elements. All other JSON remains readable in gzip.
  The digest checks every middle element too, including hourly ISO timestamps and object arrays.
- All numeric arrays from `calendar`, `pipeline` and `layouts`: each original array name retains its dtype,
  shape, SHA-256 of the complete C-order bytes and first/last two values. Both languages are still checked
  independently, including every array. No numerical output is omitted or inferred from the other language.
  Byte fingerprints also detect signed-zero and NaN-bit changes, which are stricter than array equality.
- `metadata.json`, debt lists, historical fixture fingerprints and `generic/declared.json`: unchanged in
  plain text. The generic bank is already only 385 bytes and contains no hourly arrays.

All `source`/`reference` string values are also retained in a separate inventory, including those in the
middle of hashed lists. The source-inventory test visits all 22 compressed references and cannot pass on
an empty file glob.

On failure, the parity test prints the first eight differing JSON pointers with expected/actual values
or fingerprints. It preserves the **complete current JSON and NPZ** in a new system temporary directory,
whose absolute path is printed. For a hashed list/vector, its pointer identifies the changed section;
the old middle values are intentionally represented only by their digest and cannot be reconstructed.
The original frozen capture remains available in the local branch history, never reacquired from new code.

To regenerate the complete current output independently, create a new empty temporary directory and run
`python -m profili.worker <bank> <it|en> <new-folder>` with `PYTHONPATH=tests;src` and the assignment environment.
This is also the exact worker run by the parity tests. It refuses to overwrite existing output files.
To inspect a stored reference: `python -m gzip -d <file.json.gz>` on a **temporary copy** of the file.
Acquisition refuses to overwrite either the original JSON or its compressed replacement. Tests never update
references. Original-to-lightweight conversion was checked for all 22 JSON outputs and 2,276 named arrays;
all original files were copied to ignored local scratch before replacement.

Text, list order, counts, timestamps, masks, floats, array dtype and shape are all still checked.
Only generated project identities, project creation/modification dates and the report's date are fixed,
with explicit keys in the metadata. No numeric fields, sources, paragraphs or list ordering are discarded.
Physical geometry and computation algorithms have not been changed.

`debiti-iniziali.json` is the immutable initial census; `debiti.json` is the active, exact debt list. Each entry
has a path, symbol/JSON pointer, complete exact string, count and reason. Both additions and paid entries left
in the active list fail. The active list must remain a subset of the original. Only the three layers'
`profiles/it` folders are allowed by position. The test's synthetic counterexamples cover Python, QML, JSON,
Italian imports, removed debt and a core profile importing data/gui.

The generic profile's executable counterproofs, registry equality and format-31 migration tests belong to
their implementation steps. This baseline does not claim these future behaviors already exist.
