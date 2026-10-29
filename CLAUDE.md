# Meridiana: notes for Claude Code

Meridiana designs photovoltaic plants: site on a map, buildings and roofs, module layout with the fire brigade
rules, hourly energy with every loss (PVsyst is the reference for the functions, Aurora for the modelling and
the use, PVGIS for the data), string checks, consumption, economics, a PDF report where every number says where
it comes from. Python 3.12+, Qt 6.12 with PySide6 6.12.0 and Qt Quick 3D, pvlib 0.16.1, shapely.
GPL-3.0-or-later. Public repository `daniel-g-carrasco/meridiana` since 25/10/2026 (the history before it is in
the private `meridiana-archivio`); the owner is Daniel Grasso, an electrical
engineer in Italy, and the scope is national (regional rules are modules, never the scope).

These notes are read by local sessions and by cloud sessions. A cloud session sees only this repository: not
Daniel's PC, his archive of standards, the shared drive, his Linux laptop or the local session's memory. What it
needs to know is here or in `docs/`.

## Language and style

- **Replies to Daniel in Italian.** Code, comments and commit messages in English. The documents in `docs/`
  (`progetto.md`, `funzionalita.md`, `studio/*`) and the translations are in Italian: short sentences, lists,
  numbers with the decimal comma, [V] for what was verified (with how) and [I] for what was inferred.
- **Never the em dash (U+2014), anywhere**: a colon, a comma, a full stop. `tests/nucleo/test_release.py` checks it.
- **No AI attribution** in commits or pull requests: no Co-Authored-By, no session link, no "Generated with".
  `.claude/settings.json` turns the default lines off; keep it so. Commit messages in the first person or
  impersonal.
- **Decisions are Daniel's.** When there is a choice, give the options with their pros and cons and a
  recommendation, then follow what he decides. Decisions already taken are in the studies and in
  `docs/progetto.md` section 1: do not reopen them.
- **Standards and laws are never quoted from memory** (CEI, UNI, IEC, decrees, fire brigade rules). The archive
  is on Daniel's PC: a cloud session that needs an article says so and leaves it to the local session.

## The code

- The core is pure Python without Qt in `src/meridiana/` (geometry, sun, roofs, layout, model, `settings.py`,
  `energy/`, `checks.py`, `rules.py`, ...); `model.py` does not import `energy/`. The session (`session.py`,
  without Qt) holds the work in hand: project, layouts with their keys, energy year, selection, undo, what
  is saved; `jobs.layout_of` and `energy/pipeline.compute` are the computations as plain functions. The
  window is in `src/meridiana/ui/`. **The window displays and collects the gestures; everything that
  computes lives in the core, with its tests.** The module map is in `docs/progetto.md`, section 2.
- **The window never waits.** Layout and energy run in `QRunnable` jobs on `QThreadPool.globalInstance()`
  (`LayoutJob`, `EnergyJob` in `ui/window.py`, `CompareJob` in `ui/variants.py`); results come back with
  signals. Charts and formulas are drawn only when visible.
