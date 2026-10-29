# Accumulo e audit catalogo R237-R238, revisione 01

Data: 29/10/2026. Base bf0767b. Stato: implementazione R237 con limiti dichiarati; R238 parziale per la verifica puntuale delle schede, completo per l'audit strutturale dei record distribuiti.

## Accumulo

[V] `StoragePage` prepara una patch senza mutare il progetto. Il controller principale applica la patch tramite `session.edit`, rendendo la scelta annullabile. Campi aggiuntivi nel dizionario economics: `storage_coupling`, `storage_inverter`, `storage_efficiency_pct`. La struttura del progetto resta compatibile. I progetti precedenti, con coupling vuoto, conservano il calcolo storico e le sue stime; il nuovo percorso richiede energia utilizzabile, potenze documentate e rendimento AC esplicito.

[V] Connessione AC con convertitore proprio indipendente dal marchio dell'inverter FV. Connessione DC con associazione esatta a un inverter del progetto. Una corrispondenza di marchio o una frase generica non costituiscono prova. Stati documentato, incompatibile e sconosciuto separati; configurazioni sconosciute non avviano il nuovo calcolo. Rimozione/sostituzione dell'inverter interrompe il calcolo con messaggio di riconnessione.

[V] Controllati quantità intera positiva, quantità documentata, intervallo tensione operativo, limiti corrente e potenza condivisi del convertitore. La tensione nominale non sostituisce quella di esercizio. I limiti assenti restano segnalati; stato di compatibilità del modello non significa verifica completa di ogni limite.

[V] Il bilancio rimane sul bus AC: applica un rendimento di ciclo equivalente una volta, ripartito simmetricamente tra carica e scarica. Non applica nuovamente il rendimento dell'inverter FV. Il rendimento indicato dal progettista compare come input nella provenienza. Le potenze limitate sono calcolate, non presentate come letture dirette della scheda. Il dimensionamento generico conserva il suo modello stimato separato.

Limite: non è una simulazione oraria dei flussi DC e non recupera clipping FV. Non modella cablaggio multiramo, derating termico, protocolli/firmware, backup o servizi di rete. Nel caso MB0 usa conservativamente un ramo (21 kW carica, 26,25 A complessivi) anche con più batterie; la scheda ammette 25 kW con due rami. La limitazione conservativa è mostrata in pagina. Il calcolo non sostituisce il progetto elettrico.

## Fonti effettivamente rilette

[V] Prima controllati reference/catalogs e i nomi dei PDF in Elettrico. Presente la scheda Huawei MB0; la scheda BYD HVM di commessa non è stata usata per estendere compatibilità BCU2.0. Il disco I non è disponibile in questa sessione. La precedente raccolta è descritta in `docs/catalogo/mlpe-e-accumuli.md`, ma non viene trattata come nuova verifica.

- Huawei SUN2000-12/15/17/20/25K-MB0, versione 01-202504, p. 2, PDF locale `C:\Users\Grasso\Elettrico\reference\catalogs\Huawei\inverters\Huawei - SUN2000-12-25K-MB0 - 01-202504 EN.pdf`. Limiti carica/scarica/corrente/tensione del modello SUN2000-20K-MB0 strutturati con provenienza per campo.
- Huawei LUNA2000-5/7/10/12/14/15/17/19/21-S1, versione 01-202509, p. 2 e nota 8. PDF ufficiale scaricato da `https://solar.huawei.com/dam/asset/view/8ab57198f55f4643a1b933163b460d6a.pdf` e archiviato in `C:\Users\Grasso\Elettrico\reference\catalogs\Huawei\batteries\Huawei - LUNA2000-S1 - 01-202509 IT.pdf`. Testo letto e tabella visualizzata: sei configurazioni già presenti in catalogo, energia e potenze, tensioni dipendenti dal numero di fasi, compatibilità MB0 e massimo quattro sistemi. Nessun rendimento ricavato o inventato.

## Audit generale

[V] `catalog.audit.audit_catalogue` legge i file grezzi, quindi include anche record eventualmente scartati dalla normalizzazione. Tutti i 24.262 record: 21.713 moduli, 2.443 inverter, 31 microinverter, 21 ottimizzatori e 54 batterie. Ogni campo ha uno stato; unità e provenienza disponibili sono conservate nel registro JSON compresso. Il CSV offre una riga per record; il JSON di riepilogo riporta i conteggi.

Distinzioni: `provenance_dataset` identifica la provenienza NREL/SAM documentata in ATTRIBUTIONS, non una scheda esatta; `source_declared` indica una fonte dichiarata non riletta; `verified_field` è riservato ai 34 campi con fonte, pagina e data della verifica di questa revisione. `unknown` include null e segnaposto nan. I record CEC inverter restano senza revisione esatta del dataset se non presente: la provenienza generale non colma questo vuoto.

[V] Quattro incoerenze Imp > Isc, tutte moduli CEC:

- LENERGY POWER INC, LP-505-144M-B.
- LENERGY POWER INC, LP-505-144M-W.
- Sonali Energees USA LLC, SS-505-144M-B.
- Sonali Energees USA LLC, SS-505-144M-W.

Valori conservati in attesa della fonte; il catalogo blocca la selezione dei record con incoerenze attraverso `audit_record` (integrazione lotto R236). Gli altri 24.258 record superano questi controlli strutturali, non una verifica completa delle schede. Mancano ancora verifiche puntuali delle fonti, qualificatori, pagine e compatibilità di gran parte del catalogo: R238 non è dichiarato concluso.

## Verifiche eseguite

[V] 8 test nucleo: corrispondenza esatta, quantità/tensione, AC indipendente, limite convertitore condiviso, rendimento obbligatorio, NaN, associazione eliminata, ciclo numerico 2 kWh -> 1,62 kWh con rendimento 81%, provenienza non promossa automaticamente.

[V] 16 test economics preesistenti passano. Prova annuale esplicita LUNA2000-7-S1 + MB0 e sweep generico a sette taglie completati. Due test widget verificano che la bozza non modifica il progetto prima di Applica e che l'ignoto non avvia il calcolo. Ruff sui file del lotto passato.

[V] Immagine offscreen `storage-page-offscreen-R03.png`, pagina larga 480 px, etichette visibili. Le prime due immagini documentano un problema del font nella piattaforma offscreen Windows; R03 carica Segoe UI esplicitamente per la verifica. Non è una prova su schermo reale né della finestra integrata. Undo, traduzioni e integrazione della pagina vengono verificati dalla sessione principale.
