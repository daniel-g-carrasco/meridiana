# Incarico 2 per Kimi: le correzioni approvate (25/10/2026)

Sei al lavoro su Meridiana, il programma di Daniel Grasso (ingegnere elettrico, Italia) per progettare impianti
fotovoltaici: Python 3.12+, Qt 6.12 con PySide6 6.12.0 e Qt Quick 3D, pvlib 0.16.1, shapely; GPL-3.0-or-later;
repository pubblico github.com/daniel-g-carrasco/meridiana. Un altro assistente (Claude) lo sviluppa ogni giorno.

Questa è una sessione nuova. Stamattina, in un'altra sessione, hai scritto una revisione indipendente in cinque
rapporti: sono in docs/revisioni (kimi-0-riepilogo.md, kimi-1-window.md, kimi-2-vita-qt.md, kimi-3-armonia.md,
kimi-4-testi.md, kimi-5-prove.md). Leggi prima il riepilogo, poi il rapporto di ogni punto che correggi. Daniel
li ha letti e Claude li ha verificati, ripetendo le tue prove sul PC Windows e su questo portatile: gran parte è
confermata, alcune diagnosi e proposte cambiano. Ora fai le correzioni nella forma scritta qui sotto: dove
differisce dal tuo rapporto, vale questa.

## Dove lavori
- Un portatile Linux con sistema immutabile («Lucciola», Fedora 45 su base Universal Blue, compositore Niri).
  Non installare né modificare nulla nel sistema: niente dnf, rpm-ostree, sudo, flatpak, né pacchetti nel
  Python o in Homebrew. Non creare contenitori né immagini. Se ti manca uno strumento, scrivilo e vai avanti.
- Due cartelle, entrambe sul ramo git kimi-revisione: ~/dev/meridiana-kimi (Meridiana) e
  ~/dev/qt-app-template-kimi (il modello grafico qtkit, estratto da Meridiana). Non scrivere altrove: non in
  ~/dev/meridiana (la copia di prova di Daniel, che si aggiorna da sola a ogni avvio), non nelle cartelle di
  Meridiana sotto ~/.config, ~/.local/share, ~/.local/state, ~/.cache, non in ~/fvtest. Non leggere ~/.ssh,
  ~/.gnupg, le credenziali di git e gh, gli altri repository della home.
- Il push è disattivato: non provarci e non cambiare i remote. Mai merge su altri rami, mai rebase, reset --hard
  o force.

## Regole di casa
- Leggi CLAUDE.md nella radice di Meridiana e quello del modello: valgono anche per te. Codice, commenti e
  messaggi di commit in inglese; documenti in italiano; mai il trattino lungo U+2014 da nessuna parte; le
  decisioni sono di Daniel e quelle prese qui sotto non si riaprono; norme e leggi mai citate a memoria.
- Un commit per punto, identità Daniel Grasso <code@danielgrasso.com>
  (git -c user.name="Daniel Grasso" -c user.email=code@danielgrasso.com commit ...), messaggio in inglese che
  dice cosa e perché, nessuna attribuzione AI (niente Co-Authored-By, niente "Generated with").
- Commenti nello stile e nella densità del codice intorno. Non cambiare l'aspetto oltre a quanto scritto qui.
- Per ogni difetto: prima una prova che fallisce, poi la correzione che la fa passare.

## Come si provano le cose
- Interprete: ~/fvtest/venv314/bin/python (Python 3.14 di Homebrew, PySide6 6.12, pvlib 0.16.1, ruff), solo per
  eseguire, sempre con PYTHONPATH=src della cartella in cui lavori. Controlla prima che
  python -c "import meridiana; print(meridiana.__file__)" indichi ~/dev/meridiana-kimi/src.
- Meridiana: lint con python -m ruff check src tests tools. Prove offscreen, un gruppo per processo (finestra e
  widget nello stesso processo rompono il caricamento del plugin 3D), dalla cartella tests:
  QT_QPA_PLATFORM=offscreen python -m unittest discover -s <gruppo> -t .
  con i gruppi nucleo, calcoli, formati, esterni, widget, finestra. Il catalogo italiano va compilato prima:
  ~/fvtest/venv314/bin/python tools/compile_po.py (senza, il self-test e test_map_sources falliscono).
- Il modello: dalla sua radice, QT_QPA_PLATFORM=offscreen PYTHONPATH=src ~/fvtest/venv314/bin/python -m unittest
  discover -s tests (54 verdi oggi) e ruff check .
- Prima di ogni commit: ruff e i gruppi di prove toccati. Alla fine di ogni parte: la suite intera, tutti i
  gruppi, con i numeri.
