# Rapporto S: studio R87, Meridiana su ARM e su tablet (30/10/2026)

Studio, non revisione: nessun difetto da correggere, nessun file del programma toccato. Scritto solo in
`docs/studio/21-arm-tablet/` (README.md, script, log) e in questo rapporto.

## 1. Che cosa ho letto e provato

- `requirements.txt`, `build-aux/flatpak/requirements-flatpak.txt`, `python3-requirements.json` (le voci
  `only-arches`), `python3-kokoro.json`, il manifesto Flatpak, `build-aux/windows/meridiana.iss` (righe 40-50),
  `.github/workflows/*.yml`, `ui/selftest.py` (testa), `tests/_setup.py`, `tests/_fixtures.py`,
  `tests/calcoli/test_pipeline.py`.
- Per il tocco: `src/meridiana/navigation.py` (tutto), `ui/plan.py` (costanti 46-103, `_pick`/`_vertex_near`/
  `_side_near` 1265-1360, eventi 1916-2333), `ui/view3d.py` (backend 520-700, `View3D.event`/`wheelEvent` 916-958),
  `ui/quick_image.py` (inoltro eventi 284-316), `ui/qml/Scene.qml` (MouseArea 401-453), `ui/viewcube.py` (191-206),
  `ui/design.py` (Size, Button, Icon).
- Prove vere (comandi e esiti nel README, sezioni 2 e 3.1, log in `docs/studio/21-arm-tablet/wsl/log/`):
  1. PyPI JSON per 29 pacchetti (`pypi_wheels.py`): tabella delle ruote per win_arm64, manylinux/musllinux aarch64,
     macOS arm64, Android, iOS.
  2. WSL openSUSE: installati come root `qemu-linux-user` 11.1.2 e `podman` 6.1.2 (16 s); binfmt `qemu-aarch64`
     attivo con flag F; remote Flathub aggiunto.
  3. Contenitore aarch64 (`python:3.12-slim-trixie`, glibc 2,41) con PySide6 6.12.0, numpy, scipy, pandas, shapely,
     pvlib, matplotlib, pyqtgraph, ifcopenshell: import di Meridiana, `tests.calcoli.test_pipeline`,
     `tests.finestra.test_selection_3d`, `meridiana --self-test`. Esito: import in 24,9 s (`qt 6.12.0`, `meridiana
     0.1.0` su `aarch64`); pipeline 8 test OK (3 min 19 s emulati); finestra offscreen 3 test OK (6 min 57 s), 3D
     non disegnato per mancanza di dispositivo grafico; self-test 28 PASS/INFO e un solo FAIL, il limite di 240 s
     scaduto prima dell'anno e della relazione (la finestra da sola ha preso 129,6 s sotto qemu).
  4. Flatpak aarch64: `org.kde.Platform//6.11` e `io.qt.PySide.BaseApp//6.11` installati (1 min 35 s) e Python del
     BaseApp eseguito sotto qemu: PySide6 6.11.2 e numpy 2.3.5 importati in 4,0 s.
  5. Tocco offscreen su Windows (`prova_tocco.py`, QTouchEvent con `QTest.createTouchDevice`): un dito = tasto
     sinistro sintetizzato (seleziona in pianta, picking nel 3D); due dita = niente zoom né pan, e il secondo dito
     seleziona; 77 pulsanti visibili, 66 tra 23 e 40 px, 11 sotto 23 px.
- Letture (non prove): doc Qt (Qt Quick 3D requirements, Android, iOS, QNativeGestureEvent, attributi
  `AA_SynthesizeMouseForUnhandledTouchEvents`, `WA_AcceptTouchEvents`), blog Qt su PySide6 iOS (30/07/2026), note
  settimanali Qt for Python, indice download.qt.io, python.org, aiuto Inno Setup, Microsoft Learn (Prism, bersagli
  del tocco), ricerche web (PyInstaller 5.7.0 ARM64, runner GitHub ARM, ricette python-for-android).

## 2. Difetti trovati

Nessuno cercato nel codice (compito di studio). Osservazioni che somigliano a difetti, per quando si farà il tocco:
- Un trascinamento a due dita in pianta oggi cambia la selezione (il secondo dito arriva come clic sinistro): con
  uno schermo touch è un comportamento sbagliato, riprodotto da `prova_tocco.py` (`test_plan`, terza riga).
