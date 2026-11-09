# Proprietà, Verifiche e Progetto: esito r13-proprieta

05/11/2026. Codice applicativo: `d8bcc0ee`, più l'allineamento finale delle frecce
numeriche a `field:up/down`, dopo l'unione di Shell, Controlli, Fasi, File e Meridio.
Widgets e nucleo invariati. Nessun push, tag o release.

## Esito

[V] I tre pannelli sono installati nella finestra vera dal registro delle parti,
con la stessa `ProjectSession` delle viste e dei calcoli. Il lanciatore autonomo
non è più l'unico posto in cui funzionano. Le modifiche passano da `session.edit`.

[V] Il porting assegnato è integrato e verificato. La finestra intera non è ancora
indistinguibile dai Widgets: disposizione Shell, pianta, terreno e posizione di
Meridio hanno differenze visibili, elencate sotto. Le foto non certificano la
fluidità al monitor.

Aprire `confronto/r13-proprieta/index.html`: ritagli originali con comandi 100 % e
200 %, percorso sul progetto reale di Rho, schede delle Verifiche e fotogrammi R377.
Le immagini di lavoro e i log restano in `build/quick-foto/r13-proprieta/` e `build/`.

## Cosa è stato portato

| Riferimento Widgets | Risultato Quick e prova |
|---|---|
| `ui/properties.py` | Sito, connessione e obblighi; edifici con tutte le forme di tetto; sottocampi con montaggi, moduli, piano di posa, distanze, passo e azioni; esclusioni e oggetti 3D. Inventario eseguito sui controlli Widgets veri: 130 configurazioni e 1.721 confronti di campi, valori, opzioni, abilitazioni, intervalli, unità e passi. |
| `quantity_field.py` | Espressioni con unità, virgola italiana, conferma con Invio o uscita, Esc, frecce e rotella solo col focus. Una conferma produce una modifica annullabile. Valori non validi lasciano intatto il progetto. |
| `rows.py`, `sections.py`, C3 di `style.py` | Righe e griglie di campi, sezioni apribili, titolo, cornice e piccolo aiuto 16×16. Etichette misurate come QLabel, campi misurati sugli estremi dell'intervallo, margini distinti dei gruppi iniziali e dei normali moduli. |
| `checks_page.py` | Quattro viste, gruppi apribili con conteggio, icone, schede continue, dettagli, Correggi, occhio, tastiera e menu contestuale. Anteprima della correzione, Mantieni/Ripristina e annulla. Filtri per livello, fase e oggetto; titolo e copia. Il messaggio vuoto italiano resta intero anche a testo grande. |
| `status_pill.py`, `marks.py` | CountPill condivisa, colonna degli avvisi dell'albero, simboli dalle forme comuni, stessi risultati pubblicati nell'albero, nella pianta e nel 3D. |
| Albero del progetto | Conteggi, icone colorate, Esclusioni, selezione, avvisi numerati; tasto destro, F2, rinomina, duplicazione, eliminazione e annulla. Varianti e operazioni dei sottocampi mantenute. |
| `guide_card.py` | Riutilizzato `Assistant/GuideCard.qml`, già portato dal ramo Meridio. Aiuto contestuale instradato una volta al servizio condiviso; catalogo dei testi e ripresa del tour verificati. |
| `fades.py` | Veli di 12 px sui bordi che proseguono, con le curve pagina/albero dei Widgets. Collegati a tutti e tre i pannelli. La prova verifica visibilità, posizione durante lo scorrimento e attenuazione dei pixel. |

[V] I risultati delle Verifiche vengono da `checks.gather` e dalle verifiche
dell'impianto. Il controller aggiorna i risultati dopo i calcoli, scarta risposte
obsolete e non inventa esiti per riempire il pannello. Il confronto diretto con
il nucleo è in `test_checks.py`; l'aggancio effettivo è in `test_fidelity.py`.

## Scheda destra e passaggi di fase

[V] Contratto adottato dal registro Shell e verificato nella finestra completa:

- Modellazione usa `PropertiesHost`, sulla selezione comune.
- Impianto, Produzione, Consumi ed Economia ricevono le proprie pagine/editor dai
  rispettivi adattatori. I Loader delle fasi sono conservati e i controller sono
  quelli registrati, non copie create per la prova.
