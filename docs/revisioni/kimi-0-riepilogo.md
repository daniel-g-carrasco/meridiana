# Revisione indipendente di Meridiana: riepilogo

Data: 25/10/2026. Ramo: `kimi-revisione`.

Ho completato i cinque punti senza modificare il codice. I rapporti completi sono:

- `docs/revisioni/kimi-1-window.md`
- `docs/revisioni/kimi-2-vita-qt.md`
- `docs/revisioni/kimi-3-armonia.md`
- `docs/revisioni/kimi-4-testi.md`
- `docs/revisioni/kimi-5-prove.md`

Ogni osservazione indica file e riga, scenario, gravità, prova verificata o dedotta, correzione e rischio. Qui sotto
ci sono le tre priorità di ciascun punto, in italiano semplice.

## 1. Spezzare `window.py`

1. **`MainWindow` fa troppo.** Ha 4.435 righe e 274 metodi. File, relazione, energia, impianto, stringhe,
   importazioni e aggiornamenti dipendono tutti dalla stessa classe. Una modifica piccola può avere effetti in
   punti lontani.
2. **Costruzione e segnali hanno un ordine obbligato.** `_actions`, `_build_phases`, `_theme_changed`, `_show_all`
   e `Chat` non possono essere spostati a caso. Se pvlib è già caricato, `PlantJob` può rispondere subito, sullo
   stesso stack di chiamata: le pagine devono già esistere.
3. **Le prove usano la finestra come contratto.** Contano 1.646 accessi a 182 attributi, inclusi 69 nomi privati.
   Ci sono anche patch su `meridiana.ui.window.CatalogDialog` e su metodi privati. Eliminare questi nomi durante lo
   spostamento romperebbe le prove senza migliorare il programma.

**Correzione consigliata**: migrazione per passi piccoli, non riscrittura. Prima i quattro job in `ui/workers.py`,
poi azioni, file, viste, editing, energia, verifiche, impianto, stringhe, relazione e importazioni. `MainWindow`
resta il guscio Qt e una facciata temporanea con gli stessi nomi. Ordine, segnali e import pigri invariati. Ogni
passo con tutta la suite verde; prima occorre correggere i fallimenti attuali, altrimenti la base non è verde.

## 2. Oggetti Qt, thread e segnali

1. **Aggiornamenti e IFC possono rispondere dopo la morte della finestra.** Le lambda in `window.py:4258-4259` e
   `:4520` catturano `self`. Ho riprodotto `MainWindow already deleted`, `QProgressBar already deleted` e
   `QTimer already deleted`. Il `LayoutJob` bound non ha mostrato il problema.
2. **La chiusura non ferma PDF e anteprima.** `closeEvent` non chiama `_cancel_report` e non chiude `preview_run`.
   Una sonda ha lasciato `report_run`, `preview_run` e il file `.part` ancora aperti dopo `close()`.
3. **Altri rilasci non sono protetti.** Il nuovo tentativo di una tessera usa il caricatore dopo la distruzione;
   il focus delle Proprietà chiama un pannello morto; `QuickImage` riusa una `QQuickWindow` rilasciata in un
   ridimensionamento; `Theme` emette dopo la distruzione; due `gdbus` restano attivi alla chiusura.

**Correzione consigliata**: prima metodi bound per aggiornamenti e IFC. Poi chiusura esplicita dei generatori PDF e
anteprima. Contesto Qt ai timer di `TileLoader`, `Properties` e `Theme`. Stato rilasciato e guardie in `QuickImage`,
arresto ordinato di `SystemAccent`. Ogni caso con una prova rossa prima e verde dopo. La sequenza GPU vera resta da
verificare da Claude sullo schermo.

## 3. Armonia del sistema grafico

1. **Le Verifiche calcolano colori fuori dal tema.** Fondo scuro e passaggio hanno formule locali; alcuni fallback
   non corrispondono ai token. Vanno creati ruoli `checks_card` e `checks_hover`, oltre ai colori `info` e agli
   inchiostri dei segni.
2. **Le pagine energetiche non usano sempre il sistema.** Il bordo d'errore è `#d03b3b` invece di `danger`; margini
   da 10 e 14 px e spazi da 10 px sono fuori scala. Il minimo dei grafici, 160 px, è ripetuto in tre file.
3. **Movimento, misure e fallback non sono tutti catalogati.** Meridio scivola in 320 ms, il fumetto chiude in 130,
   la camera in 250, mentre il catalogo dichiara solo 110, 180 e 240. Alcuni fallback colore e molte dimensioni di
   componente non hanno un nome condiviso.

**Correzione consigliata**: prima sostituire i valori già equivalenti a `Space`, `Radius`, `Size`, `Icon` e
`Button.HELP`, senza cambiare un pixel. Aggiungere `Timing` per debounce e attese e i nuovi ruoli colore con test di
contrasto. Solo dopo scegliere le eccezioni estetiche vere su schermate prima/dopo, non normalizzare tutto alla
cieca. Fluidità e aspetto reale li misura Claude.

