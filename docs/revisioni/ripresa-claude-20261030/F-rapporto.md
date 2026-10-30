# F, rapporto: R267, scelta automatica degli inverter con SolarEdge e ABB/FIMER (30/10/2026)

Agente «Opus F». Cartella `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10`, ramo `integra-kimi-9-10`, nessun commit.
I miei file non erano toccati dalla tranche R07 (`git diff 23bd7a9` vuoto su sizing, plant, optimizers, stringing,
system, components, sizing_job prima del mio lavoro): tutte le differenze su questi file sono mie.

## 1. Che cosa ho rivisto

- `src/meridiana/energy/sizing.py` (tutto, 157 righe di partenza): ordine dei candidati, limiti sul numero di unità,
  bilancio di ricerca condiviso, filtro dei record, messaggi.
- `src/meridiana/energy/plant.py`: `_optimized_sizes`, `_propose_optimized`, `_optimizer_group_choices`,
  `_search_assignment` (domini, potatura, foglie), `_optimizer_entry_variants`, `_propose`, `_check`,
  `_check_optimized`, `_optimized_unit_checks`.
- `src/meridiana/energy/optimizers.py`: `fixed_voltage`, `rules_for`, tabelle RES/COM, `string_plan`, `unit_checks`,
  `suggest`, `choice`.
- `src/meridiana/energy/stringing.py` (`series_range`, `vmp_at`, `ku`, `strings_allowed`, `SearchBudget`),
  `components.py` (`InverterSpec` limiti di corrente), `ui/sizing_job.py`, e in sola lettura `ui/window.py`
  righe 3900-3980 (`_size_inverters`, `_sizing_done`) e 4208-4250 (`_string_proposal_done`).
- Catalogo (sola lettura): 2443 inverter; marche «SolarEdge» (13 curati), «SolarEdge Technologies Ltd» (69 CEC),
  «ABB» (136 CEC), «FIMER» (4 curati); 12 ottimizzatori SolarEdge.
- Schede in locale (prima di internet): `C:\Users\Grasso\Elettrico\reference\catalogs\SolarEdge\inverters\` e
  `...\optimizers\`, lette con `pdftotext`: DS-000297-EU (Synergy), DS-000105-IT (S1000/S1200), DS-000205-EU
  (S1400), DS-000012-ENG (P800p-P1100), DS-000091-IT (S440-S650B). Nessuna scheda FIMER/ABB inverter in locale
  (i record FIMER citano `fimer.com`); unico dato preso dal web: il passaggio del ramo inverter ABB a FIMER
  (comunicato FIMER del 02/03/2020, `https://fimer.com/fimer-becomes-4th-largest-solar-inverter-suppliers-world`).

## 2. Riproduzione e cause (prima delle correzioni)

Script di prova (fuori dal repo, nello scratchpad):
`C:\Users\Grasso\AppData\Local\Temp\claude\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55\scratchpad\bench.py`
(sei impianti x sei marche, moduli reali del catalogo; `bench-before.txt` e `bench-after.txt` accanto).
Il «prima» gira su una copia dei sorgenti con i tre file di `HEAD` (`scratchpad\oldsrc`).

| Marca | Caso | Prima | Causa esatta [V] |
|---|---|---|---|
| ABB | tutti | «No inverter with a nominal AC power and a complete MPPT datasheet» | i 136 record «ABB» sono la lista CEC (USA, reti 208/240/277/480/800 V): manca `mppt_count` in 136 su 136, mancano le correnti per ingresso; il messaggio non lo diceva e non indicava FIMER (4 modelli curati completi) |
| SolarEdge Technologies Ltd | tutti | stesso messaggio | 69 record CEC USA senza `mppt_count`; non riconosciuti come tensione fissa (il nome non è «solaredge»); la marca curata «SolarEdge» è un'altra voce della lista |
| SolarEdge | 100 x 495 W (49,5 kWp) | 51,9 s, «search limit reached», nessuna scelta | `_optimized_sizes` divide in stringhe uguali (34/34/32) e una stringa sola su un'unità Synergy supera i 15 750 W di una stringa sola; la ricerca esaustiva provava lunghezze fino a 60 moduli (29 700 W, mai valide) e le varianti con più moduli singoli, e controllava la potenza solo alle foglie: 200 000 passi bruciati |
| SolarEdge | 60 E + 44 O x 495 W | 23,5 s, «search limit reached» | come sopra, più: la famiglia S1000 non può fare la falda ovest (44 moduli: né 1 stringa ≤ 37, né 2 ≥ 27) e consumava tutto il bilancio prima di provare S1400 |
| SolarEdge | 600 x 620 W (372 kWp) | «search limit reached» dopo 1 candidato | il primo candidato (1 x SE100K, 175 kW CC al massimo) è impossibile per potenza CC ma la ricerca delle stringhe consumava il bilancio **condiviso** di tutta la scelta; inoltre con il 620 W l'unico ottimizzatore che lo prende senza difetti è l'S1400, la cui avvertenza fissa sui fusibili («warn») rendeva ogni stringa gialla e quindi mai accettabile |
| SolarEdge | 3 falde 200+150+130 x 495 W | «search limit reached» | stesso bilancio condiviso |
| FIMER | 14 x 450 W, e 10+8 su due falde | «No complete string proposal was found ...» senza dire perché | impossibile davvero: PVS-10/20-TL vogliono 16-25 moduli in serie, PVS-50/100-TL 17-23; la falda ha 14 (o 10 e 8) moduli |
| FIMER | 3 falde | «search limit reached» | bilancio condiviso |

