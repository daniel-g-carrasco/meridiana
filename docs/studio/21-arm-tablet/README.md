# Studio 21: Meridiana su ARM e su tablet (R87)

Daniel, 24/10/2026: «Meridiana su tablet e/o su ARM?». Studio fatto il 30/10/2026 (dopo mezzogiorno, come chiesto),
con prove vere dove questo PC lo permette. Convenzioni: [V] verificato, con il comando o la fonte; [I] dedotto o
solo letto. I numeri con la virgola decimale. Gli script di prova sono in questa cartella (sezione 7).

## 0. Sintesi

- **Linux aarch64: funziona.** [V] In un contenitore aarch64 emulato con qemu-user nella WSL (Debian 13, Python
  3.12, glibc 2,41) si installano le ruote di PySide6 6.12.0, numpy, scipy, pandas, shapely, pvlib, matplotlib,
  pyqtgraph, ifcopenshell; Meridiana si importa e la pipeline energetica dei test passa. I dettagli e i tempi in 2.2.
- **Flatpak aarch64: la strada è aperta.** [V] Su Flathub esistono `org.kde.Platform//6.11`, `org.kde.Sdk//6.11` e
  `io.qt.PySide.BaseApp//6.11` per aarch64; installati nella WSL ed eseguiti sotto qemu, il Python del BaseApp importa
  PySide6 6.11.2 e numpy 2.3.5 in 4,0 s. [V] La ricetta `python3-requirements.json` porta già le ruote aarch64
  (30 voci `only-arches`). Manca solo la costruzione vera con `flatpak-builder --arch=aarch64` (2.3: passi e tempi).
- **Windows ARM64: tutto esiste, nessuna macchina per provare.** [V] Ruote win_arm64 per ogni dipendenza compilata
  (una sola eccezione innocua, protobuf, che ha la ruota pura), Python 3.12.10 e 3.13.17 con installer ARM64,
  PyInstaller 6.22.3 con la ruota win_arm64, Inno Setup con `arm64` in `ArchitecturesAllowed`, runner GitHub
  `windows-11-arm` gratuiti per i repository pubblici. [V] Intanto l'installer x64 di oggi gira già su un Surface
  ARM con l'emulazione Prism di Windows 11 (Microsoft Learn), più lento e con più batteria.
- **Tablet Windows e Linux: il programma gira, il tocco no.** [V] Prova offscreen con QTouchEvent: un dito fa
  da tasto sinistro (seleziona, disegna), due dita non fanno né zoom né pan, in pianta e in 3D; anzi, il secondo
  dito finisce per selezionare. 77 pulsanti visibili nella finestra: 66 sotto i 40 px raccomandati da Microsoft,
  11 sotto il minimo di 23 px. Il lavoro sul tocco è un lotto a sé (sezione 4), parente di R242.
- **iPad: no, non con questo codice.** [V] PySide6 6.12 porta iOS, ma «Packages with C extensions (numpy, Pillow,
  etc.) can't be used at all» (blog Qt, 30/07/2026): senza numpy, scipy e shapely non c'è Meridiana. Le alternative
  realistiche sono il desktop remoto (gratis, oggi) o un cliente web separato (riscrittura).
- **Android: possibile in teoria, costoso in pratica.** [V] Ruote PySide6 android_aarch64 su download.qt.io,
  strumento `pyside6-android-deploy` solo da host Linux o macOS; numpy ha una ricetta python-for-android, scipy e
  shapely sono incerte; Qt Quick 3D vuole OpenGL ES 3.0. [I] Settimane di lavoro per un risultato con finestra da
  PC su uno schermo da 11 pollici.
- **Raccomandazione** (sezione 5): fare il pacchetto Linux aarch64 (Flatpak) e Windows ARM64 nel CI, che costano
  poco; rimandare il tocco a un lotto dopo R242; non inseguire iPad e Android. La decisione è di Daniel.

## 1. Dipendenze per piattaforma

[V] Interrogata l'API JSON di PyPI il 30/10/2026 con `pypi_wheels.py` (sezione 7): per ogni pacchetto di
`requirements.txt` e di `build-aux/flatpak/requirements-flatpak.txt` (più quelli che il Flatpak aggiunge in
`python3-kokoro.json` e gli strumenti di pacchetto), la ruota trovata per famiglia di piattaforma, Python 3.12 o
abi3. Versione: quella fissata dal programma, altrimenti l'ultima su PyPI. «pura» = ruota `py3-none-any`, vale ovunque.

