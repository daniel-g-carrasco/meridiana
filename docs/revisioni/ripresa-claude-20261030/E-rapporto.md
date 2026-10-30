# Rapporto E: R266 (Production bloccata) e revisione del lotto E (R243-R247, R255, R256)

Opus E, 30/10/2026. Cartella `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10`, nessun commit. Prove e script di
misura nello scratchpad della sessione:
`C:\Users\Grasso\AppData\Local\Temp\claude\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55\scratchpad\r266\`
(`repro.py`, `compare.py`, log `before-2016.log`, `before-2016-profile.log`, `compare-2016.log`, `after-scaling.log`,
`compare-47-chimney.log`, copia della rete prima della modifica `electrical_network_before.py`).

## 1. Che cosa ho rivisto

- `src/meridiana/energy/electrical_network.py` (tutto, `solve` riga per riga), `pipeline.py` (diff da 23bd7a9 e passo
  della rete), `simulate.with_network`, `electrical.py` (curve, serie, parallelo, MPP), `calculation_basis.py`.
- `src/meridiana/ui/energy_pages.py` (diff: `FittedFlow`, riga del calcolo, `set_stale`), `plant_page.py` (diff:
  riepilogo inverter, `StringSectionDelegate`, `row-pills`), `charts.py` (diff colonne impilate), `status_pill.py`,
  `waiting.py` (Progress), `phases.py` (diff), `jobs.py` (nessuna modifica R07, nulla da dire).
- In `window.py` (solo lettura): `EnergyJob`, `_compute_energy`, `_computing`, `_energy_step`, `_cancel_pvgis`,
  `_energy_done`, `_show_energy_forms`, `_show_stale`, `_layout_done`, `_switch_variant`, `_sizing_done`,
  `_string_proposal_done`, `_strings_clear`; `session.py` (`energy_done`, `energy_outdated`, `take`).
- Le tre foto di Daniel (tutte delle 23:39 del 29/10): è la R06 installata sul laptop (la R07 non è installata).

## 2. R266: diagnosi

### Che cosa mostrano le foto [V, lette]
2016 moduli, 907,20 kWp, 84 stringhe su 42 ingressi, 5 x Huawei SUN2000-100KTL-M2 (500 kW AC), un edificio, un
sottocampo, 0 esclusioni, sito 45,4642 / 9,19. Barra «PVGIS: the electrical network (3 of 4)» al 50 % con Cancel; la
scheda Production ha il segno «·» di valori da aggiornare (anche «Checks ·»).

### La scritta «PVGIS» [V, codice]
È solo il prefisso della barra: `window._computing` apre `pvgis_progress` con `_("PVGIS: {what}")` ogni volta che il
calcolo può usare la rete (`fetch`), e `_energy_step` scrive `_("PVGIS: {what} ({n} of {total})")` per ogni passo della
pipeline. «the electrical network» è il passo 2 di `pipeline.STEPS` (la rete elettrica delle stringhe, calcolo locale):
nessuna chiamata a PVGIS è in corso in quel momento.

### Perché resta al 50 % [V, codice e misura]
`electrical_network.solve` chiamava `progress()` prima di ogni blocco di 48 ore (90 blocchi in un anno), ma la pipeline
diceva ogni volta lo stesso `step(2, 4, "the electrical network")`: la barra resta ferma a 2/4 = 50 % per tutta la
durata del passo, che su questa taglia è lunga.

### Quanto è lungo, e perché [V, misura]
Impianto sintetico equivalente costruito con le funzioni del programma (`repro.py`): tetto 114 x 76 m, modulo
`generic-450` di default, file inclinate di default, 5 x SUN2000-100KTL-M2 dal catalogo, stringhe da
`plant.proposal`: **2016 moduli, 84 stringhe da 24 su 42 ingressi**, come nelle foto. Meteo: copia del TMY PVGIS in
cache per 45,4642 / 9,19 (stessa coordinata del progetto di Daniel), nessuna rete.

| impianto | prima | dopo |
|---|---|---|
| 160 moduli, 8 stringhe | 11,4 s (profilato) | 2,2 s pipeline intera |
| **2016 moduli, 84 stringhe** | **64,8 s pipeline, rete ~63 s**; `solve` da solo 150,9 s sotto carico | **2,9-4,7 s pipeline; `solve` 2,3 s** |
| 3175 moduli, 100 stringhe | non misurato | 7,3 s (rete 4,4 s) |
| 6956 moduli, 100 stringhe | non misurato | 20,9 s (rete 4,8 s; il resto è primo passaggio e impianto) |

Misure sul PC Windows con altri agenti al lavoro (carico variabile: le cifre «prima» vanno da 65 a 151 s secondo il
carico). Il profilo prima (`before-2016-profile.log`): 61 s su 156 in `min(p.row for p in ap.a.placed)` dentro
`_row_cohorts`, rifatto per ogni modulo di ogni blocco (366 milioni di iterazioni: costo quadratico nei moduli), più
125 s complessivi nelle coorti di fila ricalcolate modulo per modulo anche quando sono identiche.

### È un ciclo, un blocco, un job mai concluso? [V/I]
- Ciclo o blocco: no [V]. Lo stesso impianto termina (1 056 094 kWh), solo lentamente; la cancellazione era già
  controllata a ogni blocco.
- Durata sul laptop [I]: la misura è sul PC fisso; sul Framework 13 il passo è prevedibilmente più lento. In più
  **ogni modifica rilancia un nuovo anno senza fermare il precedente** [V, codice]: `_layout_done` riavvia
  `energy_timer` quando l'anno è vecchio, `_compute_energy` crea un nuovo `EnergyJob` e sovrascrive `self.energy_job`
  senza `interrupt()` sul precedente. Con dimensionamento inverter + proposta stringhe + ritocchi, più job da un minuto
  o più girano insieme nel pool e si contendono il GIL: quello atteso finisce dopo tutti gli altri. È la spiegazione
  più probabile del «resta bloccata», non verificata sul laptop (SSH non risponde).
- Risultato vecchio [V]: «907,20 kWp; 824,8 kW AC, DC/AC 1,10; 0 kWh» è esattamente l'anno calcolato **prima di
  scegliere gli inverter** (ricalcolato su questo impianto senza inverter: `p_ac_kw` 824,8, rapporto 1,10, 0 kWh,
  nota «Only modules connected...»). La finestra lo segnava già come vecchio: segno «·» sulle schede (visibile nelle
  foto) e numeri attenuati, misurati offscreen: testo #ededed -> #9b9b9b nel tema scuro, #1e1c19 -> #6f685d nel chiaro.
  Anche il controllo «Unconnected modules produce no energy» era di quell'anno vecchio.

### Correzione (file miei)
`energy/electrical_network.py`, `solve`:
1. la fila davanti di ogni campo e l'indice dei moduli nella tabella degli ostacoli calcolati **una volta per l'anno**
   (non più per modulo e per blocco); `_row_key`, `_obstacle_index`;
2. **forme condivise** per blocco: le coorti di cella dipendono solo dalla forma del modulo (fila davanti, livello
   nella pila dietro, oppure il modulo stesso se un ostacolo lo ombreggia davvero); moduli con la stessa forma le
   calcolano una volta. Nulla viene mediato: ogni modulo ombreggiato da un ostacolo resta un caso a sé;
3. stringhe con le stesse curve nello stesso ordine: una sola serie; inseguitori MPPT con le stesse stringhe e gli
   stessi limiti: un solo punto di lavoro e una sola corrente per stringa;
4. ripartizione delle potenze per campo: somma dei pesi dei moduli di un campo prima di aggiungere alle serie orarie
   (prima: 24 somme con indici per stringa e per tappa); riferimento, 25 °C e nominale sommati come n x valore;
5. `progress(share)` riceve la quota fatta (0-1) prima di ogni blocco.

`energy/pipeline.py`: il passo della rete dice `step(2 + share, STEPS, "the electrical network")`, cioè da 2 a 3.
Con la finestra di oggi (`Signal(int, int, int, str)`) il valore viene troncato a 2 senza errori [V: PySide6 6.12
tronca un float in un segnale int]; perché la barra si muova serve la modifica alla finestra del punto 4.

### Uguaglianza dei risultati [V]
`compare.py` esegue sulla stessa prima passata e sulle stesse stringhe la rete prima (copia del file originale) e
dopo, e confronta tutte le serie orarie (`reference`, `nominal`, `at25`, `dc` per inverter, tutte le tappe
`p_el/p_opt/p_cut/p_dc`):
- 2016 moduli: **massima differenza 5,1e-14 relativa al picco di ogni serie**, note identiche, DC annua per
  inverter 316 051,874 / 315 643,518 x 3 / 63 128,704 kWh, energia 1 056 094 kWh come prima.
- 47 moduli con tre camini (percorso degli ostacoli, `_obstacle_index`): massima differenza 1,2e-15, note
  identiche, 24 451,545 kWh DC (`compare-47-chimney.log`).
- Tolleranza dichiarata: 1e-12 relativa (resti di arrotondamento dall'ordine delle somme).

### Prove aggiunte
- `tests/calcoli/test_electrical_network.py`, classe `SharedShapes`:
  - `test_each_string_gets_what_it_gets_alone`: quattro stringhe in posizioni diverse (fila davanti, fila dietro,
    due livelli della pila) su tre inverter; il risultato insieme coincide (rtol 1e-12) con ogni stringa calcolata da
    sola, e le forme sono davvero diverse. Prova di mutazione: con `_row_key` che dimentica il livello la prova
    **fallisce** [V].
  - `test_the_curves_computed_do_not_grow_with_the_modules`: con 16 e 96 moduli nelle stesse quattro posizioni,
    stesse chiamate a `module_curve` e a `cell_histogram`. Sul codice di prima **fallisce** (48 contro 288 coorti) [V,
    `old_tests.py`].
  - `test_network_cancellation_is_observed_before_a_chunk`: ora verifica anche la quota passata (0,0).
- `tests/calcoli/test_pipeline.py`:
  `test_the_electrical_network_tells_how_far_it_is_and_stops_in_the_middle`: il passo della rete dice valori
  crescenti tra 2 e 3, e un Interrupted a metà rete ferma il calcolo prima della stima PVGIS. Sul codice di prima
  fallisce (tutti 2).

## 3. Revisione del lotto E

### Difetto trovato e corretto: R245 «Active inverters» contava gli inverter scelti, non quelli attivi
- Descrizione: il riquadro «Active inverters» mostrava «3 inverters / 3 x Acme AC-20K, 60.0 kW AC» anche con un
  inverter senza stringhe (foto `build/overnight-r07/e-real-250-R02-*-overview.png`), mentre la riga «basi del
  calcolo» (R246) conta solo gli inverter con stringhe: due numeri diversi per la stessa parola. Gravità media.
- Correzione: `plant_page.active_overview(plant)` con la stessa regola della pipeline (inverter installato, stringa
  con moduli su un ingresso esistente): «2 of 3 inverters with strings · 40.0 kW AC», poi una riga per unità
  («Inverter 3 · Acme AC-20K: no strings»), le prime 6, il resto in «and {n} more», tutte nel tooltip. Mentre
  l'impianto è in calcolo (`plant is None`) resta il testo di prima (inverter scelti).
- Prove: `widget.test_string_list.WorkingInverter.test_overview_shows_all_installed_units_before_the_working_selector`
  (riscritta: prima pretendeva «3 inverters»), `test_overview_names_the_first_units_and_counts_the_rest` (nuova).
- Foto offscreen a 2,5 (QT_SCALE_FACTOR), chiaro e scuro, 240 e 360 px:
  `build/overnight-r07/e-offscreen-250-R03-*.png` (stesso script `e-verify.py` del lotto, nomi nuovi). A 240 px il
  testo va a capo e resta leggibile.

### Verificato senza difetti
- R246 [V, codice + prove]: `basis` nasce in `pipeline.compute` da `sim.arrays/sim.inverters` della rete e dal
  bilancio orario; la finestra lo mostra in `_energy_done` e in `_show_energy_forms` dall'anno in mano
  (`self.energy`), mai dal progetto. Percorsi: nuovo/apri/recupero (`session.take` svuota l'anno -> `basis` None,
  riga nascosta); variante (`_switch_variant` svuota l'anno -> None); anno vecchio dopo una modifica (resta la riga
  dell'anno, attenuata da `set_stale`); errore o meteo mancante (`basis` None). Prove `widget.test_energy_basis`,
  `nucleo.test_calculation_basis`, `calcoli.test_pipeline` verdi.
- R243 [V, codice]: «Start again» in barra è la stessa QAction `strings_clear`; `_strings_clear` chiede conferma e
  scrive con un solo `_strings_put` (un solo annulla). `nucleo.test_phases` verde.
- R244 [V, codice]: i tre messaggi (dimensionamento, proposta, cancellazione) dicono dove (Plant > Strings / Active
  inverters) e che l'annulla ripristina.
- R247 [V, prova `widget.test_charts` + foto R02]: un solo contorno per colonna impilata, 40 % di inchiostro e velo
  leggero.
- R255/R256 [V, prove `widget.test_string_list`, `widget.test_status_pill`; foto]: pillole righe con sfondo del
  delegate, simbolo 13 px, 10 px a destra del numero.

### Difetti sospetti non confermati / di altri
- R244, messaggio di `_strings_clear` (window.py): «all {n} strings cleared» con n = 1 dà «all 1 strings cleared»;
  andrebbe `ngettext`. Gravità bassa.
- R244, `_sizing_done`: «All {n} modules have a valid string» conta i moduli nelle stringhe del risultato; è vero
  solo se `sizing.choose` con `ok` e `search_complete` garantisce tutti i moduli posati (file di F, non verificato).
- `CalculationBasis.inverters` contiene il nome del modello ripetuto per unità («Huawei SUN2000-100KTL-M2» x 5 nel
  tooltip): leggibile ma poco utile; bassa, non toccato perché la prova del lotto fissa questo formato.

## 4. Modifiche richieste a file non miei (window.py, po)

1. **Fermare l'anno precedente** (R266, gravità alta: job da un minuto che si accumulano), `window.py` riga 3321, in
   `_compute_energy`, subito prima di `job = EnergyJob(...)`:
   ```python
   if self.energy_job is not None:
       self.energy_job.interrupt()     # the year asked before is awaited no longer: it stops at its next chunk
   ```
2. **Barra che avanza nel passo della rete**, `window.py` riga 156:
   ```python
   step = Signal(int, float, int, str)        # generation, steps done (a fraction inside the network), steps, what
   ```
   e riga 3349-3354 in `_energy_step` (firma `done: float`):
   ```python
   self.pvgis_progress.set(done / total, _("Production: {what} ({n} of {total})").format(
       what=what, n=int(done) + 1, total=total))
   ```
   (con `int(done)`: senza, l'etichetta direbbe «3.37 of 4»).
3. **Etichetta**: il prefisso «PVGIS:» solo quando parla davvero PVGIS. Proposta minima: la riga sopra
   («Production: ...» per tutti i passi) e in `_computing` riga 3339 lasciare `_("PVGIS: {what}")` per il primo
   passo, che con `fetch` è davvero lo scaricamento. Va aggiornata
   `tests/finestra/test_waits.py` riga 217: `"Production: the horizon (2 of 3)"`.
4. **Cancel anche senza rete** (consigliato): oggi un calcolo senza `fetch` mostra solo l'arco, senza Cancel. In
   `_energy_step`, se `generation == self.energy_generation and not self.pvgis_progress.running()`:
   `self.busy_wait.end(); self.pvgis_progress.begin(_("Production: {what}").format(what=what))` prima del `set`.
   E in `_cancel_pvgis` riga 3363 un testo non legato a PVGIS:
   `_("Production stopped: the values are those of the last computation.")` (la prova `test_waits` cerca solo
   «stopped»).
5. `_strings_clear` (riga 4297): `ngettext` per «all {n} strings cleared» (vedi sopra).

## 5. msgid nuovi o cambiati

Nei miei file:
| msgid | traduzione proposta |
|---|---|
| `{active} of {total} inverter with strings` / `{active} of {total} inverters with strings` | `{active} di {total} inverter con stringhe` (entrambe le forme) |
| `on {n} input` / `on {n} inputs` | `su {n} ingresso` / `su {n} ingressi` |
| `no strings` | `nessuna stringa` |
| `and {n} more` | `e altri {n}` |
Riusati: `{n} string`/`{n} strings`, `No inverter selected.`, `{n} inverter`/`{n} inverters`.

Nelle proposte per window.py (punti 2-4):
| msgid | traduzione proposta |
|---|---|
| `Production: {what} ({n} of {total})` | `Produzione: {what} ({n} di {total})` |
| `Production stopped: the values are those of the last computation.` | `Calcolo della produzione fermato: i valori sono quelli dell'ultimo calcolo.` |
(`Production: {what}` esiste già, tradotto «Produzione: {what}»: stessa scelta.)

