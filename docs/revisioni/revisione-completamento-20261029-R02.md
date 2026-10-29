# Revisione indipendente del completamento, 29 ottobre 2026, R02

Revisione mirata del delta applicativo prima dell'integrazione: limiti di corrente opzionali/scalari, partizioni
fisiche degli ottimizzatori, formato 20, dialogo dei gruppi, proposta asincrona e applicazione dell'hardware,
registro orario e report per inverter. Il primo passaggio è stato di sola lettura. Le prove nuove sono isolate
in `build/probe_root_review_20261029.py`; soltanto il successivo fix CSV è stato affidato a questa revisione.

## Difetti riprodotti e risolti

- **Alta, P1: cancellazione degli inverter scelti.** Una proposta ordinaria completa restituiva
  `Plant.entries=[]`; il consumer interpretava la lista come sostituzione esplicita e cancellava gli inverter
  esistenti. Lo stesso contratto coinvolgeva l'adozione della proposta con `session.amend`, senza normale passo
  di undo. Riprodotto con una proposta reale su 19 moduli e hardware selezionato. Il contratto a monte ora usa
  `None` per conservare l'hardware e una lista per sostituirlo. La regressione indipendente è verde.
  Il coordinatore ha verificato inoltre i consumer di applicazione/undo e adozione in
  `finestra.test_string_proposal_async`.
- **Media, P2: tabella opzionale parzialmente vuota.** Un record con
  `dc_current_max_per_mppt_by_strings_a=[None, {"1": 10}]` era tollerato da `current_limit`, ma il percorso di
  proposta iterava `None` in `strings_allowed`; anche la chiave della cache presumeva ogni riga un dizionario.
  La costruzione reale dell'impianto terminava con `TypeError`. Le correzioni a monte sono verificate dalla
  regressione indipendente, ora verde.
- **Media, P2: intestazioni CSV incoerenti.** I nomi liberi degli inverter finivano in `sep.join(header)`.
  `Roof, east` generava 10 campi di intestazione contro 8 campi dati in inglese; il punto e virgola produceva
  lo stesso errore in italiano. Virgolette e newline interrompevano anche i metadati e i record fisici.
  `register.write_csv` ora usa `csv.writer` per intestazioni e righe e mantiene il prefisso `#` su ogni riga
  fisica dei metadati. La nuova regressione verifica sei combinazioni nome/lingua, struttura, testo completo
  dei campi e valori numerici. Non cambia il calcolo dell'energia né la scala delle unità.

## Prove e stato

[V] Le tre regressioni indipendenti sono verdi: 3 prove in 1,834 s, registro
`build/probe-root-review-20261029-R02.log`. I fallimenti iniziali restano in
`build/probe-root-review-20261029.log` e `build/probe-root-review-csv-20261029.log`.

[V] Fix CSV e compatibilità: 4 prove verdi in 13,112 s, due di `calcoli.test_inverter_register` e i due
controlli del registro nella classe `widget.test_report.Report`. Ruff dei due file e diff check superati.
`src/meridiana/energy/register.py` e `tests/calcoli/test_inverter_register.py` sono congelati e restituiti
al coordinatore; nessun commit Meridiana creato da questa revisione.

La lettura delle guardie asincrone non ha trovato altri difetti concreti: identità del job, annullamento,
chiave dello stato, chiavi dei layout e layout ancora in corso vengono verificati prima di applicare il
risultato. La suite sequenziale complessiva e il freeze dei pacchetti restano verifiche del coordinatore.

Resta un rilievo testuale non bloccante, segnalato al coordinatore: l'avviso `opt_orientations` in
`plant._check_optimized` afferma ancora che i limiti di tensione degli ottimizzatori non sono calcolati ora per
ora. Il nuovo solver e il nuovo pedigree dichiarano invece il calcolo quando i dati sono documentati.
Il messaggio va riferito ai limiti effettivi del modello, senza cambiare la fisica in questa revisione.

[V] Seguito dell'integratore: il testo è stato corretto e tradotto; la prova di orientamenti multipli è verde.
Il messaggio distingue ora i limiti orari documentati dalle dinamiche proprietarie non simulate.

## Controllo del modello condiviso

[V] Il template privato è sul commit `0b5d9654b3ec9cd79aa25cc8df73f384112b7c7b`, identico al remoto.
Il controllo del precedente `template-sync-qt_R03.json`, ancora riferito a `3da1098`, segnala soltanto i
tre scostamenti attesi: `checkboxes.py` sui due lati e `window.py` del consumatore ora esteso dal delta root.
Il manifest R04 va generato sul freeze definitivo, mantenendo il carattere adattato della finestra.

Il verificatore normalizza CRLF in LF: per `checkboxes.py`, hash del sorgente qtkit
`912513031a7d553e98e63aa56634854d126952862a42cd4817b2b94e2b081b66`, hash del consumatore Meridiana
`87a3cd834a2688d56934a4820642f2c85f7a044733eb730aa6b14a9b4ce070b8`.
La differenza è limitata agli import. Il manifest non è stato modificato da questa revisione.

[V] Seguito dell'integratore: generati `template-sync-qt_R04.json` e `template-sync-qt-tables_R05.json`;
il verificatore conferma 21 + 1 mapping contro il commit aggiornato.

Configurazione del laptop ritrovata in memoria e nel file SSH locale senza leggere chiavi o aprire connessioni;
la successiva connessione di controllo è stata effettuata dal coordinatore. Nessuna attività su R235-R240.