Difetti trovati leggendo il codice, oltre a quelli di R267:

- **D4, potenza CC per unità Synergy non verificata** [V]: DS-000297-EU p. 1 stampa «Maximum DC Power (Module STC)
  Inverter / Synergy Unit» (SE50K 87 500 / 43 750 W; SE66.6K 116 550 / 58 275; SE90K 157 500 / 52 500; SE100K
  175 000 / 58 300). Meridiana controllava solo il totale: 49,5 kWp tutti su una unità SE25K di un SE50K risultavano
  verdi (lo ha prodotto la ricerca alla prima prova dopo la potatura).
- **D5, più di un modulo singolo nelle stringhe di ottimizzatori doppi** [V]: DS-000105-IT p. 3 nota 2, DS-000205-EU
  nota 9, DS-000012-ENG nota 6: un ottimizzatore può avere un modulo solo se tutta la stringa è 1:1 oppure se è
  l'unico. `_optimizer_group_choices` proponeva gruppi con 2 o più singoli e nessun controllo li segnalava (anche a
  mano).

## 3. Correzioni (tutte con prova)

1. **Bilancio per candidato** (`sizing.py`, `CANDIDATE_STATES = 20000`): ogni combinazione ha la sua quota del
   bilancio globale (200 000); se non si decide, è «non decisa» (mai «impossibile») e si passa alla successiva. Se
   una successiva è valida, il risultato la applica e lo dice in `Result.notes` («N combinazioni prima in classifica
   non decise: ...»); se nessuna è valida e qualcuna non è decisa, `search_complete=False` e il motivo dice che non è
   una prova di impossibilità. Annullamento invariato (la quota usa lo stesso `cancelled`).
   Prova: `calcoli.test_sizing.SharedSearch.test_an_undecided_combination_does_not_use_up_the_others_search`.
2. **Potenza CC massima come limite certo** (`sizing._dc_capacity`, `_unit_bounds`): per gli inverter a tensione fissa
   con `dc_power_max_w` stampato, le combinazioni con Σ count x P_dc,max < P_STC sono scartate senza ricerca (il
   controllo `opt_dc_max` fallirebbe comunque) e il numero minimo di inverter è ceil(P_STC / max P_dc,max).
   Prova: `test_solaredge_plant_of_hundreds_of_kw_skips_combinations_beyond_the_dc_maximum`.
3. **Vincoli statici prima della ricerca** (`sizing._static`): per ogni modello e ogni falda (gruppi dello stesso
   modulo e piano insieme, come li unisce la proposta) si calcola senza ricerca se la falda può avere almeno una
   stringa: finestra MPPT e tensione massima (`series_range`), corrente di un ingresso (`strings_allowed`),
   ottimizzatori SolarEdge che prendono il modulo e il minimo di ottimizzatori/moduli per stringa. Una falda che
   nessun modello può servire dà subito il motivo; i modelli che non servono nessuna falda escono; il numero massimo
   di inverter scende a moduli // stringa più corta. Prove: `test_a_plane_too_small_for_any_model_is_said_at_once`,
   `test_fimer_residential_says_the_series_length_it_needs`,
   `Impossible.test_no_valid_combination_leaves_the_choice_unchanged_and_says_why` (esistente, ancora verde).