- Relazione entra in Pronto per la consegna; tornando alla fase precedente si
  ripristina la vista delle Verifiche che era attiva.
- Trova il sito apre il dialogo visibile tramite File; Catalogo passa al servizio
  Impianto. Scelta del lato, evidenziazione al passaggio e aiuto sono collegati.

[V] R377: stesso tipo di oggetto, editor conservati; tipo diverso, forma nuova
già costruita sotto la precedente, dissolvenza 180 ms OutCubic come Widgets.
Trenta fotogrammi della finestra completa, D3D11 a scala 2, verificano contenuto
presente e assenza di finestre di primo livello inattese.

## Verifiche e prove ripetibili

Ambiente: Python 3.12, PySide6 6.12, Windows; prove ordinarie offscreen,
catture native Direct3D 11 sul desktop isolato. Nessun mouse o tasto di sistema.

| Controllo | Evidenza |
|---|---|
| Suite del ramo | 56 test, OK con 5 metodi nativi esclusi ed eseguiti separatamente. `python -W default -m unittest discover -s tests/quick/proprieta -t tests`; log `build/proprieta-final-r06.log`. Comprende inventario in sottoprocesso, parità delle modifiche, componenti e finestra completa. Dopo l'ultimo allineamento delle frecce: 4 test pertinenti, OK con un nativo escluso, `properties-arrows-final.log`; matrice nativa rigenerata. |
| Inventario originale | 8 casi parametrizzati, 130 configurazioni, 1.721 campi confrontati. `build/field-inventory-final.log`. Le configurazioni non sono 130 schermate: il confronto esaustivo qui riguarda i controlli e i loro dati. |
| Sistema | 46 test verdi, `build/sistema-final-r03.log`. |
| Compatibilità Quick | 70 test eseguiti in due gruppi: 7 formati verdi, `parity-formats-trace.log`; altri 63 verdi con 7 esclusioni native e 2 fallimenti attesi, `parity-rest-final.log`. I due attesi preesistenti riguardano il vecchio adattatore di riferimento: nome del nuovo edificio e testo dell'annulla della rinomina. La prova dell'albero reale confronta anche annulla e selezione ed è verde. |
| Formati Widgets | 96 test verdi; non sono stati modificati il modello né i file congelati. |
| Aiuto e guida condivisi | 4 test verdi, `build/guide-help-final.log`. |
| Native | Tutti i 5 metodi esclusi dalla suite ordinaria sono stati eseguiti: 4 test componenti/albero verdi in `native-components-r02.log`, 2 test fotografici e di scorrimento verdi in `native-photos-final.log`, un test con 30 fotogrammi verdi in `r377-native-r04.log`. Integrazione completa verde anche in `native-integration-pump.log`. Lo scorrimento della scheda non richiama Python a ogni fotogramma. |
| Percorso comune | 17 passi di `tests/quick/percorsi/proprieta.json` sul progetto reale di Rho. Il confronto dei progetti dopo ciascun passo esclude soltanto `modified`; l'audit JSON è accanto alle foto. |
| Foto | Tre misure: 1366×900, 1600×960, 1920×1080; chiaro/scuro; scale 1 e 2. In più 1366×900 con testo grande a entrambe le scale. Cinque selezioni in ogni configurazione, più righe unite e vuoto delle Verifiche. Metadati registrano renderer, tema e warning. |

[V] La matrice pubblicata contiene 98 coppie di ritagli originali: 70 stati
Quick finali da `matrix-r08`, con riferimenti Widgets da `matrix-r04`. I 140
record sono conservati in `metadata.json`, tutti senza warning. Il percorso è
`pilot-rho-r03`; le prove delle giunzioni sono `cards-r02` e `empty-r03`.
Gli ultimi tre precedono soltanto la sostituzione della freccia numerica.
L'ispezione visiva ha riguardato oggetti, temi, testo grande, righe unite e
transizioni; non equivale a una comparazione automatica pixel per pixel di ogni foto.

[V] Il progetto reale è aperto in memoria; non viene salvato sul file originale.
La coppia con righe di verifica aggiuntive è dichiarata come fixture visiva: serve
a vedere le giunzioni e il bordo inferiore, non è un risultato di calcolo di Rho.

