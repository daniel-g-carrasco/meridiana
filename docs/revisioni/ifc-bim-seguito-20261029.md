# R230-R231: identita BIM, IFC complessi e superfici di posa

Revisione del 29/10/2026. [V] indica una verifica eseguita; [I] un limite o una scelta di implementazione.

## Esito dell'audit e modifiche

- [V] L'export assegnava GUID nuovi a ogni scrittura. Ora il progetto salva un namespace BIM (`bim_id`, UUID),
  indipendente dal nome e dalla posizione, e deriva GUID deterministici da identita degli oggetti. Progetto, sito,
  edifici, falde, moduli, tipi, gruppi, impianto, Pset e relazioni conservano identita tra esportazioni. I test
  confrontano tutti gli `IfcRoot`, cercano GUID duplicati e ripetono export dopo rinomina, movimento e salvataggio.
- [V] I moduli conservano geometria mappata e dimensioni del catalogo; ricevono identita progetto, variante, catalogo,
  edificio/falda, sottocampo e modulo. Rimangono potenza, inclinazione, azimut, fila, posto e stringa, oltre ai dati
  elettrici disponibili sul tipo. Un `IfcSystem` raggruppa i moduli dell'impianto; restano i gruppi sottocampo/stringa.
  Il contenimento spaziale viene scritto una volta per contenitore, senza relazioni duplicate.
- [V] Le trasformazioni del lettore esistente non presentano il difetto inizialmente sospettato. Dodici confronti
  differenziali con il kernel IfcOpenShell coprono tessellazioni/BRep, metri/millimetri/piedi, geometria mappata con
  origine non nulla e scala 1,2, e posizionamenti annidati ruotati. Gli estremi coincidono entro `1e-6 m`.
- [V] Il tetto interno ricava la direzione di caduta da un bordo. Un piano IFC arbitrario puo quindi essere
  approssimato anche se il lettore ne ha trovato correttamente la normale. L'import ora propone un'area di posa con
  piano indipendente quando quota e orientamento del tetto ricostruito non riproducono quel piano. Il riepilogo
  precedente alla conferma specifica file, elementi STEP IFC, normale nel riferimento di progetto, inclinazione,
  azimut e quota locale. Il progetto non cambia fino alla conferma. L'area e attiva, **senza moduli**.
- [V] `SupportPlane(enabled, tilt, azimuth, z0, x0, y0)` e opzionale nel sottocampo. Il formato passa a 19, con
  migrazione delle versioni precedenti, fixture congelata v19, validazione di valori finiti e intervalli. Quota e
  coordinate sono in metri locali. Disattivare il supporto conserva i suoi valori e ripristina il riferimento
  edificio/falda. I nuovi progetti ricevono UUID4; revisioni e copie del file mantengono il namespace salvato.
- [V] L'inspector permette di attivare il piano e modificarne quota al centro dell'area, inclinazione e azimut tramite
  il normale `session.edit`. Undo/redo, layout, spostamento, rotazione, copia del sottocampo, contorno e quota delle
  indicazioni 3D usano la stessa superficie. Il piano e incluso nella scena 3D anche senza moduli; i buffer geometrici
  sono verificati numericamente. Il riferimento a edificio e
  falda rimane conservato; un supporto indipendente puo essere spostato fuori dal contorno del suo edificio.
- [V] Un supporto attivo viene esportato anche vuoto come `IfcAnnotation`, con geometria `IfcCurveBoundedPlane`,
  GUID stabile, Pset e contenimento spaziale. `ObjectType=MERIDIANA_PLACEMENT_SURFACE` distingue questa superficie
  virtuale dagli elementi costruiti. Il lettore riconosce soltanto questo tag esplicito, senza trasformare le
  annotazioni generiche in tetti. Il roundtrip della superficie vuota preserva il piano, conservando un riferimento
  a edificio/falda quando disponibile. Sono importabili anche file con sole superfici a terra: anteprima,
  conferma e annullamento unico sono verificati nella finestra reale in modalita offscreen.

## Prove

Interprete Windows: `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`.
Per i test Qt: `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH` alla cartella `tests` e directory PySide6 nel `PATH`.
Non e stata eseguita una suite completa da questo agente.

| Gruppo mirato | Esito |
| --- | --- |
| `nucleo.test_ifc_bim`, `test_ifc_export`, `test_ifc_complex`, `test_ifc_import` | [V] 36 test PASS |
| `nucleo.test_bim_support`, `nucleo.test_move` | [V] 36 test PASS |
| `nucleo.test_bim_support`, `formati.test_project_files`, `nucleo.test_session`, `finestra.test_bim_support`, `widget.test_properties.NarrowPanel` | [V] 60 test PASS nella verifica iniziale del modello/interfaccia |
| `nucleo.test_ifc_bim`, `nucleo.test_ifc_complex`, `nucleo.test_bim_support`, `finestra.test_bim_support`, `widget.test_properties.NarrowPanel` | [V] 18 test PASS dopo annotazione e movimento falda libera |
| `finestra.test_ifc_surfaces`, `widget.test_ifc_import` | [V] 12 test PASS dopo aggancio import di sole superfici |
| Ruff sui sorgenti/test modificati | [V] PASS |

Le fixture parametriche verificano anche quote del piano in punti interni, indipendenti dai bordi, unitamente alla
serializzazione. La rotazione del TrueNorth di 37 gradi ruota contorno e normale senza perdere la quota. Il kernel
geometrico legge l'annotazione esportata; la validazione IFC4 non trova errori di schema. La validazione non include
tutte le regole EXPRESS. Il test preesistente di memoria del processo emette un `ResourceWarning` sul processo figlio
in chiusura; la suite IFC termina con esito positivo.