- **Every change to the project goes through `session.edit()`** (the window's `edit()` delegates to it): the
  undo snapshot before and after, the project put back if the change raises, and the listeners told by
  topic (`project:text`, `project:geometry`, `layout:<id>`, `energy`, `checks`...; the list is in
  `session.py`). A view follows its topics, never "everything": a rename lays out nothing and computes no
  year (`tests/finestra/test_speed.py`).
- Never `except Exception: pass`: what goes wrong is said (status bar, a message, the log).
- User-facing strings are wrapped in `_()` from `meridiana.i18n`; numbers are formatted with `number()`.
- The project file (`model.py`) is written whole or not at all, with the previous copy kept as `.bak`; a format
  change bumps the format version and adds a migration. The user's settings are in `config.py`: a field with a
  typed default, and a format change is a migration step with `CONFIG_VERSION + 1`.
- Qt lessons already paid for:
  - the 3D view is a `QuickImage` (`ui/quick_image.py`: `QQuickRenderControl` into a texture, read back into an
    image the raster window paints) since 25/10/2026: a `QQuickWidget` made every repaint of the 4K window slow
    (`docs/prestazioni`), and `QQuickView` in `createWindowContainer` deadlocks with the threaded render loop
    (Python instancing called from the render thread);
  - values for the 3D scene go in as QML bindings: a value set from Python overrides the binding;
  - `QScrollArea.setWidget` deletes the old page at once: use `takeWidget` and `deleteLater`;
  - Qt Quick 3D takes at most 4 directional lights;
  - spin boxes and combo boxes must not take the wheel without focus (`ui/wheel.py`).

## How Meridiana runs

Read this before judging how much a defect matters.

- **One main window per process** (`app.py`): no `WA_DeleteOnClose`, alive until `exec()` returns; closing it quits
  the program and nothing is dispatched after `exec()`. The File page, Meridio and the docks are its children;
  dialogs are modal or short-lived.
- **Threads**: layout, energy, plant, IFC, comparisons run as `QRunnable` jobs on the global pool and answer with
  queued signals on the main thread; the report and the map tiles go in steps on the event loop
  (`ui/tileloader.py`); the 3D view renders on the main thread through `QQuickRenderControl` (`ui/quick_image.py`).
- **What the user meets**: the window and its status bar, the log (`log.file()`), and the files written next to the
  project: the project itself (whole or not at all, the previous copy as `.bak`), the revisions `_Rnn`, the report
  (written as `.pdf.part`, renamed at the end).
- **The tests are not the program**: the suite builds and disposes many windows in one process, offscreen. A
  use-after-delete that fires only after `dispose()`, or a picture that differs only offscreen, is a test matter,
  not a user's.

**Severity**, the same words in every review:
- **high**: loses or corrupts the user's data, crashes or freezes in normal use, a wrong number in a computation or
  in the report;
- **medium**: something the user sees wrong or that gets in the way (a text in the wrong language, a file left next
  to the project, a control that does nothing), with a way around it;
- **low**: cosmetic, or only on an unusual path;
- **tests only**: happens only in the suite; fixed when cheap, never called a user's bug.

## Diagnosing a failure

- **A diagnosis counts only when it reproduces the observed symptom**: the same message, the same numbers, the same
  place (for a CI failure, the same values in the assertion, the same pixel). A similar failure found locally is a
  different failure until shown otherwise: say which one was reproduced.
- **Start from the raw evidence and quote it**: the CI run's log (the repository is public:
  `https://github.com/daniel-g-carrasco/meridiana/actions`, or `gh run view <id> --log-failed`), the traceback, the
  user's screenshot.
- **Say what differs** between where it failed and where it is reproduced: platform, fonts and their antialiasing,
  screen scale, offscreen or a real screen, Python version, models or programs installed in the home.
- Every claim [V] verified (and how) or [I] inferred; a fix for an [I] diagnosis says so.
- **A test fixed by loosening it must still catch what it was written for**: add the case that proves it.
  (25/10/2026: a review blamed the accent test's CI failure on a field's focus ring, 62 points; the CI had one
  pixel, coloured by the subpixel antialiasing of a title. The fix proposed would have left the CI red.)

## Tests, lint, translations

```
python -m ruff check --select F,E9,B .          # the rules are also in pyproject.toml (F, E9, B)
python tools/compile_po.py                      # the catalogues the tests load
QT_QPA_PLATFORM=offscreen python -W default -m unittest discover -s tests
# one group: nucleo, calcoli, formati, widget, finestra (esterni only when asked, below)
QT_QPA_PLATFORM=offscreen python -W default -m unittest discover -s tests/nucleo -t tests
# the coverage, once a week or on request (not at every push): sysmon, or the window's threads are not seen
COVERAGE_CORE=sysmon QT_QPA_PLATFORM=offscreen python -m coverage run --source=src/meridiana -m unittest discover -s tests
python -m coverage report -m
```

