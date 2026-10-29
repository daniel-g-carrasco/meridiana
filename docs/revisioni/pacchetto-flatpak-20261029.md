# Pacchetto Flatpak: 29 ottobre 2026

## Stato

La R03 è l'anteprima verificata per la consegna locale. Include le correzioni al calcolo dei moduli non collegati
e alla lettura dei numeri non finiti, più la prova IFC4 reale nel diagnostico. R01 e R02 sono conservate
nelle rispettive directory, senza sostituzioni.

## Ricetta e ambiente

- [V] WSL `openSUSE-Tumbleweed`: Flatpak 1.18.4, flatpak-builder 1.4.12, runtime e SDK KDE 6.11,
  `io.qt.PySide.BaseApp//6.11`. Il Python del sandbox è 3.13.15; PySide è 6.11.2 e numpy 2.3.5.
- [V] Aggiunti `pypdf>=6.0` e `ifcopenshell>=0.9.0.post1` ai requisiti Flatpak. La ricetta JSON fissa
  pypdf 6.21.4, IfcOpenShell 0.9.0.post1, lark 1.3.1 e isodate 0.7.2 con URL e SHA-256 di PyPI.
  Le altre dipendenze di IfcOpenShell sono già fornite dai moduli precedenti o dal BaseApp; `pip3 check`
  non trova requisiti mancanti.
