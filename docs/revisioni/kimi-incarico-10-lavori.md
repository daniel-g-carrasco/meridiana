ESITO: in verifica

# Incarico 10: Meridio trova e apre i progetti

29/10/2026, ramo `kimi-incarico-10`, base `kimi-incarico-9` (`d327b92`). R151 e studio 20, sezione 6. Nessun merge,
rebase, reset, force o push. Nessuna dipendenza installata. Clienti, commesse e progetti delle prove sono inventati.
Nessuna chiamata a un modello vero. [V]

## Punto 1: indice locale

Commit `63b75ac`, «Index linked projects in the background (R151, point 1)».

- `project_index.py` legge soltanto le cartelle collegate alle commesse e conserva dati derivati, non una seconda
  copia dei progetti: serie, percorso, luogo, potenza posata, tipo, edifici, sottocampi, montaggi, inclinazioni,
  date, revisione e riservatezza. Cliente e commessa vengono dal registro. [V: `tests/nucleo/test_project_index.py`]
- Dimensione, data e SHA-256 evitano di interpretare di nuovo i file invariati. Un file danneggiato resta visibile
  con il motivo. Le serie senza id usano cartella e nome senza `_Rnn`. [V]
- Il registro versione 2 conserva l'indice in SQLite e lo sostituisce atomicamente. La finestra esegue le scansioni
  in un `QRunnable`, all'avvio, dopo apertura, salvataggio, revisione e cambiamenti dei collegamenti. Una generazione
  scarta i risultati vecchi. [V: `tests/finestra/test_project_index_window.py`]
- Una prova ha mostrato che i metadati amministrativi cambiati non restavano vecchi quando il file era invariato.
  Un'altra ha impedito una scansione pianificata dopo la chiusura del registro. [V: ciclo rosso-verde]

## Punto 2: strumenti di Meridio

Commit `bef753b`, «Let Meridio find and confirm projects to open (R151, point 2)».

- `search_projects` cerca per testo, codice, cliente, tipo, potenza, data e distanza. `project_revisions` restituisce
  l'ultima revisione leggibile di ogni serie, senza lasciare che un file più recente danneggiato nasconda quella
  valida. `similar_projects` filtra tipo e potenza, conta ogni serie una volta e spiega montaggio, inclinazione,
  distanza e revisione. La similarità aiuta la ricerca, non valuta la bontà tecnica. [V:
  `tests/nucleo/test_meridio_projects.py`]
- `prepare_open_project` crea soltanto una scheda con percorso e revisione. Non apre mai da solo. Il clic «Apri»
  passa dal consueto «salva, scarta o annulla»: Annulla conserva progetto e scheda, Scarta apre il bersaglio. [V:
  `tests/finestra/test_meridio_projects.py`]
- Le chiamate fra strumenti usano alias locali `pr…`, non richiedono al modello di conoscere percorsi. [V]

## Punto 3: riservatezza

Commit `f7226e3`, «Filter and redact the archive before Claude (R151, point 3)».

- Il filtro è nel programma, prima degli strumenti e del modello. Il cloud non riceve l'indice né progetti riservati,
  nemmeno come conteggio. Le righe non riservate strettamente necessarie contengono solo alias e dati tecnici
  consentiti. Nomi, titoli, percorsi, clienti e codici commessa restano fuori. [V: `tests/nucleo/test_meridio_privacy.py`]
- `Redactor.with_archive` redige anche le domande e i risultati precedenti, compresi nomi riservati e nomi brevi.
  Il percorso contenuto in un messaggio d'errore diventa soltanto `readable: false`. [V]
- Una richiesta che riguarda i riservati forza il modello locale. Il ripiego locale dopo un errore di rete disattiva
  il filtro cloud per i messaggi successivi. [V]
- Le prove con `FakeAnthropic` hanno prima riprodotto l'invio di nome e percorso, poi hanno verificato che tutti i
  messaggi destinati a Claude restino privi di quei dati. [V: `tests/finestra/test_meridio_privacy.py`]

## Punto 4: attività locali

Il commit finale comprende anche documenti, fotografie e la correzione grafica descritta sotto.

- Il registro versione 3 aggiunge attività con testo, scadenza ISO, stato e collegamenti facoltativi a commessa e
  progetto. Scrittura transazionale, backup e persistenza alla riapertura restano quelli del registro. La migrazione
  2→3 è stata eseguita su un database di prova. [V: `tests/nucleo/test_meridio_tasks.py`]
