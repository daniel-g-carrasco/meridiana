# Tema C: prestazioni, con un bilancio da rispettare

Studio 18 (revisione completa), tema C. Misure del 23/10/2026 sul PC di Daniel, offscreen, con il programma al
ramo `revisione-completa` (dopo i ritocchi della fase 2). Ogni affermazione è marcata [V] (misurata: comando,
macchina, ripetizioni) o [I] (dedotta). Mai il trattino lungo.

## 0. In breve

- **Il bilancio**: due obiettivi su cinque sono rispettati oggi (posa sotto 1 s per 5.000 moduli, apertura sotto 3 s);
  tre no: l'avvio dura 1,5 s (0,9 s sono import di pandas e matplotlib), il calcolo energetico dura 1,2-1,4 s a caldo e
  2,1-2,5 s a freddo per 188 moduli (obiettivo 1 s), e sul progetto grande alcuni gesti superano i 100 ms (selezione
  61-80 ms più il 3D, modifica con blocchi di 126-164 ms) [V].
- **R31, il ciclo `dispatch`**: 156 chiamate per 8.760 ore costano 0,54-0,60 s, il 43% del calcolo a caldo [V]. Non
  va compilato: va cambiato l'algoritmo. Le 150 chiamate distinte (il bilancio del primo anno è identico all'anno 1
  del ciclo) si fanno in una passata sola con lo stato a vettore: **70 ms, 7,7 volte più veloce, stessi risultati a
  1e-9** [V], zero costi di distribuzione. numba dà 9 ms (58 volte) ma porta 147 MB di pacchetti, 0,45 s di import e
  0,15-0,45 s di prima chiamata per processo [V]; Rust darebbe lo stesso guadagno di numba [I] con il costo più alto
  (toolchain C su ogni macchina che compila: il WSL di prova non ha né `cc` né `glibc-devel` e la compilazione si
  ferma lì [V]; wheel per piattaforma; CI).
- **Scalabilità**: la posa è lineare e veloce (0,8-0,9 s per 20.493 moduli) [V]; la tabella d'ombra non cresce con i
  moduli ma costa 8-10 s già a 5.000 e domina il calcolo a freddo (11,3 s a 20.000) [V]; il calcolo a caldo resta
  1,2-1,3 s a qualsiasi taglia [V]; la pianta è un solo elemento grafico per sottocampo (15 elementi anche con
  20.000 moduli) e un passaggio del mouse costa 5 ms a 20.000 [V]; nella finestra il collo è il filo principale in
  `_layout_done` (tabella 3D e pianta rifatte in Python: 2 s per aprire il progetto da 20.000, 0,6 s per 5.000) [V].
- **Verdetto**: non si compila nulla e non si riscrive nulla per le prestazioni; si cambiano tre algoritmi
  (`dispatch` a vettore, una sola `simulate`, la tabella d'ombra per cella invece che per piano x cella) e si
  vettorializzano quattro cicli Python (`module_table`, la posa, il resto di `evaluate`, `module_shapes`); gli import
  pesanti diventano pigri. Con questi interventi il calcolo a caldo scende sotto 1 s per 200 moduli [I] e l'avvio
  intorno a 0,6-0,7 s [I].
- **Fatto (compito 18c, 23/10/2026 sera)**: il bilancio rimisurato sta nella sezione 2, «Dopo il compito 18c»:
  avvio 1,59 -> 0,96 s, calcolo di Rho a caldo 0,29 s e a freddo 0,73 s, selezione e modifica sul progetto grande
  16 e 22 ms sincroni senza blocchi sopra 40 ms [V]; restano la tabella d'ombra a freddo sui progetti grandi (1,9 s a
  5.000, 5 s a 20.000) e i blocchi di 78-90 ms alla prima apertura di Consumi e Bilancio.

## 1. Metodo

**Macchina** [V]: Intel Core i7-12700H (14 core, 20 thread, 2,3 GHz base), 31,6 GB di RAM, Windows 11 Pro 26100;
Python 3.12.6 nel venv dell'app (`C:\Users\utente\dev\meridiana\.venv`): PySide6 6.12.0, numpy 2.5.4, pandas 3.0.6,
pvlib 0.16.1, shapely 2.2.0, matplotlib 3.11.2, scipy 1.18.1. Tutto offscreen (`QT_QPA_PLATFORM=offscreen`): la
vista 3D gira con `GraphicsApi.Software`, quindi i tempi di disegno del 3D non dicono nulla della GPU; i tempi del
lato Python (tabella delle istanze, mesh) sì. Ambienti a parte: numba 0.68.0 + llvmlite 0.50.0 nel venv
`scratchpad\numba-venv` (stesso Python 3.12.6); nella WSL openSUSE Tumbleweed cargo 1.99.1, rustc 1.99.1, maturin
1.15.0, Python 3.13.16 con numpy 2.5.4 (`~/perf-venv`).

