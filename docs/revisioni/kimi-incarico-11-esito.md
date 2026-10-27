# Incarico 11: esito

## 1. La sessione nascosta e la base

[V] `tools/real_session.sh` crea un display Wayland privato, attende il suo socket, assegna quattro cartelle XDG nuove sotto `/tmp`, esegue il comando e chiude il compositore anche quando il comando fallisce. La prova con `false` ha restituito 1 e non ha lasciato processi. `REAL_SESSION_SIZE` cambia il monitor, `REAL_SESSION_COMPOSITOR` sceglie il compositore, `REAL_SESSION_DBUS=1` conserva il bus privato quando serve provarlo.

[V] GNOME Shell 51.0 apriva il socket ma non completava la sincronizzazione Wayland nemmeno con una `QApplication` vuota. Il registro del protocollo si fermava dopo `wl_display.sync`. Con il bus dei portali il blocco comprendeva anche questi errori esatti: `Error calling StartServiceByName for org.freedesktop.impl.portal.desktop.gtk: Timeout was reached` e `Not providing Settings portal: No working backend`. L'alternativa `--display-server` ha risposto esattamente: `Failed to configure: Can't run in display server mode headlessly`.

[V] Il sistema ha già `mutter` 51.0. Con lo stesso `--headless --wayland --virtual-monitor`, la finestra Qt minima si apre e si chiude subito. Il lanciatore usa quindi `mutter` quando è disponibile, altrimenti `gnome-shell`; si può forzare la scelta con `REAL_SESSION_COMPOSITOR=gnome-shell`. Non è stato installato nulla e non si è usato `offscreen` per il giro reale. Il programma usa Wayland, Qt 6.12.0 e la GPU AMD attraverso `/dev/dri/renderD128`.

[V] `tools/real_tour.py` apre `capannone()`, guida le sei fasi con clic di QTest, apre tutte le sezioni di File e lo chiude con Esc. Le 14 fotografie `docs/revisioni/foto/kimi11-giro-*.png` sono state aperte e guardate. Tempi e avvisi sono in `docs/revisioni/kimi11-giro.txt`.

Risultato del giro:

- [V] Il 3D mostra edificio, copertura e moduli in chiaro e in scuro, non è vuoto (`kimi11-giro-01-model-*.png`). Lo scheletro è sparito prima delle fotografie.
- [V] Tutte le fasi arrivano al clic; File si apre, le cinque sezioni cambiano e Esc torna al progetto. La foto a metà dell'apertura precedente è `kimi11-giro-file-meta.png`.
- [V] Grafici, pannelli e comandi restano leggibili nei due temi. Non si vedono sovrapposizioni o salti di disposizione nelle fotografie ferme.
- [V, bassa] Alcuni testi dei pannelli laterali sono abbreviati: per esempio «Riservato: mai inviato a un modello r...» in Modello e il titolo «Campi (i moduli posati, per orien...» in Producibilità. Sono visibili nelle foto del giro a 1600 px; non riguardano i nuovi strumenti.
- [V] Qt ripete `QWaylandTextInputv3::disableSurface ... Trying to disable ... but 0x0 is focused` ai cambi di fase e scrive una volta `QGraphicsGridLayout::removeAt: invalid index -1` entrando in Consumi. Non ho osservato un effetto associato nelle fotografie o nei comandi guidati; restano registrati, senza una diagnosi non riprodotta.
- [V] Alla fine non restano `gnome-shell`, `mutter`, `real_tour.py` o `dbus-run-session` del giro.

### Prove automatiche sulla base c207d1b

[V] Catalogo compilato prima delle prove e `meridiana.__file__` verificato dentro questo worktree. Ogni gruppo è stato eseguito in un processo proprio, offscreen:

| Gruppo | Esito |
|---|---:|
| nucleo | 790 prove, OK, 4 saltate |
| calcoli | 175 prove, OK |
| formati | 59 prove, OK |
| esterni | 6 prove, OK, 6 saltate perché gli ingressi esterni non sono richiesti |
| widget | 310 prove, OK, 1 saltata |
| finestra | 132 prove, OK |

[V] Non ci sono fallimenti della base da correggere e nessun commit di correzione separato è necessario. `ruff` sui due nuovi strumenti, `bash -n tools/real_session.sh` e `git diff --check` sono puliti.

## 2. R178: l'animazione della pagina File

[V] Ho fotografato tre proposte nella sessione Wayland reale, tutte di 180 ms e con curva `OutCubic`. I nomi `0, 25, 50, 75, 100` indicano la percentuale del tempo, non il valore della curva. Le 15 immagini definitive sono state aperte e guardate:

| Proposta | Fotogrammi | Giudizio |
|---|---|---|
| Dissolvenza e scorrimento di 16 px dal lato File | `foto/kimi11-file-scorrimento-{0,25,50,75,100}.png` | La scelta raccomandata e realizzata: il piccolo spostamento dà la provenienza senza spostare davvero i contenuti; il progetto resta leggibile durante il passaggio |
| Foglio che si scopre da sinistra | `foto/kimi11-file-foglio-{0,25,50,75,100}.png` | Più legato al gesto di aprire, ma il bordo netto taglia temporaneamente testi e pannelli; resta disponibile come `kind="sheet"` |
| Sola dissolvenza incrociata | `foto/kimi11-file-dissolvenza-{0,25,50,75,100}.png` | La più discreta, ma tutta la finestra cambia insieme e il passaggio è meno localizzato; resta disponibile come `kind="fade"` |

[V] La realizzazione è in `ui/motion.py`: `Entrance` e `enter()` usano due fotografie e un velo opaco, non `QGraphicsOpacityEffect`, maschere o ridisposizioni ai fotogrammi. `FilePage` usa `slide`; con «meno movimento» appare subito e la chiusura resta immediata. `ui/window.py` non disabilita più gli aggiornamenti durante l'apertura o la chiusura: la fotografia iniziale deve essere reale e il ridisegno non deve restare trattenuto.

[V] Le foto hanno riprodotto due difetti che le prove offscreen iniziali non vedevano: lo sfondo nero catturato con aggiornamenti disabilitati e il velo finale lasciato visibile da un ciclo `processEvents()`. Il primo è risolto catturando con aggiornamenti attivi, il secondo nascondendo il velo prima di `deleteLater`. Le prove ora confrontano anche i pixel prima e dopo e richiedono che il velo finale non sia visibile.

[V] Il giro completo è stato ripetuto dopo la correzione, in chiaro e scuro. `kimi11-giro-file-meta.png` mostra il passaggio reale in scuro, `kimi11-giro-file-aiuto.png` la pagina finale senza residui. Tutte le sezioni rispondono e Esc chiude. Le 23 prove di `test_design_system.py` passano, compresa quella nuova per animazione, pixel, chiusura e movimento ridotto. Tempi e valori dei fotogrammi sono in `kimi11-giro-file.txt`; il giro finale è in `kimi11-giro.txt`.

[V] `docs/design/sistema-grafico.md` descrive la nuova regola. Per il modello grafico condiviso, il punto 2 cambia `ui/motion.py` e aggancia `ui/file_page.py`; non cambia `ui/design.py`, `ui/phasebar.py` o `ui/theme.py`.

## 3. R180: i gruppi degli strumenti

### Inventario precedente

[V] L'inventario deriva da `phases.py`, dai comandi e dai suggerimenti di `shortcuts.py` e `ui/window.py` al commit `1581564`. «Mai» indica un comando senza tasto proprio, raggiungibile dal menu o dal pulsante. Ogni riga dice che cosa fanno gli strumenti e in quale momento servono.

| Fase e gruppo | Strumenti, tasti, funzione e momento d'uso |
|---|---|
| Modello, Disegna | Edificio (B): disegna il perimetro, all'inizio del modello. Modello (mai): crea un edificio da una forma parametrica, all'inizio o per aggiungere un corpo. Falda (P): disegna una falda libera, dopo il perimetro. Sottocampo (S): delimita la zona dei moduli, prima della posa. Esclusione (X): delimita ostacoli o corridoi, prima della posa. Fila (L): disegna una fila a mano, durante la posa manuale. |
| Modello, Modifica | Seleziona (V): sceglie oggetti e moduli, prima di ogni modifica. Sposta (M): sposta o copia la selezione, mentre si sistema il modello. Ruota (mai): ruota la selezione, nello stesso momento. Misura (D): controlla una distanza, durante disegno e verifica. Squadra (Q): regolarizza gli angoli della selezione, dopo un disegno libero. Rettangolo (R): costruisce un rettangolo con tre clic, durante il disegno. |
| Modello, Posa | Posa (mai): calcola i moduli del sottocampo scelto, dopo averne definiti geometria e parametri. Svuota (mai): toglie i moduli lasciando il perimetro, per rifare la posa. Riposa in automatico (mai): sostituisce anche le file manuali, solo quando si vuole ricominciare la posa. |
| Impianto, Inverter | Catalogo (mai): aggiunge un inverter, quando si compone l'impianto. Dimensiona (mai): sceglie numero e taglia dal rapporto DC/AC, dopo aver scelto il modulo e prima delle stringhe. |
| Impianto, Stringhe | Proponi (mai): crea una stringatura con la strategia scelta, dopo gli inverter. Completa (mai): collega solo i moduli rimasti fuori, dopo modifiche o stringhe manuali. Disegna (mai): costruisce una stringa a mano, quando serve un percorso preciso. Elimina tutte (mai): cancella tutte le stringhe dopo conferma, per ricominciare. |
| Producibilità, Calcolo | Calcola (F5): calcola l'anno della variante, quando il modello è pronto o è cambiato. Da PVGIS (mai): scarica clima e orizzonte e poi calcola, quando mancano o si aggiornano i dati del sito. |
| Producibilità, Confronto | Varianti (Ctrl+Maiusc+C): confronta i risultati delle varianti, dopo almeno un calcolo. «PVGIS a fianco» era già previsto ma non disponibile. |
| Consumi, Dati | Curva (mai): importa una curva misurata, quando ci sono dati orari o quartorari. Base (mai): sceglie origine e profilo dei consumi, prima del bilancio energetico. |
| Bilancio, Componenti | Batteria (mai): sceglie un accumulo dal catalogo, prima di calcolare il bilancio con accumulo. |
| Bilancio, Calcolo | Calcola (F5): calcola produzione, consumi ed economia, quando si valuta la variante. |
| Bilancio, Confronto | Varianti (Ctrl+Maiusc+C): confronta i risultati economici, dopo il calcolo delle varianti. |
| Relazione, Esporta | Relazione (Ctrl+E): scrive il PDF, alla consegna. IFC4 (mai): esporta il modello BIM, per il coordinamento. CSV (mai): esporta il registro orario, per analisi e verifiche. «DXF» era previsto ma non disponibile. |
| Relazione, Varianti | Confronta (Ctrl+Maiusc+C): confronta le varianti, prima di scegliere quella da consegnare. Revisione (Ctrl+Maiusc+R): salva una copia revisionata, per conservare una consegna o uno stato. |
| Relazione, Appunti | Copia le note (mai): copia le regole applicabili con le fonti, mentre si integra la relazione. |

### Regole e proposta

[V] Le regole applicate sono uguali per tutte le fasi: gruppi ordinati secondo il lavoro da sinistra a destra; da due a cinque strumenti disponibili per gruppo; nomi uguali per funzioni uguali; un comando in un solo gruppo della stessa fase; i comandi rari restano nei menu, nelle Proprietà o negli ispettori. I tasti non cambiano. Gli strumenti futuri «PVGIS a fianco» e «DXF» conservano il loro posto ma non entrano nel conto perché non compaiono ancora nella barra.

| Fase | Prima | Dopo |
|---|---|---|
| Modello | Disegna: Edificio, Modello, Falda, Sottocampo, Esclusione, Fila. Modifica: Seleziona, Sposta, Ruota, Misura, Squadra, Rettangolo. Posa: Posa, Svuota, Riposa. | Disegna: Edificio, Modello, Falda, Sottocampo, Esclusione. Modifica: Seleziona, Sposta, Ruota. Precisione: Misura, Squadra, Rettangolo. Posa: Fila, Posa, Svuota. |
| Impianto | Inverter: Catalogo, Dimensiona. Stringhe: Proponi, Completa, Disegna, Elimina tutte. | Inverter invariato. Stringhe: Proponi, Completa, Disegna. |
| Producibilità | Calcolo: Calcola, Da PVGIS. Confronto: Varianti. | Calcolo invariato. Confronto: Nuova variante, Varianti. |
| Consumi | Dati: Curva, Base. | Dati: Base, Curva. |
| Bilancio | Componenti: Batteria. Calcolo: Calcola. Confronto: Varianti. | Calcolo: Batteria, Calcola. Confronto: Nuova variante, Varianti. |
| Relazione | Esporta: Relazione, IFC4, CSV. Varianti: Confronta, Revisione. Appunti: Copia le note. | Confronto: Nuova variante, Confronta. Esporta: Relazione, IFC4, CSV, Revisione, Copia le note. |

Motivo di ogni spostamento:

| Fase | Spostamenti e perché |
|---|---|
| Modello | Fila va in Posa perché costruisce moduli, non il perimetro; così Disegna scende da sei a cinque strumenti. Misura, Squadra e Rettangolo formano Precisione: sono aiuti geometrici, diversi da Seleziona, Sposta e Ruota, e Modifica scende da sei a tre. Riposa esce dalla barra perché distrugge le file manuali e serve raramente: resta in Disegna e nelle Proprietà. |
| Impianto | Elimina tutte esce perché è un ripristino raro e confermato: resta in Calcola e nel pannello Stringhe. Gli altri strumenti seguono già l'ordine inverter, proposta, completamento, disegno manuale. |
| Producibilità | Nuova variante entra prima di Varianti: prima si crea l'alternativa, poi la si confronta. Il gruppo mantiene il nome Confronto usato nelle altre fasi. |
| Consumi | Base precede Curva: prima si sceglie la provenienza dei dati, poi, se serve, si importa la curva. |
| Bilancio | Batteria entra in Calcolo perché è un dato dello stesso calcolo ed elimina un gruppo con un solo strumento. Nuova variante entra in Confronto come in Producibilità. |
| Relazione | Varianti diventa Confronto, con lo stesso nome e gli stessi due comandi delle altre fasi, e precede Esporta perché la scelta viene prima della consegna. Nuova variante completa il percorso. Revisione e Copia le note entrano in Esporta: producono o preparano consegne, quindi non richiedono due gruppi separati, uno dei quali con un solo strumento. |

[V] La descrizione ordinata vive in `phases.py`; `ui/phasebar.py` la disegna senza regole specifiche per fase. `ui/icons.py` aggiunge solo il simbolo «Nuova variante» e `ui/window.py` lo collega all'azione esistente. Le prove controllano ordine, nomi, limiti dei gruppi, assenza di duplicati e presenza dei comandi rari soltanto fuori dalla barra. Non è cambiato alcun tasto.

### Fotografie prima e dopo

[V] `tools/real_tour.py --toolbars LABEL` fotografa la sola scheda della barra, senza ritagli arbitrari. Ho raccolto 72 fotografie «prima» e 72 «dopo» in sessioni Wayland reali con la stessa procedura: sei fasi, temi chiaro e scuro, larghezze 1280, 1600 e 1920, testo Medio e Grande. I nomi sono `foto/kimi11-strumenti-{prima,dopo}-FASE-TEMA-LARGHEZZA-TESTO.png`; tempi e avvisi sono in `kimi11-giro-prima.txt` e `kimi11-giro-dopo.txt`.

[V] Ho aperto tutte le 144 immagini in coppie prima/dopo e, alla dimensione originale, i casi più stretti e i nuovi gruppi. Le etichette restano intere, i titoli dei gruppi sono centrati, nessun gruppo si sovrappone o esce dalla scheda. Modello a 1280 con testo Grande, il caso più carico, entra con spazio libero a destra (`kimi11-strumenti-dopo-model-{chiaro,scuro}-1280-grande.png`). Relazione conserva tutti i comandi leggibili (`kimi11-strumenti-dopo-report-{chiaro,scuro}-1280-grande.png`). I due temi mantengono contrasto e separatori. Non ci sono stati scatti o ridisposizioni: gli strumenti cambiano subito come già richiesto dal sistema grafico. Gli avvisi Wayland registrati sono gli stessi `QWaylandTextInputv3::disableSurface` del giro iniziale, senza nuovi errori attribuibili alle barre.

[V] Alla fine del giro non restano il compositore, `real_tour.py` o la sua sessione D-Bus.

[V] Prima del commit: `nucleo` 790 prove OK (4 saltate), `calcoli` 175 OK, `formati` 59 OK, `esterni` 6 OK (6 saltate), `widget` 310 OK (1 saltata), `finestra` 132 OK. La prima corsa di `finestra` ha trovato una sola aspettativa alla vecchia barra, aggiornata in `test_window.py`; la prova isolata e poi tutto il gruppo sono passati. `ruff check src tests tools` e `git diff --check` sono puliti.

## 4. Registro, traduzioni e moduli condivisi

[V] Le righe R178 e R180 di `docs/richieste.md` rimandano a questo esito e sono segnate «fatto sul ramo kimi-incarico-11, da guardare con Daniel». `CHANGELOG.md` descrive i due cambiamenti. Il catalogo contiene la nuova etichetta inglese `Precision`, tradotta «Precisione»; le altre etichette riusano voci già tradotte.

Per il modello grafico condiviso:

| Modulo | Cambiamento e motivo |
|---|---|
| `ui/motion.py` | Nuovi `Entrance` ed `enter()`: dissolvenza, scorrimento e scopertura riusabili, due fotografie sotto un velo opaco, durata e movimento ridotto del sistema. È il modulo da portare nel modello per R178. |
| `ui/file_page.py` | Aggancia la pagina File all'entrata condivisa, con lo scorrimento di 16 px scelto e la chiusura immediata. |
| `ui/phasebar.py` | Nessun cambiamento: la struttura esistente già disegna qualunque gruppo ordinato descritto dal nucleo. |
| `ui/design.py` | Nessun cambiamento: durate e spostamento usano i gettoni esistenti. |
| `ui/theme.py` | Nessun cambiamento: nessun nuovo colore o stile. |
| `ui/icons.py` | Aggiunto soltanto il nome `new_variant`, associato all'icona Lucide `copy-plus`, per riusare il simbolo dell'azione. |

[V] La riorganizzazione dei contenuti è in `phases.py`, non nel componente grafico: Claude può quindi portare il comportamento di `ui/motion.py` nel modello senza dipendenze fotovoltaiche e senza dover modificare `ui/phasebar.py`, `ui/design.py` o `ui/theme.py`.

[V] Il controllo finale degli artefatti ha verificato l'integrità di tutti i 173 PNG dell'incarico: 14 del giro, 15 delle proposte File e 144 delle barre. I quattro commit contengono ciascuno il proprio punto e usano l'identità di Daniel.

### Verifica finale

[V] Dopo registro, changelog e catalogo, ogni gruppo è stato ripetuto in un processo proprio: `nucleo` 790 prove OK (4 saltate), `calcoli` 175 OK, `formati` 59 OK, `esterni` 6 OK (6 saltate), `widget` 310 OK (1 saltata), `finestra` 132 OK. Totale: 1.472 prove superate, 11 saltate. `ruff check src tests tools`, `msgfmt --check`, `bash -n tools/real_session.sh` e `git diff --check` sono puliti; nessuna voce fuzzy. L'interprete importa `meridiana` da questo worktree e il catalogo compilato restituisce «Precisione».

[V] Le sessioni nascoste sono chiuse e non restano processi di Meridiana, `real_tour.py`, `real_session.sh`, GNOME Shell, Mutter o D-Bus avviati per le prove.