4. **Messaggi con la causa e le alternative** (`_unusable_reason`, `_no_choice`, `alternatives`): campi mancanti con
   il numero di record e un esempio, origine CEC e mercato USA con le tensioni di rete, «Meridiana non inventa i dati
   mancanti»; per ogni modello (raggruppati per causa uguale) il limite che lo ferma con i numeri; poi le marche del
   catalogo che possono dimensionare: stessa azienda con altro nome («SolarEdge» per «SolarEdge Technologies Ltd») e
   successore documentato (FIMER per ABB, con fonte). Prove: `test_abb_records_of_the_cec_say_what_is_missing_and_where_to_go`,
   `test_solaredge_records_of_the_cec_point_to_the_curated_ones`.
5. **Potatura della ricerca esaustiva** (`plant._search_assignment`): lunghezze delle stringhe di ottimizzatori
   limitate a floor(max(P_one, P_many, P_cont) / P_STC,modulo) (sopra nessun numero di stringhe le rende valide;
   per i residenziali con P_AC unità > P_cont il tetto è P_cont, oltre il quale `string_plan` avverte); potenza per
   unità Synergy (D4) come vincolo di ramo; condizione necessaria esatta: il totale di ogni falda deve essere somma
   di lunghezze ammesse (`_representable`, programmazione dinamica), altrimenti la famiglia è impossibile senza
   cercare. Prove: `test_solaredge_commercial_roof_is_found_without_exhausting_the_search`,
   `test_solaredge_east_west_roof_needs_the_s1400_and_says_its_condition`,
   `TheProposal.test_a_commercial_roof_on_a_synergy_inverter_is_found_quickly_within_each_unit`,
   `TheProposal.test_a_plane_that_no_string_length_sums_to_is_rejected_without_a_search`.
6. **S1400: la condizione d'ordine non è un difetto della stringa** (`plant.CONDITIONS`, `acceptable`,
   `conditions_of`): l'avvertenza «S1400: inverter senza fusibili CC» (DS-000205-EU p. 2 nota 4) resta gialla nella
   UI, ma una proposta automatica può usarla; la scelta la riporta in `Result.notes` con la fonte. Ogni altra
   avvertenza (clipping Imp, potenza oltre il continuo, falde diverse, S1200 a 850 V) continua a escludere.
   Prova: `TheProposal.test_the_s1400_fuse_condition_is_acceptable_and_a_loss_warning_is_not`.
   **Decisione da confermare con Daniel** (vedi 7).
7. **D4** (`optimizers.FixedVoltage.p_dc_max_unit`, `SYNERGY_UNIT_DC`, controllo `opt_unit_dc_max` in `unit_checks`):
   valori letti dalla scheda, non divisi (SE100K 58 300 W, non 175 000/3); un record con `dc_power_max_unit_w` ha la
   precedenza. Prove: `TheInverter.test_a_synergy_unit_has_its_own_dc_maximum_as_printed`,
   `TheInverter.test_a_synergy_unit_above_its_dc_maximum_fails_even_within_the_inverters`.
8. **D5** (`optimizers.string_plan`, controllo `opt_singles`, fail; `plant._optimizer_group_choices` non genera più
   quelle varianti). Prova: `TheProposal.test_one_single_module_per_string_of_two_module_optimizers_or_all`.

Le prove nuove falliscono sul codice di partenza: 6 su 8 di `SolarEdgeAndAbb`/`SharedSearch` falliscono con i tre file
di `HEAD` (le 2 che passano: residenziale SolarEdge e FIMER commerciale/grande, che già funzionavano) [V, eseguito
con `scratchpad\oldsrc`].

## 4. Tre casi (e due in più) calcolati a mano accanto al programma

Condizioni del programma senza anno calcolato: T_min = -10 °C (Voc), cella 60 °C (Vmp minima), cella 20 °C (Vmp
massima) [scelte PVsyst di Meridiana, `plant.DESIGN_*`]. Formule: K_U = 1 + β_Voc/100 x (T_min - 25);
N_max = min(floor(U_max / (K_U Voc)), floor(U_MPPT,max / Vmp(20 °C))); N_min = ceil(U_MPPT,min / Vmp(60 °C)).
Vmp(T) del programma = modello a un diodo (pvlib); a mano ho usato la stima lineare Vmp x (1 + β_Voc/100 x (T - 25))
come controllo indipendente: dà gli stessi interi.