| pacchetto | versione | win_amd64 | win_arm64 | manylinux x86_64 | manylinux aarch64 | musllinux aarch64 | macOS arm64 | Android | iOS |
|---|---|---|---|---|---|---|---|---|---|
| PySide6_Essentials | 6.12.0 | cp310-abi3 | **cp310-abi3-win_arm64** | manylinux_2_34 | **manylinux_2_39_aarch64** | no | macosx_14_0_universal2 | no (1) | no (1) |
| PySide6_Addons | 6.12.0 | cp310-abi3 | **win_arm64** | manylinux_2_34 | **manylinux_2_39_aarch64** | no | universal2 | no (1) | no (1) |
| PySide6_Pdf | 6.12.0.140 | cp310-abi3 | **win_arm64** | manylinux_2_34 | **manylinux_2_39_aarch64** | no | universal2 | no (1) | no (1) |
| shiboken6 | 6.12.0 | cp310-abi3 | **win_arm64** | manylinux_2_34 | **manylinux_2_39_aarch64** | no | universal2 | no (1) | no (1) |
| shapely | 2.2.0 | cp312 | **win_arm64** | manylinux_2_28 | **manylinux_2_28_aarch64** | musllinux_1_2 | macosx_11_0_arm64 | no | no |
| numpy | 2.5.4 (nel Flatpak 2.3.5 dal BaseApp) | cp312 | **win_arm64** | manylinux_2_28 | **manylinux_2_28_aarch64** | musllinux_1_2 | macosx_11_0_arm64 | no | no |
| pandas | 3.1.0 | cp312 | **win_arm64** | manylinux_2_28 | **manylinux_2_28_aarch64** | musllinux_1_2 | macosx_11_0_arm64 | no | no |
| requests | 2.34.2 | pura | pura | pura | pura | pura | pura | pura | pura |
| pvlib | 0.16.1 | pura | pura | pura | pura | pura | pura | pura | pura |
| scipy | 1.18.1 | cp312 | **win_arm64** | manylinux_2_28 | **manylinux_2_28_aarch64** | musllinux_1_2 | macosx_12_0_arm64 | no | no |
| matplotlib | 3.11.2 | cp312 | **win_arm64** | manylinux2014 | **manylinux_2_28_aarch64** | no | macosx_11_0_arm64 | no | no |
| pyqtgraph | 0.14.0 | pura | pura | pura | pura | pura | pura | pura | pura |
| pypdf | 6.21.4 | pura | pura | pura | pura | pura | pura | pura | pura |
| anthropic | 2.3.0 | pura | pura | pura | pura | pura | pura | pura | pura |
| keyring | 25.7.0 | pura | pura | pura | pura | pura | pura | pura | pura |
| kokoro-onnx | 0.6.1 | pura | pura | pura | pura | pura | pura | pura | pura |
| onnxruntime | 1.31.1 | cp312 | **win_arm64** | manylinux_2_28 | **manylinux_2_28_aarch64** | no | macosx_14_0_arm64 | no | no |
| espeakng-loader | 0.2.4 | py3-none-win_amd64 | **py3-none-win_arm64** | manylinux2014 | **manylinux_2_28_aarch64** | no | macosx_11_0_arm64 | no | no |
| phonemizer | 3.4.0 | pura | pura | pura | pura | pura | pura | pura | pura |
| protobuf | 7.36.2 | cp310-abi3 | **manca** (2) | manylinux2014 | **manylinux2014_aarch64** | no | universal2 | pura | pura |
| flatbuffers | 25.12.19 | pura | pura | pura | pura | pura | pura | pura | pura |
| ifcopenshell | 0.9.0.post1 | py310..py315 | **win_arm64** (py310..py315) | manylinux_2_31 | **manylinux_2_31_aarch64** | no | macosx_11_0_arm64 | no | no |
| pillow (da matplotlib) | 13.0.0 | cp312 | **win_arm64** | manylinux_2_28 | **manylinux_2_28_aarch64** | musllinux_1_2 | macosx_11_0_arm64 | no | sì, cp313 ios_13_0 (3) |
| contourpy (da matplotlib) | 1.4.0 | cp312 | **win_arm64** | manylinux_2_28 | **manylinux_2_28_aarch64** | musllinux_1_2 | macosx_11_0_arm64 | no | no |
| kiwisolver (da matplotlib) | 1.5.1 | cp312 | **win_arm64** | manylinux2014 | **manylinux_2_28_aarch64** | musllinux_1_2 | universal2 | no | sì, cp313 ios_13_0 (3) |
| fonttools (da matplotlib) | 4.68.0 | cp312 | **win_arm64** | manylinux2014 | **manylinux_2_28_aarch64** | musllinux_1_2 | universal2 | pura | pura |
| pyinstaller (strumento) | 6.22.3 | py3-none-win_amd64 | **py3-none-win_arm64** | manylinux2014 | **manylinux2014_aarch64** | musllinux_1_1 | universal2 | no | no |

Note:
1. [V] Le ruote PySide6 per Android e iOS non stanno su PyPI ma su `download.qt.io/official_releases/QtForPython/pyside6/`:
   per 6.12.0 `pyside6-6.12.0-6.12.0-cp310-abi3-android_aarch64.whl`, `...-android_x86_64.whl`,
   `pyside6-6.12.0-6.12.0-cp315-cp315-ios_arm64.whl` e due per il simulatore iOS (arm64 e x86_64). Si scaricano con
   `qtpip download PySide6 --android --arch aarch64` (documentazione di `pyside6-android-deploy`).
2. [V] protobuf 7.36.2 non ha la ruota win_arm64 ma ha `protobuf-7.36.2-py3-none-any.whl` (implementazione pura in
   Python): pip la prende da solo su Windows ARM64. Serve solo a onnxruntime, cioè alla voce di Meridio; più lenta,
   ma la voce non la usa in modo pesante.
3. [V] pillow e kiwisolver hanno ruote iOS (cp313, ios_13_0_arm64_iphoneos e simulatore), per Python ufficiale su
   iOS (PEP 730). Non aiutano: numpy, scipy, shapely, pandas non ne hanno, e PySide6 per iOS usa un altro Python
   (sezione 3.3).

Che cosa manca e le alternative:
- **musllinux aarch64** (Alpine): mancano PySide6, matplotlib, onnxruntime, espeakng-loader, ifcopenshell. Non serve:
  il Flatpak usa glibc e nessun pacchetto di Meridiana è previsto su Alpine.
