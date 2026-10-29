# Pacchetto Flatpak: 29 ottobre 2026

## Stato

La R01 è un'anteprima conservata prima della correzione del calcolo dell'energia dei moduli non collegati.
Il suo self-test passa, ma questo non verifica quel difetto di dominio. La R02 deve includere la correzione
prima della consegna finale.

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
- [V] Per la R02 è stata aggiunta la pulizia dei dizionari QtWebEngine ereditati in
  `/app/share/locale/*/qtwebengine_dictionaries`. La vecchia pulizia cercava soltanto il percorso
  `/app/qtwebengine_dictionaries`: i dizionari inutilizzati occupavano circa 297 MB nella R01.

Fonti delle nuove dipendenze: [pypdf su PyPI](https://pypi.org/pypi/pypdf/6.21.4/json),
[IfcOpenShell su PyPI](https://pypi.org/pypi/ifcopenshell/0.9.0.post1/json).

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

## Prove del pacchetto

- [V] `desktop-file-validate`, `appstreamcli validate --no-net` e compilazione con GNU `msgfmt --check`
  completati nel build. Il PO iniziale conteneva sei duplicati obsoleti; la sessione principale li ha rimossi
  prima del build riuscito.
- [V] Self-test del programma impacchettato, tramite `flatpak-builder --run`: **0 errori in 21,35 s**.
  Import obbligatori di pypdf e `ifcopenshell.geom`, finestra offscreen, posa di 128 moduli,
  calcolo annuale, rapporto PDF di 1.397.097 byte e acquisizione della finestra.
- [V] Prova aggiuntiva nel sandbox: salvataggio e riapertura `.mer`, contenitore ZIP con `mimetype`
  come prima voce non compressa, MIME `application/x-meridiana-project+zip` e schema logico 18;
  scrittura e lettura IFC4 con IfcOpenShell; scrittura e lettura PDF con pypdf;
  traduzione italiana e dichiarazioni MIME del desktop.
- [V] Il catalogo italiano è presente nell'export principale. Gli hash del manuale distribuito
  `README.md` e `6-relazione.md` corrispondono al workspace; il confronto dei 328 file dello snapshot
  non mostrava differenze al termine del build R01.

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