**A. FIMER, 100 x LONGi LR7-54HVH-495M (49,5 kWp), PVS-50-TL** (dati: Voc 40,64 V, Vmp 33,62 V, Isc 15,43 A,
Imp 14,73 A, β -0,20 %/K; PVS-50-TL MPPT 480-800 V, 1000 V, 3 MPPT, 36 A / 55 A per MPPT, record curato FIMER Rev E)

| Grandezza | A mano | Programma |
|---|---|---|
| K_U, Voc a -10 °C | 1 + 0,002 x 35 = 1,07; 43,48 V | 1,07; 43,48 V |
| N_max | floor(1000/43,48) = 22; floor(800/33,95) = 23 → 22 | 22 |
| Vmp a 60 °C | lineare 31,27 V | 30,79 V (un diodo) |
| N_min | ceil(480/31,27) = 16; ceil(480/30,79) = 16 | 16 |
| Stringa scelta 20 moduli | Uoc 20 x 43,48 = 869,7 V ≤ 1000; Vmp 20 x 30,79 = 615,8 V ≥ 480; 20 x 34,27 = 685,5 V ≤ 800 | 869,7 / 615,8 / 685,5 V |
| 2 stringhe su un MPPT | Imp 2 x 14,73 = 29,5 A ≤ 36; 1,25 x Isc x 2 = 38,6 A ≤ 55 | ammesse 2 |
| CC/CA | 49,5 / 50 = 0,99 | 0,99 |

**B. SolarEdge, 100 x LR7-54HVH-495M, SE50K + S1000 (2 moduli)** (DS-000297-EU p. 1; DS-000105-IT p. 3, colonna
SE25K: 14-30 ottimizzatori, 27-60 moduli, 15 750 W con 1 stringa, 18 500 W con 2 o più, continua 13 500 W)

| Grandezza | A mano | Programma |
|---|---|---|
| Modulo sull'S1000 | 2 x 495 = 990 ≤ 1100 W; 2 x 43,48 = 87,0 ≤ 125 V; Isc 15,43 ≤ 20 A; Imp 14,73 ≤ 15 A | tutti ok |
| Stringhe | 37 (19 ott., 18 315 W), 36 (18 ott., 17 820 W) su unità 1; 27 (14 ott.: 13 doppi + 1 singolo, 13 365 W) su unità 2 | uguali |
| Limiti | 2 stringhe su unità 1 → 18 500 W: 18 315 ≤ 18 500 ok; 1 stringa su unità 2 → 15 750: 13 365 ok | ok |
| Differenza ottimizzatori unità 1 | 19 - 18 = 1 ≤ 5 | ok |
| CC per unità (nuovo) | 36 135 ≤ 43 750; 13 365 ≤ 43 750 W | ok |
| CC inverter | 49 500 ≤ 87 500 W; CC/CA 0,99 | ok, 0,99 |
| Perché non 34/34/32 | 32 x 495 = 15 840 > 15 750 da sola su un'unità | era la proposta golosa respinta |

**C. SolarEdge, 600 x JA Solar JAM66D45-620/LB (372 kWp), 3 x SE100K + S1400 (2 moduli)** (Voc 48,5 V, Isc 16,13 A,
Imp 15,42 A, β -0,25 %/K; DS-000205-EU, colonna SE33.3K: 14-30 ott., 27-60 moduli, 20 250 W con 1 stringa, 28 000 W
con 2 o più, continua 18 000 W)

| Grandezza | A mano | Programma |
|---|---|---|
| Numero minimo di inverter | ceil(372 000 / 175 000) = 3 | 3 (prima: 1 x SE100K provato e bilancio esaurito) |
| Perché S1400 | S1000: 2 x 620 = 1240 > 1100 W; S1200: Imp 15,42 > 15 A (clipping, avvertenza); residenziali e P: Isc 16,13 > 15 / 14,1 A | S1400 |
| Modulo sull'S1400 | 1240 ≤ 1400 W; 2 x 48,5 x 1,0875 = 105,5 ≤ 125 V; 16,13 ≤ 20 A | ok |
| Stringhe | 18 stringhe da 32 (16 ott., 19 840 W) e 34 (17 ott., 21 080 W), 2 per unità | uguali |
| Limiti | 21 080 ≤ 28 000 (2 stringhe); oltre la continua 18 000: tagliata ai picchi come la tabella ammette (info) | ok |
| CC per unità | 2 x 21 080 = 42 160 ≤ 58 300 W | ok |
| CC/CA | 372 / 300 = 1,24 | 1,24 |
| Condizione | S1400 solo su inverter senza fusibili CC integrati (DS-000205-EU p. 2 nota 4) | in `Result.notes` |