- **glibc minima su Linux aarch64**: le ruote PySide6 6.12.0 aarch64 sono `manylinux_2_39` (x86_64: `_2_34`): [V]
  servono glibc ≥ 2,39, cioè Ubuntu 24.04, Debian 13, Fedora 40 o più nuovi. Su Debian 12 e Raspberry Pi OS
  «bookworm» (glibc 2,36) pip non installa PySide6 6.12 da ruota. Il Flatpak non ha questo problema (porta il suo
  runtime); la ricetta `python3-requirements.json` non porta PySide6 (viene dal BaseApp).
- **Android e iOS**: dalla tabella, nessuna dipendenza compilata ha ruote; è il cuore delle sezioni 3.3 e 3.4.

## 2. Prove vere da questo PC

### 2.1 L'ambiente: WSL openSUSE Tumbleweed con qemu-user e podman

Stato trovato [V]: WSL2 con `openSUSE-Tumbleweed` (20260723, kernel 6.x, systemd attivo, 20 CPU, 15 GB di RAM,
922 GB liberi), utente `daniel` con sudo a password; `wsl -u root` entra senza password. Già presenti flatpak 1.18.4
e flatpak-builder 1.4.12; mancavano podman, docker e qemu-user. Installati come root nella WSL (niente toccato su
Windows), con `wsl_install.sh` (sezione 7):

```
zypper --non-interactive install qemu-linux-user podman      # 26 pacchetti, 16 s
systemctl restart systemd-binfmt
cat /proc/sys/fs/binfmt_misc/qemu-aarch64                      # enabled, interpreter /usr/bin/qemu-aarch64, flags: PF
podman --version                                               # 6.1.2
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

`qemu-linux-user` 11.1.2 registra da solo i binfmt per aarch64 (e per altre 30 architetture) con il flag `F`
(l'interprete resta aperto: funziona anche dentro i contenitori e dentro flatpak-builder). Tutto il giro: 16 s.

### 2.2 Linux aarch64 in un contenitore emulato

[V] Immagine `docker.io/library/python:3.12-slim-trixie` tirata con `podman run --arch arm64`: `uname -m` dice
`aarch64`, Python 3.12.16, glibc 2,41 (Debian 13; serve ≥ 2,39 per PySide6 aarch64, vedi 1). Poi l'immagine
`meridiana-arm64` dal `Containerfile` della sezione 7: le librerie di sistema di Qt (libgl1, libegl1, libxkbcommon0,
libfontconfig1, libdbus-1-3, libpulse0...) e `pip install --only-binary=:all:` di PySide6_Essentials, PySide6_Addons,
PySide6_Pdf 6.12.0, shapely, numpy, pandas, requests, pvlib 0.16.1, scipy, matplotlib, pyqtgraph, pypdf, keyring,
ifcopenshell. Il repository montato in sola lettura in `/src`, `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH=/src/tests:/src/src`.

Esiti [V] (`run_arm64.sh`, log in `wsl/log/run_arm64.log`; i tempi sono sotto emulazione, da 10 a 30 volte il
nativo, e non dicono nulla sulle prestazioni di una macchina ARM vera):

| passo | esito | tempo (emulato) |
|---|---|---|
| `podman build --arch arm64` (apt + pip di 36 pacchetti, tutte ruote, nessuna compilazione) | immagine `meridiana-arm64` | 10 min 50 s |
| import di numpy, scipy, pandas, shapely, pvlib, matplotlib, pyqtgraph, PySide6 (QtCore, QtWidgets, QtQuick3D, QtQuickWidgets) e `meridiana` | `machine aarch64 python 3.12.16`, `qt 6.12.0 numpy 2.5.4 scipy 1.18.1 pandas 3.1.0 pvlib 0.16.1 shapely 2.2.0`, `meridiana 0.1.0` | 24,9 s |
| `python -m unittest tests.calcoli.test_pipeline` (la catena energetica senza Qt sul capannone di Rho: layout, anno sintetico, stringhe, economia) | `Ran 8 tests ... OK` (solo i `Pandas4Warning` su `weekday`, già noti con pandas 3) | 3 min 19 s |
| `python -m unittest tests.finestra.test_selection_3d` (la MainWindow offscreen con pianta e 3D) | `Ran 3 tests ... OK`; il 3D dice `QRhiGles2: Failed to create context` e `QQuickRenderControl: Failed to initialize QRhi` (nessun dispositivo grafico nel contenitore) e il programma va avanti come previsto | 6 min 57 s |
| `python -m meridiana --self-test /out/self-test-aarch64.txt` | 28 righe PASS o INFO (catalogo, font, icone, manuale, 24 262 prodotti, scena 3D, pvlib, matplotlib, pyqtgraph, scipy, shapely, pypdf, ifcopenshell, keyring, finestra in 129,6 s, layout di 128 moduli in 10,8 s, IFC andata e ritorno, scena 3D `Ready`, 3D non disegnato: `offscreen: no graphics device`), poi `FAIL time: more than 240 s`: il limite del self-test (`LIMIT_S`) è scaduto prima dell'anno e della relazione | 4 min 5 s |

Il solo FAIL è il tempo: sotto qemu la finestra impiega 130 s dove sul PC ne impiega pochi. Nessun errore di
architettura: tutte le ruote aarch64 si caricano, la geometria e l'energia danno gli stessi risultati dei test
(sono gli stessi test), la finestra si costruisce. Il 3D non si può giudicare qui (niente GPU né llvmpipe
raggiungibile dal plugin offscreen): va visto su una macchina ARM vera, dove conta anche la GPU
(Qt Quick 3D su OpenGL o Vulkan; su un Raspberry Pi 5 o un portatile Snapdragon con Linux è da misurare).
Il rapporto del self-test è in `wsl/log/self-test-aarch64.txt`.

### 2.3 Il Flatpak aarch64

[V] Flathub ha i tre mattoni per aarch64, letti con `flatpak remote-info --arch=aarch64 flathub ...` il 30/10/2026:

| ref | commit del | scaricare | installato |
|---|---|---|---|
| `runtime/org.kde.Platform/aarch64/6.11` | 24/10/2026 | 400,2 MB | 1,2 GB |
| `runtime/org.kde.Sdk/aarch64/6.11` | esiste (dimensione non letta) | | |
| `app/io.qt.PySide.BaseApp/aarch64/6.11` (PySide6 6.11.2) | esiste | 331,4 MB | 948,8 MB |

`flatpak remote-ls --arch=aarch64` elenca il BaseApp per 6.7, 6.8, 6.9, 6.10 e 6.11 e la Platform KDE 6.10 e 6.11:
aarch64 è un'architettura di prima classe su Flathub (ogni app viene costruita anche lì).

[V] Prova fatta (`flatpak_arm64.sh`): `flatpak install --arch=aarch64 flathub org.kde.Platform//6.11
io.qt.PySide.BaseApp//6.11` (con Mesa 26.2.5, i codec e la Locale: 1 min 35 s di scaricamento e installazione), poi