- [V] Il generatore ufficiale `flatpak-builder-tools` selezionava la wheel IfcOpenShell `py310-none`.
  Sono state selezionate le wheel `py313-none-manylinux_2_31` per x86_64 e aarch64 dal
  [catalogo ufficiale PyPI](https://pypi.org/pypi/ifcopenshell/0.9.0.post1/json), con i rispettivi hash.
  La prova nativa x86_64 importa anche `ifcopenshell.geom`. Le ricette aarch64 sono presenti, ma non sono state costruite.
- [V] `default-branch: stable` allinea l'export al comando che crea il bundle.
  `separate-locales: false` include il catalogo italiano nel singolo file installabile. Il primo export
  senza questa impostazione lo separava nell'estensione Locale, che un bundle locale non può recuperare
  da un repository dell'app ancora non pubblicato.
- [V] Il manifest esclude sorgenti Git, ambienti virtuali, directory di build, repository e log.
  Lo snapshot WSL contiene 328 file; le risorse necessarie sono copiate prima della compilazione.
- [V] Dalla R02 è stata aggiunta e verificata la pulizia dei dizionari QtWebEngine ereditati in
  `/app/share/locale/*/qtwebengine_dictionaries`. La vecchia pulizia cercava soltanto il percorso
  `/app/qtwebengine_dictionaries`: i dizionari inutilizzati occupavano circa 297 MB nella R01.

Fonti delle nuove dipendenze: [pypdf su PyPI](https://pypi.org/pypi/pypdf/6.21.4/json),
[IfcOpenShell su PyPI](https://pypi.org/pypi/ifcopenshell/0.9.0.post1/json).

## R03 verificata

```text
C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\dist\packages-20261029-R03\meridiana-0.1.0-preview20261029-R03-linux-x86_64.flatpak
```

- [V] Dimensione: 185.271.488 byte.
- [V] SHA-256: `fe8719717a27d23e8f31e088a250095f04dfc850fb5c4a9ffe2302f7dc9d761d`.
- [V] Copia Windows verificata rileggendo il file e confrontando lo SHA-256.
- [V] Importazione in un nuovo repository OSTree temporaneo, senza installazione dell'app;
  `ostree fsck` verifica 21.724 oggetti senza errori. Il commit importato è identico all'export:
  `14a54f5449a9a1d7f1a40fe62a1547820e1257d70528fc1737381be141f3dc60`.
- [V] Il catalogo italiano è leggibile anche dal repository ottenuto importando il bundle.
  Checksum, self-test, log completo del runtime, prove aggiuntive e rapporto dell'importazione sono accanto al file.

## R01 conservata

Directory Windows:

```text
C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\dist\packages-20261029-R01
```

Bundle: `meridiana-0.1.0-preview20261029-linux-x86_64.flatpak`.

- [V] Dimensione: 224.785.880 byte.
- [V] SHA-256: `fa1d443753b77e8b65de7b96265dbeda3fc83dee1ee64b02420bb302452c79af`.
- [V] Copia Windows verificata rileggendo il file e confrontando lo SHA-256.
- [V] Importazione del bundle in un repository OSTree temporaneo e `ostree fsck`: 21.941 oggetti verificati,
  nessun errore. Il commit importato è identico all'export:
  `cd918ae5455afcea2b3699ff07c2ca67fd1d49392cb132df6dacd74d72af3b76`.
- [V] Accanto al bundle: checksum, rapporto del self-test, prova del formato e delle dipendenze,
  rapporto dell'importazione. Tutti i file sono nuovi; nessun artefatto precedente è stato sostituito.

## R02 conservata

Directory Windows:

```text
C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\dist\packages-20261029-R02
```

Bundle: `meridiana-0.1.0-preview20261029-R02-linux-x86_64.flatpak`.

- [V] Dimensione: 185.269.176 byte.
- [V] SHA-256: `0f61064320c00cb5ceb7d7aa21e00427b0c49cddbff8ce8f3b381726c20ff4d5`.
- [V] Copia Windows verificata rileggendo il file. Importazione OSTree e controllo di 21.724 oggetti riusciti;
  commit identico all'export: `619a1a21a95680bf951e417ddd06b4e1d19e13a562cacd8b76de8efccf2da871`.
- [V] Il self-test della R02 termina con 0 errori in 23,29 s; gli artefatti e i rapporti restano accanto alla R01
  nelle rispettive directory, senza sostituzioni. La R03 estende la sola diagnostica IFC.

## Prove del pacchetto

- [V] `desktop-file-validate`, `appstreamcli validate --no-net` e compilazione con GNU `msgfmt --check`
  completati nel build. Il PO iniziale conteneva sei duplicati obsoleti; la sessione principale li ha rimossi
  prima del build riuscito.
- [V] Self-test R03 del programma impacchettato, tramite `flatpak-builder --run`: **0 errori in 21,57 s**.
  Import obbligatori di pypdf e `ifcopenshell.geom`, finestra offscreen, posa di 128 moduli,
  calcolo annuale positivo, rapporto PDF di 1.604.488 byte e acquisizione della finestra.
- [V] Nuova prova nel self-test R03: esportazione IFC4 della fixture con il codice dell'app e riapertura
  del file di 192.367 byte; contati tutti i 128 oggetti `IfcSolarDevice`.
- [V] Nella fixture R02, invariata nella R03, sono presenti 128 moduli posati e 38 collegati in due stringhe.
  Il self-test R03 calcola 23.683 kWh/anno. I 57,6 kWp indicati nel log sono la potenza di tutti i moduli posati.
- [V] Prova aggiuntiva nel sandbox: salvataggio e riapertura `.mer`, contenitore ZIP con `mimetype`
  come prima voce non compressa, MIME `application/x-meridiana-project+zip` e schema logico 18;
  scrittura e lettura IFC4 con IfcOpenShell; scrittura e lettura PDF con pypdf;
  traduzione italiana e dichiarazioni MIME del desktop.
- [V] Prova aggiuntiva R03 tramite l'API pubblica `project_archive.read_document`: rifiutati sia `1e999` sia `NaN`.
- [V] I sorgenti applicativi, le risorse e tutti i file del manuale distribuito R03 corrispondono al workspace.
  L'unica differenza rilevata dopo il congelamento è una successiva modifica alla ricetta Windows,
  che non viene usata nel Flatpak. Ogni revisione conserva il proprio snapshot e i rapporti.

Le prove usano cartelle temporanee isolate e Qt offscreen. L'app non è stata installata nel profilo utente.
La scena 3D è `Ready`, ma la WSL offscreen non produce un frame GPU; il self-test lo registra come `INFO`.
Nell'ambiente di prova mancano il motore delle voci di sistema e i portali desktop; i relativi messaggi
sono conservati nel log. L'apertura con doppio clic da un desktop Linux installato resta da provare.

## Workflow

[V] Il nuovo `.github/workflows/flatpak-build.yml` costruisce, prova e carica come artifact il bundle,
lo SHA-256 e il rapporto del self-test. Si avvia manualmente o quando cambiano ricette, requisiti o workflow.
Usa le azioni già fissate a commit nel CI del repository, permessi `contents: read` e nessun segreto.
La sintassi YAML e `nucleo.test_release.WorkflowTest` sono stati verificati; il workflow remoto non è stato avviato.
Non crea release, non pubblica un repository Flatpak e non installa l'app.

## Ripresa delle prove locali

[V] Build, snapshot, repository OSTree e log rimangono nella directory nuova:

```text
\\wsl.localhost\openSUSE-Tumbleweed\home\daniel\meridiana-flatpak-20261029-172631
```

Le directory `source-r03`, `build-dir-r03`, `repo-r03` e `bundle-check-repo-r03` distinguono rispettivamente
lo snapshot, il programma costruito, l'export e la verifica del bundle. Non sono stati modificati build
o repository preesistenti. Da PowerShell, le chiamate Bash usano `wsl --exec bash -lc`: senza `--exec`,
la shell intermedia espandeva variabili come `$PWD` e `$?`, alterando directory temporanea ed esito del comando.