**D. SolarEdge, 60 E + 44 O x LR7-54HVH-495M: SE50K + S1400** [V a mano]: con S1000 la falda ovest è impossibile
(44 moduli: una stringa ≤ floor(18 500/495) = 37, due stringhe ≥ 2 x 27 = 54). Con S1400: unità 1 = O 44 (22 ott.,
21 780 W) + E 33 (17 ott., 16 335 W): 2 stringhe → 28 000 W, differenza 5 ottimizzatori ≤ 5, CC 38 115 ≤ 43 750 W;
unità 2 = E 27 (14 ott., 13 365 ≤ 20 250 W). Il programma trova esattamente questa (0,2 s; prima 23,5 s senza esito).

**E. FIMER, 14 x JAM54S40-450/LR (6,3 kWp)**: Vmp(60 °C) 29,58 V (lineare 32,82 x 0,9125 = 29,95 V); PVS-10-TL
N_min = ceil(460/29,58) = 16 > 14 → impossibile con qualunque quantità; N_max = min(floor(1100/42,74) = 25,
floor(850/33,20) = 25) = 25. Il messaggio dice «PVS-10-TL, PVS-20-TL: Field 1: 14 modules, a string needs 16 to 25 in
series (MPPT from 460 V, module Vmp 29.6 V at 60 °C of cell)» e lo stesso per PVS-50/100-TL (17-23).

## 5. Tempi (prima/dopo, stessa macchina, `bench.py`)

Secondi per una scelta completa; «nodi» = passi di ricerca. Prima = tre file di `HEAD`; dopo = questo lavoro.
Misure con altri agenti attivi sulla macchina (ordine di grandezza, non cronometro fine). Il primo caso di ogni
processo include il caricamento di pvlib (~0,4-2 s).

| Marca | Caso | Prima | Dopo |
|---|---|---|---|
| SolarEdge | 14 x 450 W | 0,41 s, SE6000H | 0,37 s, SE6000H (S500B, 2 x 7) |
| SolarEdge | E/O 10+8 x 450 W | 0,00 s, SE8000H HH | 0,01 s, uguale |
| SolarEdge | 100 x 495 W | **51,9 s, nessuna scelta** (200 000 nodi) | **0,01 s**, SE50K (71 nodi) |
| SolarEdge | E/O 60+44 x 495 W | **23,5 s, nessuna scelta** | **0,18 s**, SE50K + S1400 |
| SolarEdge | 600 x 620 W | 0,38 s, nessuna scelta | 0,02 s, 3 x SE100K + S1400 |
| SolarEdge | 3 falde 200+150+130 | 1,9 s, nessuna scelta | 1,3 s, 2 x SE90K (+ nota: 2 x SE100K non deciso) |
| FIMER | 14 x 450 W | 2,4 s, motivo generico | 1,8 s, motivo per modello (impossibile davvero) |
| FIMER | E/O 10+8 | 0,12 s, motivo generico | 0,04 s, motivo per modello |
| FIMER | 100 x 495 / E/O 60+44 / 600 x 620 | 0,11 / 0,06 / 0,35 s | 0,08 / 0,05 / 0,23 s, stesse scelte |
| FIMER | 3 falde | **8,7 s, nessuna scelta** | 3,6 s, 1 x PVS-20-TL + 2 x PVS-100-TL |
| ABB | tutti | 0,00 s, motivo generico | 0,01 s, motivo con campi, CEC/USA, FIMER |
| Huawei | 3 falde | **4,2 s, nessuna scelta** | 0,66 s, 1 x SUN2000-100KTL-M2 (+ nota: 1 combinazione non decisa) |
| Huawei, SMA, Sungrow | gli altri 17 casi | 0,03-0,40 s | 0,04-0,36 s, stesse scelte |

Annullabilità: invariata e verificata da `Impossible.test_search_can_be_cancelled_without_applying_a_partial_choice`
e dalle prove della finestra `finestra.test_sizing_async` (annullamento e risultato vecchio mai applicati); la quota
per candidato usa la stessa funzione `cancelled`.

