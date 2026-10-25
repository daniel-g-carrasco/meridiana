# Compito 20: IFC4 in uscita e in entrata (R91)

Daniel, 25/10/2026: «Vai con gli IFC. Ma l'import è possibile farlo? So che è un tema delicato perché se il modello
in ingresso è complesso può anche bloccare o rendere molto lenti gli import. Noi non abbiamo bisogno di dettagli per
fare gli FV, quindi troviamo una buona ed efficiente strada per farlo».

Ramo `ifc` (dalla `grafica` a c99a6f5), copia di lavoro `%USERPROFILE%\dev\meridiana-wt-ifc`. Studi: 15 (sezione 5.2,
l'esportazione e il prototipo del lettore) e **20** (`docs/studio/20-ifc-importazione.md`, le misure e la scelta).

## Fatto

### Esportazione IFC4 (parte 1)

- `src/meridiana/ifc_export.py`, dal prototipo del 22/10 (`meridiana-prove\freecad-2026-10-22\meridiana_ifc.py`):
  - progetto in metri, gradi, watt; contesto Model/Body con il TrueNorth su +Y (il sistema di Meridiana è quello del
    nord vero);
  - IfcSite con RefLatitude e RefLongitude ai milionesimi di secondo (conversione nostra, `ifc_export.dms`: quella di
    ifcopenshell può arrotondare a 1.000.000 di milionesimi) e una IfcMapConversion su WGS 84 / UTM della zona del sito,
    con la convergenza del meridiano (`geo.to_utm`, serie di Krüger come in Karney 2011; disattivabile da codice);
  - un IfcBuilding con un piano per edificio (e un piano «Terreno» per ciò che sta a terra); pareti fino al tetto,
    IfcRoof con un IfcSlab ROOF per falda e i Pset `Pset_SlabCommon` e `Meridiana_Falda`; parapetti IfcWall PARAPET;
    camini IfcChimney, lucernari IfcWindow SKYLIGHT, alberi IfcGeographicElement, il resto IfcBuildingElementProxy;
  - un IfcSolarDeviceType SOLARPANEL per modulo e orientamento, con la forma una volta sola (IfcRepresentationMap) e i
    Pset del costruttore e `Meridiana_DatiModulo`; un IfcSolarDevice per modulo posato (i moduli girati di 90° compresi)
    con `Meridiana_Modulo`: sottocampo, chiave, fila, posto, livello, inclinazione, azimut CEI e dal nord, potenza,
    **stringa** («1.2.3», dalle stringhe proposte o da quelle a mano); un IfcGroup per sottocampo e uno per stringa;
  - i moduli scritti come entità dirette: 2.900 moduli in circa 3 s (lo script intero 3,5 s contro 11,3 s del
    prototipo), il file valido per `ifcopenshell.validate` [V];
  - il file scritto accanto e rinominato solo quando è intero: Annulla a metà lascia il file di prima.
- Finestra: File > «Esporta il modello in IFC4…», la pagina File (Esporta, gruppo Modelli), il pulsante IFC4 della
  fase Relazione (prima era «previsto»), il consegnabile «Modello (IFC4)» nell'ispettore della Relazione (da fare,
  fatto, da rifare se il progetto cambia). Gira in un lavoro (`ExportIfcJob`) con la barra e Annulla: le pose mancanti
  si fanno lì, le stringhe si propongono lì (`plant.build` senza verifiche).
- ifcopenshell 0.9.0.post1 (LGPL-3.0-or-later) installato nel venv comune, in `requirements.txt`, in `pyproject.toml`
  come extra `ifc`, in `tools/cloud-setup.sh` e in `ATTRIBUTIONS.md` (con lark e isodate). Importato solo quando serve:
  senza, la finestra dice che cosa installare.

### Importazione (parte 2)

- Lo studio 20 con le misure su 20 campioni pubblici e sintetici: la strada scelta è «c+b in un processo a parte».
- `src/meridiana/ifc_read.py`, `ifc_import.py`, `ifc_worker.py`, `procmem.py`, `ui/ifc_import.py` (la mappa è nello
  studio 20, sezione 6, e in `docs/progetto.md`, sezione 2).
