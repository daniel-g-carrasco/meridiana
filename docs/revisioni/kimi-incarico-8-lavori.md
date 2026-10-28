ESITO: verde

# Incarico 8: il Nuovo progetto parte dal posto

27/10/2026, ramo `kimi-incarico-8`, base `kimi-integra` (`130c60a`). R148 e studio 20, sezione 3. La sessione è
ripresa dai tre commit funzionali già presenti e dalle modifiche non committate del punto 4. Nessun merge, rebase,
reset, force o push. Nessuna dipendenza installata. [V]

## Punto 1: lettore delle coordinate

Commit `3289108`, «Read decimal, DMS, linked and projected coordinates (R148, point 1)», già presente all'inizio
della ripresa.

- `coordinates.py` è senza Qt e senza rete. Legge gradi decimali, DMS, gradi e primi decimali, collegamenti di Google
  Maps, OpenStreetMap e Apple, UTM WGS84, ED50 e Gauss-Boaga Roma40. Restituisce punto, formato, datum e zona;
  rifiuta testi ambigui o impossibili con il motivo. I collegamenti non vengono aperti. [V]
- pyproj non era fra le dipendenze del progetto. Il commit non ne aggiunge una: usa nel nucleo le trasformazioni con i
  parametri EPSG dichiarati. [V: `requirements.txt`, `src/meridiana/coordinates.py`]
- Il riferimento ufficiale è Roma Monte Mario, con coordinate Roma40, ED50 e WGS84 pubblicate da SISEF:
  https://foresta.sisef.org/contents/?id=0228-0010128 . I parametri delle proiezioni sono
  https://epsg.io/3003.proj4 , https://epsg.io/3004.proj4 e https://epsg.io/23032.proj4 . Le fonti sono scritte anche
  in `tests/nucleo/test_geo.py`. [V]
- Le prove coprono i formati, i cinque collegamenti, i tre sistemi proiettati e gli errori. UTM WGS84 torna entro 1 cm;
  ED50 e Roma40 entro 4 m dal punto pubblicato. [V: `tests/nucleo/test_geo.py`]

## Punto 2: pagina Nuovo progetto

Commit `f73b06a`, «Start a new project from its place (R148, point 2)», già presente all'inizio della ripresa.

- File > Nuovo mostra un solo campo, la mappa con il segno e «Crea e disegna». I dati facoltativi vengono dopo il
  posto. Il progetto vecchio resta intatto fino alla creazione, poi Meridiana passa al Modello. [V:
  `tests/finestra/test_new_project.py`]
- Mentre si scrive i suggerimenti vengono soltanto dai progetti recenti e dai comuni ISTAT inclusi. Nominatim viene
  chiamato soltanto da «Cerca». Le prove non fanno richieste vere. [V: `tests/widget/test_new_project.py`]
- Il file ufficiale ISTAT del 21/02/2026, la sua fonte e la licenza CC BY 4.0 sono inclusi in `data/istat/` e
  `ATTRIBUTIONS.md`; il dato entra anche nei pacchetti Flatpak e Windows. [V]
- Fotografie offscreen già presenti e rilette: `foto/kimi8-nuovo-chiaro.png` e `foto/kimi8-nuovo-scuro.png`. [V]

## Punto 3: dati di rete facoltativi

Commit `f49cbd1`, «Keep optional grid data with the project (R148, point 3)», già presente all'inizio della ripresa.

- Distributore, POD, tensione, fasi, livello e tipo di connessione, potenza disponibile, potenza richiesta e codice
  della pratica stanno sia nella pagina Nuovo sia nelle Proprietà del sito. Sono facoltativi e non entrano nel calcolo
  del sole. [V]
- La tensione sceglie la dicitura CEI 0-21 o 0-16. Livello e potenza disponibile restano sincronizzati con i campi
  delle regole già usati dal programma, senza inventare valori mancanti. [V: `tests/nucleo/test_network.py`]
- Il formato 15 ha la sua migrazione e il file congelato `tests/formati/file/progetto-v15.meridiana`. [V]
- Fotografie offscreen già presenti e rilette: `foto/kimi8-rete-chiaro.png` e `foto/kimi8-rete-scuro.png`. [V]

## Punto 4: progetto riservato

Commit `d14477d`, «Keep reserved projects offline until each consent (R148, point 4)».

- `Project.online_allowed` applica insieme l'interruttore generale e la scelta del progetto. In un progetto riservato
  la geocodifica è sempre vietata; tessere e PVGIS hanno consensi distinti, con data, conservati nel progetto. [V:
  `tests/nucleo/test_project_privacy.py`]
- La pagina Nuovo non manda il testo a Nominatim quando il progetto è riservato. La mappa resta offline fino al
  consenso esplicito; quel consenso arriva al progetto creato, senza creare un consenso meteo implicito. Anche il
  vecchio dialogo «Trova il sito» rispetta il divieto. [V: `tests/widget/test_project_privacy.py`]
- La finestra applica i consensi alle tessere e ai job PVGIS. Passare offline ferma anche la coda e le risposte già
  avviate; un file riservato migrato parte senza consensi. [V: `tests/finestra/test_project_privacy.py`,
  `tests/widget/test_tile_loader.py`]