Osservazione fuori compito [V, comportamento già presente prima]: con Huawei, 14 x 450 W (6,3 kWp) la scelta è
1 x SUN2000-20K-MB0 (CC/CA 0,32): i modelli Huawei più piccoli del catalogo non riescono a stringare quella falda o
non hanno i dati; non indagato oltre.

## 6. Difetti sospetti non confermati

- **Minimo di moduli con S1000/S1200/S1400 in 1:1** [I]: la tabella DS-000105-IT p. 3 dà «Lunghezza minima: 14
  ottimizzatori / 27 moduli»; Meridiana applica 27 moduli anche alle stringhe tutte 1:1 (nota 2). Leggo il 27 come
  14 ottimizzatori doppi meno un singolo, quindi per una stringa 1:1 basterebbero 14 moduli; ma la scheda non lo
  dice esplicitamente. Non ho cambiato nulla: da chiedere a SolarEdge (o decidere Daniel).
- **3 falde 200+150+130 x 495 W, 2 x SE100K + S1000** [V che non si decide, I che esiste]: a mano trovo una
  configurazione valida (unità con 3 stringhe da 33-34 della falda grande; la falda da 130 in 4 stringhe da 32-33
  insieme a stringhe da 30 della falda da 150), ma la ricerca esaustiva non la trova nemmeno con 400 000 passi
  (35 s). Ora il programma lo dice («1 combination ranked before this one could not be decided: 2 x SE100K») e
  applica la successiva valida (2 x SE90K). La ricerca esaustiva per le unità Synergy multi-falda andrebbe
  riscritta con vincoli per unità (numero di stringhe per unità noto prima delle foglie): lavoro più grande, non
  fatto.
- La proposta automatica non mette mai falde diverse nella stessa stringa (scelta di progetto esistente, anche per
  SolarEdge che lo ammette con perdite): alcuni «impossibile» residenziali (FIMER 10+8) sarebbero possibili con una
  stringa a cavallo di due falde. Il messaggio dice «different planes never in one string».
- `test_a_synergy_inverter_spreads_alike_strings_over_its_units` (esistente) usa 90 kWp su un SE50K (87,5 kW): il
  totale fallisce già prima del mio lavoro e ora fallisce anche il limite per unità; la prova controlla solo lo
  stato delle stringhe e resta verde. Non l'ho toccata.

## 7. Modifiche richieste a file non miei (`src/meridiana/ui/window.py`, `po/it.po`)

Decisione da confermare con Daniel: accettare l'S1400 nelle proposte automatiche con la condizione detta (punto 3.6).
Se Daniel non vuole, basta togliere `"opt_fuses"` da `plant.CONDITIONS`.

1. `window.py`, `_sizing_done` (riga ~3976), dopo `self.edit(...)`: dire le note. Sostituire
   ```python
           self.tell(_("Inverters sized in Plant: {what}, DC/AC {r}. All {n} modules have a valid string. "
                       "Review Plant > Active inverters and Strings. Choice: {criterion}.").format(
                           what=what, r=number(result.ratio, 2), n=modules, criterion=result.criterion))
   ```
   con
   ```python
           message = _("Inverters sized in Plant: {what}, DC/AC {r}. All {n} modules have a valid string. "
                       "Review Plant > Active inverters and Strings. Choice: {criterion}.").format(
                           what=what, r=number(result.ratio, 2), n=modules, criterion=result.criterion)
           if result.notes:
               message += " " + _("Note: {notes}").format(notes="; ".join(result.notes))
           self.tell(message, 30.0)
   ```
2. `window.py`, `_sizing_done` (riga ~3970): il motivo ora ha più righe («Why:» e un punto per modello); la barra di
   stato ne mostra una. Proposta:
   ```python
           if not result.ok or not result.search_complete:
               first, _sep, rest = result.reason.partition("\n")
               self.tell(first, 30.0)
               if rest:
                   QMessageBox.information(self, _("Size the inverter by itself"), result.reason)
               return
   ```
   (oppure il pannello che R268 sta rifacendo; il testo completo è in `result.reason`).
3. `window.py`, `_string_proposal_done` riga 4223: `failed = [s.why for s in result.strings if s.state != "ok"]`
   → `failed = [s.why for s in result.strings if not plant_model.acceptable(s)]`, altrimenti «Proponi le stringhe»
   rifiuta le stringhe S1400 che la scelta automatica accetta.