- `python3-kokoro.json` ha `only-arches: x86_64` su onnxruntime, espeakng-loader e protobuf: un Flatpak aarch64 lo
  costruirebbe senza la voce (le ruote aarch64 esistono: `onnxruntime-1.31.1-cp313-cp313-manylinux_2_28_aarch64.whl`,
  `espeakng_loader-0.2.4-py3-none-manylinux_2_28_aarch64.whl`, `protobuf-7.36.2-cp310-abi3-manylinux2014_aarch64.whl`).

## 3. Difetti sospetti non confermati

- Il self-test (`LIMIT_S = 240`) sotto emulazione potrebbe scadere: se accade, è il limite, non il programma.
- Il 3D offscreen nel contenitore dipende da Mesa llvmpipe: se la scena non parte, il programma deve dirlo
  (`View3D.failed`), non bloccarsi. Confermato: con `QRhiGles2: Failed to create context` i test della finestra
  passano e il self-test scrive `INFO 3D graphics: none`; il limite dei 240 s è scaduto davvero (FAIL time), come
  previsto, senza altri FAIL.

## 4. Modifiche richieste a file non miei

Nessuna da applicare ora. Proposte per quando Daniel decide (sezione 5 del README):
- `build-aux/flatpak/python3-kokoro.json`: aggiungere le tre ruote aarch64 (sopra) con `only-arches: [aarch64]`.
- `.github/workflows/test.yml` e `flatpak-build.yml`: matrice con `windows-11-arm` e `ubuntu-24.04-arm`.
- `build-aux/windows/meridiana.iss`: seconda compilazione con `ArchitecturesAllowed=arm64` per il pacchetto ARM64.

## 5. msgid nuovi

Nessuno.

## 6. Prove eseguite

- `python -I pypi_wheels.py <29 pacchetti>` -> tabella (log `wsl/log/pypi_table.md`).
- `wsl -d openSUSE-Tumbleweed -u root -- bash wsl_install.sh` -> podman 6.1.2, qemu-aarch64 enabled, Flathub aarch64
  refs (log `wsl_install.log`).
- `bash run_arm64.sh` (podman build/run --arch arm64) -> build 10 min 50 s; import OK 24,9 s; `test_pipeline` 8 OK;
  `test_selection_3d` 3 OK; self-test 28 PASS/INFO + `FAIL time: more than 240 s` (log `run_arm64.log`,
  rapporto `self-test-aarch64.txt`).
- `bash flatpak_arm64.sh` -> `machine aarch64 qt 6.11.2 numpy 2.3.5 in 4.0 s` (log `flatpak_arm64.log`).
- `python docs/studio/21-arm-tablet/prova_tocco.py` offscreen -> 3 test OK, esiti nel log `prova_tocco.log`.
- `ruff check --select F,E9,B docs/studio/21-arm-tablet/prova_tocco.py` -> All checks passed.
- Nessun trattino lungo nei file scritti (grep).

## 7. Limiti

Nessuna macchina Windows ARM64, nessuno schermo touch, nessun tablet: le prove ARM sono emulate (esatte per le
istruzioni, non per i tempi), quelle del tocco sono eventi sintetici offscreen. Costruzione del Flatpak aarch64 e
del pacchetto Windows ARM64 non eseguite: passi e tempi stimati nel README (2.3 e 2.4). Ricette python-for-android
per scipy e shapely: fonti di seconda mano. Rete usata solo per PyPI, Flathub, immagini Debian e documentazione.

Che cosa resta nella WSL `openSUSE-Tumbleweed` (nulla su Windows): i pacchetti `qemu-linux-user` e `podman` con i
binfmt attivi, il remote Flathub, il runtime `org.kde.Platform//6.11`, Mesa e `io.qt.PySide.BaseApp//6.11` per
aarch64 (circa 2,2 GB installati, system), le immagini podman `python:3.12-slim-trixie` (149 MB) e
`localhost/meridiana-arm64` (1,53 GB). Si tolgono con `flatpak uninstall --arch=aarch64 ...` e `podman rmi`, se
Daniel lo vuole; servono tal quali per la costruzione Flatpak aarch64 (README 2.3).