## 6. Prove eseguite

Ambiente delle regole (Git Bash, offscreen, PYTHONPATH `tests;src`, PATH con PySide6).
- `python -m unittest calcoli.test_electrical_network` -> 10 OK.
- Conferma finale: `python -m unittest calcoli.test_electrical_network calcoli.test_pipeline calcoli.test_connected_production calcoli.test_electrical_iv calcoli.test_energy widget.test_string_list widget.test_energy_basis nucleo.test_calculation_basis nucleo.test_phases` -> 111 OK.
- `python -m unittest widget.test_string_list` -> 16 OK (15 prima dell'aggiunta).
- `python -m unittest widget.test_energy_basis nucleo.test_calculation_basis widget.test_charts widget.test_status_pill
  nucleo.test_phases calcoli.test_pipeline calcoli.test_connected_production calcoli.test_electrical_iv` -> 65 OK.
- `python -m ruff check --select F,E9,B` sui file toccati -> pulito (corretto un B905 nella prova nuova).
- Nessun U+2014 nei file toccati.
- Misure: `repro.py 114 76` (prima e dopo), `compare.py 114 76`, `compare.py 24 14 chimney`, scala dopo 160-6956
  moduli; `stale_look.py` (colori dei valori vecchi).
- Non eseguita la suite intera (lasciata al consolidamento).

## 7. Limiti e cose non verificate

- **Laptop non raggiungibile**: progetto vero, log e autosalvataggio non letti; la riproduzione è su un impianto
  sintetico con le stesse grandezze. Daniel potrebbe avere ostacoli o parametri di fila diversi.
- **Ombre di ostacoli (camini, edifici vicini): problema aperto, gravità alta per chi li ha.** Ogni modulo
  ombreggiato da un ostacolo è un caso a sé e il costo resta quello delle curve per celle
  (`electrical.module_curve`, circa 35 ms per modulo e blocco di 48 ore). Misure: 47 moduli con tre camini, `solve`
  130 s prima e 174 s dopo (stesso ordine: stesse chiamate a `module_curve`, la differenza è il carico del PC);
  149 moduli con tre camini: oltre 200 s di CPU senza finire. Un impianto come quello di Daniel **con** ostacoli
  richiederebbe decine di minuti o ore. Il progetto delle foto ha 0 esclusioni e un solo edificio, quindi non è il suo
  caso [V foto, I sul progetto]. Ora la barra avanza e Cancel funziona anche lì. Strade possibili, non fatte perché
  cambiano la numerica (campionamento a 129 punti, scorciatoia del modulo uniforme decisa sul blocco intero) e vanno
  decise: dividere il blocco per ora e riusare le ore senza ombra di un modulo; interpolazione vettoriale al posto del
  ciclo di `np.interp` riga per riga; blocchi di coorti calcolati una volta per forma d'ombra quantizzata.
  **Aggiornato nella sezione 8**: fatte le accelerazioni esatte, da 2 a 2,4 volte.
- La barra che avanza e il Cancel senza rete dipendono dalle modifiche a window.py del punto 4.
- Misure di tempo sotto carico di altri agenti: i valori assoluti oscillano; il rapporto prima/dopo (oltre 20 volte
  sul passo della rete) è stabile in tutte le prove.

## 8. Seguito R266: ombre di ostacoli, solo accelerazioni esatte (richiesta del coordinatore)

Vincolo: nessun cambio della numerica (niente quantizzazione delle forme d'ombra, niente campionamento ridotto).
Riferimento per l'uguaglianza: `electrical.py` e `electrical_network.py` come a 23bd7a9 (copie da `git show`), sulla
stessa prima passata e sulle stesse stringhe salvate (`shaded.py capture`, poi `time before` / `time after`,
confronto `same.py` su tutte le serie orarie: `reference`, `nominal`, `at25`, `dc`, tappe `p_el/p_opt/p_cut/p_dc`).

### Che cosa ho fatto (file `energy/electrical.py`, `energy/electrical_network.py`)
1. **Ore di un altro modulo** (punto 1 della richiesta, generalizzato). Ho verificato nel codice che `module_curve`
   decide poche cose sul blocco intero di 48 ore e poi lavora ora per ora. Le decisioni sono: modulo a un diodo,
   numero di coorti dopo l'impacchettamento, coorti occupate per blocco. Le ho rese esplicite (`iv.CurvePlan`,
   `iv.curve_plan`, parametro `plan=` di `module_curve`). Con il piano del blocco intero, un sottoinsieme di ore dà
   le stesse ore. La curva di un'ora dipende solo dalla luce e dalla temperatura dell'ora (uguali per tutti i moduli
   di un campo), dalle sue coorti e da `CurvePlan.hourly`. `hourly` dice se il modulo è a un diodo e, per ogni
   blocco, se il blocco ha una coorte o più. Il motivo: una coorte vuota in quell'ora ha frazione serie zero,
   tensione esattamente zero e corrente a 0 V non superiore a quella delle occupate, quindi non cambia i campioni.
   `electrical_network._module_curve` tiene, per campo e `hourly`, le ore già calcolate nel blocco, indicizzate dalle
   loro coorti. Ogni modulo calcola solo le ore che nessun altro ha già calcolato. Le ore libere dagli ostacoli (o
   con la sola ombra di fila, uguale per i moduli della stessa fila e livello) si calcolano una volta. Il «dividere
   il blocco e riusare le sole ore chiare» della richiesta, provato per primo, non dava guadagno (89 -> 92 s): le
   ore davvero «chiare» sono poche nelle file dietro, e il piano cambia da modulo a modulo.
2. **Interpolazione** (punto 2). Ho misurato tre versioni vettoriali di `np.interp` riga per riga: ricerca unica sui
   numeri complessi (riga, valore), ordinamento stabile, conteggio. Danno numeri identici bit per bit (2000 casi a
   caso con duplicati, infiniti, zeri con segno), ma sono **più lente** del ciclo con 48 righe e 129 punti:
   0,255 / 0,306 s contro 0,177 s per 500 chiamate. Quindi: il ciclo resta, chiama direttamente la funzione
   compilata di NumPy (`numpy._core.multiarray.interp`, la stessa che `np.interp` chiama, senza il suo involucro).
   Solo la lettura di un valore per riga (le curve lette a 0 V, metà delle ricerche) è vettoriale (`_interp_one`),
   con la regola di NumPy riscritta: identica bit per bit, segno degli zeri compreso.
3. **Coorti di un blocco tutte insieme**: i calcoli di ogni coorte (diodo, inversa, concatenazione) sullo stesso
   asse in mezzo, e la serie delle coorti in una chiamata (`_series_stacked`), con la somma nello stesso ordine.
4. **Coorti vuote nelle ore chieste**: non calcolate; ne resta una se il piano ne ha più di una (conta solo «una o
   più», vedi punto 1).

### Uguaglianza [V]
| caso | prima | dopo | differenza massima (relativa al picco di ogni serie) |
|---|---|---|---|
| 47 moduli, tre camini (`shaded_24_14`) | 89,3 s | 45,1 s | 1,2e-15, note identiche, 24 451,545 kWh DC |
| 2016 moduli, impianto di Daniel senza ostacoli (`shaded_114_76_clear`) | 71,6 s | 2,5 s | 5,1e-14, note identiche |
| 149 moduli, tre camini (`shaded_40_20`) | 209,9 s | 85,9 s | 3,2e-15, note identiche, 89 897,888 kWh DC |

Tolleranza dichiarata 1e-12. I tempi di `solve` da solo (senza primo passaggio), sul PC Windows con altri agenti al
lavoro.

### Prove aggiunte
- `tests/calcoli/test_electrical_iv.py`, classe `HourByHour`:
  - `test_any_hours_with_the_batchs_plan_are_those_of_the_whole_batch`: con il piano del blocco, ogni sottoinsieme
    di ore coincide con quelle del blocco intero (1e-12). Senza il piano, l'ora chiara da sola è diversa: il piano
    serve davvero.
  - `test_interp_is_numpys_row_by_row`: `interp` uguale a `np.interp` riga per riga, bit per bit. Anche il percorso
    vettoriale di un valore per riga, con infiniti e zeri con segno.
- `tests/calcoli/test_electrical_network.py`, `HoursOfAnotherModule.test_a_module_takes_the_hours_it_shares_and_gets_its_own_curve`:
  due moduli con piani diversi (3 e 6 coorti). Il secondo calcola solo 5 ore su 10 e ottiene la curva che avrebbe
  da solo (1e-12).

### Prove eseguite dopo il seguito
- `python -m unittest calcoli.test_electrical_network calcoli.test_electrical_iv calcoli.test_pipeline
  calcoli.test_connected_production calcoli.test_energy calcoli.test_nearshade calcoli.test_optimizers
  calcoli.test_optimizer_partitions calcoli.test_input_topology widget.test_string_list widget.test_energy_basis
  nucleo.test_calculation_basis nucleo.test_phases` -> 186 OK (comprese le prove sui riferimenti PVGIS di
  `test_energy`).
- Ruff F, E9, B sui quattro file toccati: pulito. Nessun U+2014.
- Script di misura nello scratchpad: `shaded.py`, `same.py`, log `split-chimney.log`, `split-daniel.log`,
  `split-149.log`.

### Che cosa resta
- Con gli ostacoli il guadagno è da 2 a 2,4 volte, non di più. Il resto è fisica: per ogni ora in ombra, sei blocchi
  con fino a 17 coorti, ciascuna ricampionata con `np.interp` (circa 1,2 microsecondi a chiamata compilata,
  milioni di chiamate). Un impianto grande con molti moduli in ombra di camini resta lungo (minuti), con la barra
  che ora avanza e Cancel che funziona. Andare oltre senza cambiare la numerica richiederebbe una ricerca compilata
  per tutte le righe (estensione C/numba, nuova dipendenza): decisione di Daniel.
- La strada «forme d'ombra quantizzate» o «campionamento ridotto» non è stata toccata, come chiesto.
- `window.py` non toccato: le modifiche della sezione 4 le applica Opus I.

