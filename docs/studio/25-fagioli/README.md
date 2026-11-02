# Studio 25: i «fagioli»

Fable FB, 02/11/2026, ramo `r10-fagioli`, R322. Daniel: «continuano a non piacermi questi fagioli. Proponimi con
fable dei draft, ispirati ad altri elementi simili che ci sono in meridiana». Solo studio: nessun codice del programma.

Cosa c'è nella cartella:

- `README.md`: censimento delle pillole, perché stonano, da cosa partire, raccomandazione.
- `bozzetti.html`: i bozzetti con i gettoni veri del tema (`theme_colors.derive`, accento indigo come nelle foto di
  Daniel), chiaro e scuro affiancati, almeno tre proposte per ruolo con pro e contro. Si apre nel browser;
  `?only=a|b|c|l` mostra una sezione sola.
- `foto/sezione-a.png`, `-b.png`, `-c.png` (Chrome headless, 1400 px), `sezione-l.png` la tabella del linguaggio.

## 1. Dove compaiono le pillole, e con quale ruolo

Tutte da `Button.CHIP` (24 px, raggio 12, `ui/design.py`) e dalle regole `QTabBar::tab`, `QToolButton#filter`,
`#count`, `#variant-pill`, `QLabel#state-*` di `ui/theme.py`. Verificato nel codice e nelle foto 38, 39, 40, 45.

| Dove | Che cosa | Ruolo | File |
|---|---|---|---|
| Relazione, testa della pagina | «Esporta la relazione (PDF)…», «Confronta le varianti…», «Salva come nuova revisione», «Copia le note per la relazione» | azione | `ui/report_page.py` (sono `QPushButton`, 28 px raggio 6: non pillole in senso stretto, ma la fila di rettangoli grigi col testo lungo è ciò che Daniel vede; «Esporta» col fuoco ha l'anello d'accento) |
| Producibilità, Consumi, Bilancio ed economia | «Mesi», «Perdite», «Giorno tipo», «Come è calcolato»; in Consumi anche «Anno», «Settimana», «Durata»; «Tabella» a destra | scelta fra viste; «Tabella» è un interruttore | `ui/energy_pages.chart_card`, `ui/charts.py` (`toggle`) |
| Schede accorpate (Proprietà, Verifiche, Aiuto in una scheda) | le linguette | scelta fra viste | `ui/cards.py`, R109 |
| Angolo della riga delle fasi | le varianti «Base», «Est-ovest»…, «+», «…» | quale documento in mano | `ui/variant_bar.py`, R73 |
| Verifiche, testata | «Per livello ▾» | scelta fra viste (menu) | `ui/checks_page.py` (`view_button`) |
| Verifiche, testata | «✕ 2», «▲ 5», «✓ 31» | stato, e filtro per livello | `CountChip`, `ui/status_pill.py` |
| Verifiche, testata | «Questa fase», «Questo oggetto» | filtro sì/no | `phase_button`, `object_button` |
| Albero del progetto, sezioni | i segni a destra delle righe | stato | `ui/marks.py`, `ui/sections.py` |
| Relazione, consegne | «fatto», «da aggiornare», «da fare» | stato | `QLabel#state-*` |
| Pagina File | il formato dei file («.meridiana») | stato | `QLabel#ftile-format` |

Quattro ruoli diversi (azione, scelta fra viste, filtro, stato) con la stessa forma.

## 2. Perché stonano

- **Forma uguale per ruoli diversi.** Una pillola col bordo è «Per livello ▾» (apre un menu), «✓ 31» (un conteggio
  che filtra) e «Questa fase» (un interruttore): l'occhio non sa cosa aspettarsi dal clic. Le linguette dei grafici
  e le varianti sono la stessa pillola, ma una sceglie una vista e l'altra un documento.
- **Peso visivo.** Sei pillole piene in fila (Consumi) sono sei macchie grigie prima del grafico; nella Relazione
  quattro rettangoli pieni sono la prima cosa della pagina, più pesanti del contenuto che dovrebbero servire. Il
  sistema grafico chiede l'accento con misura (R104) e nessun pulsante pieno (R158), ma il grigio pieno ripetuto fa
  lo stesso effetto.
- **Testo lungo con i puntini.** «Esporta la relazione (PDF)…», «Copia le note per la relazione», «Come è calcolato»:
  una pillola è fatta per una parola; con una frase diventa una salsiccia. I puntini sono una convenzione da menu,
  non da pagina.
- **Doppioni.** La fase 6 ha già nella sua barra «Confronta», «Relazione», «Revisione», «Copia le note»
  (`phases.py`, gruppi Confronto ed Esporta): le quattro azioni della pagina sono le stesse, dette in modo diverso.

## 3. Da cosa partire: ciò che Meridiana ha già di coerente

