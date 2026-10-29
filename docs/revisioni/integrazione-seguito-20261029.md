# Integrazione del seguito Meridiana

Richiesta di Daniel: procedere con i punti rimasti, conservando le aggiunte fino a R234 e riportando i
componenti condivisi nel template Qt. Base applicativa af17add. Nessuna richiesta precedente viene eliminata;
`docs/richieste.md` distingue adesso funzioni implementate, prove eseguite e residui tecnici.

## Cambiamenti integrati

- File e Impostazioni separati nella navigazione; Salva e revisioni riuniti, colonne adattive, campi leggibili,
  conferma di ripristino annullata al cambio di categoria.
- Meridio con superficie conversazione e ruoli distinti, scorrimento conservato durante lo streaming.
- Strumenti riordinati, posa est-ovest e pensiline a una/due falde; nuova icona Allinea.
- Tooltip stabili e con palette autonoma, hover calendario, rientro Verifiche invariabile.
- Testo tecnico e PDF riformattati, tre profili per destinazione, tabelle con intestazioni ripetute,
  didascalie mantenute con la figura quando entrano nella stessa pagina.
- Scelta inverter/stringatura corretta per orientamenti, limiti totali e per MPPT, connettori e famiglie
  SolarEdge trattate. Ricerca annullabile fuori dal thread grafico, risultati vecchi scartati.
- Caricamento concorrente pvlib corretto, senza appesantire l'importazione iniziale della finestra.
- IFC con identità stabili e proprietà, piani ausiliari esatti e modificabili, roundtrip delle superfici virtuali;
  schema logico del progetto 19 nel contenitore `.mer`.

Rapporti specifici: `testi-strumenti-pensiline-20261029.md`, `ux-condivisa-seguito-20261029.md`,
`ombre-stringatura-audit-20261029.md`, `ifc-bim-seguito-20261029.md`.

## Revisione e verifiche

Le revisioni indipendenti hanno trovato e fatto correggere tre problemi concreti: ripristino della categoria
sbagliata nelle Impostazioni, didascalia separata dalla pianta nel PDF, dimensionamento su una posa precedente
durante il ricalcolo. Quest'ultimo era riproducibile con 128 moduli vecchi e 48 attuali: ora il comando aspetta
la posa corrente, rilegge i risultati dopo il dialogo e verifica anche la loro firma alla consegna del job.

| Verifica | Esito osservato |
| --- | --- |
| Nucleo, passaggio esteso | 886 test; tre aspettative obsolete su versione 18 e vecchio ordine strumenti, poi aggiornate; 22 mirati verdi includendo i casi interessati |
| Calcoli, passaggio esteso | 217 test verdi |
| Formati, passaggio esteso | 85 test verdi |
| Widget, passaggio esteso | 453 test; due aspettative obsolete su nome Input/MPPT e righe informative, corrette; 22 mirati verdi successivi |
| Percorsi finestra, secondo passaggio | 32 test verdi in 147,438 s, File, pensiline, BIM, navigazione, Meridio, IFC e impianto |
| Dimensionamento asincrono e fasi | 12 test verdi; dopo revisione posa, altri 4 verdi in 12,113 s |
| Import concorrenti pvlib | regressione subprocess falliva prima e passa dopo; 25 e 10 test mirati verdi, avvio differito conservato |
| Fallimento attività clima | 1 test: ImportError produce il segnale di errore e non lascia attesa pendente |
| IFC specifici | prove numeriche/kernel/UI dettagliate nel rapporto BIM, inclusi tre modelli locali Revit/IFC |
| Lint e traduzioni | Ruff src/tests/tools e GNU msgfmt --check superati |
| Template Qt | suite completa 150 test verdi in 130,650 s, lint e foto chiaro/scuro |

I numeri dei gruppi mirati possono sovrapporsi: non sono sommati come test unici. Il primo passaggio finestra
era stato interrotto dopo la riproduzione dell'import concorrente pvlib; non viene descritto come verde.
La precedente soglia prestazionale del cambio tema di 1 s non è stata modificata né dichiarata risolta.
Non è stata ripetuta per ogni ritocco l'intera suite di finestre, che nel lotto precedente richiedeva circa 24 minuti.

Foto root in `foto/seguito-20261029`, con revisioni distinte; PDF `relazione-R03` usa i font reali e la
correzione di paginazione. Le prove offscreen non costituiscono prova del frame GPU o del compositore desktop.

## Template

Commit privato pubblicato `3da1098cc8e659a3a9f6b20a7ae90d28fdc39e15`. Include componenti condivisi e
note su File, conversazioni, documenti tecnici, animazioni e differenze tra renderer Qt e browser.
I file preesistenti CLAUDE.md, README.md e docs/dal-template-gtk.md nel template sono stati preservati e
non inclusi nel commit. Manifest applicazione `template-sync-qt_R03.json` e tabelle `_R04.json`, 21+1 mapping.
Quotario è stato confrontato in sola lettura: il template è aggiornato, non si dichiara aggiornato Quotario.

## Richieste tecniche ancora aperte

R215 e R225-R229 restano parziali: algoritmo di assegnazione globale, limiti condizionati e mappa fisica completa
degli ingressi, curve I/V dettagliate di celle/bypass/stringhe, dinamica e clipping degli ottimizzatori,
conversione distinta per singolo inverter e validazione su misure. L'audit chiarisce cosa calcola oggi il
programma e non equivale a dichiarare corretto ogni caso. Due moduli su un ottimizzatore non significano due
MPPT indipendenti; l'ordine della stringa non spegne i moduli successivi a quello ombreggiato.

Per BIM restano interoperabilità nel software destinatario e geometrie curve/non planari o con fori oltre
i casi coperti. Le proprietà IFC non diventano automaticamente famiglie parametriche native Revit.
Restano separate installazione/disinstallazione dei pacchetti, firma, pubblicazione di release e prove GPU native.

## Consegna

I dati finali di commit applicativo, integrazione Windows e pacchetti verificati vengono aggiunti dopo
il completamento delle prove del binario congelato. Le anteprime precedenti restano conservate.