## 4. Testi e traduzioni

1. **Alcuni messaggi arrivano in inglese anche in italiano.** Le note `BALLAST_WARNING` e
   `no room left inside the margins`, l'area sotto 1 m², errori di sottofondo, progetto, PVsyst, meteo e geocoding
   non sono nel catalogo. Gettext li restituisce invariati.
2. **La galleria non è bilingue.** Titolo, schede, pulsanti, etichette ed esempi sono in italiano senza `_()`.
   Serve sorgente inglese e traduzione italiana, non `_()` attorno all'italiano esistente.
3. **Il catalogo contiene storia e due incoerenze.** Ci sono 105 voci attive non più nei sorgenti e una già
   obsoleta. `Layout` diventa «Disposizione» accanto alla «posa»; le colonne dell'ombra hanno traduzioni poco
   naturali e non concordi in numero.

**Correzione consigliata**: prima marcare i messaggi alla fonte e provare il catalogo italiano. Poi uniformare
«Posa» e correggere «File, ombra lineare», «Ostacoli, ombra lineare», «File, effetto elettrico». Rendere la galleria
bilingue. Aggiornare il PO con revisione umana e solo dopo rimuovere gli obsoleti. Nessun trattino lungo trovato
oltre all'asserzione che lo vieta.

## 5. Prove

1. **Il fumetto non può ridursi sotto il contenuto nuovo.** La scheda «No local model on this PC» aggiunge 87 px e
   porta il minimo a 305. Il test chiede 130, ma `resizeDocks` non può andare sotto 305. Con
   `win.assistant_chat._drop_survey()` prima del ridimensionamento, il minimo diventa 212 e il test passa.
2. **L'accento sul focus è un falso positivo.** La prova consente l'accento sui pulsanti ma non sul campo attivo,
   mentre il tema lo usa correttamente anche per l'anello del focus. Con un `QuantityField` attivo trova 62 punti;
   aggiungendo il solo rettangolo del widget attivo, scende a zero.
3. **Voce e RHI dipendono dal PC.** Kokoro è presente nella home reale e invalida tre test «nessun motore»: home
   temporanea e `natural_model = None` li fanno passare. Il renderer RHI, invece, non costruisce la pipeline e
   produce due PNG bianchi: va saltato con motivo esplicito, non valutato come disegno valido. Il self-test fallisce
   solo perché il catalogo non era compilato; dopo `compile_po.py` passa.

**Correzione consigliata**: prima sistemare le attese dei test e la compilazione del catalogo, per avere una base
verde. Poi spostare le soglie di millisecondi in `esterni`, mantenendo comportamento, pixel e struttura nelle suite
normali. Le 20 prove più lente sono tutte in `finestra` e occupano 98,042 s su 234,589: sono soprattutto lavoro
reale, non doppioni. Non ho trovato corpi di prova identici o quasi identici, quindi non consiglio rimozioni.

## Ordine di lavoro consigliato

1. **Rendere affidabile la base**: correzioni ai test per fumetto, accento, voce e RHI; compilazione del catalogo;
   nuova suite completa verde.
2. **Correggere i difetti di chiusura**: lambda di aggiornamenti e IFC, poi PDF e anteprima.
3. **Completare le traduzioni dei messaggi utente**, con prove in italiano.
4. **Proteggere gli altri rilasci Qt**: timer di mappe e Proprietà, `QuickImage`, `Theme`, `SystemAccent`.
5. **Spezzare `window.py` per passi**, iniziando dai job e conservando la facciata.
6. **Centralizzare ruoli colore e durate**, poi le misure componenti senza cambiare pixel.
7. **Pulire catalogo e galleria**, e spostare le soglie temporali in `esterni`.

Ogni correzione approvata dovrebbe avere un commit separato, con prova rossa prima e verde dopo, `ruff` e suite
intera. Le scelte che cambiano aspetto o movimento vanno mostrate a Daniel prima dell'applicazione.

## Verifiche e limiti

- `ruff check src tests tools`: verde.
- `nucleo`: 780 prove verdi, 4 saltate; `calcoli`: 174 verdi; `formati`: 58 verdi; `esterni`: 6 saltate.
- `widget`: 276 prove con 3 fallimenti analizzati; `finestra`: 118 prove con 3 fallimenti analizzati.
- Self-test inizialmente rosso per il catalogo non compilato, poi verde con `PASS all: 0 failed`.
- Non ho aperto finestre sullo schermo, non ho usato le cartelle reali di Daniel e non ho misurato fluidità o aspetto.
- Offscreen la vista 3D ordinaria non viene disegnata. Il caso RHI ha prodotto immagini bianche e errori di pipeline,
  quindi non permette conclusioni sul rendering reale.

Mi fermo qui, in attesa delle scelte di Daniel. Nessun commit e nessuna modifica al codice sono stati fatti.