- **La barra delle fasi** (`ui/phasebar.py`, `ToolGroup`): icona 24 sopra, parola `secondary` 12 sotto, gruppi
  separati da un filo con il titolino `GROUP` (10 px, maiuscole, `muted`); nessun fondo a riposo, `hover` all'8 %,
  acceso in `press`. È il linguaggio delle azioni.
- **La barra della vista** (`ui/viewbar.py`): strumenti a raggio 6, trasparenti, acceso in `press`. Il linguaggio
  degli interruttori.
- **Le intestazioni dei gruppi richiudibili** (`ui/style.py`, `Group`): banda `line_soft` per tutta la larghezza,
  chevron 10 px, `hover` sulla banda. Un titolo che si clicca senza sembrare un pulsante.
- **Le linguette delle fasi** (R84): la scelta unita al foglio sotto, il filo che scorre in 240 ms. Il linguaggio
  di «questa vista è aperta», da cui viene la linguetta sottolineata di B2.
- **La pista delle varianti** (R73): segmenti su un velo `field`, la scelta rialzata in `panel` col filo. Dice
  «uno fra N».
- **Le pillole dei conteggi e dei segni** (`ui/status_pill.py`, `ui/marks.py`): segno a sinistra, bordo, 24 px.
  Restano: dicono uno stato, e lì la pillola è giusta.
- **I campi a elenco** (velo `field`, raggio 6, 28 px): la scelta di un valore dove lo spazio manca.

## 4. Le proposte (dettagli e foto in `bozzetti.html`)

**(a) Azioni della Relazione.** A1 come la barra delle fasi dentro la pagina; A2 tutto nella barra della fase e la
pagina parte dal titolo («Relazione tecnica · anteprima · 12 pagine · aggiornata alle 16:42»); A3 intestazione di
scheda con la sola «Esporta PDF» e un «…»; A4 cambio minimo (parole corte, primario col bordo, gli altri senza velo).

**(b) Viste dei grafici.** B1 segmenti su una pista a raggio 6 (anche per le varianti); B2 linguette sottolineate,
solo testo, filo di 2 px nel colore del testo sul filo `line_soft` della scheda, «Tabella» strumento a icona e
parola a destra; B3 tendina accanto al titolo; B4 linguette a scheda come le fasi.

**(c) Filtri delle Verifiche.** C1 tendina per «Per livello» e caselle di spunta; C2 strumenti con icona, accesi in
`press`; C3 tendina più interruttori a raggio 6 con la spunta davanti quando accesi; C4 viste come linguette
sottolineate su una riga sopra.

## 5. Raccomandazione

- **(a) A2**: le azioni restano solo nella barra della fase (ci sono già), la pagina della Relazione parte dalla
  riga del titolo di A3; al più la sola «Esporta PDF» in pagina.
- **(b) B2**: linguette sottolineate per ogni scelta fra viste dentro una scheda (grafici delle tre pagine dei
  risultati, schede accorpate R109); «Tabella» come strumento; la barra delle varianti resta a segmenti ma a
  raggio 6 (B1), perché sceglie un documento e sta fuori dalle schede. Se Daniel non vuole un elemento nuovo: B1
  ovunque.
- **(c) C3**: «Per livello» come tendina, «Questa fase» e «Questo oggetto» come interruttori con la spunta, i
  conteggi a pillola invariati.

Il linguaggio che ne esce, una forma per ruolo: strumento a raggio 6 per un'azione; linguetta sottolineata (o
tendina se lo spazio manca) per scegliere una vista; interruttore a raggio 6 acceso in `press` con la spunta per un
filtro; segmenti su pista per il documento in mano; la pillola solo per uno stato.

## 6. Cosa cambierebbe nel codice (dedotto, non fatto)

- `Button.CHIP` resterebbe per stati e conteggi; una `Button.TAB` nuova (28 px? o 24 con il filo) e una classe
  `ui/tabs.py` che disegna la linguetta sottolineata con il filo che scorre (`Motion.NORMAL`); `chart_card` e le
  schede accorpate la usano al posto di `QTabBar::tab` a pillola.
- `ui/report_page.py`: via la fila dei pulsanti, dentro la riga del titolo; la barra della fase 6 rinomina
  «Relazione» in «PDF» se Daniel vuole.
- `ui/checks_page.py`: `view_button` diventa un campo a elenco; `phase_button` e `object_button` perdono il bordo e
  la pillola, prendono il raggio 6 e la spunta.
- `ui/variant_bar.py` e `ui/theme.py`: raggi 8 e 6 al posto di 14 e 12.
- Da portare nel modello `qt-app-template`: la linguetta sottolineata, l'interruttore con la spunta, la tabella del
  linguaggio nel sistema grafico (§4).

Non verificato: le proposte sono disegnate in HTML, non in Qt; le misure delle linguette (28 o 24 px, padding 10)
vanno provate sul programma vero.