```
flatpak run --arch=aarch64 --command=sh io.qt.PySide.BaseApp//6.11 -c 'uname -m; python3 --version; python3 -c "..."'
aarch64
Python 3.13.15
machine aarch64 qt 6.11.2 numpy 2.3.5 in 4.0 s          (import numpy, PySide6.QtCore, PySide6.QtQuick3D)
real 0m5.705s
```

Il runtime aarch64 gira sotto qemu dalla WSL senza altre impostazioni (il binfmt con flag `F` basta anche dentro il
sandbox di bubblewrap).

**La costruzione vera non è stata fatta** (tempo): i passi, in ordine, e i tempi stimati [I]:
1. `flatpak install --arch=aarch64 flathub org.kde.Sdk//6.11` (qualche GB, 5-10 min di rete).
2. `flatpak-builder --arch=aarch64 --repo=repo-aarch64 build-aarch64 build-aux/flatpak/io.github.daniel_g_carrasco.meridiana.yaml`
   dalla radice del repository. La ricetta pip usa già le ruote aarch64 con `only-arches` (30 voci: shapely, pandas,
   scipy, matplotlib, pillow, contourpy, kiwisolver, h5py, jiter, pydantic_core, cffi...), quindi non serve rigenerarla;
   `python3-kokoro.json` invece ha `only-arches: x86_64` su onnxruntime, espeakng-loader e protobuf: va aggiunta la
   riga aarch64 per ciascuno (le ruote esistono, tabella in 1) oppure il modulo si salta la prima volta.
   Sotto qemu `pip3 install` di ruote già scaricate e i `cleanup-commands` costano minuti, non ore; `compile_po.py`
   e `appstreamcli validate` pochi secondi; `meridiana --version` alla fine gira emulato. Stima: 10-20 min.