- Traduzioni: testi sorgente in inglese con _(), traduzione in po/it.po, msgfmt --check su po/it.po prima di ogni
  commit che lo tocca.
- Mai aprire finestre sullo schermo e mai con le cartelle vere di Daniel: ogni script che importa meridiana
  imposta XDG_CONFIG_HOME, XDG_STATE_HOME, XDG_DATA_HOME e XDG_CACHE_HOME su una cartella temporanea dentro /tmp
  e QT_QPA_PLATFORM=offscreen. Offscreen la vista 3D non viene disegnata. La fluidità e l'aspetto sullo schermo
  vero li misura Claude.

## Parte 1: Meridiana (~/dev/meridiana-kimi)
1. Commit dei rapporti in docs/revisioni, compreso questo file (solo documenti).
2. Isolamento delle prove in tests/_setup.py: HOME e USERPROFILE su una cartella temporanea per tutta la suite,
   MERIDIANA_KOKORO_DIR tolta, così le tre prove della voce (widget/test_voice, due; finestra/test_assistant_chat,
   Spoken.test_without_an_engine) non trovano il Kokoro vero di ~/.local/opt/kokoro e nessuna prova avvia il suo
   processo. Verificalo qui, dove Kokoro c'è davvero.
3. La prova del fumetto (test_assistant_window, again()): in again() sostituisci survey con nothing_local come fa
   _setup.window, aspetta wait_until(not chat.surveying), poi win.assistant_chat._drop_survey() prima del
   ridimensionamento. Le altre verifiche della prova restano (< 260, domande nascoste, campo e conversazione
   visibili). Su Windows passava solo perché la ricerca dei modelli locali era ancora in corso.
4. La prova dell'accento (test_the_accent_shows_only_on_the_phase_in_hand_and_the_one_action): la diagnosi del
   focus non spiega il fallimento del CI. Claude ha riprodotto il punto del CI (1257,369, nel titolo del gruppo
   «Row pitch from the sun») accendendo l'antialiasing subpixel del testo: un pixel #87511e accanto a frange di
   colore. Correzione: un pixel conta come accento solo se almeno uno dei suoi quattro vicini è anche lui
   accento. In più ammetti l'anello del focus, ma solo per il campo d'inserimento attivo (QLineEdit, QSpinBox e
   simili), non per i contenitori. Aggiungi una prova che un'etichetta colorata d'accento per sbaglio viene
   ancora trovata.
5. La prova delle immagini 3D della relazione (report_3d): skip con motivo solo quando lo stderr contiene
   entrambi «No GLSL shader code found» e «Failed to build graphics pipeline state». Mai uno skip più largo: su
   Windows la prova disegna davvero.
6. Chiusura con la relazione in corso: in closeEvent chiama _cancel_report() (esiste già) e ferma l'anteprima
   (il timer preview_soon e il generatore preview_run). Prova: dopo la chiusura nessun file .part resta.
7. Timer con il contesto: QTimer.singleShot(ms, self, ...) nel nuovo tentativo di TileLoader, nella rimessa a
   fuoco di Properties e in Theme.apply. Prova per ognuno: l'oggetto distrutto prima che il timer scatti, nessun
   errore.
8. Aggiornamenti e IFC: le tre lambda che catturano la finestra (window.py vicino a 4258-4259 e 4520) diventano
   metodi legati, con lo stato che serve tenuto nel job o nella finestra. Prova.
9. QuickImage: solo la guardia «if self.held.quick is None: return» in _fit e in resizeEvent. Non cambiare gli
   accessori. Il caso del timer dello screenshot non è confermato: non toccarlo. SystemAccent: lascialo così.
10. Traduzioni dei messaggi della posa: aggiungi N_ a i18n.py (segna senza tradurre; la parola chiave è già in
    compile_po.py). BALLAST_WARNING e «no room left inside the margins» con N_ e _() dove si mostrano;
    l'errore dell'area sotto 1 m² con _() al raise. Prova con il catalogo italiano: il dettaglio nelle Verifiche,
    la riga delle Proprietà e il messaggio d'errore escono in italiano.
11. Gli altri messaggi che l'utente vede in inglese, solo questi: «not a Meridiana project», il file di una
    versione più nuova di Meridiana (formato N), gli errori di lettura dei file PVsyst («not a PVsyst text
    file…»), il sottofondo con «two distinct points», «damaged horizon profile». Le f-string diventano messaggi
    con {segnaposto}. Traduzioni in po/it.po nello stesso commit. Non toccare le validazioni interne di model.py,
    i guard di viewaids, roofs e tiles, la ricerca dei luoghi (è già tradotta a monte).