- Finestra: File > «Importa un modello IFC…» e la pagina File (Importa, Progetto). La lettura in un processo a parte
  con la barra (che si muove senza percentuale mentre il file si apre) e Annulla; fermata oltre 180 s o oltre metà
  della memoria del PC (8 GiB al massimo); se IfcOpenShell cade o si blocca, un secondo tentativo con le sole forme
  semplici. Poi il riquadro: dove vanno gli edifici (dove dice il file intorno al sito, il sito spostato sul modello,
  l'origine del sito), il nord quando mappa e TrueNorth non tornano, l'anteprima dall'alto, che cosa è preso,
  approssimato, lasciato fuori. Gli edifici entrano con una sola modifica (Ctrl+Z la toglie), selezionati e
  inquadrati.
- Robustezza trovata con le misure e corretta: la memoria del processo si conta con i suoi figli (su Windows il
  `python.exe` di un ambiente virtuale è un lanciatore di 4 MB e l'interprete è suo figlio: guardare solo il
  lanciatore non avrebbe fermato niente); un file tagliato a metà si legge fin dove arriva (posizionamenti mancanti
  all'origine, forme mancanti contate); un .ifczip si estrae e si apre in modo pigro (IfcOpenShell lo aprirebbe per
  intero); qualunque altro errore del lettore torna come motivo, non come crollo.
- Formato del progetto e configurazione invariati: niente migrazioni.
- Manuale: `docs/manuale/1-modello.md`, «Dal modello dell'architetto (IFC)».

### Test

- `tests/nucleo/test_ifc_export.py`: UTM (valori noti, andata e ritorno, convergenza, sistemi accettati), esportazione (valida, ogni modulo, sito ai milionesimi, mappa UTM, Pset e stringhe, posizione di un modulo,
  Annulla che non scrive, senza mappa).
- `tests/nucleo/test_ifc_import.py`: la memoria di un processo e dei suoi figli; andata e ritorno (contorni, quote, tipi di tetto, testate, falde, ostacoli, una
  sola modifica annullabile, sito spostato, origine), un modello ruotato col suo TrueNorth, i campioni di buildingSMART
  (`tests/data/ifc`, CC BY 4.0), i file che non sono IFC, il .ifczip, la strada semplice, i millimetri di Revit, il
  processo a parte.
- `tests/widget/test_ifc_import.py`: la lettura che finisce, quella che non finisce (tempo), quella che mangia memoria,
  quella che cade, il secondo tentativo, Annulla, il file non IFC; la barra che si muove; il riquadro (scelte,
  anteprima, niente da aggiungere).
- `tests/finestra/test_ifc_window.py`: un viaggio nella finestra (menu e pagina File, esportazione nel lavoro e il
  consegnabile, importazione del file appena scritto e del campione, Ctrl+Z, Annulla, un file sbagliato detto).

## Da fare (proposte, decide Daniel)

1. **Cortili e fori** nelle falde importate: vengono con il passo 4 del compito 16a.
2. **Gauss-Boaga ed ED50** nelle mappe degli IFC italiani: il cambio di datum (parametri IGM). Solo se un architetto
   li usa.
3. **Opzioni dell'esportazione** in un riquadro: la mappa sì o no (oggi sempre sì), il sistema RDN2008 / UTM al posto di
   WGS 84 / UTM (differenza sotto il metro), i moduli sì o no.
4. **Tempo massimo della lettura** nelle Preferenze (oggi 180 s fissi).
5. **Pacchetto Windows**: il processo a parte si lancia con `python -m meridiana.ifc_worker`; un eseguibile PyInstaller
   dovrà riconoscere un argomento suo.
6. Nomi dei Pset: in italiano come nel prototipo letto da FreeCAD (`Meridiana_Modulo`, `Inclinazione`...). Se servono
   in inglese per i colleghi inglesi, si cambia ora, prima che qualcuno li usi.

## Da provare sul PC di Daniel

- File > Importa un modello IFC… con un IFC vero di un architetto (non quelli delle commesse sul server: un file che
  Daniel sceglie): il tempo, la memoria (il riquadro dice i secondi), le coperture riconosciute, la quota di gronda.
- La vista 3D degli edifici importati: offscreen la scena 3D non si disegna, quindi nelle immagini manca.
- L'IFC esportato aperto in FreeCAD, BlenderBIM, Revit, nel visore di chi lo riceve: la posizione (mappa UTM), i
  moduli con le stringhe.
- La barra e Annulla con un file grande (per esempio 200 MB): la finestra deve restare viva.

Le immagini per Daniel sono in
`%TEMP%\meridiana\per-daniel\ifc`.