3. `flatpak-builder --run build-aarch64 ... meridiana --self-test` sotto emulazione: il self-test ha un limite di
   240 s (`ui/selftest.py`, `LIMIT_S`); emulato può non starci. Meglio provarlo sul portatile ARM vero o sul runner
   `ubuntu-24.04-arm` di GitHub (2.4), dove il `flatpak-build.yml` di oggi gira tal quale con `runs-on: ubuntu-24.04-arm`
   e `--arch=aarch64` non serve nemmeno (è l'architettura nativa).
4. `flatpak build-bundle repo-aarch64 meridiana-aarch64.flatpak io.github.daniel_g_carrasco.meridiana stable`.

Trappola nota [I] (commenti al post di Hadess sul cross-build Flatpak, 2016): con binfmt senza flag `F` l'interprete
qemu non è visibile dentro il sandbox e serve `--bind-mount`; con il flag `F` che openSUSE mette (visto in 2.1) il
problema non si pone, e la prova del 2.3 lo conferma per `flatpak run`.

### 2.4 Windows ARM64: senza macchina, ma con tutti i pezzi

Non c'è un PC Windows ARM64 qui; verificato quello che si può da remoto:
- [V] Ruote `win_arm64` per ogni dipendenza compilata (tabella in 1; protobuf con la ruota pura).
- [V] python.org: «Windows installer (ARM64)» per Python 3.12.10 e 3.13.17 (pagina downloads/windows, 30/10/2026).
- [V] PyInstaller 6.22.3 pubblica `pyinstaller-6.22.3-py3-none-win_arm64.whl` (PyPI JSON): il bootloader per Windows
  ARM64 è nella ruota. [I] Il changelog (ricerca web) data il supporto nativo ARM64 alla 5.7.0 (12/2022: «if it runs
  on an ARM machine with an ARM build of Python, it produces an ARM application») e alla 6.5.0 una correzione
  («bootloaders not being found when running an Intel build of Python on Windows ARM64»). Non c'è cross-build:
  il pacchetto ARM64 va costruito su una macchina ARM64 con un Python ARM64.
- [V] Inno Setup (aiuto in linea, `ArchitecturesAllowed`): identificatori `x64compatible` (x64 e Arm64 di Windows
  11), `arm64` (solo binari Arm64), `x86compatible`, `win64`. Oggi `build-aux/windows/meridiana.iss` ha
  `ArchitecturesAllowed=x64compatible` e `ArchitecturesInstallIn64BitMode=x64compatible` (righe 46-47): l'installer
  x64 si lascia installare anche su Windows 11 ARM. Per un installer ARM64 nativo: una seconda compilazione dello
  stesso `.iss` con `ArchitecturesAllowed=arm64` e il `dist\Meridiana` costruito su ARM64, nome del file con `-arm64`.
- [V] Microsoft Learn («How emulation works on Arm», «Windows App SDK deployment overview»): Windows 11 ARM esegue
  le app x64 con Prism; con 24H2 Prism espone AVX, AVX2, FMA, F16C alle app x64 (numpy e scipy li usano). «Emulated
  apps typically run with acceptable performance for productivity workloads, but graphics-intensive or
  compute-heavy apps benefit significantly from a native ARM64». Quindi l'installer di oggi funziona su un Surface
  Pro 11 (Snapdragon X), ma con più batteria e latenza; la build nativa è la strada giusta.
- [V, fonti secondarie] GitHub offre runner ospitati `windows-11-arm` e `ubuntu-24.04-arm` gratuiti per i repository
  pubblici (blog Windows Developer 14/04/2025; changelog GitHub 07/08/2025: «Linux and Windows arm64 hosted runners
  for public repositories are now generally available», 4 vCPU). Meridiana è pubblica dal 25/10/2026: il lavoro di
  `test.yml` (PyInstaller, self-test, zip, Inno Setup) si può duplicare in una matrice con `windows-11-arm`, e lo
  stesso per il Flatpak su `ubuntu-24.04-arm`. Questa è la «macchina ARM64» che manca qui.
- Da controllare sul runner [I]: `setup-python` con Python ARM64 (c'è dalla 3.11 in poi); Inno Setup sul runner ARM
  (l'installer di Inno è x86, gira sotto emulazione: va bene); la firma minisign (ruota pura); Kokoro (onnxruntime ha
  la ruota win_arm64, ma le prestazioni della voce su Snapdragon vanno misurate).

## 3. Tablet: le strade a confronto

### 3.1 Windows su tablet (Surface Pro, anche ARM)

Il programma gira (3.1 e 2.4). Il problema è l'uso con le dita. Prova fatta [V] (`prova_tocco.py`, offscreen,
PySide6 6.12.0 su questo PC, dispositivo di tocco registrato con `QTest.createTouchDevice`):

| gesto | pianta (`ui/plan.py`) | 3D (`ui/view3d.py`) |
|---|---|---|
| un dito, tap su un modulo | selezione `('', '')` -> `('building', 'b1')`: come un clic sinistro (lo stesso che dà `QTest.mouseClick` nello stesso punto) | il navigatore vede `{'left'}` premuto e il clic arriva al picking (`pointPicked`) |
| due dita, pizzico da 20 a 100 px | scala 11,5112 -> 11,5112: **nessuno zoom** | camera ferma: **nessuno zoom** |
| due dita trascinate di 100 px | traslazione (0, 0) -> (0, 0): **nessun pan**; e la selezione passa a `('subfield', 's1')`: il secondo dito ha selezionato | non provato (stesso meccanismo) |
| eventi che arrivano al widget | solo `MouseMove`, `MousePress`, `MouseRelease` «synthesized by Qt», più `QGestureEvent` durante il trascinamento a due dita (nessuno li gestisce) | idem |

Perché: nessun widget ha `WA_AcceptTouchEvents` (verificato nei due `testAttribute`), nessuno chiama `grabGesture`;
Qt allora, con `AA_SynthesizeMouseForUnhandledTouchEvents` (attivo per impostazione, verificato), traduce il primo
dito in tasto sinistro e scarta gli altri. Stili di navigazione a parte, con le dita si può solo selezionare e
disegnare; pan, zoom e orbita restano alla rotella, al tasto centrale e alla tastiera, che un tablet non ha.
I pulsanti della finestra a 1200 x 800 [V]: 77 visibili; 66 tra 23 e 40 px su un lato (altezze 24, 27, 28 px:
`Size.CONTROL` 28, `Size.CHIP` 24 in `ui/design.py`), 11 sotto 23 px (`help-button` 16 x 16, `CloseButton` 20 x 20,
`help-pin` e `help-detach` 21 x 21, `QCheckBox` 22 x 28). Microsoft chiede 40 x 40 epx (raccomandato, 7,5 mm), 23 x 23
come minimo e 5 px tra i bersagli (Learn, «Guidelines for touch targets» e «Touch», UX guide Win32).
Che cosa servirebbe nel codice: sezione 4. Collegamento a R242 (touchpad): la stessa coppia di funzioni, `zoom_at`
del plan e `touch_zoom`/`touch_pan` del backend 3D, serve al pizzico delle dita; sistemarle una volta per il
touchpad (zoom attorno al puntatore, velocità) le rende pronte anche per il tocco.

Surface Pro con Snapdragon X: Windows ARM64, quindi anche 2.4. Surface Pro Intel: l'installer di oggi.

### 3.2 Tablet Linux

Pochi dispositivi (PineTab2, Surface con Linux, portatili 2 in 1 con Plasma Mobile o GNOME). Il Flatpak x86_64
c'è, quello aarch64 è a un passo (2.3). Il tocco su Wayland arriva a Qt come QTouchEvent e finisce nello stesso
tasto sinistro sintetizzato della 3.1; in più Wayland manda `QNativeGestureEvent` di zoom e rotazione per il
pizzico sul touchpad (documentazione QNativeGestureEvent: «Wayland: three or more fingers moving as a group» per il
pan), e `plan.py` e `view3d.py` già li gestiscono (`event()` con `ZoomNativeGesture` e `PanNativeGesture`) [V, letto].
Sul portatile Lucciola (Niri, Wayland, touchpad, nessuno schermo touch) è la prova da fare per R242. Un tablet Linux
vero non c'è tra le macchine di Daniel; vale quanto detto per Windows in 3.1 e 4.

### 3.3 iPad

[V] Blog Qt del 30/07/2026 («Python mobile app development: bringing PySide6 on iOS»): con Qt 6.12 PySide6 gira su
iOS; la cross-compilazione produce librerie statiche `.a` da collegare in un progetto Xcode con i framework statici
di Qt e il `Python.xcframework` di BeeWare; `pyside6-ios-deploy` genera il progetto Xcode; «Packages with C
extensions (numpy, Pillow, etc.) can't be used at all»; ogni build è per un'architettura (dispositivo e simulatore
separati). Le note di sviluppo di Qt for Python (wiki, 22/10/2026: «iOS: Support of third party packages», 15/10:
«Update Python version to 3.15») dicono che i pacchetti puri in Python si aggiungono; nulla sulle estensioni C.
Su download.qt.io ci sono le ruote `ios_arm64` e simulatore per 6.12.0 (cp315).
Qt 6.12 chiede iOS 18 o più nuovo e Xcode 16 (quindi un Mac) [V, doc Qt per iOS].

Per Meridiana è un no: numpy, scipy, shapely, pandas sono il nucleo (geometria, sole, energia). Anche
`matplotlib`, `h5py`, `pyqtgraph` (numpy) cadono. Resta il costo: Apple Developer Program per distribuire
(App Store o TestFlight) [V, pagina compare-memberships: «to distribute apps, you'll need to be an Apple Developer
Program member»]; il prezzo non è sulla pagina letta, [I] 99 USD l'anno, più un Mac.

Alternative realistiche per usare Meridiana da un iPad:
- **Desktop remoto** (Microsoft Remote Desktop / Windows App, o RustDesk, Parsec verso il PC o il portatile): gratis,
  funziona oggi, il tocco diventa mouse e con la Apple Pencil si disegna bene; serve il PC acceso e la rete. È la
  risposta pratica per «guardare un progetto dal cantiere» o mostrarlo a un cliente.
- **Cliente web**: una seconda interfaccia (browser) sopra un servizio Meridiana sul PC o su un server, con il 3D in
  WebGL. È un prodotto nuovo, mesi di lavoro; non riusa `ui/`.
- **Relazione PDF e IFC sull'iPad**: già oggi i prodotti di Meridiana (relazione, IFC con un visualizzatore
  BIM per iPad) si aprono sul tablet. Nessun lavoro.

