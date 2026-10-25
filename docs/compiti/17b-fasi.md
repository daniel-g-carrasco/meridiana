# Compito per una sessione: le fasi e la barra della fase (studio 17, tema B, riscritto dalla revisione 18)

Riscrittura del 23/10/2026 di `17b-strumenti.md`, che era scritto sulla direzione B1 mentre Daniel ha scelto B4 («bella la suddivisione in fasi») con il testo sotto le icone e l'opzione per toglierlo. Il progetto è `docs/design/interfaccia.md` (sezioni 2.1, 3.3, 3.4, 5.3, le contraddizioni C1, C5, C6, C8); le regole di lavoro sono quelle di `docs/compiti/fase-2.md`. Da lanciare dopo `18b-sessione.md` (la riga delle fasi e l'ispettore passano da `phases.py`, non più da `index == 0` e `TABS[index]` in `window.py`) e dopo `17a-superfici-controlli.md` (il fondo e i token della barra).

**Deciso da Daniel il 23/10/2026:** B4, le fasi numerate (1 Modello, 2 Impianto, 3 Producibilità, 4 Consumi, 5 Bilancio ed economia, 6 Relazione) con la barra della fase a gruppi etichettati; il testo sotto le icone come predefinito, con l'opzione «Testo sotto le icone» per toglierlo e rimetterlo; su un fianco sempre sole icone (R19); «Variante» nell'angolo destro della riga delle fasi.

## Passo 1: `phases.py` nel nucleo
1. `src/meridiana/phases.py`, senza Qt: la descrizione delle sei fasi (id, numero, titolo con `_()`, i gruppi con i comandi nell'ordine, l'ispettore della fase, le aree delle verifiche, le tre domande di Meridio) e le funzioni `by_id`, `next`, `previous`. I gruppi sono quelli del progetto (3.3): Modello = Disegna, Modifica, Posa; Impianto = Inverter, Stringhe; Producibilità = Calcolo, Confronto; Consumi = Dati; Bilancio = Componenti, Calcolo, Confronto; Relazione = Esporta, Varianti, Appunti. Niente Sole né Sfondo nella barra (C5: restano nelle viste).
2. Test del nucleo: ogni comando citato esiste in `shortcuts.py`; ogni fase ha un ispettore e almeno un'area di verifiche; i numeri sono 1-6 in ordine.

## Passo 2: la riga delle fasi
3. Il `QTabWidget` centrale resta e diventa la riga delle fasi: etichette «1 Modello», «2 Impianto», ..., stile a riga d'accento con il punto davanti alla fase attiva (studio 13); «Variante» (il `QComboBox` di oggi) nell'angolo destro con `setCornerWidget`. I numeri sono etichette, non tasti (C8): si cambia fase con Ctrl+Tab, Ctrl+PagGiù e Ctrl+PagSu e dalla palette («Vai a: Impianto»).
4. La fase 6 Relazione come guscio: la pagina con i pulsanti di oggi (Esporta la relazione, Confronta le varianti, Salva come nuova revisione, Copia le note) e l'ispettore «Elaborati» con lo stato di ciascuno; il contenuto pieno è il compito della Relazione (design §7).
5. `window.py`: `_tab_changed`, `_show_inspector` e ogni `index == 0` o `TABS[index]` leggono da `phases.py` (la sessione del 18b sa in che fase è).

## Passo 3: la barra della fase
6. Una `QToolBar` per fase in un `QStackedWidget` sotto la riga delle fasi, costruita da `phases.py`; i gruppi separati e con l'etichetta sotto (11 px, attenuata); i nomi dei comandi nei suggerimenti con il tasto; il pulsante pieno d'accento una volta per fase (Posa i moduli, Calcola).
7. Il testo sotto le icone: predefinito acceso, 68 px (icone 24 px, etichetta 12 px, aria 6 px, etichetta del gruppo 11 px); spento 44 px (icone 22 px, i gruppi come separatori con l'etichetta del gruppo). L'opzione «Testo sotto le icone» nel menu Vista e in Preferenze > Aspetto; la barra passa da sola alle sole icone quando l'altezza utile della finestra scende sotto 900 px (design 5.3), la preferenza può forzare.
8. La barra c'è in tutte le fasi, anche con due gruppi (le viste non saltano di 70 px a ogni cambio di fase).
9. La preferenza `toolbar` dei ritocchi («icons» o «text») cambia significato: «text» = etichette sotto sì, «icons» = no; migrazione delle impostazioni (versione nuova) con il test; la variante «a sinistra» (B2) resta come preferenza: a sinistra sempre sole icone, i gruppi come separatori.
10. La barra della vista (R27) resta in alto a sinistra dentro la scheda della vista, con 8 px di rientro e icone da 16 px (C6); una schermata di confronto con la barra della vista in basso a sinistra, da far vedere a Daniel (domanda 9 dello studio 18).

## Passo 4: la chiusura
11. Test della finestra: cambio di fase da tastiera e dalla palette; la barra giusta per ogni fase; l'opzione del testo; il passaggio automatico sotto 900 px; «Variante» nell'angolo; la fase Relazione con i suoi pulsanti.
12. `docs/funzionalita.md`, `docs/richieste.md` (R19, R27), il diario; i testi in `po/it.po`.

## Da provare sul PC di Daniel
- Le sei fasi con la barra sui due schermi (il verticale e il principale), con e senza testo; la barra della vista nelle due posizioni (le due schermate per la domanda 9).

## Fatto il 24/10/2026 (ramo `fasi`), note per chi prova
- I passi 1-3 sono un commit solo: la finestra non sta in piedi con il nucleo senza la riga delle fasi (ogni comando del registro deve avere la sua azione e un menu, e gli indici delle schede cambiano i posti di Meridio). Il passo 4 è il secondo commit.
- Le altezze della barra sono misurate, non fisse: Titillium Web a 12 px ha una riga di 19 px, quindi con il testo la barra è 66 px e senza 47 (il progetto diceva 68 e 44); il test le tiene entro quei limiti.
- I comandi dei compiti 16a-16d e della relazione (Edificio da modello, Fila, Sposta, Ruota, le stringhe, PVGIS a fianco, DXF, IFC4, CSV) sono in `phases.py` con il nome del compito (`planned`) e non compaiono nella barra: quel compito li collega e toglie il segno.
- Il punto 10 (schermata di confronto con la barra della vista in basso a sinistra) non si fa offscreen: sul PC, con la finestra vera, due schermate della fase Modello sullo schermo principale, una con la barra della vista in alto a sinistra com'è e una con la stessa barra spostata in basso a sinistra accanto alla barra di scala (`ViewBar.place` con `area.bottom()` al posto di `area.top()`), da far vedere a Daniel per la domanda 9 dello studio 18.
- La migrazione delle impostazioni (v10) porta tutti a «testo sotto le icone»: chi aveva scelto «solo icone» nei ritocchi deve risceglierlo (la vecchia «solo icone» era il predefinito, non si distingue da una scelta).
