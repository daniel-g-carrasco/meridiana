ESITO: verde

# Incarico 9: clienti, commesse e progetto autonomo

28/10/2026, ramo `kimi-incarico-9`, base `kimi-incarico-8` (`dfbe7d5`). R150 e studio 20, sezione 5. La sessione è
ripresa dal commit del punto 1 e dalle modifiche non committate dei punti 2 e 3. Nessun merge, rebase, reset, force o
push. Nessuna dipendenza installata. Tutti i nomi di clienti, commesse e progetti nelle prove sono inventati. [V]

## Punto 1: il progetto viaggia con tutte le risorse

Commit `5e2f503`, «Carry every project resource in its file (R150, point 1)», già presente all'inizio della ripresa.

- Il formato 17 incorpora allegati della relazione, profilo e logo dell'autore, meteo e orizzonte. Moduli, inverter e
  ottimizzatori personalizzati viaggiavano già nel file. L'apertura con catalogo, impostazioni e cache vuoti conserva
  i dati e il calcolo non chiede la rete. [V: `tests/formati/test_portability.py`]
- Il meteo incorporato di un altro sito viene rifiutato. La scelta di nessun autore resta tale. Un allegato esterno
  mancante viene nominato all'apertura invece di sparire in silenzio. [V]
- Il file campione congelato è `tests/formati/file/progetto-v17.meridiana`. Manuale e registro delle richieste sono
  aggiornati nello stesso commit. [V]

## Punto 2: registro SQLite

Commit «Store clients and jobs in a safe SQLite registry (R150, point 2)».

- `registry.py` conserva clienti, commesse, serie di progetti e cartelle con id stabili. I codici commessa sono testi
  di cinque cifre. Chiavi esterne, schema versionato, transazioni immediate, WAL e sincronizzazione completa
  proteggono le scritture. Una copia SQLite consistente `.bak` viene rinnovata dopo ogni commit. [V]
- Le prove coprono round-trip, ricerca, archiviazione del cliente con commesse, rollback senza record parziali,
  backup con i dati committati, codici duplicati e schemi più recenti rifiutati. [V:
  `tests/nucleo/test_registry.py`]

## Punto 3: clienti e commesse nella finestra

Commit «Choose clients and jobs in the project workflow (R150, point 3)».

- File > Clienti e commesse usa tre colonne: clienti, commesse e dettaglio. Creazione e ricerca restano nella pagina;
  stati e fasi sono mostrati con parole tradotte, non con i codici interni. [V: `tests/widget/test_registry_page.py`]
- Nel Nuovo progetto si scelgono cliente e commessa. Scegliendo soltanto la commessa, il suo cliente arriva comunque
  nella relazione. Questo caso era rosso prima della correzione, poi verde. Una commessa riservata rende riservato il
  progetto. [V: `tests/finestra/test_new_project.py`]
- Salvataggio, revisioni e riapertura mantengono lo stesso id della serie e il collegamento alla commessa. [V]

## Punto 4: cartelle e scambio del registro

Commit «Share job manifests and merge registry exchanges (R150, point 4)».

- Il manifesto `.meridiana-commessa.json` nasce solo dopo il consenso della singola cartella. Contiene i dati minimi
  della commessa e i collegamenti ai progetti, e segue le modifiche successive. La revoca rimuove file e `.bak`;
  una commessa riservata non lo consente e, se diventa riservata, lo rimuove. [V]
- Export e import usano JSON completo versionato. L'anteprima conta nuovi, aggiornati, invariati e conflitti prima di
  cambiare il database. L'unione per id non duplica e non elimina i record assenti. Codici commessa o percorsi in
  conflitto, file non validi e versioni future bloccano tutto senza scritture parziali. [V]
- L'export di commesse riservate avvisa che il JSON non è cifrato e attende un sì. I consensi delle cartelle non
  viaggiano nel file: una cartella importata parte senza manifesto, mentre un consenso già dato sul PC resta.
  Quest'ultimo caso è stato aggiunto dopo una prova rossa sulla prima versione dell'import. [V]
- La pagina offre collegamento della cartella, casella per il consenso, anteprima con comando separato «Applica
  importazione» ed export. Le prove dei widget azionano questi controlli e i dialoghi restano finti. [V]

## Revisione indipendente e correzioni

Un revisore indipendente ha letto tutto il ramo e ha trovato casi scoperti dalle prime prove. Sono stati corretti con
una prova rossa prima e verde dopo per ciascuno:

- un nuovo sito con meteo proprio non conserva più l'orizzonte del sito precedente;
- il risalvataggio conserva i byte degli allegati incorporati anche senza la copia materializzata nella cache;
- commessa e serie sono scritte nel progetto, formato 18 con migrazione e file congelato: R02 e la riapertura di R01
  mantengono gli id; import PVsyst e recupero non ereditano associazioni sbagliate;