### 3.4 Android

[V] `pyside6-android-deploy` (doc Qt for Python 6.12): «only works with a Unix (Linux or macOS) host at the moment»;
host con Python ≥ 3.10, JDK 17, NDK r28c; il Python dentro l'app lo costruisce python-for-android (CPython 3.14 oggi);
impacchetta con buildozer in `.apk` o `.aab`; ruote `android_aarch64` e `android_x86_64` da download.qt.io o con
`qtpip download PySide6 --android --arch aarch64`. [V] Qt for Android 6.12: Android 9 (API 28) fino a 16, ABI
arm64-v8a, x86_64, x86, armeabi-v7a. [V] Qt Quick 3D: OpenGL ES 3.0 consigliato (2.0 con funzioni ridotte), nessun
rendering software per il 3D; i tablet Android recenti hanno ES 3.2 e Vulkan.
Estensioni C [V, fonti secondarie]: python-for-android compila i pacchetti con «ricette»; numpy ha la ricetta
ufficiale; per scipy la ricetta è stata aggiornata a 1.15.2 ma segnala fallimenti sul ramo di sviluppo; per shapely
(GEOS), pandas, matplotlib, onnxruntime, ifcopenshell non c'è traccia di ricette mantenute. Senza shapely non c'è
`layout.py`; senza scipy non c'è il punto di massima potenza di pvlib.
[I] Oltre alle librerie: finestra da PC (dock, barra delle fasi, ispettore) su 11 pollici, tastiera a schermo,
`keyring` senza Secret Service, file del progetto nello storage con permessi Android, niente processo separato per
la voce. Settimane, con esito incerto. Costo di distribuzione: Google Play 25 USD una tantum [V]; un `.apk` si
installa anche senza Play.

### 3.5 Confronto con voti

Voti da 1 (male) a 5 (bene). «Fattibilità» = si può fare con questo codice; «sforzo» = 5 è poco lavoro;
«valore» = quanto serve a Daniel (progettista alla scrivania, cantieri e clienti ogni tanto).