**Carico**: la CPU era condivisa con altri agenti. Ogni script stampa la quota di CPU occupata (tutti i 20 thread)
durante la propria misura, letta da `GetSystemTimes` (`carico.py`): 5-15% durante le misure riportate, salvo dove
indicato (le ripetizioni del profilo del mattino, 34%; la seconda catena, 12-23%). Ogni misura è ripetuta almeno 5
volte (3 per i casi da 20.000 moduli e per l'apertura della finestra, detto dove vale) e si riporta la mediana con
minimo e massimo.

**Strumenti** (tutti in `docs/studio/18-prove/`, da lanciare dalla radice del repository con `PYTHONPATH=src` e
`QT_QPA_PLATFORM=offscreen`):
- `profilo_energia.py`: la misura del 23/10 ripetuta 5 volte sotto cProfile (risultati in
  `profilo_energia-risultati.txt`);
- `energia_tempo.py`: `EnergyJob._compute` senza profiler, a freddo (cache delle ombre svuotata) e a caldo, con i
  passi principali cronometrati da involucri sulle funzioni (`energia_tempo-risultati.txt`);
- `dispatch_varianti.py`: le cinque versioni di `dispatch`, il controllo di uguaglianza e il benchmark
  (`dispatch_varianti-risultati.txt`), più il crate `dispatch_rs/` (Cargo.toml, pyproject.toml, src/lib.rs);
- `avvio.py`: l'avvio in processi freschi (`avvio-risultati.txt`);
- `scalabilita.py`: progetti generati da 880, 4.964 e 20.493 moduli (`scalabilita-risultati.txt`);
- `probe.py` del 22/10 (`C:\Users\utente\dev\meridiana-prove\ux-2026-10-22\probe.py`), lanciato offscreen da una copia
  nella scratchpad con due ritocchi necessari (una funzione rinominata, i campi delle quantità, lo stub del 3D
  cresciuto dal 22/10); i suoi `results.json` sono riassunti in `probe-offscreen-risultati.txt`.

Per confronto, le misure del 22/10 sullo schermo vero (Direct3D 11, prima della fase 1 e 2):
`C:\Users\utente\dev\meridiana-prove\ux-2026-10-22\misure\win-*\results.json`.

## 2. Il bilancio: obiettivi proposti e dove sta Meridiana oggi

| Obiettivo | Proposta | Oggi, progetto di prova (188 moduli) | Oggi, progetto grande (4.682-4.964) | Esito |
|---|---|---|---|---|
| Avvio | sotto 1 s | 1,52 s fino alla finestra pronta col progetto aperto (mediana di 5 processi) [V] | idem | **no** |
| Selezione di un oggetto | sotto 100 ms | 25-38 ms [V] | 61-80 ms sincroni, blocco di 80-114 ms [V] | sì / **al limite** |
| Modifica di una proprietà (inclinazione) | sotto 100 ms | 10-14 ms sincroni, posa e ridisegno finiti dopo 142-179 ms, nessun blocco sopra 30 ms [V] | 53-64 ms sincroni, blocchi di 126-164 ms [V] | sì / **no** |
| Cambio di scheda | sotto 100 ms | 14-23 ms; la prima apertura di Consumi 76-108 ms, di Bilancio 127-166 ms [V] | idem [V] | sì, salvo la prima apertura |
| Passaggio del mouse sulla pianta | sotto 100 ms | 0,8-1,0 ms (mediana), 3-4 ms (p95) [V] | 0,8-1,4 ms [V] | sì |
| Calcolo energetico | sotto 1 s per 200, sotto 10 s per 5.000 | 1,18-1,39 s a caldo, 2,12-2,52 s a freddo, 2,95-3,5 s la prima volta della sessione [V] | 4,6-5,2 s a freddo e 1,13-1,18 s a caldo (4.964); 6,5-7,7 s la prima volta (4.682) [V] | **no** / sì |
| Posa | sotto 1 s per 5.000 | 9-20 ms [V] | 0,34-0,37 s (4.682, due sottocampi, nel thread) [V]; 0,40-0,76 s (4.964) [V] | sì |
| Apertura di un progetto | sotto 3 s per 5.000 | 0,23-0,24 s fino a finestra ferma [V] | 0,49-0,51 s (4.682, con le tessere in cache) [V]; 0,61 s (4.964, senza sfondo) [V] | sì |

**Dopo il compito 18c** (23/10/2026 sera, parte A e parte B, stessi script e stesse condizioni: offscreen, mediane di 5,
`misure.sh` della sessione; prima -> dopo) [V]:

| Obiettivo | Proposta | Progetto di prova (188 moduli) | Progetto grande (4.682-4.964) | Esito |
|---|---|---|---|---|
| Avvio | sotto 1 s | 1.589 -> 958 ms (import di Meridiana 988 -> 282 ms; costruzione della finestra 272 -> 383 ms: `theme._register_for_charts` carica ora lì `matplotlib.font_manager`) | idem | **sì, al limite** |
| Selezione di un oggetto | sotto 100 ms | 20 -> 17 ms sincroni, 27 -> 15 ms fino a finestra ferma | 53 -> 16 ms sincroni, blocco di 53 ms -> nessuno (`_show_3d` 40 -> 2,4 ms, `module_table` fatta una volta nel thread) | sì / sì |
| Modifica di una proprietà (inclinazione) | sotto 100 ms | 17 -> 13 ms sincroni, nessun blocco | 90 -> 22 ms sincroni, `_layout_done` 91 -> 21 ms, blocchi 129 e 90 -> 37 ms (`Plan.show_project` 70 -> 2 ms, pose già disegnate tenute; `_show_3d` 75 -> 5 ms) | sì / sì |
| Cambio di scheda | sotto 100 ms | la prima apertura di Consumi dipinta in 19 ms invece di 85 (poi i grafici uno per giro, blocco più lungo 78 ms), di Bilancio 23 invece di 146 (blocco 90 ms); il primo passaggio alla Produzione 83 ms di blocco con matplotlib caricato in un thread (210 ms senza, 68 prima quando era importato all'avvio) | idem | sì, salvo i blocchi di 78-90 ms della prima apertura |
| Calcolo energetico | sotto 1 s per 200, sotto 10 s per 5.000 | a caldo 0,42 -> 0,29 s, a freddo 0,94 -> 0,73 s (prima della parte A: 1,39 e 2,52 s); `simulate` due corse 195 ms -> 86 + 24 ms (`with_strings`); il conteggio fuori ombra 11 ms -> 0 a scena ferma | 4.964: 1,81 -> 1,85 s a freddo, 0,30 -> 0,31 a caldo; 20.493: 4,91 -> 5,05 a freddo, 0,40 -> 0,52 a caldo (rumore: resta la tabella d'ombra) | **sì** / sì |
| Posa | sotto 1 s per 5.000 | 4-6 ms | 22 ms (4.964), 0,15-0,17 s (20.493), dalla parte A; più la tabella 3D 3-5 ms nel thread | sì |
| Apertura di un progetto | sotto 3 s per 5.000 | finestra ferma 207 -> 177 ms, il blocco della decodifica delle 15 tessere (67-82 ms) non c'è più | 0,29 -> 0,26 s (4.964); 0,77 -> 0,49 s (20.493); `Plan.show_project` 38 -> 6 ms (4.964), 227 -> 26 ms (20.493) | sì |

Dettagli e fonti:
- **Avvio** (`avvio.py`, 5 processi, 3D vero, sfondo «nessuno», progetto Rho): import di PySide6 77 ms, import di
  Meridiana 907 ms, costruzione della finestra 271 ms, mostra e primo disegno 42 ms, `open_path` 29 ms, finestra
  ferma 197 ms dopo; totale 1.525 ms (1.472-1.610) [V]. Con `-X importtime` [V]: `meridiana.energy.consumption`
  trascina pandas (414 ms cumulati), `meridiana.ui.charts` matplotlib con il backend Qt (348 ms), `PySide6.QtCore` 79
  ms. Con il 3D sostituito da uno stub la costruzione è 297 ms e il totale 1.739 ms, ma quelle 5 corse avevano il
  13-23% di CPU occupata da altri: offscreen il 3D non pesa all'avvio, sullo schermo vero il 22/10 la costruzione
  costava 494-862 ms col 3D e 516 ms senza [V, misure del 22/10].
- **Gesti** (probe offscreen, `probe-offscreen-risultati.txt`): la selezione del sottocampo costa `Properties.show_subfield`
  13-19 ms, `matplotlib.draw` 9-14 ms (le 16 figure delle schede nascoste ricevono un resize), `Plan.paintEvent` 5-9 ms;
  sul progetto grande si aggiunge `_show_3d` 45-61 ms, quasi tutto `mesh.module_table` (37-53 ms per 4.682 moduli) rifatta
  a ogni clic [V]. La modifica dell'inclinazione: `edit` 10-14 ms piccolo, 53-115 ms grande (dentro `_show_all`, che
  ridisegna la pianta con i risultati vecchi: `Plan.show_project` 38-46 ms); poi `_layout_done` sul filo principale
  13-16 ms piccolo, 106-160 ms grande (`_show_3d` 46-87, `Plan.show_project` 38-46) [V]. Il passaggio del mouse era
  14-17 ms (188 moduli) e 60-69 ms (4.682) sullo schermo il 22/10: la correzione P2-A della fase 1 lo ha portato a 1 ms [V].
  La rotella su un campo non lo cambia (accettata: no, valore uguale, nessun passo di annulla) [V]; il testo scritto
  mentre torna la posa resta nello stesso campo (`same_widget` True, «0,07» conservato) [V].
- **Calcolo**: `energia_tempo.py` (5 ripetizioni, carico 8-12%): a freddo 2,12 s (2,11-2,50), a caldo 1,18 s
  (1,17-1,23); la stessa misura ripetuta con il 12-20% di carico: 2,52 s e 1,39 s [V]. Nel probe la prima
  computazione della sessione dura 2,95-3,5 s (188) e 6,5-7,7 s (4.682): la differenza con il «freddo» di
  `energia_tempo.py` è il primo uso dei moduli nel thread (import di `scipy.optimize` dentro `irr`,
  `economics.py:184`, e primi usi di pvlib e shapely) [I].
- **Posa e apertura**: dal probe (`LayoutJob.run` nel thread 343-365 ms per 4.682 moduli) e da `scalabilita.py`
  (sezione 5).

## 3. Dove va il tempo nel calcolo energetico (188 moduli, Rho)

`energia_tempo.py`, 5 corse a freddo e 5 a caldo, medie per corsa; i passi annidati contano anche nei genitori [V]:

| Passo | A freddo | A caldo | Chiamate per corsa |
|---|---|---|---|
| `EnergyJob._compute`, totale | 2.520 ms | 1.390 ms | 1 |
| `simulate` (le due corse: `window.py:187` e `:206`) | 1.413 | 268 | 2 |
| di cui `nearshade.shading` (la tabella d'ombra) | 1.144 | 0 (cache) | 1 |
| di cui `nearshade.electrical` | 117 | 117 | 1 |
| di cui posizione del sole (SPA, pvlib) | 57 | 55 | 2 |
| di cui trasposizione (Perez), file di moduli, suolo (pvlib) | 26 | 26 | 6 |
| `economics.evaluate` (17 chiamate: 1 + 9 taglie + 7 batterie) | 1.071 | 1.066 | 17 |
| di cui `storage_sizing` (7 batterie) | 824 | 801 | 1 |
| di cui `sizing` (9 taglie) | 228 | 247 | 1 |
| di cui **`dispatch`** (156 chiamate) | 619 | 601 | 156 |
| `consumption.build` | 21 | 19 | 2 |
| `checks.count_out_of_shadows` (una posa in più) | 21 | 18 | 1 |
| `meteo.typical_year` (lettura della cache) | 10 | 9 | 1 |

Letture:
- **A caldo il 77% è economia** (`evaluate`), di cui il 43% del totale è `dispatch` e il 34% è il resto di
  `evaluate`: 17 volte il ciclo dei 25 anni in Python con `self_[band_h == b]` (tre confronti di 8.760 stringhe per
  anno, `economics.py:269`; circa 1.700 `<genexpr>` per 0,12-0,18 s sotto cProfile [V, profilo]), la costruzione di
  tre DataFrame e del registro con le traduzioni (`:205-360`). `storage_sizing` da solo vale 0,80 s: 6 batterie per
  26 `dispatch` più 7 `evaluate` interi.
- **A freddo si aggiunge la tabella d'ombra**: 1,14 s per 188 moduli e 10 solidi (parapetti, impianti, l'altro
  edificio), `nearshade.py:208-282`; la cache (`cached_shading`, hash di tutti i moduli e solidi) costa 1 ms [V]. La
  seconda corsa di `simulate` (quella con le stringhe, per l'effetto elettrico) rifà tutto tranne l'ombra: 0,13 s a
  caldo [V].
- Il profilo del mattino (3,55 s, 2,3 s in `dispatch`) era preso con il 34% di CPU occupata e sotto cProfile, che
  gonfia i cicli Python; oggi le 5 ripetizioni sotto cProfile danno 1,76-2,57 s con `dispatch` a 0,59-0,86 s [V,
  `profilo_energia-risultati.txt`], e senza profiler 0,54-0,60 s.

## 4. La prova decisiva per R31: `dispatch` in cinque modi

### 4.1 Perché 156 chiamate

`economics.evaluate` (`economics.py:200-360`) chiama `dispatch` una volta nel bilancio del primo anno (`balance`,
`:204` e `:165`) e una volta per ognuno dei 25 anni del flusso di cassa (`:255-266`), sulla produzione degradata
`prod_h * k`. `storage_sizing` (`:390-414`) valuta 7 capacità di batteria (fattori 0, 0,25 ... 2 dell'energia
giornaliera spostabile), e la taglia 0 non ha batteria: 6 x 26 = 156 chiamate, anche quando il progetto non ha una
batteria (il caso di Rho). Con una batteria scelta si aggiungono 26 chiamate in `evaluate` e 9 x 26 in `sizing`: 416.
Il bilancio del primo anno e l'anno 1 del ciclo sono la stessa computazione (fattore 1,0): i risultati distinti sono
150 [V, controllo in `dispatch_varianti.py check`].

### 4.2 Le varianti (`dispatch_varianti.py`)

- (a) **Riferimento**: la funzione di `economics.py:130-153` copiata tale e quale.
- (b) **Stato a vettore**: la stessa ricorrenza con lo stato per tutte le coppie (batteria, anno) insieme, un solo
  ciclo Python sulle 8.760 ore e tre operazioni numpy a ora su un vettore di 150 (`np.add`, `np.maximum`,
  `np.minimum` in loco); `stored` e `given` si ricavano dalle variazioni del livello dopo il ciclo. Una chiamata
  sostituisce le 156.
- (c) **numpy senza ciclo sulle ore**: la ricorrenza è L_h = clip(L_{h-1} + d_h, 0, E), una somma con saturazione
  ai due estremi che `cumsum` da solo non dà. Ma le mappe x -> clip(x + d, lo, hi) sono chiuse per composizione
  (f poi g = (d1 + d2, clip(lo1 + d2, lo2, hi2), clip(hi1 + d2, lo2, hi2))) e associative: una scansione a
  raddoppio (Hillis e Steele) compone tutti i prefissi in ceil(log2 8760) = 14 passate numpy, poi si applica allo
  stato vuoto. (c') è la stessa scansione sullo stato a due dimensioni (150 x 8.760).
- (d) **numba**: il ciclo del riferimento sotto `@njit`, nel venv a parte; misurati a parte la prima chiamata
  (compilazione o caricamento dalla cache) e il tempo a caldo.
- (e) **Rust con PyO3**: il crate `dispatch_rs/` (pyo3 0.27.2, numpy 0.27.1; `maturin develop --release`), lo stesso
  ciclo riga per riga.

**Uguaglianza** [V]: `dispatch_varianti.py check` in entrambi i venv di Windows: 60 casi casuali (anni corti,
batterie minuscole e enormi, potenze nulle, ore senza surplus) e l'anno di 8.760 ore con 6 batterie x 25 anni:
ogni variante uguale al riferimento con `numpy.allclose(rtol=1e-9, atol=1e-9)`; differenza massima 6,4e-14 kWh
(b), 3,2e-13 (c), 4,6e-13 (c'), 0 (numba).

### 4.3 I tempi

Dati: anno sintetico (seme 7, 90 kWp, carico con plateau diurno) e, per controllo, produzione e carico veri del
progetto Rho (`--data`, salvati da `energia_tempo.py`). Mediane di 7 ripetizioni; una chiamata è la media di
3-50 chiamate consecutive; carico CPU 8-11% [V].

| Variante | Una chiamata (8.760 ore) | 156 chiamate (le 150 distinte) | Rapporto | Note |
|---|---|---|---|---|
| (a) riferimento, Python puro (venv app, 3.12) | 3,36 ms (Rho: 3,20) | 538 ms (Rho: 550) | 1 | 519-559 ms su 7 ripetizioni |
| (b) stato a vettore, ciclo sulle ore in numpy | una chiamata per tutte | **70 ms** (Rho: 74) | **7,7** (7,5) | 65-76 ms |
| (c) scansione numpy, nessun ciclo | 0,87 ms (Rho: 1,38) | 204 ms (Rho: 184) | 2,6 (3,0) | per chiamata 3,9 volte |
| (c') scansione numpy a due dimensioni | una chiamata per tutte | 384 ms (Rho: 332) | 1,4 (1,7) | tre array da 10,5 MB riscritti 14 volte: limitata dalla memoria |
| (d) numba 0.68 a caldo (venv numba, 3.12) | **0,055 ms** | **9,3 ms** | **58** | prima chiamata 409-499 ms compilando, 142-186 ms dalla cache |
| (e) Rust, PyO3 | non misurabile sul PC (sotto) | | | stesso ordine di numba [I] |
| (a) riferimento nella WSL (Python 3.13.16, Linux) | 3,69 ms | 491 ms | 1 | |
| (b) nella WSL | | 40 ms | 12,2 | numpy su vettori corti più veloce su Linux |
| (c) nella WSL | 0,50 ms | 78 ms | 6,3 | |

Letture: la variante (b) è la più conveniente per il programma: nessuna dipendenza nuova, una funzione di 25
righe, e nel calcolo a caldo di Rho toglie 0,53 s su 1,18-1,39 s [I, somma delle misure]. La (c) è utile dove serve
una chiamata singola (3-4 volte più veloce) ma su 156 chiamate la (b) la batte, perché il costo per chiamata della
(c) è nelle 14 passate di numpy, non nelle ore. numba è 7,5 volte più veloce della (b) sulle 156 chiamate, cioè 61
ms di guadagno su un calcolo di 1,2 s: non cambia la classe del risultato.

### 4.4 Il costo di distribuzione di ogni strada

- **(b) e (c), numpy o algoritmo**: nessuno. Entrambe stanno in `economics.py` con un test di uguaglianza contro il
  ciclo di riferimento.
- **(d) numba**: numba 0.68.0 + llvmlite 0.50.0 occupano 147 MB su disco (30 + 117) contro i 1.076 MB del venv
  intero (PySide6 656) [V, `du`]; `import numba` costa 294-307 ms in un processo fresco [V]; la prima chiamata
  costa 409-499 ms compilando, 142-186 ms caricando dalla cache (`cache=True`, file `.nbi` e `.nbc` da 52 kB in
  `NUMBA_CACHE_DIR`), e la cache si invalida a ogni modifica del file sorgente [V, tre corse di seguito 449, 309,
  149 ms e tre processi freschi 142-186 ms]. In tutto 0,45-0,65 s per processo, pagabili nel thread del calcolo
  invece che all'avvio [I]. Per il pacchetto: PyInstaller ha gli hook di numba e llvmlite (il DLL di LLVM è uno
  solo) [I]; Flatpak ha le wheel manylinux di entrambi [I]; numba segue le nuove versioni di Python con mesi di
  ritardo (3.12 in 0.59 del gennaio 2024, 3.13 in 0.61 del gennaio 2025) [I]: un vincolo sulla versione di Python
  dell'app.
- **(e) Rust**: il crate è scritto e le dipendenze sono scaricate (15 crate, 3,5 MB di sorgenti in `~/.cargo`); la
  compilazione si ferma a «linker `cc` not found» [V]: nella WSL non ci sono `gcc`, `glibc-devel`, `clang`, `lld`
  (`rpm -q`) e il toolchain di rustup (solo `x86_64-unknown-linux-gnu`, con `rust-lld` e `gcc-ld`) non può collegare
  gli script di build senza i file del runtime C (`crt1.o`) [V]. Su Windows non c'è né rustc né cargo né MSVC né
  gcc [V, `where`]. Installare `gcc glibc-devel` esce dal mandato di questa sessione: è il primo costo della strada
  Rust, un toolchain C su ogni macchina che compila (su Windows gli strumenti di compilazione di Visual Studio,
  alcuni GB [I]). Poi: una wheel per sistema (Windows x64, Linux x64; con `abi3-py312` una per sistema invece che
  per versione di Python [I]), una CI per piattaforma (`maturin-action`, minuti per build), per Flatpak l'estensione
  SDK di Rust e i crate «vendored» (il builder non ha rete) [I]; per PyInstaller solo un `.pyd` da qualche centinaio
  di kB [I]. Il guadagno atteso è quello di numba: il ciclo compilato fa 6 ns per ora (55 µs per 8.760 ore), vicino
  al limite della macchina; Rust potrebbe stare tra 0,5 e 1 volta numba [I].

Comando per chiudere la prova (e) sul PC, se Daniel vuole il numero: nella WSL `sudo zypper install gcc
glibc-devel`, poi
`cd <repository>/docs/studio/18-prove/dispatch_rs && export CARGO_TARGET_DIR=$HOME/perf-venv/cargo-target && . ~/perf-venv/bin/activate && maturin develop --release`
e `cd <repository> && ~/perf-venv/bin/python docs/studio/18-prove/dispatch_varianti.py check` e `... bench --repeats 7`
(la variante (e) compare da sola quando il modulo è importabile; la cartella `target` va fuori da `/mnt/c`, che è un
mount 9p lento).

### 4.5 Fermare la ricerca prima?

Le 7 valutazioni di `storage_sizing` servono a disegnare due curve (autosufficienza e VAN per capacità) e il
massimo del VAN: fermarsi quando il VAN scende cambierebbe i risultati mostrati (meno punti) e non è stato
provato; con la variante (b) non serve: tutte le capacità costano 70 ms insieme.

## 5. Scalabilità

`scalabilita.py` (offscreen; progetti generati come il `big_project` del probe: un capannone con parapetto e tre
impianti in copertura con file inclinate a 15°, un campo a terra a 25° con tavole di due moduli; sito di Rho con la
sua cache PVGIS). 5 ripetizioni fino a 5.000 moduli, 3 a 20.000; la prima ripetizione gira sotto `tracemalloc`,
che rallenta il Python puro, perciò accanto alla mediana è dato il minimo. Carico CPU 13-15% [V].

| Misura | 880 moduli | 4.964 moduli | 20.493 moduli | Crescita |
|---|---|---|---|---|
| `Project.fill`, due sottocampi | 30 ms (min 28) | 763 ms (min 399) | 885 ms (min 810) | lineare o meno; 40-80 µs per modulo |
| `nearshade.shading`, 2 vettori x 7-8 solidi, 777 celle | 1,46 s | 4,2 s in un momento quieto (2,3 copertura + 1,9 campo, `shading_check.py`); 7,8-10,2 s sotto carico esterno | 10,3 s (min 9,6) | **meno che con i moduli**: cresce con i piani (le righe) e le celle (sotto) |
| memoria di `shading` (picco tracemalloc; tabelle per modulo) | 15 MB (11) | 80 MB (60) | 325 MB (248) | lineare: 12,7 kB per modulo (2 array float32 di 23 x 72) |
| `mesh.building_triangles` + prismi + `module_table` | 10 ms | 150 ms (min 57) | 192 ms (min 175) | lineare, 9-30 µs per modulo |
| `PlanView.show_project` | 7 ms | 127 ms (min 86) | 253 ms (min 191) | lineare; sempre 15 elementi grafici |
| `PlanView._pick` nel campo a terra / un passaggio del mouse | 0,3 / 0,3 ms | 5,2 / 4,5 ms | 5,5 / 5,5 ms | lineare nei moduli del sottocampo colpito |
| `EnergyJob._compute` a freddo | 2,58 s | 5,21 s (min 4,63); 5,9-8,9 s nella verifica sotto carico | 11,3 s (min 11,3) | segue l'ombra |
| `EnergyJob._compute` a caldo | 2,44 s (min 1,47) | 1,18 s (min 1,13) | 1,33 s (min 1,28) | **costante**: è economia |
| memoria del calcolo (picco tracemalloc) | 21 MB | 85 MB | 331 MB | come l'ombra |
| file `.meridiana`: dimensione, `save`, `load` | 3,4 kB, 4,5 ms, 0,3 ms | 3,3 kB, 4,5 ms, 0,2 ms | 3,4 kB, 5,2 ms, 0,3 ms | i moduli non sono nel file: aprire è riposare |
| finestra: `open_path` torna / ferma dopo (3D vero, senza sfondo, 3 corse) | 57 ms / 0,49 s | 27 ms / 0,61 s | 29 ms / 2,05 s | superlineare oltre 5.000 |

Note:
- Il valore a caldo di 880 moduli (2,44 s, min 1,47) è sporcato dal carico esterno: la mediana a 4.964 e 20.493 dice
  1,2-1,3 s [V].
- L'apertura del progetto da 20.493 moduli: 0,85 s di posa nel thread e circa 1,2 s sul filo principale in
  `_layout_done` (tabella delle istanze 0,19 s, pianta 0,25 s, due `_show_3d`, albero, proprietà, verifiche) [I, dalle
  misure dei singoli passi].
- La memoria del processo (working set) non è stata letta nei tre lanci: la chiamata `GetProcessMemoryInfo` dello
  script restituiva 0 (argomenti ctypes); corretta dopo, i numeri sopra sono i picchi di `tracemalloc` (Python e
  numpy; non gli oggetti GEOS di shapely né gli elementi Qt).
- **Perché l'ombra non cresce con i moduli**: `nearshade.shading` raggruppa i moduli per piano (`nearshade.py:229-233`:
  un piano per riga di tavole inclinate) e per ogni piano e ogni cella illuminata della griglia solare fa, in Python,
  l'unione delle ombre dei solidi e le intersezioni con i «run» di moduli e con i moduli vicini (`:239-272`); le
  operazioni shapely sono vettoriali per cella ma il ciclo `for k in np.flatnonzero(...)` è Python e il numero di
  passi è (piani x celle colpite), non moduli. `shading_check.py` sul progetto da 4.964 moduli [V]: la copertura
  (1.652 moduli, 15 piani, 7 solidi) costa 2,3 s e il campo a terra (3.312 moduli, 12 piani, 8 solidi) 1,9 s; a
  20.493 moduli i piani raddoppiano e il tempo va a 9,6-10,3 s: circa 2,3 volte per 4 volte i moduli. Le misure
  di `scalabilita.py` a 5.000 (7,8-10,2 s) erano gonfiate dal carico degli altri agenti, come il calcolo a freddo
  della stessa verifica (5,9-8,9 s per lo stesso lavoro in tre corse di seguito) [V].

## 6. I difetti, in ordine di gravità (file:riga)

1. **`src/meridiana/energy/economics.py:130-153`** `dispatch`: ciclo Python sulle 8.760 ore; chiamato 156 volte per
   calcolo (`:204`, `:255-266`, `:375-387`, `:390-414`), 416 con una batteria: 0,54-0,60 s, il 43% del calcolo a
   caldo [V]. Cura: la variante (b), una passata per tutte le (batteria, anno); e il bilancio del primo anno riusa
   l'anno 1 (`:204` e `:260` sono la stessa chiamata) [V].
2. **`economics.py:200-360`** `evaluate`: 17 chiamate per calcolo (una, 9 taglie, 7 batterie) con il ciclo dei 25
   anni in Python, le maschere `band_h == b` su stringhe (`:269`, `:207`, `:350-351`) e tre DataFrame con il
   registro: 0,47 s oltre a `dispatch` [V]. Cura: tre maschere booleane calcolate una volta, il ciclo degli anni come
   array (25 x 8.760 e somme per fascia), il registro costruito solo per la valutazione principale.
3. **`src/meridiana/energy/nearshade.py:239-272`** la tabella d'ombra: 1,14 s per 188 moduli, 8-10 s da 5.000 in su,
   per (piani x celle) in Python [V]; memoria 12,7 kB per modulo per le tabelle `modules` e `blocks` [V]. Cura: un
   solo `shapely.intersection` per piano su tutte le celle (array di ombre contro array di moduli con `STRtree.query`
   vettoriale), oppure l'ombra per riga invece che per modulo; la cache in processo (`:285-310`) va bene.
4. **`src/meridiana/ui/window.py:187` e `:206`** due corse intere di `simulate` per calcolo: la seconda, per
   l'effetto elettrico delle stringhe, rifà sole, trasposizione, temperatura e modulo: 0,13 s a caldo, 0,27 s con il
   confronto della prima [V]. Cura: conservare i prodotti intermedi del primo passaggio e applicare solo il passo
   8 (`simulate.py:313-327`).
5. **`src/meridiana/mesh.py:296-302`** `module_table`: ciclo Python con tre prodotti di matrici numpy per modulo,
   37-75 ms per 4.682 moduli [V], rifatta a ogni selezione (`window.py:1345-1346` e `:1642-1654`) e a ogni posa:
   45-61 ms per clic sul progetto grande [V]. Cura: vettorializzare (le rotazioni sono le stesse per ogni sottocampo:
   una moltiplicazione (N, 3, 3) sola) e tenere la tabella per sottocampo, cambiando solo i colori della selezione.
6. **`window.py:1585-1598`** `_layout_done` sul filo principale: 106-160 ms per 4.682 moduli, 1,2 s per 20.493 [V,
   I], con `plan.show_project` (`plan.py:254-340`: `module_shapes` è una lista di N `QPolygonF` costruita in Python,
   `:330`) e `_show_3d`. Cura: preparare nel thread della posa ciò che è puro dato (tabella delle istanze, corner
   dei moduli come array) e dare alla pianta un array, non N poligoni.
7. **`window.py:1564-1576`** `_show_all` ridisegna la pianta con i risultati vecchi a ogni modifica, e `_layout_done`
   la ridisegna un attimo dopo: `Plan.show_project` x 2 per modifica, 75-135 ms sul progetto grande [V]. Cura:
   a una modifica disegnare solo l'oggetto cambiato (o niente) e lasciare il ridisegno al ritorno della posa.
8. **`src/meridiana/layout.py:323-354`** la posa: `box` + due `affinity` + `centroid` di shapely per modulo
   (`:347-348`): 75-80 µs per modulo, 0,34-0,76 s per 4.700-5.000 moduli [V]. Sotto obiettivo, ma è il primo tempo
   del thread della posa a ogni modifica. Cura: i corner di tutti i moduli con numpy (rotazione e scala sono una
   matrice 2 x 2), shapely solo per `usable` e per gli intervalli liberi.
9. **`src/meridiana/ui/tileloader.py:43-57`** le tessere in cache sono decodificate sul filo principale
   (`QImage(str(path))`, `:54`): 75-113 ms all'apertura con 15 tessere [V]. Cura: decodifica in `QThreadPool` o
   `QImageReader` asincrono.
10. **`src/meridiana/energy/consumption.py:1-15`, `ui/charts.py:19-29`, `ui/window.py:25-32`**: pandas, matplotlib
    (con il backend Qt), shapely, pvlib importati all'import della finestra: 0,76 s dei 1,52 s di avvio [V]. Cura:
    import pigri nei moduli che li usano (le pagine dell'energia e il lavoro), `scipy.optimize` già pigro in
    `economics.py:184` ma pagato alla prima computazione [I].
11. **`ui/charts.py:136-148`** (`when_shown`) e `ui/energy_pages.py:762-836`: la prima apertura di Consumi e
    Bilancio disegna 4-6 grafici matplotlib: 76-108 e 127-166 ms una volta per sessione [V]. Cura: disegnare il
    grafico visibile prima e gli altri al ritorno nel ciclo degli eventi, o un primo disegno più povero.
12. **`window.py:218`** `checks.count_out_of_shadows`: una posa intera in più per ogni sottocampo ombreggiato, dentro
    il lavoro dell'energia: 15-21 ms a Rho [V], proporzionale al costo della posa.
13. **`nearshade.py:387-393`** `_read` e `:345-364` `electrical`: 0,12 s per 16 stringhe (quattro letture avanzate
    per stringa su tabelle float32) [V]. Cura: una sola lettura per tutti i moduli e somme per stringa con
    `np.add.reduceat`.
14. **`window.py:1649`** e `viewaids.py:168`: scansioni lineari dei moduli a ogni selezione (`sel = {...}`,
    `next(pm for pm in r.modules ...)`): millisecondi a 20.000, minori [V, I].

Quello che va bene e si tiene: la posa nel thread con il numero di generazione; la pianta con un solo elemento per
sottocampo e la cache per zoom (15 elementi a 20.000 moduli, passaggio del mouse 1-5 ms) [V]; la cache delle
formule e i grafici disegnati quando si vedono (il ritorno del calcolo blocca 59-75 ms invece di 2-2,6 s) [V]; la
cache in processo della tabella d'ombra (1 ms) [V]; le scritture atomiche e i file piccoli (3,4 kB, 0,3 ms a
leggere) [V]; i modi di vista (6-17 ms) [V].

## 7. Verdetto

**Che cosa si compila: niente.** Il solo ciclo caldo in Python puro del calcolo (`dispatch`) si elimina con un
cambio di algoritmo che dà 7,7 volte su quelle 156 chiamate (0,54 s -> 0,07 s) senza una dipendenza nuova [V]; numba
e Rust danno 58 volte sullo stesso pezzo, cioè 61 ms in più su un calcolo di 1,2 s, e costano rispettivamente 147 MB
con 0,45-0,65 s per processo e un toolchain C con wheel e CI per piattaforma [V, I]. L'altro collo (l'ombra) è già
in C dentro shapely: lì conta il numero di operazioni, non il linguaggio.

**Che cosa si riscrive per le prestazioni: niente per intero.** `evaluate` va riscritta per array (è il 34% del
calcolo a caldo oltre a `dispatch`) e `_layout_done` va spostato in gran parte nel thread; sono funzioni, non
moduli.

**Che cosa si vettorializza o si cambia di algoritmo**, in ordine di guadagno per fatica:
1. `dispatch` a stato vettoriale e riuso dell'anno 1: -0,5 s per calcolo [V]; mezza giornata, con il test di
   uguaglianza già scritto.
2. una sola `simulate` con l'effetto elettrico applicato a valle: -0,13 s a caldo, -0,27 s a freddo [V, I].
3. `evaluate` per array e maschere delle fasce una volta: -0,3-0,4 s [I].
   Con 1-3 il calcolo a caldo di Rho scende da 1,2-1,4 s a 0,4-0,6 s [I], sotto l'obiettivo; a freddo resta l'ombra.
4. `nearshade.shading` per cella, vettoriale: da 1,1 s a qualche decimo per Rho [I] e da 8-10 s a 1-2 s per 5.000 e
   20.000 [I]; è il lavoro più lungo (una giornata o due) e il solo che decida il calcolo sotto 10 s a 20.000.
5. `module_table` vettoriale e stabile tra una selezione e l'altra: -45-60 ms per clic sul progetto grande [V].
6. import pigri di pandas, matplotlib e pvlib: -0,7 s all'avvio [I]; tessere decodificate fuori dal filo principale:
   -75-113 ms all'apertura [V].
7. la posa con i corner in numpy: da 0,4-0,9 s a circa 0,1 s per 5.000-20.000 moduli [I].

**La raccomandazione per R31, con i numeri.** La domanda era se Rust al posto di Python avrebbe dato velocità: sul
pezzo misurato la risposta è che Python con numpy, scritto nel modo giusto, dà il 90% del guadagno di un linguaggio
compilato (7,7 contro 58 volte sul ciclo, ma 0,07 s contro 0,01 s in assoluto) senza alcun costo di distribuzione,
e che i colli veri (ombra 1,1-10 s, economia 0,47 s, filo principale 0,1-1,2 s) sono questioni di algoritmo e di
dove gira il codice, non di linguaggio. Compilare `dispatch` con numba o Rust è da non fare; se mai tornasse
l'esigenza di un nocciolo compilato (un motore d'ombra per modulo e per cella, oltre quello che shapely vettoriale
può dare), la via con il costo minore è numba nel thread del calcolo con la cache, e Rust solo con una CI già
pronta per piattaforma.

## 8. Non fatto, e da provare sul PC di Daniel

- **Rust (variante e)**: non misurata. La compilazione del crate si ferma al linker: la WSL non ha `gcc` né
  `glibc-devel` e installarli è fuori dal mandato (comandi in 4.4); su Windows non ci sono rustc né MSVC. Il
  numero atteso è quello di numba [I].
- **Memoria del processo** (working set) nei tre progetti generati: lo script la leggeva male (0 MB); i numeri
  del rapporto sono i picchi di `tracemalloc`, che non contano gli oggetti GEOS di shapely né gli elementi Qt.
  Lo script è corretto, la corsa non è stata ripetuta per il limite di tempo della sessione.
- **Scalabilità con la seconda verifica**: `shading_check.py` è stato lanciato solo a 4.964 moduli; a 20.493 vale la
  misura di `scalabilita.py` (3 ripetizioni) senza la controprova per vettore.
- **La prima computazione della sessione** (2,95-3,5 s nel probe contro 2,1-2,5 s a freddo in `energia_tempo.py`):
  la differenza è attribuita ai primi import nel thread (`scipy.optimize`, pvlib, shapely) per deduzione, non per
  misura.
- **Schermo vero**: tutte le misure di oggi sono offscreen (3D in software). Il probe sul secondo schermo
  (`MERIDIANA_TEST_SCREEN=1`, `probe.py` dal 22/10 con i tre ritocchi della copia in scratchpad) darebbe i blocchi
  reali di `_show_3d` e `_layout_done` con Direct3D; il 22/10 la costruzione della finestra costava 494-862 ms sullo
  schermo contro 271 ms offscreen oggi.
- **La memoria del processo** nei tre progetti generati: lo script è corretto, i numeri sopra sono di `tracemalloc`.
- `probe.py` del 22/10 non gira più così com'è sul codice di oggi (`checks._count_out_of_shadows` rinominata, i campi
  delle quantità, lo stub del 3D senza `backend`): la copia corretta sta nella scratchpad di questa sessione; vale la
  pena portare i tre ritocchi nel file di `meridiana-prove` (fuori dal mandato di questa sessione).

## 9. File di questa prova

In `C:\Users\utente\dev\meridiana-lavoro\docs\studio\18-prove\`:
`C-prestazioni.md` (questo), `carico.py`, `dispatch_varianti.py`, `dispatch_rs\` (Cargo.toml, pyproject.toml,
src\lib.rs, .gitignore), `energia_tempo.py`, `avvio.py`, `scalabilita.py`, `shading_check.py`, e i risultati
`profilo_energia-risultati.txt`, `energia_tempo-risultati.txt`, `dispatch_varianti-risultati.txt`,
`avvio-risultati.txt`, `scalabilita-risultati.txt`, `probe-offscreen-risultati.txt` con i quattro `results.json`
del probe in `probe-offscreen\`. Niente è stato cambiato in `src/`, `tests/`, `po/`, `data/`, `tools/` né nei
documenti esistenti; nella WSL sono stati scaricati i crate di pyo3 e numpy in `~/.cargo/registry` (3,5 MB).