- The coverage is measured with `COVERAGE_CORE=sysmon` (Python 3.12+, coverage 7.4+): coverage's default C tracer
  does not follow the `QRunnable` jobs of Qt's thread pool and gives `ui/window.py` 73 % for a fault of the tool
  (study 18, D 3.1 and defect 20).
- The tests are in folders, each a package (study 18, D 7.1; task 18e): `nucleo/` the core without Qt (a few tests
  use a QImage or the report's HTML), `calcoli/` the energy with its references (`calcoli/riferimenti/`, the
  answers of PVGIS 5.3 recorded, with their README), `formati/` the files of every version (`formati/file/`, frozen:
  a new format adds a file, never rewrites one), `widget/` one widget at a time offscreen, `finestra/` the
  `MainWindow` itself, made by `_setup.window` (a second one only where a restart is the point) and driven along
  journeys of steps on one window (a new window costs about half a second offscreen: what a widget alone can prove
  goes in `widget/`), `esterni/` what needs Daniel's PC (`MERIDIANA_PVSYST_SAMPLES` naming the folder of the real
  PVsyst files) or a machine that is not busy (`MERIDIANA_ESTERNI=1`: the times). `_setup.py` has the paths, the
  waits on a condition (`wait_until`, `wait_settled`; `turn_events` only where the time itself is tested),
  `keyboard_or_skip`, `dispose`, `window` (the window of a test; its 150 ms pause before a layout skipped,
  `pause=True` keeps it), `meridiana_look` (the window's font and sheet for a widget alone) and
  `keep_global_state`, the `setUpModule` of every module with Qt; `_fixtures.py` the projects and the data they share
  (a test module never imports another one). The CI runs the groups one after the other.
- During development, run lint and the tests relevant to the changed behaviour before a commit. Inspect
  screenshots for visual changes, including narrow layouts and large text. Run the full suite once before
  integrating a coherent batch and before a release, not after every small visual adjustment (Daniel, 29/10/2026).
  A known failure is reported with its evidence; thresholds are not loosened to obtain a green result.
  Regression tests cover meaningful behaviour, not a copy of the implementation.
- On Linux the window's tests run on Qt's offscreen platform, as in the CI. On Daniel's PC they run on his second
  screen (`MERIDIANA_TEST_SCREEN=1`), never on the main one; a cloud session leaves real-window checks to the
  local session and says which ones are still to do.
- A `grab()` of a widget on a real screen is in device pixels (Daniel's second screen has a ratio of 2.5), while `visualItemRect`, header sections and widget sizes are logical: a test that crops a grab scales the rectangle by `image.devicePixelRatio()` and its pixel thresholds by its square, or it passes offscreen and fails on the PC (test_marks, 23/10/2026). Read a logical point in the middle of its device pixels, `image.pixelColor(int((x + 0.5) * dpr), int((y + 0.5) * dpr))`. The ratio can be tried offscreen: `QT_SCALE_FACTOR=2.5` with `QT_QPA_PLATFORM=offscreen` makes grabs at 2.5 as on that screen (test_surfaces, test_theme, 24/10/2026).
- On a Windows set to dark the system's palette is dark (style windows11, Window `#1e1e1e`, white text), while offscreen it is Fusion's light one: a test that draws without Meridiana's theme (a bare widget, `charts.set_theme` alone) sets the palette it means first, as `Theme.apply` does (the charts take light or dark from the palette), or measures against the palette in use, never "the darkest pixel is the text" (test_charts, test_waits, 24/10/2026).
- When the screen named by `MERIDIANA_TEST_SCREEN` is not connected (Qt sees fewer screens), `_setup` moves nothing and the windows open on the main screen: check `QApplication.screens()` before a run on the PC.
- The CI (`.github/workflows/test.yml`): Linux offscreen on every push of every branch (not for the studies and
  tasks in `docs/`; the manual counts), on a pull request only from a fork; Windows (suite, bundle, self-test,
  installer) on a `v*` tag or by hand; the signed release on a tag, only once the minisign secret exists. A step's
  `name:` never holds «: » (YAML takes it for a key and GitHub refuses the whole file: `test_release.WorkflowTest`).
- New strings: `python3 tools/compile_po.py --update` on Linux (on Windows MSYS2's xgettext rewrites the whole
  file), then translate the new entries of `po/it.po` and check with `msgfmt --check po/it.po`.
- A release (only when Daniel asks): version, CHANGELOG, metainfo, docs appendix; full suite and lint; push; CI
  green on the full SHA; tag on that commit; check the release's files.

## Branches

- Daniel runs the program from another checkout that follows `main` with `git pull --ff-only`.
- The local session works on the branch `lavoro` and publishes with `git push origin lavoro` and then
  `git push origin lavoro:main`.
- **A cloud session** starts from `lavoro`, works on its own branch, pushes it and opens a pull request towards
  `lavoro` (the pull request also runs the CI). It never pushes to `main` and never rewrites history; the merge
  is done after Daniel's review.

## Where the plan is

- `docs/progetto.md`: the diary. Decisions with their reasons (section 1), architecture (2), risks (3),
  verifications (appendix A). Add a dated row for each piece of work.
- `docs/funzionalita.md` and `CHANGELOG.md`: what the program does, and what changed.
- `docs/studio/`: the studies. Read the relevant one before implementing:
  - `12-revisione-ux-prestazioni.md`: UX and speed review, the plan in phases (section 7; phase 1 is done);
  - `12a-convenzioni-ux.md`: CAD and PV conventions, shortcuts (no Ctrl+Alt, which is AltGr on Italian
    keyboards; never a command only on an F key);
  - `13-studio-estetico.md`: the look ("Meridiana") and the theme computed from one chosen colour (section 12;
    the reference implementation and its checks are in `13-colori/`, run with `node`);
  - `14-assistente-agente.md`: the assistant, a floating character (section 7.3);
  - `15-freecad-riferimento.md`: FreeCAD as reference, navigation styles, IFC;
  - `16-modellazione.md`: the seven modelling requests (roofs on any footprint, move and rotate, layout by
    hand, inverters and strings, catalogue filters, waits, 3D pivot) with the proofs in `16-prove/` and the
    task drafts in `docs/compiti/16*.md`;
  - `17-interfaccia.md`: the interface (surface levels, where the tools live, buttons and fields, interactive
  - `docs/studio/18-revisione-completa.md`: the complete review of 23/10/2026 (verdict: keep the core, improve step by step; reports per theme in `docs/studio/18-prove/`; the interface design in `docs/design/interfaccia.md`; tasks `docs/compiti/18a-18f`).
    charts, help next to things, the Checks panel, Meridio animated) with the HTML mockups in `17-prove/`
    (open them in a browser; `genera.py` rewrites them), the Qt proofs and the task drafts in
    `docs/compiti/17*.md`.
- `docs/compiti/`: tasks written for cloud sessions, in Italian. When a session is given one, that file is the
  plan: reread it whenever the conversation has been summarised.
- `docs/richieste.md`: **every request and decision of Daniel**, numbered (R1, R2, ...), with its state and where it
  is handled. Read it before starting; when a commit does or changes one, update its row in the same commit.

## Cloud sessions

- The machine is prepared by `tools/cloud-setup.sh` (the environment's setup script on claude.ai/code) with
  `QT_QPA_PLATFORM=offscreen`. If `requirements.txt` changes, change the script too.
- The network is the "Trusted" level: PyPI and GitHub work, PVGIS does not. Tests never need the network.
- Commits carry Daniel's name, as everywhere in this repository: before the first commit run
  `git config user.name "Daniel Grasso"` and `git config user.email code@danielgrasso.com` in the clone (the
  machine's default author is "Claude"). The pull request's description ends with the checks, without a
  "Generated by" line or a link to the session: if the tool adds one, take it out.
- At the end, a short summary in Italian for Daniel: what was done, what was verified and how, what is left to
  check on his PC.