| strada | fattibilità | sforzo | valore | totale | note |
|---|---|---|---|---|---|
| A. Linux aarch64 (Flatpak) | 5 | 5 | 3 | 13 | runtime e ruote ci sono; CI su `ubuntu-24.04-arm` o build locale emulata (2.3) |
| B. Windows ARM64 nativo (installer `-arm64`) | 5 | 4 | 4 | 13 | tutto esiste; serve il runner `windows-11-arm` o un PC ARM per costruire e provare; intanto Prism fa girare l'x64 |
| C. Windows/Linux tablet, tocco vero (gesti, bersagli) | 4 | 2 | 3 | 9 | un lotto di lavoro sul codice (sezione 4) dopo R242; da provare su uno schermo touch vero, che qui non c'è |
| D. iPad con desktop remoto | 5 | 5 | 3 | 13 | nessun codice; il PC deve essere acceso |
| E. iPad con PySide6 iOS | 1 | 1 | 4 | 6 | niente numpy, scipy, shapely: impossibile oggi |
| F. iPad con cliente web | 3 | 1 | 4 | 8 | prodotto nuovo, mesi |
| G. Android con pyside6-android-deploy | 2 | 1 | 2 | 5 | scipy e shapely senza ricette affidabili; finestra da PC su tablet |

## 4. Che cosa servirebbe nel codice per il tocco (solo analisi)

Nessuna modifica fatta. Riferimenti ai file di questa tranche.

**4.1 Accettare il tocco e i gesti.**
- `ui/plan.py`, `PlanView.__init__` (riga 286 e seguenti): `self.viewport().setAttribute(Qt.WA_AcceptTouchEvents, True)`
  e `self.viewport().grabGesture(Qt.PinchGesture)` (e `PanGesture` o la gestione diretta dei QTouchEvent). Oggi
  `event()` (righe 2310-2333) tratta solo `NativeGesture` (macOS, Wayland) e le chiavi di Move; i `QGestureEvent`
  che la prova ha visto arrivare durante il trascinamento a due dita passano a `super().event`.
- `ui/quick_image.py` (`QuickImage`, righe 288-316): inoltra al `QQuickWindow` solo `QMouseEvent` e `QWheelEvent`
  ricostruiti (`_mouse`, `wheelEvent`); un `QTouchEvent` non viene inoltrato e non c'è `WA_AcceptTouchEvents`.
  Servono o l'inoltro dei QTouchEvent (ricostruiti con `QTouchEvent(type, device, modifiers, points)` e
  `QCoreApplication.sendEvent(self.quick, ...)`) con un `PinchHandler`/`DragHandler` in `Scene.qml`, oppure, più
  semplice, la gestione dei gesti nel widget: `grabGesture(Qt.PinchGesture)` su `View3D` e in `event()` tradurre
  `QPinchGesture.scaleFactor()` e `centerPoint()` in `backend.touch_zoom(steps, x, y)` e lo spostamento del centro in
  `backend.touch_pan(dx, dy, x, y)` (già scritti per il touchpad, `view3d.py` righe 663-692).
- `Scene.qml` (righe 401-439): la `MouseArea` con `hoverEnabled: true` e i tre pulsanti; con le dita arriva solo il
  sinistro. Un dito che trascina su uno spazio vuoto dovrebbe orbitare (come FreeCAD «Gesture», studio 15 tabella
  2.2: «tocco o sinistro» seleziona, «un dito» trascinato orbita, due dita pan, pizzico zoom): oggi il sinistro
  trascinato, nello stile AutoCAD, non fa nulla nel 3D e in pianta disegna o sposta i vertici.

**4.2 Un profilo di navigazione «Tocco» in `navigation.py`.** La macchina di stati (`Navigator`, righe 178-306)
ragiona per pulsanti e modificatori; il modulo dice da solo (righe 14-16) che «a touch screen is left out: the
mouse part only». Serve una tabella in più, non a pulsanti ma a numero di dita: 1 dito = seleziona (tap) o orbita
(trascina, nel 3D) o pan (trascina, in pianta), 2 dita = pan, pizzico = zoom attorno al centro delle dita (il
`zoom_at(factor, view_pos)` di `plan.py` riga 1982 e il `touch_zoom` del backend lo fanno già attorno a un punto),
tieni premuto = menu (il `right_click: "menu"` degli stili). Il profilo si sceglie da solo quando l'evento viene da
un `QPointingDevice` di tipo `TouchScreen`, senza chiederlo nelle preferenze.

**4.3 Bersagli grandi.** Le soglie di presa in pianta sono pensate per il puntatore: `PICK_PX = 6.0` (`plan.py` riga
103, R147: «modulo raggiungibile entro 6 px»), `_vertex_near` 8 px (riga 1349), `_side_near` 14 px (riga 1359), le
impugnature di Move e la fine della fila 8 px (righe 1821 e 2110), `navigation.CLICK_PX = 4.0` (un dito trema più di
4 px: ogni tap diventerebbe un trascinamento). Con un dito servono 20-24 px logici (Microsoft: contact geometry,
almeno 23 px). Nel 3D il `PIVOT_PX = 16` del mirino e il `hoverTimer` di 60 ms non c'entrano con le dita, ma i
`view.pick(x, y)` a raggio singolo (`Scene.qml` righe 406, 449) andrebbero fatti con un raggio di tolleranza. Per i
widget: `Size.CONTROL = 28`, `Size.CHIP = 24`, `Button.SMALL = 20`, `Button.HELP = 16` (`ui/design.py` righe 145-165)
sono sotto i 40 px; una «densità tocco» del sistema grafico (le stesse costanti moltiplicate quando il dispositivo
primario è un touch screen, `QInputDevice.devices()`) andrebbe portata anche nel modello `qt-app-template`, come chiede
la regola «armonizziamo».

