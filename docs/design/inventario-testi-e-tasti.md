# Inventario dei testi e dei tasti

Daniel, 25/10/2026 (R121): «Riverifica l'armonizzazione e la standardizzazione: deve includere tutti i tasti e tutti i
testi. Vedo ancora troppe differenze tra dimensioni testo, stili, colori nelle varie sezioni (alcune differenze ci
devono essere ma non devono essere troppe e devono avere un senso, e devono essere salvate come stile, tipo i testi
nelle linguette sono troppo grandi)».

Questo documento è la misura fatta sulla finestra vera, prima e dopo il lavoro del 25/10/2026 (ramo `armonia`), con
quello che stava fuori dal sistema e perché. Le regole che ne sono uscite stanno in `sistema-grafico.md` (§2, il
catalogo `Text` e i tipi di tasti `Button`; §3, l'accento; §5, le barre di scorrimento).

## Come è stata fatta la misura

- [V] La finestra vera di Meridiana su Windows (piattaforma `windows`, non `offscreen`), tenuta fuori da ogni schermo
  (un filtro di eventi la sposta a sinistra dello schermo più a sinistra a ogni comparsa), con le cartelle di
  impostazioni, stato, dati e cache in una cartella temporanea: le impostazioni di Daniel non sono state lette né
  scritte. Schermo Dell P2415Q al 200 %, finestra 1600 x 960 punti logici, progetto «Prova capannone Rho», in
  italiano, tema chiaro e scuro.
- Il giro: le sei fasi, la pagina File (ogni sezione), il fumetto di Meridio con una conversazione, le schede
  Proprietà e Aiuto accorpate, un menu, le Preferenze (le sette pagine), il catalogo dei moduli, il manuale.
- Per ogni widget visibile: tipo, nome, testo, famiglia, grandezza in pixel e peso effettivi (`QFontInfo`), colore del
  testo letto dalla tavolozza e ricondotto al gettone del tema; per i pulsanti anche altezza, icona e stile; per gli
  elenchi il carattere della vista e delle voci. I testi disegnati dal codice (titoli delle schede, linguette delle
  fasi, sezioni, segni, pianta, cubo) sono stati letti intercettando `QPainter.drawText`.
- Prima: 1312 widget con testo per tema; dopo: 1307 (i conteggi della barra di stato disegnano il segno, i progetti
  recenti hanno nome e cartella in due etichette).
- Gli script stanno nella cartella di lavoro della sessione (`armonia/probe.py`, `giro.py`, `inventario_doc.py`); le
  schermate in `per-daniel\armonia\` (`prima-*`, `dopo-*`).

## Che cosa stava fuori dal sistema, e perché

| # | Che cosa | Dove | Perché | Ora |
|---|---|---|---|---|
| 1 | **Segoe UI a 12 px** invece di Inter (allora a 14) | albero del Progetto, Verifiche, tabella del catalogo, elenco del manuale, anteprima di Aspetto, menu, suggerimenti, finestre di messaggio | Qt, quando si imposta lo stile (`QApplication::setStyle`, anche il primo foglio di stile ne imposta uno), ridà a elenchi, menu, suggerimenti, barra di stato e finestre di messaggio il carattere della piattaforma (Windows: Segoe UI 9 pt). Il tema caricava Inter prima di impostare lo stile. È il motivo per cui l'albero e le Verifiche sembravano più piccoli del testo dell'aiuto pur «essendo» a 14 | Inter come il resto (`body`): gli stili per classe di Qt rimessi dopo ogni stile (`theme.class_fonts`) |
| 2 | **Linguette a 15 e 14 px** | fasi 15 (la scelta 15 semigrassetto), grafici, schede accorpate e Preferenze 14; le Preferenze con la sottolineatura d'accento | il titolo era passato da 14 a 15 la sera del 25/10; ogni barra aveva il suo disegno | 13 come il testo (`control`, la fase in mano `strong`); tutte le barre come le pillole delle schede accorpate |
| 3 | **Tre pesi** (400, 600, 700) | testo ricco con `<b>` (aiuto, Meridio, intestazioni del rapporto, Impianto, Proprietà), manuale, strumenti della pianta, conteggi, cubo | `<b>` e `setBold` sono 700, i titoli 600 | due pesi: 700 non c'è più (`Type.BOLD` = semigrassetto, `design.strong`, `design.semibold`, il foglio dei documenti) |
| 4 | **15 px** fuori scala | titoli delle schede, voci e guida della pagina File, titoli dei riquadri File | la scala aveva un 15 per «titoli di scheda e linguetta» | 14 semigrassetto (`title`) per i titoli delle schede e dei riquadri File, 13 (`body`, `description`) per voci e guida |
| 5 | **10 px** | titoli dei gruppi della barra della fase | una grandezza solo per loro | 11 maiuscolo semigrassetto (`label`), come le sezioni |
| 6 | **9 px** (sotto il minimo di 10) | il numero nei segni dell'albero (« ! 13») | ricavato dall'altezza della riga (0,55 x 17) | 11 (`label`) |
| 7 | **Barra di stato a 14** | parole e pulsanti | il documento diceva 12, ma un carattere dato alla barra non arriva ai suoi figli sotto il foglio di stile | 12 (`secondary`), dato a ogni suo widget (`design.set_text_all`) |
| 8 | **Conteggi della barra di stato** in Segoe UI Symbol | «⚠ 1» | tutto il testo nel carattere dei segni | il segno disegnato come nelle Verifiche, il numero nel carattere del testo |
| 9 | **Manuale e note di versione** con titoli a 28 e 20 px | titoli del markdown | le grandezze di Qt per `#` e `##` | 22, 18 e 14 (`help_box.dress`) |
| 10 | **Fogli di stile per widget** con caratteri e colori | «?» dell'aiuto, testa e soggetto dell'aiuto, suggerimenti sotto i campi, pillole delle Verifiche, riquadri dei risultati, Meridio (`font-size: 11px`), anteprima di Aspetto (`font-weight: 600`) | ogni componente si era fatto il suo | regole del foglio globale per i colori (proprietà `tone`), caratteri dal codice |
| 11 | **Pulsanti alti 25, campi 27, numeri e date 30**, campi delle righe 22, «Correggi» 16, pillole 24-28 | ovunque | il foglio dava solo il margine interno: l'altezza veniva dal carattere | 28 per pulsanti e campi, 24 pillole e linguette, 20 i piccoli (`Button`) |
| 12 | **Scala e «N» sulla pianta** a 14 e 12 grassetto, **cubo** a 12 semigrassetto | sopra le viste | carattere della finestra | 12 (`secondary`) e 11 (`label`) |
| 13 | **Accento** come decorazione | selezione (pesca), strumenti accesi, linguette e voci scelte, riquadro chiave, «Correggi» delle righe, «File» sempre pieno, collegamenti dell'aiuto e delle stringhe, passaggio sulla barra della vista e sul cubo, arco dell'attesa | il colore scelto era anche il colore della selezione | solo cosa in mano e azione: vedi `sistema-grafico.md` §3 (R104) |
| 14 | **Barre di scorrimento** che spostano il contenuto | Proprietà, Dati, Verifiche, aiuto, pagine | la barra prendeva posto quando compariva | il posto è sempre tenuto (R100, `sistema-grafico.md` §5) |

Differenze che restano, con il loro senso (il testo a 13 px dalla sera del 25/10/2026, R123):
- 13 il testo e i comandi (linguette, pillole, pulsanti), 14 semigrassetto i titoli delle schede, 13 semigrassetto
  gruppi, righe e pulsanti, 12 ciò che accompagna, 11 le etichette in maiuscolo e le tacche dei grafici; 22 e 18 solo
  per cifre e titoli di pagina.
- I segni delle Verifiche (✔ ⚠ ✘ ℹ) restano nel carattere che li ha (Segoe UI Symbol su Windows): sono disegni, non
  testo (`theme.SYMBOL_FAMILY`).
- La pianta e la 3D tengono le loro scritte (quote, etichette delle stringhe): sono il disegno (R16).

## I numeri, prima e dopo

| | Prima | Dopo |
|---|---|---|
| Combinazioni di carattere (famiglia, grandezza, peso) sui widget | 11: Inter 10/600, 11/400, 11/600, 12/400, 14/400, 14/600, 15/400, 15/600, 22/600, Segoe UI 12/400, Segoe UI Symbol 14/400 | 7, tutte del catalogo: 11/400, 11/600 maiuscolo, 12/400, 13/400, 13/600, 14/600, 22/600 (18/600 solo nel manuale e nell'aggiornamento); più Segoe UI Symbol 13 per il «✕» di un inverter, un segno |
| Testi disegnati dal codice fuori scala | segni a 9 px, «N» 12 grassetto, scala 14, cubo 12/600, conteggi delle sezioni a 14 accanto all'etichetta a 11 | nessuno (restano i glifi dei segni, nel loro carattere) |
| Altezze dei pulsanti e dei campi | pulsanti 25, campi 22/27/30, strumenti 27-30, pillole 24-28, «Correggi» 16 | pulsanti e campi 28, pillole e linguette 24, piccoli 20 |
| Fogli di stile scritti dentro i widget con caratteri o colori | 126 occorrenze nel giro, di 8 tipi di widget (aiuto, Verifiche, riquadri, Meridio, Aspetto) | i colori dal foglio globale (proprietà `tone`), i caratteri dal codice |

## I testi, parte per parte

Ogni riga è un gruppo di widget con lo stesso carattere prima del lavoro (tema chiaro; lo scuro ha gli stessi
caratteri). «Fuori sistema» dice che cosa stava fuori dalle regole di allora; «Ora» è lo stile del catalogo che lo
stesso widget ha dopo, con grandezza, peso e colore misurati (`body/control`: le due hanno lo stesso carattere;
«non più visibile così»: il widget non c'è più in quella forma, per esempio il conteggio della barra di stato ora
disegna il segno).

| Parte | Tipo | Widget | Prima | Colore | N. | Esempi | Fuori sistema | Ora |
|---|---|---|---|---|---|---|---|---|
| Barra di stato | button | QToolButton | Inter 14/400 | text | 7 | Meridio |  | secondary (12/400, text) |
| Barra di stato | button | QToolButton | Segoe UI Symbol 14/400 | text | 7 | ⚠ 1 | sì: Segoe | non più visibile così |
| Barra di stato | button | QToolButton#panel-toggle | Inter 14/400 | text | 28 |  |  | secondary (12/400, text) |
| Barra di stato | label | QLabel | Inter 14/400 | text2 | 7 | Fai clic su un oggetto p |  | secondary (12/400, text2) |
| Catalogo | button | QPushButton | Inter 14/600 | text | 2 | Azzera i filtri; Chiudi |  | strong (13/600, text) |
| Catalogo | document | QTextBrowser | Inter 14/400 | text | 1 | 3Sun 3SHBGA-AF-470 Costr |  | body/control (13/400, text) |
| Catalogo | field | QComboBox | Inter 14/400 | text | 4 | Monofacciali e bifaccial; Qualsiasi cella; Tutti |  | body/control (13/400, text) |
| Catalogo | field | QDoubleSpinBox | Inter 14/400 | text | 4 | da 0; nessun limite; qualsiasi efficienza |  | body/control (13/400, text) |
| Catalogo | field | QLineEdit | Inter 14/400 | text | 6 | Costruttore, modello, se; Tutte le marche; da 0 |  | body/control (13/400, text) |
| Catalogo | label | QLabel | Inter 14/400 | text | 3 | -; 21.713 moduli; Potenza |  | body/control (13/400, text) |
| Catalogo | view | QTableView | Segoe UI 12/400 | text | 1 |  | sì: Segoe | body/control (13/400, text) |
| Finestre di dialogo | tabs | QTabBar#dock-tabs | Inter 14/400 | text | 1 | Proprietà / Aiuto |  | body/control (13/400, text) |
| Manuale | document | QTextBrowser | Inter 14/400 | text | 1 | 1. Modello Il Modello è  |  | body/control (13/400, text) |
| Manuale | view | QListWidget | Segoe UI 12/400 | text | 1 |  | sì: Segoe | body/control (13/400, text) |
| Meridio (fumetto) | button | QToolButton | Inter 14/400 | text | 4 | Locale; – |  | body/control (13/400, text) |
| Meridio (fumetto) | document | QTextBrowser | Inter 14/400 | text | 1 | Tu Quanti moduli ci sono |  | body/control (13/400, text) |
| Meridio (fumetto) | field | QLineEdit | Inter 14/400 | text | 1 | Chiedi a Meridio… |  | body/control (13/400, text) |
| Meridio (fumetto) | label | QLabel | Inter 11/400 | muted | 1 | Domande pronte: premi 1, |  | label (11/600, muted) |
| Meridio (fumetto) | label | QLabel | Inter 14/400 | muted | 6 | 1; 2; 3 |  | body/control (13/400, muted) |
| Meridio (fumetto) | label | QLabel | Inter 14/400 | text | 5 | <b>Meridio</b>; Che ne pensi di questa d; Dove recupero potenza se |  | body/control (13/400, text) |
| Pagina Bilancio | button | HelpButton#help-button | Inter 14/600 | muted | 10 | ? |  | label (11/600, muted) |
| Pagina Bilancio | button | QToolButton | Inter 14/400 | text | 2 | Tabella |  | non più visibile così |
| Pagina Bilancio | label | ElidedLabel | Inter 12/400 | muted | 10 | Autoconsumo; Autosufficienza; Bolletta, primo anno |  | secondary (12/400, text2) |
| Pagina Bilancio | label | QLabel | Inter 14/400 | muted | 11 | Scarica prima il meteo d |  | secondary (12/400, text2), body/control (13/400, text2) |
| Pagina Bilancio | label | QLabel | Inter 14/400 | text | 2 | <b>Consumi: coperti dall; <b>Produzione: autoconsu |  | non più visibile così |
| Pagina Bilancio | label | QLabel | Inter 22/600 | text | 10 | – |  | display (22/600, text) |
| Pagina Bilancio | tabs | QTabBar | Inter 14/400 | text | 1 | Bilancio / Anno / Bollet |  | body/control (13/400, text) |
| Pagina Consumi | button | HelpButton#help-button | Inter 14/600 | muted | 9 | ? |  | label (11/600, muted) |
| Pagina Consumi | button | QToolButton | Inter 14/400 | text | 1 | Tabella |  | non più visibile così |
| Pagina Consumi | label | ElidedLabel | Inter 12/400 | muted | 9 | Carico di base; Consumo all'anno; F1 |  | secondary (12/400, text2) |
| Pagina Consumi | label | QLabel | Inter 14/400 | muted | 18 | %; 15.149 kWh; 18.925 kWh |  | body/control (13/400, text2), secondary (12/400, text2) |
| Pagina Consumi | label | QLabel | Inter 14/400 | text | 1 | <b>Consumi mese per mese |  | non più visibile così |
| Pagina Consumi | label | QLabel | Inter 22/600 | text | 9 | 10; 111.700; 14 |  | display (22/600, text) |
| Pagina Consumi | tabs | QTabBar | Inter 14/400 | text | 1 | Mesi / Giorno tipo / Ann |  | body/control (13/400, text) |
| Pagina File | button | QPushButton | Inter 14/600 | text | 20 | Apri; Apri…; Copia |  | strong (13/600, text) |
| Pagina File | button | QToolButton#file-item | Inter 15/400 | text | 60 | Aiuto e manuale; Apri; Cataloghi | sì: 15 px | non più visibile così |
| Pagina File | button | QToolButton#recent-item | Inter 14/400 | text | 1 | progetto    C:\Users\Gra |  | non più visibile così |
| Pagina File | label | QLabel | Inter 14/400 | text | 20 |  |  | body/control (13/400, text) |
| Pagina File | label | QLabel#file-keys | Inter 12/400 | muted | 45 | Ctrl+,; Ctrl+N; Ctrl+O |  | secondary (12/400, muted) |
| Pagina File | label | QLabel#fpage-lead | Inter 15/400 | text2 | 5 | Come funziona Meridiana ; I moduli, gli inverter e; Quello che esce dal prog | sì: 15 px | body/control (13/400, text2) |
| Pagina File | label | QLabel#fpage-section | Inter 11/600 | muted | 8 | AIUTO; APERTI DI RECENTE; CATALOGHI |  | label (11/600, muted) |
| Pagina File | label | QLabel#fpage-title | Inter 22/600 | text | 5 | Aiuto e manuale; Apri; Cataloghi |  | display (22/600, text) |
| Pagina File | label | QLabel#ftile-format | Inter 11/400 | text2 | 15 | .OND; .PAN; .PRJ |  | caption (11/400, text2) |
| Pagina File | label | QLabel#ftile-name | Inter 15/600 | text | 20 | Anno tipo e orizzonte; Batterie; Curva di carico | sì: 15 px | title (14/600, text) |
| Pagina File | label | QLabel#ftile-text | Inter 14/400 | text2 | 20 | Dal servizio europeo PVG; Edifici, coperture, osta; Gli edifici del modello  |  | body/control (13/400, text2) |
| Pagina Impianto | button | QToolButton | Inter 14/400 | text2 | 1 | Sfondo |  | body/control (13/400, text2) |
| Pagina Impianto | button | ToolButton | Inter 14/400 | text2 | 6 | 3D; Affiancate; Agganci |  | body/control (13/400, text2) |
| Pagina Modello | button | QToolButton | Inter 14/400 | text | 4 | Giorno di progetto |  | body/control (13/400, text) |
| Pagina Modello | button | QToolButton | Inter 14/400 | text2 | 2 | Sfondo |  | body/control (13/400, text2) |
| Pagina Modello | button | ToolButton | Inter 14/400 | text2 | 14 | 3D; Affiancate; Agganci |  | body/control (13/400, text2) |
| Pagina Modello | field | QDateEdit | Inter 14/400 | text | 2 | 21 dic |  | body/control (13/400, text) |
| Pagina Modello | field | QLineEdit | Inter 14/400 | text | 2 | 21 dic |  | body/control (13/400, text) |
| Pagina Modello | label | QLabel | Inter 14/400 | text | 2 | 12:20 |  | body/control (13/400, text) |
| Pagina Modello | label | SteadyLabel#sun-short | Inter 14/400 | text | 2 | h 21,1° · az -0,5° |  | body/control (13/400, text) |
| Pagina Producibilità | button | HelpButton#help-button | Inter 14/600 | muted | 5 | ? |  | label (11/600, muted) |
| Pagina Producibilità | button | QCheckBox | Inter 14/400 | text | 2 | Ombre degli ostacoli del; Ombre dell'orizzonte lon |  | body/control (13/400, text) |
| Pagina Producibilità | button | QPushButton | Inter 14/600 | text | 1 | Scarica l'anno tipo e l' |  | strong (13/600, text) |
| Pagina Producibilità | button | QToolButton | Inter 14/400 | text | 1 | Tabella |  | non più visibile così |
| Pagina Producibilità | label | ElidedLabel | Inter 12/400 | muted | 5 | Energia all'anno; Indice di prestazione; PVGIS, secondo parere |  | secondary (12/400, text2) |
| Pagina Producibilità | label | QLabel | Inter 14/400 | muted | 6 | Scarica prima il meteo d |  | secondary (12/400, text2), body/control (13/400, text2) |
| Pagina Producibilità | label | QLabel | Inter 14/400 | text | 2 | <b>Produzione mese per m; Non ancora scaricato: PV |  | body/control (13/400, text) |
| Pagina Producibilità | label | QLabel | Inter 22/600 | text | 5 | – |  | display (22/600, text) |
| Pagina Producibilità | tabs | QTabBar | Inter 14/400 | text | 1 | Mesi / Perdite / Giorno  |  | body/control (13/400, text) |
| Pagina Relazione | button | QPushButton | Inter 14/600 | text | 3 | Confronta le varianti…; Copia le note per la rel; Salva come nuova revisio |  | strong (13/600, text) |
| Pagina Relazione | button | QPushButton | Inter 14/600 | view | 1 | Esporta la relazione (PD |  | strong (13/600, view) |
| Pagina Relazione | label | QLabel#muted | Inter 12/400 | text | 1 |  |  | secondary (12/400, text2) |
| Pagina Relazione | label | QLabel#muted | Inter 14/400 | text | 1 | Calcola la producibilità |  | body/control (13/400, text) |
| Preferenze | button | QCheckBox | Inter 14/400 | text | 9 | Aggancia la conversazion; Aggiornamenti: una volta; Mappa sotto la pianta: l |  | body/control (13/400, text) |
| Preferenze | button | QPushButton | Inter 14/600 | danger | 1 | Togli |  | strong (13/600, danger) |
| Preferenze | button | QPushButton | Inter 14/600 | text | 28 | Annulla; Imposta la chiave…; Leggi le capabilities |  | strong (13/600, text) |
| Preferenze | button | QPushButton | Inter 14/600 | view | 1 | Posa i moduli |  | strong (13/600, view) |
| Preferenze | button | QRadioButton | Inter 14/400 | text | 2 | Claude, con la tua chiav; Il modello locale, su qu |  | body/control (13/400, text) |
| Preferenze | field | QComboBox | Inter 14/400 | text | 19 | AutoCAD; Bronzo; Chiaro |  | body/control (13/400, text) |
| Preferenze | field | QLineEdit | Inter 14/400 | text | 20 | 19; Cerca un comando o un ta; Premi scorciatoia |  | body/control (13/400, text) |
| Preferenze | field | QSpinBox | Inter 14/400 | text | 1 | 19 |  | body/control (13/400, text) |
| Preferenze | group | Group | Inter 14/400 | text | 6 | Al sito del progetto; Anteprima; Dove pensa Meridio |  | body/control (13/400, text) |
| Preferenze | label | QLabel | Inter 14/400 | text | 58 | <span style='color:#b07a; <table><tr><td style='pa; Attribuzione |  | body/control (13/400, text) |
| Preferenze | label | QLabel | Inter 14/600 | text | 40 | Alto Adige: ortofoto 202; Amburgo: DOP 2024; Assia: DOP20 |  | strong (13/600, text) |
| Preferenze | label | QLabel#problem | Inter 14/400 | danger | 1 |  |  | body/control (13/400, danger) |
| Preferenze | label | QLabel#row-detail | Inter 14/400 | text2 | 44 | CC BY 2.5 IT; CC BY 4.0; CC BY 4.0, con un traffi |  | body/control (13/400, text2) |
| Preferenze | tabs | QTabBar | Inter 14/400 | text | 7 | Aspetto / Navigazione /  |  | body/control (13/400, text) |
| Preferenze | view | QListWidget | Segoe UI 12/400 | text | 1 |  | sì: Segoe | body/control (13/400, text) |
| Preferenze | view | QTreeWidget | Segoe UI 12/400 | text | 1 |  | sì: Segoe | body/control (13/400, text) |
| Riga delle fasi e barra della fase | button | QToolButton#file-chip | Inter 14/600 | view | 7 | File |  | strong (13/600, text) |
| Riga delle fasi e barra della fase | button | QToolButton#variant-add | Inter 14/400 | text2 | 7 |  |  | body/control (13/400, text2) |
| Riga delle fasi e barra della fase | button | QToolButton#variant-pill | Inter 14/400 | text2 | 7 | Base |  | body/control (13/400, text2) |
| Riga delle fasi e barra della fase | button | ToolButton | Inter 12/400 | text | 45 | A mano; Automatico; Base |  | secondary (12/400, text) |
| Riga delle fasi e barra della fase | button | ToolButton | Inter 12/400 | view | 4 | Calcola; Posa |  | secondary (12/400, view) |
| Riga delle fasi e barra della fase | label | QLabel | Inter 12/400 | muted | 1 | 8 stringhe su 4 ingressi |  | secondary (12/400, muted) |
| Riga delle fasi e barra della fase | label | QLabel | Inter 12/400 | text | 1 | 1 x Huawei SUN2000-50KTL |  | secondary (12/400, text) |
| Riga delle fasi e barra della fase | label | QLabel#group-title | Inter 10/600 | muted | 17 | Calcolo; Componenti; Confronto | sì: 10 px | label (11/600, muted) |
| Riga delle fasi e barra della fase | tabs | PhaseTabBar#phases | Inter 14/400 | text | 7 | 1 Modello / 2 Impianto / |  | body/control (13/400, text) |
| Scheda Aiuto | button | CloseButton | Inter 14/400 | text | 7 |  |  | body/control (13/400, text) |
| Scheda Aiuto | button | QToolButton#help-detach | Inter 14/400 | text | 7 |  |  | body/control (13/400, text) |
| Scheda Aiuto | button | QToolButton#help-pin | Inter 14/400 | text | 7 |  |  | body/control (13/400, text) |
| Scheda Aiuto | label | QLabel | Inter 14/400 | text | 14 | <a href='manual:1-modell; <a href='manual:2-impian; <a href='manual:3-produc |  | body/control (13/400, text) |
| Scheda Aiuto | label | QLabel#help-subject | Inter 14/600 | text | 7 | Bilancio ed economia; Consumi; Impianto |  | strong (13/600, text) |
| Scheda Progetto | button | CloseButton | Inter 14/400 | text | 7 |  |  | body/control (13/400, text) |
| Scheda Progetto | view | QTreeWidget#project-tree | Segoe UI 12/400 | text | 7 |  | sì: Segoe | body/control (13/400, text) |
| Scheda Proprietà / Dati | button | CloseButton | Inter 14/400 | text | 7 |  |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | button | HelpButton#help-button | Inter 14/600 | muted | 6 | ? |  | label (11/600, muted) |
| Scheda Proprietà / Dati | button | QCheckBox | Inter 14/400 | text | 22 | 1. Sintesi; 10. Allegati; 2. Sito e dati climatici |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | button | QPushButton | Inter 14/600 | text | 13 | Aggiungi file PDF…; Aggiungi un inverter dal; Dimensiona l'inverter da |  | strong (13/600, text), strong (13/600, view) |
| Scheda Proprietà / Dati | button | QPushButton | Inter 14/600 | view | 3 | Calcola |  | strong (13/600, view) |
| Scheda Proprietà / Dati | button | QRadioButton | Inter 14/400 | text | 4 | Annuo, per fascia; Curva misurata (CSV); Mese per mese e per fasc |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | button | QToolButton | Segoe UI Symbol 14/400 | text | 1 | ✕ | sì: Segoe | body/control (13/400, text) |
| Scheda Proprietà / Dati | field | QComboBox | Inter 14/400 | text | 16 | Altro; Automatico dalla potenza; Automatico: Altri usi, b |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | field | QDoubleSpinBox | Inter 14/400 | text | 43 | -1,00 %/a; -10,0 °C; 0 % |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | field | QLineEdit | Inter 14/400 | text | 54 | -1,00 %/a; -10,0 °C; 0 % |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | field | QSpinBox | Inter 14/400 | text | 6 | 12; 21; proposto |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | group | Group | Inter 14/400 | text | 17 | Accumulo; Campi (i moduli posati, ; Comunità energetica rinn |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | group | Group#lead | Inter 14/400 | text | 2 | Sito |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | group | InverterReference | Inter 14/400 | text | 1 | Inverter |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | label | QLabel | Inter 14/400 | muted | 2 | 50,0 kW AC · 4 MPPT; Verificate alle condizio |  | body/control (13/400, muted) |
| Scheda Proprietà / Dati | label | QLabel | Inter 14/400 | text | 118 | /; 1 x Huawei SUN2000-50KTL; 45,522600 |  | body/control (13/400, text), body/control (13/400, text2) |
| Scheda Proprietà / Dati | label | QLabel | Inter 14/600 | text | 1 | Copertura |  | strong (13/600, text) |
| Scheda Proprietà / Dati | label | QLabel#muted | Inter 14/400 | text | 2 | Copertina, indice e diec; File PDF dopo l'ultimo c |  | body/control (13/400, text) |
| Scheda Proprietà / Dati | label | QLabel#row-detail | Inter 14/400 | text2 | 1 | 188 moduli · 93,06 kWp · |  | body/control (13/400, text2) |
| Scheda Proprietà / Dati | label | QLabel#state-planned | Inter 14/400 | muted | 2 | non ancora |  | body/control (13/400, muted) |
| Scheda Proprietà / Dati | label | QLabel#state-todo | Inter 14/400 | text2 | 1 | da fare |  | body/control (13/400, text2) |
| Scheda Proprietà / Dati | label | QLabel#state-unavailable | Inter 14/400 | muted | 2 | non disponibile |  | body/control (13/400, muted) |
| Scheda Verifiche | button | CloseButton | Inter 14/400 | text | 7 |  |  | body/control (13/400, text) |
| Scheda Verifiche | button | QPushButton | Inter 14/600 | text | 21 | Chiedi a Meridio; Copia le note per la rel; Correggi |  | strong (13/600, text) |
| Scheda Verifiche | button | QToolButton#count | Inter 14/400 | text | 28 | 0; 1; 12 |  | body/control (13/400, text) |
| Scheda Verifiche | button | QToolButton#filter | Inter 14/400 | text | 21 | Per livello; Questa fase; Questo oggetto |  | body/control (13/400, text) |
| Scheda Verifiche | button | QToolButton#rowfix | Inter 14/600 | view | 7 | Correggi |  | body/control (13/400, text) |
| Scheda Verifiche | label | QLabel | Inter 14/400 | text | 14 |  |  | body/control (13/400, text), secondary (12/400, text2) |
| Scheda Verifiche | view | ChecksTree#checks-tree | Segoe UI 12/400 | text | 7 |  | sì: Segoe | body/control (13/400, text) |

## I tasti

| Parte | Pulsante | Prima: alto, carattere, colore | Ora: alto, carattere | N. |
|---|---|---|---|---|
| Barra di stato | QToolButton | 28, 14/400, text | 27, 12/400 | 7 |
| Barra di stato | QToolButton | 30, 14/400, text | - | 7 |
| Barra di stato | QToolButton#panel-toggle | 27, 14/400, text | 27, 12/400 | 28 |
| Catalogo | QPushButton | 25, 14/600, text | 28, 13/600 | 2 |
| Meridio (fumetto) | QToolButton | 27, 14/400, text | 27, 13/400 | 2 |
| Meridio (fumetto) | QToolButton | 28, 14/400, text | 27, 13/400 | 2 |
| Pagina Bilancio | HelpButton#help-button | 16, 14/600, muted | 16, 11/600 | 10 |
| Pagina Bilancio | QToolButton | 28, 14/400, text | - | 2 |
| Pagina Consumi | HelpButton#help-button | 16, 14/600, muted | 16, 11/600 | 9 |
| Pagina Consumi | QToolButton | 28, 14/400, text | - | 1 |
| Pagina File | QPushButton | 25, 14/600, text | 28, 13/600 | 20 |
| Pagina File | QToolButton#file-item | 34, 15/400, text | - | 60 |
| Pagina File | QToolButton#recent-item | 34, 14/400, text | - | 1 |
| Pagina Impianto | QToolButton | 27, 14/400, text2 | 27, 13/400 | 1 |
| Pagina Impianto | ToolButton | 27, 14/400, text2 | 27, 13/400 | 6 |
| Pagina Modello | QToolButton | 27, 14/400, text | 27, 13/400 | 4 |
| Pagina Modello | QToolButton | 27, 14/400, text2 | 27, 13/400 | 2 |
| Pagina Modello | ToolButton | 27, 14/400, text2 | 27, 13/400 | 14 |
| Pagina Producibilità | HelpButton#help-button | 16, 14/600, muted | 16, 11/600 | 5 |
| Pagina Producibilità | QCheckBox | 22, 14/400, text | 21, 13/400 | 2 |
| Pagina Producibilità | QPushButton | 25, 14/600, text | 28, 13/600 | 1 |
| Pagina Producibilità | QToolButton | 28, 14/400, text | - | 1 |
| Pagina Relazione | QPushButton | 25, 14/600, text | 28, 13/600 | 3 |
| Pagina Relazione | QPushButton | 25, 14/600, view | 28, 13/600 | 1 |
| Preferenze | QCheckBox | 22, 14/400, text | 21, 13/400 | 9 |
| Preferenze | QPushButton | 25, 14/600, danger | 28, 13/600 | 1 |
| Preferenze | QPushButton | 25, 14/600, text | 28, 13/600 | 28 |
| Preferenze | QPushButton | 25, 14/600, view | 28, 13/600 | 1 |
| Preferenze | QRadioButton | 22, 14/400, text | 21, 13/400 | 2 |
| Riga delle fasi e barra della fase | QToolButton#file-chip | 28, 14/600, view | 28, 13/600 | 7 |
| Riga delle fasi e barra della fase | QToolButton#variant-add | 21, 14/400, text2 | 24, 13/400 | 7 |
| Riga delle fasi e barra della fase | QToolButton#variant-pill | 24, 14/400, text2 | 24, 13/400 | 7 |
| Riga delle fasi e barra della fase | ToolButton | 43, 12/400, text | 43, 12/400 | 45 |
| Riga delle fasi e barra della fase | ToolButton | 43, 12/400, view | 43, 12/400 | 4 |
| Scheda Aiuto | CloseButton | 18, 14/400, text | 20, 13/400 | 7 |
| Scheda Aiuto | QToolButton#help-detach | 27, 14/400, text | 21, 13/400 | 7 |
| Scheda Aiuto | QToolButton#help-pin | 27, 14/400, text | 21, 13/400 | 7 |
| Scheda Progetto | CloseButton | 18, 14/400, text | 20, 13/400 | 7 |
| Scheda Proprietà / Dati | CloseButton | 18, 14/400, text | 20, 13/400 | 7 |
| Scheda Proprietà / Dati | HelpButton#help-button | 16, 14/600, muted | 16, 11/600 | 6 |
| Scheda Proprietà / Dati | QCheckBox | 15, 14/400, text | 15, 13/400 | 2 |
| Scheda Proprietà / Dati | QCheckBox | 22, 14/400, text | 21, 13/400 | 20 |
| Scheda Proprietà / Dati | QPushButton | 25, 14/600, text | 28, 13/600 | 13 |
| Scheda Proprietà / Dati | QPushButton | 25, 14/600, view | 28, 13/600 | 3 |
| Scheda Proprietà / Dati | QRadioButton | 22, 14/400, text | 21, 13/400 | 4 |
| Scheda Proprietà / Dati | QToolButton | 30, 14/400, text | 29, 13/400 | 1 |
| Scheda Verifiche | CloseButton | 18, 14/400, text | 20, 13/400 | 7 |
| Scheda Verifiche | QPushButton | 25, 14/600, text | 28, 13/600 | 21 |
| Scheda Verifiche | QToolButton#count | 24, 14/400, text | 24, 13/400 | 28 |
| Scheda Verifiche | QToolButton#filter | 24, 14/400, text | 24, 13/400 | 21 |
| Scheda Verifiche | QToolButton#rowfix | 16, 14/600, view | 20, 13/400 | 7 |

## I testi disegnati dal codice

| Disegnato da | Prima | Ora |
|---|---|---|
| AxisItem.drawPicture | 11/400 | 11/400 |
| cards.paintEvent | 15/600 | 14/600 |
| charts_pg.paint | 11/400 | 11/400 |
| marks.paint | 9/600, Segoe UI Symbol 17/700, Segoe UI Symbol 7/700, Segoe UI Symbol 9/700 | 11/600, Segoe UI Symbol 11/700, Segoe UI Symbol 17/700, Segoe UI Symbol 7/700 |
| phasebar._draw |  | 11/600, 13/400, 13/600 |
| phasebar.paintEvent | 11/600, 15/400, 15/600 |  |
| plan_overlays.paintEvent | 12/700, 14/400 | 11/600, 12/400 |
| plant_page.paintEvent | 12/400, 14/400 | 12/400, 13/400 |
| sections._paint_with_tail | 14/400 | 13/400 |
| sections.paint | 11/600, 14/400, Segoe UI Symbol 11/600 | 11/600 |
| style.drawComplexControl | 14/600 | 13/600 |
| sunbar.paintEvent | 14/400 | 13/400 |
| viewcube._draw |  | 11/600 |
| viewcube.paintEvent | 12/600 |  |