### Campioni Revit presenti nell'archivio di prove

[V] Riletti con il percorso di import ordinario, senza copiare i grandi file nel repository. Fonte/licenza erano gia
registrate in `docs/studio/20-prove/campioni.json`.

| File | Dimensione | Risultato |
| --- | --- | --- |
| `location/example-project-location.ifc`, Revit 2020 | 2.959.580 B, IFC4, mm | 2 edifici/2 piani, zero errori geometrici |
| `duplex/Duplex_A_20110907.ifc`, Revit 2011 | 2.380.763 B, IFC2X3, m | 1 edificio/1 piano, zero errori geometrici |
| `clinic-arch/Clinic_Architectural.ifc`, Revit 2011 | 13.003.205 B, IFC2X3, m | 1 edificio/1 piano dai muri, zero errori geometrici |

Tutti i progetti importati sono stati serializzati e riaperti con validazione v19. Queste coperture sono piatte e non
richiedono il supporto ausiliario. La palestra conserva le segnalazioni gia esistenti: coordinate di mappa incoerenti
con le unita dichiarate e CRS EPSG:28992 non convertito. Si usa il sito IFC e il riepilogo lo rende esplicito.
Il caso Clinic rimane un'approssimazione ricavata dai muri, senza promessa di ricostruire un tetto non presente.

Log e immagini locali, nuovi e senza sovrascrivere prove precedenti:

```text
C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\build\ifc-bim-seguito-20261029-R01\real-ifc-samples.json
C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\build\ifc-bim-seguito-20261029-R03\support-plane-card.png
C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\build\ifc-bim-seguito-20261029-R03\support-window.png
```

L'immagine R03 e stata controllata: checkbox a capo e campi leggibili nel pannello stretto. R01 e R02 conservano
tentativi precedenti; R01 precedeva il completamento del layout Qt e non rappresenta il controllo visivo finale.

## Limiti espliciti

- [I] Un IFC con geometria, tipi, Pset e appartenenze BIM non e una famiglia Revit nativa parametrica (`.rfa`). Non
  sono state create famiglie Revit, vincoli, formule o connettori MEP nativi; non e stata eseguita una prova dentro
  Revit. La leggibilita dei singoli parametri nel software destinatario dipende dal suo importatore IFC.
- [I] I GUID restano stabili per le identita persistenti: stesso progetto, variante, sottocampo e chiave modulo. Una
  rigenerazione che cambia le chiavi topologiche delle file puo creare nuove identita. Importare nuovamente lo stesso
  IFC aggiunge oggetti: questa funzione non implementa una sincronizzazione/merge tra modelli o deduplica degli import.
- [I] La migrazione dei vecchi file usa `series_id`, oppure una combinazione deterministica dei metadati disponibili.
  Vecchi file indipendenti con metadati identici possono condividere quel namespace: prima del formato 19 mancava
  un'identita BIM persistente sufficiente a distinguerli. Dopo il primo salvataggio il namespace non dipende da rinomine.
- [I] Le quote importate sono normalizzate rispetto al terreno riconosciuto dell'edificio, come nel modello
  preesistente. Non viene introdotto un datum altimetrico assoluto. Il piano di posa conserva inclinazione e quota
  locali; il tetto usato come riferimento puo rimanere approssimato e il riepilogo continua a dichiararlo.
- [I] Le prove Qt sono offscreen: i controlli e i buffer della scena sono verificati, ma non e stato acquisito un
  frame GPU della superficie nel viewport 3D. La verifica grafica interattiva sul desktop resta separata.
- [I] Le aree con fori non generano automaticamente una superficie esatta senza fori. Restano le segnalazioni sui
  fori esclusi. La lettura delle annotazioni dedicate e limitata a piani delimitati da segmenti, senza contorni interni;
  superfici curve, mesh non planari e famiglie Revit complesse richiedono una diversa rappresentazione.

## Fonti e perimetro dei file

Consultati prima gli studi locali 15 e 20, le fixture, i campioni gia archiviati e il codice installato IfcOpenShell.
La ricerca nei nomi dell'archivio `C:\Users\Grasso\Elettrico\reference` non ha trovato documenti IFC/BIM/ISO 16739.
Per la semantica dell'annotazione e stata consultata la documentazione primaria
[buildingSMART IFC4, IfcAnnotation](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/FINAL/HTML/schema/ifcproductextension/lexical/ifcannotation.htm),
che distingue annotazioni e superfici simboliche dai prodotti costruiti e ne prevede il contenimento spaziale.
Non sono state assunte soglie di norme CEI/UNI da memoria.

Sorgenti: `ifc_export.py`, `ifc_import.py`, `ifc_read.py`, `model.py`, `move.py`, `mesh.py`, `viewaids.py`;
sezioni autorizzate `ui/properties.py` (supporto), `ui/window.py` (`_show_3d`, `_ifc_read`) e `ui/ifc_import.py`.
Test nuovi: `nucleo/test_bim_support.py`, `test_ifc_bim.py`, `test_ifc_complex.py`,
`finestra/test_bim_support.py`, `test_ifc_surfaces.py`; fixture v19 e aspettativa formato del test di identita.
Traduzioni affidate all'agente principale; nessuna modifica autonoma a PO, cataloghi, energia o commit.