**4.4 Niente hover.** Il programma usa il passaggio del puntatore in 23 file di `ui/` e ha 162 tooltip. Dove il
passaggio è l'unico modo: l'evidenza di ciò che il clic selezionerà (`plan.py` `_hover`, riga 1383, studio 12 V3),
il mirino del pivot con il tasto tenuto (`view3d.py` `pivotHover`, riga 619), il cubo di navigazione
(`viewcube.py` `enterEvent`/`mouseMoveEvent`, righe 191-206: le frecce e Home si colorano solo al passaggio e il
tooltip dice cosa sono), i grafici pyqtgraph (`charts_pg.py` `leaveEvent`, il cursore sui valori), le schede
(`cards.py` riga 200, `underMouse`). Microsoft: «Provide touch equivalent for hover. Don't rely on hover as the only
way to perform an action»; Qt: `WA_AcceptTouchEvents` non cambia questo, serve un gesto in più (tieni premuto per il
tooltip, tap per evidenziare e secondo tap per selezionare).

**4.5 Tastiera.** Spazio tenuto (pan, R166 e R190), Shift + sinistro (orbita), Esc, F (adatta), i numeri di Move e
delle quote: su un tablet senza tastiera servono pulsanti nella `viewbar` (già c'è `Fit`) e la tastiera a schermo
per i campi (Qt la chiede da sola con `QInputMethod` su Windows e Wayland).

**4.6 Dove si prova.** Senza uno schermo touch, la prova offscreen di `prova_tocco.py` (QTouchEvent registrati con
`QTest.createTouchDevice`) è il banco di prova ripetibile: ogni punto di 4.1-4.3 può avere il suo test in
`tests/widget/` nello stesso modo. La prova con le dita vere resta da fare su un Surface o sul portatile con
schermo touch, quando ce ne sarà uno.

## 5. Raccomandazione

1. **Subito, a costo basso**: la matrice ARM nel CI. `test.yml` con `windows-11-arm` (PyInstaller + self-test + Inno
   Setup con `ArchitecturesAllowed=arm64`, file `Meridiana-<versione>-arm64-setup.exe`) e `flatpak-build.yml` con
   `ubuntu-24.04-arm` (bundle `meridiana-aarch64.flatpak`). Prima del CI, una costruzione Flatpak aarch64 locale
   emulata (2.3, passi 1-4) dice se la ricetta regge; `python3-kokoro.json` vuole le tre ruote aarch64.
2. **Dopo R242**: il lotto «tocco» della sezione 4, cominciando da 4.1 e 4.2 (gesti) e 4.3 (soglie), con i test
   offscreen; la densità dei widget (4.3) va fatta nel modello grafico e poi in Meridiana.
3. **iPad**: desktop remoto, oggi; nessun lavoro su PySide6 iOS finché Qt non supporta le estensioni C (seguire le
   note settimanali di Qt for Python). Android: no.

Decide Daniel.

## 6. Che cosa non è stato verificato

- Nessuna macchina Windows ARM64, nessuno schermo touch, nessun tablet: le prove di 2.2 e 2.3 sono emulate (qemu-user
  è esatto per le istruzioni, non per i tempi: i tempi misurati sotto qemu non dicono nulla sulle prestazioni vere).
- La costruzione del Flatpak aarch64 e del pacchetto Windows ARM64 non sono state eseguite (2.3 e 2.4 dicono i passi).
- PyInstaller su Windows ARM64 è dedotto dalla ruota e dal changelog, non provato.
- Le ricette python-for-android di scipy e shapely: notizie di seconda mano (ricerca web), non provate.
- Le ruote Android e iOS di PySide6 sono state viste nell'indice di download.qt.io, non scaricate.
- Il comportamento del tocco è provato con QTouchEvent sintetici sulla piattaforma offscreen di Windows: su un
  Surface vero Windows aggiunge i suoi gesti di sistema (per esempio il tieni premuto che diventa tasto destro), che
  qui non si vedono.

## 7. Script e come ripetere

In questa cartella:
- `pypi_wheels.py`: `python pypi_wheels.py PySide6_Essentials==6.12.0 numpy scipy ...` stampa la tabella della
  sezione 1 (API JSON di PyPI; rete).
- `prova_tocco.py`: dalla radice del repository, con `PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen PYTHONPATH=tests;src`,
  `python docs/studio/21-arm-tablet/prova_tocco.py`; tre «test» che non asseriscono ma raccontano (pianta, 3D,
  pulsanti della finestra). Con la PATH della cartella PySide6 della venv davanti, come per la suite.
- `wsl/wsl_install.sh`: come root nella WSL (`wsl -d openSUSE-Tumbleweed -u root -- bash <percorso>`), installa
  qemu-linux-user e podman e legge i ref aarch64 di Flathub.
- `wsl/Containerfile` e `wsl/run_arm64.sh`: l'immagine aarch64 e le tre prove di 2.2 (`podman build --arch arm64`,
  `podman run --arch arm64 -v <repo>:/src:ro ...`).
- `wsl/flatpak_arm64.sh`: installa il runtime KDE 6.11 e il BaseApp PySide aarch64 e vi esegue Python sotto qemu (2.3).

Esiti grezzi (log) in `wsl/log/`.