- scegliere una commessa riservata ferma subito ricerca e tessere, non soltanto alla creazione;
- il consenso di una cartella resta valido solo se id, percorso e commessa non cambiano;
- un registro illeggibile o più recente non blocca la finestra e non viene sovrascritto: un avviso spiega l'uso di un
  registro temporaneo;
- campi malformati e booleani testuali sono rifiutati prima dell'anteprima e della scrittura;
- errori di scrittura o cancellazione dei manifesti sono registrati per cartella, mostrati e ritentati senza fermare
  le altre;
- nome vuoto, codice duplicato e percorsi già collegati hanno messaggi chiari e tradotti.

Il revisore segnalava anche importazione dei singoli manifesti e conflitti fra manifesto e registro. Restano fuori
dal comportamento richiesto dai quattro punti, che chiedono la scrittura consentita del manifesto e l'import/export
del registro, non la lettura dei manifesti. Le modifiche esterne ai manifesti non sono quindi una funzione coperta da
questo incarico e restano da progettare separatamente. [I]

## Prova vera e fotografie

Il giro finale `tools/real_session.sh /var/home/daniel/fvtest/venv314/bin/python tools/real_tour_9.py` è riuscito tre
volte, l'ultima in 14,382 secondi su Wayland, Qt 6.12.0, monitor nascosto 1600 x 1000 e runtime privato sotto `/tmp`.
Il registro è `docs/revisioni/kimi9-giro.txt`. [V]

Sono stati percorsi con clic e tastiera: creazione di cliente e commessa, collegamento di una cartella, consenso e
revoca del manifesto, export, anteprima senza scritture, applicazione dell'import, commessa riservata senza manifesto,
export riservato prima annullato e poi confermato, selezione della commessa riservata subito offline nel Nuovo,
salvataggio di R02 e riapertura di R01 con la stessa serie. Nessun servizio esterno è stato usato. [V]

Fotografie reali aperte e guardate una per una dopo il giro finale:

- `foto/kimi9-registro-chiaro.png` e `kimi9-registro-scuro.png`;
- `foto/kimi9-import-anteprima-scuro.png`;
- `foto/kimi9-nuovo-chiaro.png` e `kimi9-nuovo-scuro.png`.

Titoli, campi, caselle, percorso della cartella e anteprima sono leggibili in entrambi i temi. Non ci sono testi
sovrapposti o comandi tagliati. Gli avvisi Qt nel registro riguardano il text input Wayland e non hanno impedito i
gesti verificati. Dopo ogni giro `findmnt /run/user/1000/doc` ha trovato il portale Flatpak ancora montato. Alla fine
non restano processi del programma, del compositore o del giro. Nessuna finestra è comparsa sullo schermo di Daniel. [V]

## Suite e controlli finali

Interprete `/var/home/daniel/fvtest/venv314/bin/python`; `meridiana.__file__` punta al `src` di questo checkout.
Prove offscreen, un gruppo per processo. [V]

| Gruppo | Esito |
|---|---:|
| nucleo | 828 prove, OK, 4 saltate |
| calcoli | 176 prove, OK |
| formati | 67 prove, OK |
| esterni | 6 prove, OK, 6 saltate perché gli ingressi esterni non sono abilitati |
| widget | 339 prove, OK, 1 saltata |
| finestra | 139 prove, OK in 413,233 s |
| totale | 1.555 prove, nessun fallimento, 11 saltate |

Ruff su `src tests tools`, catalogo compilato, `msgfmt --check`, `bash -n tools/real_session.sh` e `git diff --check`
sono verdi. Il catalogo italiano non ha voci fuzzy o non tradotte. [V]

Una prima esecuzione del gruppo widget aveva trovato un errore intermittente in
`test_plan_background.Fallback.test_failed_tiles_are_replaced_the_source_rests_and_retry_does_not_change_the_choice`:
un oggetto grafico arrivava al posto della risposta di rete. Il test da solo e l'intero gruppo widget ripetuto sono
passati, senza modifiche al codice delle mappe. [V]

## Da provare sullo schermo di Daniel

1. Importare ed esportare un registro reale dopo averne verificato l'anteprima e una copia di sicurezza.
2. Collegare cartelle reali sui volumi usati dallo studio e provare il manifesto anche con un volume non raggiungibile.
3. Aprire progetti con commesse esistenti, salvarne revisioni e controllare che la serie resti quella giusta.
4. Guardare la pagina del registro a larghezze e dimensioni del testo diverse, in particolare con percorsi molto lunghi.

## Non fatto e limiti

- Non sono state aggiunte attività, scadenze operative o strumenti di Meridio: appartengono al lavoro successivo R151,
  non ai quattro punti di questo incarico.
- Non sono state provate cartelle reali, registri reali o richieste a servizi esterni. Nessun dato vero è stato letto o
  scritto. I percorsi delle prove sono tutti sotto `/tmp`.
- Non sono stati modificati i rami `lavoro`, `kimi-incarico-8` o altri rami. Claude deve rivedere questi commit prima
  dell'unione.