- `list_tasks` filtra scadenze, commesse e attività concluse. `prepare_task` crea o completa soltanto una proposta.
  Alias `tk…`, nessuna scrittura prima del clic e nessun completamento automatico. Il cloud non vede attività
  riservate. [V]
- Le schede sulla finestra creano e completano l'attività soltanto ai due clic. Il testo delle attività entra nella
  redazione dei messaggi cloud. [V: `tests/finestra/test_meridio_tasks.py`]

## Prova reale e correzione grafica

Il comando finale è stato `tools/real_session.sh /var/home/daniel/fvtest/venv314/bin/python tools/real_tour_10.py`,
su Wayland, Qt 6.12.0, monitor nascosto 1600 x 1000 e runtime privato sotto `/tmp`. Il giro è terminato in 9,460 s.
Il registro è `docs/revisioni/kimi10-giro.txt`. [V]

Sono stati verificati con clic e controlli sul processo: indice in secondo piano, ultimo capannone simile con motivo,
scheda con percorso e revisione, Annulla che conserva il lavoro, Scarta che apre, creazione e completamento attività,
provider cloud finto senza dati dell'archivio. [V]

La prima fotografia ha mostrato un difetto reale: percorso e attività erano tagliati. Le misure hanno distinto due
cause: la `Card` veniva ridotta sotto il testo a capo e il suo contenitore non cresceva, coprendo revisione e pulsanti
con le «Domande pronte». La `Card` condivisa ora imposta l'altezza minima dal contenuto, il contenitore viene
ridimensionato aggiungendo e rimuovendo schede e le domande restano nascoste finché una conferma è aperta. La regola
vale solo per le proposte: una prova preesistente ha impedito di nasconderle anche per consensi e ricerca modelli. [V:
`tests/widget/test_assistant_card.py`, `tests/finestra/test_meridio_projects.py`, `tests/finestra/test_assistant_window.py`]

Fotografie finali aperte e giudicate: `foto/kimi10-apertura-chiaro.png`, `kimi10-apertura-scuro.png` e
`kimi10-attivita-scuro.png`. Percorso, revisione, attività e pulsanti sono interamente visibili in entrambi i temi,
senza sovrapposizioni. [V]

Dopo ogni giro `findmnt /run/user/1000/doc` ha trovato il portale Flatpak ancora montato. Finestra e compositore sono
stati chiusi. Nessuna finestra è comparsa sullo schermo di Daniel. [V]

## Suite e controlli finali

Interprete `/var/home/daniel/fvtest/venv314/bin/python`; `meridiana.__file__` punta al `src` di questo checkout.
Prove offscreen, un gruppo per processo. [V]

| Gruppo | Esito |
|---|---:|
| nucleo | 842 prove, OK, 4 saltate |
| calcoli | 176 prove, OK |
| formati | 67 prove, OK |
| esterni | 6 prove, OK, 6 saltate perché gli ingressi esterni non sono abilitati |
| widget | 340 prove, OK, 1 saltata |
| finestra | 146 prove, OK in 411,984 s |
| totale | 1.577 prove, nessun fallimento, 11 saltate |

Ruff su `src tests tools`, catalogo compilato, `msgfmt --check`, `bash -n tools/real_session.sh` e `git diff --check`
sono verdi. Il catalogo italiano non ha voci fuzzy. [V]

Una prima esecuzione di `widget` aveva trovato un errore intermittente nel rendering 3D di `test_viewcube`: un oggetto
`QGraphicsPolygonItem` al posto del contesto Quick. Il file da solo e l'intero gruppo ripetuto sono passati senza
modifiche al codice 3D. [V]

## Revisione indipendente

In verifica.

## Da provare sullo schermo di Daniel

1. Collegare cartelle reali e verificare che l'indice non attraversi volumi lenti o non raggiungibili.
2. Chiedere a Meridio progetti simili con dati reali e controllare che il motivo sia comprensibile.
3. Aprire progetti con revisioni reali e controllare le schede con percorsi molto lunghi e dimensioni del testo diverse.

## Non fatto e limiti

- Nessuna cartella, commessa o conversazione reale è stata letta o scritta. Nessun servizio esterno è stato chiamato.
- La similarità è strutturata e spiegabile, non semantica. Non usa embedding, come scelto per il primo passo dello
  studio.
- L'export JSON del registro resta quello di R150: non comprende le nuove attività né l'indice derivato, che resta
  ricostruibile dai file.
- Non sono stati modificati `lavoro`, `main` o altri rami. Claude deve rivedere i commit prima dell'unione.