4. Per R268 (lista marche, riga ~3922): `catalog.brands("inverters")` elenca anche «ABB» e «SolarEdge Technologies
   Ltd», i cui record (CEC USA) non hanno mai i dati per dimensionare. Suggerimento: segnare o mettere in fondo le
   marche senza alcun record dimensionabile, con `sizing.missing_fields(rec)` vuoto come criterio; e/o mostrare
   «SolarEdge» e «SolarEdge Technologies Ltd» come una voce. La chiamata `sizing.choose` resta uguale: con i record
   della sola marca scelta, il messaggio ora indica da sé le alternative (`sizing.alternatives(maker)`).

## 8. msgid nuovi o cambiati e traduzioni proposte

sizing.py:
- "nominal AC power" → «potenza CA nominale»
- "number of MPPT" → «numero di MPPT»
- "MPPT minimum voltage" → «tensione minima MPPT»
- "MPPT maximum voltage" → «tensione massima MPPT»
- "FIMER took over ABB's solar inverter business on 2 March 2020" → «FIMER ha rilevato il ramo inverter fotovoltaici di ABB il 2 marzo 2020»
- ngettext "{name}: {n} model with complete data, {lo} to {hi} kW" / "{name}: {n} models with complete data, {lo} to {hi} kW" → «{name}: {n} modello con dati completi, da {lo} a {hi} kW» / «{name}: {n} modelli con dati completi, da {lo} a {hi} kW»
- ngettext "{field} missing in {n} record" / "{field} missing in {n} records" → «{field} mancante in {n} record» / «{field} mancante in {n} record»
- "None of the {n} inverters of {maker} in the catalogue can be sized: {missing} (for example {model}). Meridiana does not invent missing datasheet values." → «Nessuno dei {n} inverter di {maker} nel catalogo si può dimensionare: {missing} (per esempio {model}). Meridiana non inventa i dati che mancano nelle schede.»
- "These records come from the CEC list of the California Energy Commission, which gives no MPPT count and no current per input" → «Questi record vengono dalla lista CEC della California Energy Commission, che non dà né il numero di MPPT né la corrente per ingresso»
- ", for the US market (grid {volts} V), not for a 230/400 V grid" → «, per il mercato USA (rete {volts} V), non per una rete 230/400 V»
- "Sizable instead: {brands}." → «Si possono dimensionare invece: {brands}.»
- "no SolarEdge optimizer of the catalogue takes {module} (Pmax {p} W, Voc {voc} V, Isc {isc} A): {why}" → «nessun ottimizzatore SolarEdge del catalogo accetta {module} (Pmax {p} W, Voc {voc} V, Isc {isc} A): {why}»
- "{group}: {n} modules on one plane, a string needs at least {lo} even with {opt} ({source})" → «{group}: {n} moduli su una falda, una stringa ne vuole almeno {lo} anche con {opt} ({source})»
- "no series length of {module} fits the MPPT window {vmin} to {vmax} V within {vdc} V (cell from {cold} to {hot} °C, lowest {tmin} °C)" → «nessun numero di {module} in serie sta nella finestra MPPT da {vmin} a {vmax} V entro {vdc} V (cella da {cold} a {hot} °C, minima {tmin} °C)»
- "{group}: {n} modules, a string needs {lo} to {hi} in series (MPPT from {vmin} V, module Vmp {vmp} V at {hot} °C of cell)" → «{group}: {n} moduli, una stringa ne vuole da {lo} a {hi} in serie (MPPT da {vmin} V, Vmp del modulo {vmp} V con la cella a {hot} °C)»
- "{module}: no input takes even one string: the input current limits ({limits}) are below the module's Imp {imp} A or Isc x 1.25 = {i} A" → «{module}: nessun ingresso prende nemmeno una stringa: i limiti di corrente degli ingressi ({limits}) sono sotto la Imp del modulo {imp} A o Isc x 1,25 = {i} A»
- "string" → «stringa»
- ngettext "{n} module in no string" / "{n} modules in no string" → «{n} modulo in nessuna stringa» / «{n} moduli in nessuna stringa»
- ngettext "{n} combination could not be decided within {k} search steps: {which}." / "{n} combinations could not be decided within {k} search steps each: {which}." → «{n} combinazione non si è potuta decidere entro {k} passi di ricerca: {which}.» / «{n} combinazioni non si sono potute decidere entro {k} passi di ricerca ciascuna: {which}.»
- "Why:" → «Perché:»
- ngettext "and {n} other" / "and {n} others" → «e {n} altro» / «e altri {n}»
- ngettext "• and {n} more" / "• and {n} more" → «• e {n} altro» / «• e altri {n}»
- "Other names in the catalogue: {brands}." → «Altri nomi nel catalogo: {brands}.»
- "No complete string proposal is possible with these inverters: some modules cannot be strung by any of them, whatever their quantity." → «Con questi inverter non è possibile una proposta completa di stringhe: alcuni moduli non possono andare in stringa su nessuno di essi, qualunque sia la quantità.»
- ngettext "{n} combination ranked before this one could not be decided within the search limit: {which}" / "{n} combinations ranked before this one could not be decided within the search limit: {which}" → «{n} combinazione prima di questa in classifica non si è potuta decidere entro il limite di ricerca: {which}» / «{n} combinazioni prima di questa in classifica non si sono potute decidere entro il limite di ricerca: {which}»
- "No valid combination was found among those decided, and not every combination could be decided: this is not a proof that none exists." → «Nessuna combinazione valida tra quelle decise, e non tutte si sono potute decidere: non è la prova che non ne esista una.»
- Già usate ma assenti in `po/it.po`: "No inverter with a nominal AC power and a complete MPPT datasheet is available." → «Nessun inverter con potenza CA nominale e scheda MPPT completa disponibile.»