- Meridio aveva già il blocco cloud per il riservato. È stato verificato sia nelle prove automatiche sia nel giro reale:
  con Claude scelto, la domanda va al provider locale finto e nessun client Claude viene creato. [V:
  `tests/finestra/test_assistant_chat.py`, `tools/real_tour_8.py`]
- Il formato 16 conserva i consensi con migrazione, validazione e file congelato `progetto-v16.meridiana`. [V:
  `tests/formati/test_project_files.py`]
- L'argomento `project:privacy` evita effetti collaterali: una rinomina non riattiva le mappe e i consensi non
  ricalcolano posa o anno. La prova di rinomina era rossa prima della separazione, poi verde. [V]
- Le prime prove erano rosse perché mancavano metodo, round-trip, caselle e applicazione alla finestra. Dopo la
  correzione sono verdi. La prova ereditata sostituiva anche `start` sul pool globale senza ripristinarlo: questo
  bloccava i layout dei test successivi, ora il metodo viene ripristinato nella pulizia. [V]
- Le prime fotografie mostravano le caselle tagliate a destra. Ora riservatezza e consensi usano `WrappedCheck`, il
  componente condiviso con testo a capo; il test che cercava la scritta usa il nome accessibile. [V]

## Prova vera e fotografie

Il giro finale `tools/real_session.sh /var/home/daniel/fvtest/venv314/bin/python tools/real_tour_8.py` è riuscito in
13,7 secondi su Wayland, Qt 6.12.0, monitor nascosto 1600 x 1000. Il runtime era privato sotto `/tmp`, come richiesto.
Il registro è `docs/revisioni/kimi8-giro.txt`. [V]

Sono stati percorsi con clic e tastiera: File > Nuovo, suggerimento ISTAT mentre si scrive, coordinate DMS, dati
facoltativi, progetto riservato, creazione, assenza di consensi iniziali, calcolo senza PVGIS, consensi separati nelle
Proprietà e domanda a Meridio con Claude selezionato ma mai chiamato. Tutte le funzioni di rete esterna sollevavano
errore se invocate: nessuna è stata invocata. [V]

Fotografie reali aperte e guardate una per una:

- `foto/kimi8-riservato-nuovo-chiaro.png` e `kimi8-riservato-nuovo-scuro.png`;
- `foto/kimi8-riservato-proprieta-chiaro.png` e `kimi8-riservato-proprieta-scuro.png`.

Negli scatti finali i comandi e le caselle sono leggibili, i consensi vanno a capo, il punto DMS è visibile e non ci
sono sovrapposizioni nuove. Restano abbreviazioni nei campi laterali già presenti nel layout esistente, fuori dallo
scopo di questo incarico. Gli avvisi Qt ripetuti riguardano il text input Wayland e il popup del completer; non hanno
impedito i gesti verificati. [V]

Dopo ogni giro `findmnt /run/user/1000/doc` ha trovato il portale Flatpak ancora montato. Alla fine non restano
processi del programma, del compositore o del giro. Nessuna finestra è comparsa sullo schermo di Daniel. [V]

## Suite e controlli finali

Interprete `/var/home/daniel/fvtest/venv314/bin/python`; `meridiana.__file__` punta al `src` di questo checkout.
Prove offscreen, un gruppo per processo. [V]

| Gruppo | Esito |
|---|---:|
| nucleo | 816 prove, OK, 4 saltate |
| calcoli | 176 prove, OK |
| formati | 61 prove, OK |
| esterni | 6 prove, OK, 6 saltate perché gli ingressi esterni non sono abilitati |
| widget | 332 prove, OK, 1 saltata |
| finestra | 136 prove, OK in 401,337 s |
| totale | 1.527 prove, nessun fallimento, 11 saltate |

Ruff su `src tests tools`, catalogo compilato, `msgfmt --check`, `bash -n tools/real_session.sh` e `git diff --check`
sono verdi. Il catalogo italiano ha 3.161 messaggi tradotti, nessun fuzzy e nessun non tradotto. [V]

## Da provare sullo schermo di Daniel

1. Creare un progetto da indirizzo, comune, ogni formato di coordinata e collegamento; verificare il punto prima di
   «Crea e disegna».
2. Con un progetto non riservato e la geocodifica consentita, provare «Cerca» e la scelta fra i risultati Nominatim.
3. Aprire e chiudere i dati facoltativi, compilare rete e pratica, riaprire il file e controllare i valori.
4. Marcare il riservato prima di qualunque richiesta: suggerimenti locali e coordinate devono continuare a funzionare,
   «Cerca» non deve mandare il testo. Dare e revocare separatamente i consensi mappe e PVGIS.
5. Guardare le Proprietà a larghezze diverse e nei due temi, con le caselle a capo.

## Non fatto e limiti

- Nessuna richiesta vera a Nominatim, PVGIS, fornitori di tessere o Claude, per decisione dell'incarico. Copertura e
  qualità delle risposte dei servizi reali restano quindi da provare sullo schermo con il consenso di Daniel.
- Nessun indice di clienti o commesse e nessun Plus Code: fuori dai quattro punti e dalle decisioni immediate di R148.
- Non sono stati modificati i rami `lavoro`, `kimi-integra` o altri rami degli incarichi. Claude deve rivedere questi
  commit prima dell'unione.