12. Le 105 voci del catalogo non più nei sorgenti: rimuovile con un parser che legge le voci (chiave msgctxt,
    msgid, msgid_plural), non tagliando il testo a blocchi (a po/it.po 7742-7743 due voci non hanno la riga vuota
    fra loro). Prova: il catalogo compilato è quello di prima meno esattamente quelle 105. Commit a sé.
13. «Posa» (scelta di Daniel): il msgid "Layout" (checks.py, l'area delle verifiche; phases.py, il gruppo della
    barra i cui pulsanti dicono già «Posa») si traduce «Posa»; le domande di Meridio che dicono «disposizione» per
    la posa dei moduli diventano «posa». «Disposizione» resta per la disposizione delle finestre e per
    l'orientamento del modulo (verticale, orizzontale).
14. Armonia senza cambiare un pixel: i colori di stato da theme_colors.STATUS invece dei doppioni (COLOURS di
    checks_page, i «#d03b3b» che sono esattamente STATUS["critical"]); Space, Radius, Icon e Button solo dove il
    significato è lo stesso (barra di stato, «?» dell'aiuto, icone delle fasi, PAD, AIR, INSET e RADIUS delle
    Verifiche, margini delle tessere); i colori di riserva da cards.default_tokens(); un solo CHART_MIN_HEIGHT;
    la carta della relazione in un solo modulo; nomi locali per i valori dei timer che non ne hanno. No: il
    catalogo Timing, i circa 35 nomi nuovi usati una volta, STATUS["info"] (cambia i colori di Meridio e delle
    stringhe), corrispondenze solo numeriche (22 come Size.COMPACT, 12 come Space.L e simili), i colori dei segni
    sulla pianta e nella 3D (restano fissi in entrambi i temi, R16).
15. e 16. FATTI DA CLAUDE il 25/10 sera (durate a 130 ms, pagine dell energia): saltali, non toccare
    i loro file per questi due scopi. Il punto 14 resta tuo: finiscilo come scritto sopra.

## Parte 2: il modello (~/dev/qt-app-template-kimi)
Leggi CLAUDE.md, README.md, docs/da-dove-viene.md (la storia degli allineamenti con Meridiana e gli adattamenti
voluti) e docs/sistema-grafico.md.
17. Rapporto docs/revisioni/kimi-template.md nel modello: cosa è ridondante, incoerente con le scelte attuali di
    Meridiana, più complicato del necessario, o resto specifico di Meridiana; le differenze con i moduli ui di
    Meridiana che non sono adattamenti documentati; dove l'interfaccia del pacchetto si può semplificare per chi
    lo riusa. Formato: file e riga, cosa, gravità, prova [V] o [I], correzione, rischio.
18. Applica al modello le correzioni della Parte 1 che valgono anche lì (timer con il contesto, prova
    dell'accento con la regola dei vicini, armonia senza cambiare un pixel, durate) e le semplificazioni del tuo
    rapporto che non cambiano l'aspetto. Un commit per punto, prove e ruff verdi; aggiorna da-dove-viene.md. Le
    semplificazioni che cambiano l'aspetto o l'interfaccia del pacchetto le lasci nel rapporto per Daniel.

## Parte 3: il peso del foglio di stile
19. Misura, non cambiare: Daniel pensa che il foglio di stile (ui/theme.py di Meridiana, circa 42 KB di QSS
    applicato a tutta l'applicazione) non sia la causa delle lentezze, e le misure di docs/prestazioni lo fanno
    pensare anche a Claude; verificalo con numeri. Quante regole e caratteri; il tempo di setStyleSheet e della
    prima lucidatura (polish) della finestra; il costo del disegno di una ventina di widget comuni con il foglio
    di stile e con il solo stile (ScrollStyle o Fusion) senza QSS, offscreen in raster, mediane su molte
    ripetizioni; quanti widget si rilucidano a un cambio di tema e a un cambio di proprietà dinamica (tone,
    primary); i selettori più costosi, se ce ne sono. Rapporto docs/revisioni/kimi-6-css.md con i numeri e una
    conclusione; proposte solo se qualcosa pesa davvero. Le misure sullo schermo vero le ripete Claude.

## Fine
Scrivi docs/revisioni/kimi-7-lavori.md in Meridiana: per ogni punto il commit (hash), cosa è cambiato, le prove
(rossa prima, verde dopo), i numeri della suite finale in entrambe le cartelle, cosa non hai fatto e perché.
Poi fermati: Claude rivede i commit prima che entrino nel ramo lavoro.

Lavora in autonomia dal punto 1 al 19 senza fermarti e senza chiedere conferme. Se una cosa non torna o non
riesci a verificarla, scrivilo in kimi-7-lavori.md e vai avanti. Prima si prova, poi si afferma.