optimizers.py:
- "{name}: DC power within the Synergy unit's maximum" → «{name}: potenza CC entro il massimo dell'unità Synergy»
- "At most one optimizer with a single module in the string" → «Al più un ottimizzatore con un solo modulo nella stringa»
- "{n} optimizers with a single module: either one, or all of them" → «{n} ottimizzatori con un solo modulo: o uno, o tutti»

window.py (se si applica il punto 7.1): "Note: {notes}" → «Nota: {notes}».

## 9. Prove eseguite

Ambiente: Git Bash, `PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen PYTHONPATH="tests;src"`, PATH con PySide6 davanti,
`C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`.

- `python -m unittest calcoli.test_sizing calcoli.test_optimizers calcoli.test_global_stringing calcoli.test_optimizer_partitions calcoli.test_stringing calcoli.test_input_topology calcoli.test_inverter_register nucleo.test_string_paths` → 165 OK.
- `python -m unittest discover -s tests/calcoli -t tests` → 291 OK (60 s).
- `python -m unittest widget.test_optimizer_groups widget.test_string_list widget.test_report finestra.test_sizing_async finestra.test_string_proposal_async formati.test_project_files nucleo.test_catalog nucleo.test_manual` → 149 OK (256 s; la riga «Qt Quick has no RHI here» è un messaggio del render software, non un errore).
- `python -m ruff check --select F,E9,B src/meridiana/energy/sizing.py src/meridiana/energy/optimizers.py src/meridiana/energy/plant.py tests/calcoli/test_sizing.py tests/calcoli/test_optimizers.py` → All checks passed.
- Prove nuove contro il codice di partenza (copia `scratchpad\oldsrc`): 6 su 8 falliscono come atteso.

## 10. Limiti e cose non verificate

- Nessuna prova sullo schermo né nella finestra (`window.py` non è mio): il testo multiriga del motivo nella barra di
  stato va sistemato (punto 7.2).
- Schede FIMER non in archivio locale: ho usato i record curati come sono (fonte `fimer.com`, revisioni nel record),
  senza rileggerle. Non scaricate: da fare con la skill `archivi-tecnici` se servono citazioni nella relazione.
- Le marche «ABB» e «SolarEdge Technologies Ltd» restano non dimensionabili: i loro record CEC non hanno MPPT né
  correnti per ingresso e sono per reti USA. Non ho aggiunto dati.
- La ricerca esaustiva resta debole sugli impianti Synergy con più falde (vedi 6); ora lo dice invece di fallire in
  silenzio. Tempi misurati con altri agenti al lavoro sulla stessa macchina.
- Non ho verificato la regola «S1400 senza fusibili» sul codice d'ordine degli SE100K italiani (part number
  `SE-TRI-RW00IBNM4/IBNQ4` di DS-000297-EU non è nella lista A4...Z4 della nota, ma la nota parla di fusibili 25/30 A
  integrati: lo dice la condizione, non lo deduco).