[V] Lint: `python -m ruff check --select F,E9,B .`. Registro sorgenti aggiornato
con `tools/quick_rif_registry.py --refresh`: nessun errore. Nessuna soglia di
confronto dei dati è stata ridotta.

[V] Controllo finale degli artefatti: 260 PNG decodificabili, 253 collegamenti
locali validi; tema, font, misura del testo e selezione uguali nei 70 stati
accoppiati. `tools/quick_rif_registry.py --check` termina con zero errori.

## Difetti riprodotti e correzioni

- Loader vuoti nella prima integrazione: il doppio uso di `source` e
  `sourceComponent` annullava il caricamento. Riprodotto sulla finestra; correzione
  ricevuta da Shell e adattatore temporaneo rimosso.
- Bordo delle righe interrotto: una copertura cancellava i lati alla giunzione.
  Prova rossa con differenza di luminosità 42, poi verde usando il ritaglio della
  forma estesa di `_card_slice`. Nessun contorno accentato aggiuntivo alla selezione.
- Testata sovrapposta: ripresa la disposizione di `TitleTools.plan`, confrontata
  a tre larghezze e due misure del testo. Copia rimane nella prima riga.
- Campi e tendine: la larghezza minima fissa non teneva conto degli estremi dei
  numeri. Misura ora confrontata esattamente con i Widgets. Riferimento aggiuntivo:
  [QAbstractSpinBox, implementazione Qt](https://raw.githubusercontent.com/qt/qtbase/6.10/src/widgets/widgets/qabstractspinbox.cpp),
  verificata contro i controlli installati 6.12; stessa lettura dei limiti, stile locale misurato.
- La prima prova R377 classificava come vuoto un fotogramma con due strati di
  testo grigio a metà dissolvenza. Foto controllata; ora misura il contrasto anche
  dei toni intermedi. Una prova negativa rifiuta schede vuote con soli bordi e
  campi colorati: il controllo conserva il suo scopo.
- Le prove native attendono l'apertura reale dei menu e usano il ciclo eventi Qt.
  Un'attesa `QTest.qWait` si era fermata durante il lavoro 3D; traccia e ripetizione
  conservate. Non viene presentata come diagnosi di un blocco nell'uso normale.

## Differenze rimaste e limiti

1. **Disposizione Shell.** A 1600×960, scala 1, la cattura campione ha Proprietà
   Quick 370×800 e dock Widgets 380×649, comprendente i margini esterni del dock.
   Il titolo/contenuto iniziano circa 8 px più in basso nei Widgets. Cambiano
   spazio visibile e necessità della barra di scorrimento. Le foto conservano
   queste differenze; non sono state deformate per nasconderle. A scala 2 il
   dock Widgets campione è largo 300 px logici contro i 370 di Quick: questo
   cambia anche gli a capo dei campi. Nel testo grande le righe di Prevenzione
   incendi ne mostrano l'effetto. I triangoli delle sezioni, dal controllo
   comune, risultano più sottili di quelli Widgets.
2. **Parti esterne.** Nei percorsi restano il terreno 3D a righe, differenze di
   moduli/prese in pianta e Meridio sovrapposto ad altre zone. Le correzioni sono
   dei rispettivi rami. Il tema è impostato esplicitamente uguale per il confronto:
   alcune configurazioni salvate della Shell avevano ripristinato bronzo/beige.
3. **Controlli condivisi.** `Properties/ScrollEdges.qml` è pronto da promuovere in
   Controls; finché ciò non avviene, la copertura delle altre pagine resta al loro
   proprietario. Segments riceve localmente il tooltip completo, in attesa di
   un campo `model.tip` nel componente comune.
4. **Monitor e carico.** Non verificati puntatore di sistema, presentazione sul
   monitor di Daniel e soglie di fluidità. Le letture dei pixel alterano i tempi;
   la durata della suite non è una misura della velocità del programma.
5. **Fine processo delle prove.** La suite con `-W default` segnala pulizia di
   una cartella temporanea e oggetti non raccolti dal garbage collector in uscita.
   Le prove passano; non è stata attribuita una causa né trasformata questa
   segnalazione in un difetto dell'uso normale.

Nessuna semplificazione funzionale deliberata. I limiti sopra sono dichiarati;
non viene affermata una parità pixel per pixel dell'intera applicazione.
