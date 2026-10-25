# Meridiana: stato dell'arte per funzioni e interfaccia

Ricerca del 21/10/2026. **[V]** = letto in fonte ufficiale (help, manuale, scheda o codice del produttore). **[I]** = fonte secondaria o deduzione. Le date sono quelle in pagina; dove mancano vale la consultazione del 21/10/2026.

**Metodo.** In locale non ci sono cataloghi di strutture FV: sono stati controllati `l'archivio locale delle norme\catalogs` e `<archivio aziendale>\LIBRERIE Impianti Elettrici\20-Fotovoltaico`. Quattro agenti hanno lavorato in parallelo (CAD, programmi FV in due gruppi, montaggi); KDE, GNOME e Qt sono stati letti direttamente. Limiti:
- gli help Zendesk di Aurora, HelioScope e OpenSolar rifiutano le pagine HTML: sono stati letti dall'API pubblica;
- Sun Ballast, Nextracker e REM Tec sono stati letti da copie Wayback;
- i forum Autodesk e Adobe non si sono potuti leggere.

Il rapporto di dettaglio sul disegno CAD, con i GUID delle pagine Autodesk, è `05a-disegno-cad-dettaglio.md`.

## 1. Principi e modelli UX

**KDE o GNOME.** Per un'app Qt il riferimento è la KDE HIG (https://develop.kde.org/hig/, senza data di revisione, © 2026).
- La HIG dice che Qt Widgets va bene per le «traditional desktop applications with complex interfaces», come KDevelop [V] (/hig/kde_app_design/).
- Per le app nuove consiglia QtQuick con Kirigami, ma i principi valgono anche per Widgets [V].
- Un editor su QGraphicsView con una vista Qt Quick 3D incorporata resta quindi una scelta coerente [I].
- Della GNOME HIG valgono i principi. I suoi modelli (header bar, niente menubar, componenti libadwaita) sono legati a GTK [I].

**Limite pratico.** I binding Python dei KDE Frameworks si trovano solo nei pacchetti di alcune distribuzioni Linux; la pagina non parla né di pip né di Windows [V] (https://develop.kde.org/docs/getting-started/python/python-bindings/).
- Coprono KXmlGuiWindow, KActionCollection, KToolBar, KMessageBox e KNotification.
- Non coprono KCommandBar né KMessageWidget.
- Per questo i modelli KDE vanno rifatti in Qt puro, con QMainWindow, QDockWidget, QToolBar e QUndoStack [I].

**Regole KDE da adottare [V]** (pagine /hig/...)
- **Filosofia.** «Simple by default, powerful when needed». Il caso d'uso comune (l'80%) deve essere semplice e ovvio. «Don't be afraid to pick your users.»
- **Primo impatto** (/simple_by_default/):
  - all'avvio deve esserci subito qualcosa da fare;
  - le viste vuote mostrano un'icona, una spiegazione e un pulsante d'azione;
  - wizard solo per il setup obbligatorio, e senza chiedere preferenze;
  - indicatore di avanzamento per le operazioni oltre 1 s, con la percentuale quando il conteggio è noto;
  - nelle app a progetto l'app ricorda la vista attiva e i file aperti.
- **Funzioni visibili.** «never rely exclusively on keyboard shortcuts or context menus to access functionality» (/powerful_when_needed/).
- **Annulla.** «Offer an undo for every action that removes content not trivial to re-add», con un avviso che non blocca.
- **Impostazioni:**
  - hanno effetto subito, senza riavviare;
  - quelle che servono solo ad accendere o spegnere una funzione sono «warning signs of sloppy design»;
  - niente pagine «Advanced»: meglio sottopagine o sezioni comprimibili.
- **Scorciatoie:**
  - una per ogni azione, oppure assegnabile dall'utente;
  - niente tasto Meta, gesti solo a due dita;
  - «never just a function key, as these can be hard to access on laptops» (/layout_and_nav/).
- **Menu e layout** (/layout_and_nav/):
  - il menu hamburger va bene fino a «about 15 items»; oltre ci vuole «a real menubar between the titlebar and toolbar»;
  - le voci che non servono si disabilitano, non si nascondono;
  - in un'app Qt Widgets: «KXmlGui is recommended» e «Sidebars can be implemented using QDockWidget»;
  - i controlli propri di una vista vanno in una barra secondaria sotto quella principale;
  - a destra, «Contextual Toolviews» per l'oggetto selezionato; sotto il contenuto, la barra di stato.
- **Stato ed errori** (/status_changes/):
  - il successo si vede dal cambiamento dell'oggetto, non da un messaggio;
  - gli errori si prevengono con campi strutturati e validati;
  - «All error messages must be actionable», meglio se con un'azione «Fix it»;
  - messaggio in linea nell'intestazione per i problemi della pagina; notifiche di sistema solo con l'app in secondo piano;
  - colori: blu per la selezione, arancione per gli avvisi e i valori non predefiniti, rosso per gli errori. «Don't rely on color alone».
- **Input** (/getting_input/):
  - lo Switch ha effetto immediato, la CheckBox alla conferma;
  - fino a 3 scelte: pulsanti radio; fino a 10: elenco a discesa; oltre: un elenco;
  - slider con spinbox per regolare prima grossolanamente, poi fine;
  - con un input non valido: messaggio in linea e pulsante di conferma disabilitato;
  - dialoghi solo per le decisioni immediate. «Don't display more than one dialog at a time.»
- **Contenuti e accessibilità** (/displaying_content/, /accessibility/):
  - una tabella quando ogni elemento ha 3 o più dati; alberi solo per dati già gerarchici in app tecniche;
  - pulsanti di rimozione sempre visibili, non solo al passaggio del mouse;
  - tutto deve funzionare da tastiera, con il focus ben distinto dalla selezione;
  - niente informazioni essenziali solo nei tooltip; nomi univoci per gli screen reader;
  - provare l'app con il font di sistema a 14 e con le animazioni spente.

**Palette dei comandi.** La HIG non ne parla.
- KXmlGuiWindow crea l'azione «Find Action…» con Ctrl+Alt+I. L'azione raccoglie i comandi di tutta l'app e mostra quelli dei sottomenu come «padre > figlio» [V] (https://invent.kde.org/frameworks/kxmlgui/-/raw/master/src/kxmlguiwindow.cpp).
- QGIS fa lo stesso con la «locator bar», su Ctrl+K e con prefissi di filtro [V] (https://docs.qgis.org/3.44/en/docs/user_manual/introduction/qgis_gui.html).

**GNOME HIG [V]** (https://developer.gnome.org/hig/principles.html, senza data)
- Principi: Design for People, Make it Simple, Reduce User Effort, Be Considerate. Dall'ultimo: «Allow destructive actions to be undone instead of asking for confirmation».
- Tastiera (/guidelines/keyboard.html):
  - «every action should also be possible with the keyboard»;
  - Ctrl+lettera, Shift+Ctrl per l'azione inversa;
  - «Do not use Alt for shortcut keys»; Super è del sistema;
  - Shift+F10 per il menu contestuale, Esc chiude menu e popover.
- Avvisi (/patterns/feedback/toasts.html): un toast per un evento singolo, spesso con «Annulla» dopo un'eliminazione; un banner per uno stato che dura.

**Qt [V]**
- QKeySequence::StandardKey dà le scorciatoie della piattaforma: «It is preferable to use standard shortcuts where possible» (https://doc.qt.io/qt-6/qkeysequence.html).
  - Ripeti è Ctrl+Y o Shift+Ctrl+Z su Windows, Shift+Ctrl+Z su KDE e GNOME.
  - Su KDE e GNOME anche Ctrl+D vuol dire Elimina: non usarlo per «duplica».
  - F11 è lo schermo intero su Windows e KDE.
- Annulla e ripeti (https://doc.qt.io/qt-6/qundostack.html, modulo QtGui):
  - QUndoStack, con le macro per raggruppare più modifiche in un passo;
  - mergeWith, che fonde un trascinamento in un solo passo;
  - setClean per lo stato «salvato» e QUndoView per mostrare la cronologia.

**Finestra proposta per Meridiana [I]**
- **In alto:** la barra dei menu completa, perché le azioni sono ben più di 15. Poi la barra principale (file, annulla, 2D/3D, sole) e, sotto, le opzioni dello strumento attivo.
- **A sinistra:** l'albero del progetto (Sito > Edificio > Falda > Campo > Sottocampo > Stringa) e i livelli (ortofoto, catasto, DSM, vincoli).
- **Al centro:** le viste 2D e 3D, con la stessa selezione.
- **A destra:**
  - le proprietà dell'oggetto, con le unità;
  - il pannello «Problemi», dove ogni verifica ha un pulsante «Correggi» e porta all'oggetto;
  - la cronologia degli annullamenti.
- **In basso:** la barra di stato con le coordinate, gli interruttori degli agganci (come in AutoCAD) e la scala.
- **Comandi:** «Trova azione…» con Ctrl+Alt+I e con Ctrl+K. Le eliminazioni non chiedono conferma e mostrano un avviso con «Annulla».

## 2. Disegno da CAD

**Cosa fanno i programmi di riferimento [V]**

**AutoCAD 2026** (https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/, pagine senza data)
- Valori predefiniti: APERTURE 10 in pixel logici, PICKBOX 3. Con OSNAPCOORD 2 le coordinate digitate vincono sugli snap.
- Snap polare: incrementi da 90° fino a 5°, più 10 angoli aggiuntivi, misurabili anche dall'ultimo segmento.
- Tab scorre gli snap candidati. Shift+tasto destro apre il menu snap per un solo punto.
- Puntamento: un punto si «acquisisce» fermandocisi sopra e viene segnato con «+». Il marker ha una forma per tipo: quadrato per l'estremo, triangolo per il medio, cerchio per il centro, X per l'intersezione.
- Override tenuti premuti: Shift inverte l'orto; Shift+A, Shift+Q e Shift+X attivano o disattivano snap, puntamento e polare; Shift+E, M e C forzano estremo, medio e centro.
- Input dinamico: si scrive la lunghezza, Tab, l'angolo, Invio; Tab blocca il campo e mostra un lucchetto; le coordinate sono relative di default, «#» le rende assolute e «@» relative; la freccia su richiama i valori recenti.
- Tasti: F3, F8, F10, F11, F12.

**SketchUp** (https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts, 29/09/2026)
- I punti di aggancio hanno un colore per tipo: verde l'estremo, ciano il medio, rosso il punto su uno spigolo, blu quello su una faccia. Gli assi sono rosso, verde e blu; parallelo e perpendicolare in magenta.
- Fermarsi su un punto «sveglia» l'allineamento con quel punto. Shift blocca la direzione.
- Le frecce bloccano gli assi: → rosso, ← verde, ↑ blu, ↓ parallelo o perpendicolare.
- Measurements box: si digita senza cliccare nel campo e si preme Invio, e si può correggere finché non si comincia altro; [x,y,z] sono coordinate assolute, <x,y,z> relative; «3x» e «3/» creano serie di copie.

**Onshape e Fusion** (https://cad.onshape.com/help/Content/constraints.htm, 15/10/2026)
- Onshape colora lo schizzo: blu se mancano vincoli, nero se è vincolato, rosso se ce ne sono troppi.
- Shift durante il trascinamento evita i vincoli automatici.
- Un valore digitato con Invio subito dopo una linea diventa una quota; una quota di troppo diventa di riferimento.
- Fusion mostra le quote di riferimento tra parentesi e non ammette schizzi con troppi vincoli [V]. Ctrl sopprime i vincoli automatici [I].

**QGIS**, un'app Qt su mappa (https://docs.qgis.org/latest/en/docs/user_manual/working_with_vector/editing_geometry_attributes.html, 10/08/2026)
- Campi d, a, x, y: la lettera imposta il valore, Ctrl o Alt+lettera lo blocca, Shift+lettera lo rende relativo.
- C entra in modalità costruzione. P dà la perpendicolare, premuto due volte la parallela.
- Distanza e angolo compaiono accanto al cursore. Backspace toglie l'ultimo vertice.
- Tolleranza di aggancio predefinita 12 px, marker magenta (dal codice).

**Altri**
- FreeCAD Draft: raggio di aggancio 8 px; l'aggancio «Near» perde contro gli altri; Shift vincola il tratto; X, Y e Z bloccano l'asse; «/» toglie l'ultimo punto.
- Inkscape: tolleranze di 20 px per oggetti e guide, 10 per la griglia, 5 per gli allineamenti.
- Bier e Stone, «Snap-dragging» (SIGGRAPH 1986, doi:10.1145/15922.15912): il cursore è attratto da allineamenti costruiti in automatico, e il punto agganciato si distingue dal cursore.

**Regole per Meridiana [I, salvo dove indicato]**
1. **Priorità degli agganci.** Vertice e intersezione; poi medio, centro della falda e perpendicolare; poi incrocio di guide, punto su spigolo, guida, griglia; infine il punto libero. A pari priorità vince il più vicino, e Tab scorre gli altri. Un margine di 2-3 px evita che l'aggancio salti avanti e indietro.
2. **Tolleranze in pixel di schermo**, convertite in metri a ogni movimento: 10 px per i punti, 6 per spigoli e guide, 3-5 per la selezione; tutti regolabili. Lo schermo ad alta risoluzione è già gestito da Qt, che lavora in pixel indipendenti dal dispositivo [V].
3. **Guide solo dalla geometria «svegliata»:** l'ultimo punto, i punti acquisiti (sosta di circa 400 ms o un tasto, massimo 5-7) e lo spigolo sotto il cursore. L'angolo polare si misura dagli assi dell'edificio o della falda, oppure dall'ultimo segmento.
4. **Riscontro visivo:** marker con la forma del tipo e un alone scuro, per restare leggibile sull'ortofoto; guide tratteggiate colorate per direzione, come in SketchUp; un'etichetta accanto al cursore con tipo, distanza e angolo; marker a dimensione costante con ItemIgnoresTransformations [V].
5. **Misure digitate:** una cifra apre il campo senza clic; Tab passa all'angolo e blocca il valore, Invio conferma, la freccia su richiama i valori recenti; di default lunghezza e angolo dal punto precedente; «;» separa i valori, perché la virgola è decimale; valore e Invio subito dopo un clic correggono l'ultimo segmento; «L;W» per i rettangoli; «x5» e «/5» per le serie; le coordinate digitate vincono sugli agganci.
6. **Tasti modificatori:**
   - Shift tenuto blocca la guida attiva; con l'orto acceso lo sospende, come AutoCAD.
   - Le frecce bloccano gli assi.
   - Ctrl tenuto sospende agganci e guide, come chiesto da Daniel.
   - Alt mai durante un trascinamento: su Niri in finestra, Alt+trascinamento sposta la finestra.
   - Super e Meta mai: Niri, KDE Plasma 6 e GNOME li usano col mouse [V], e la KDE HIG li vieta.
   - Mai funzioni su Shift premuto più volte: cinque pressioni attivano i Tasti permanenti di Windows [V].
7. **AltGr.** Sulla tastiera italiana «@» e «#» si scrivono con AltGr, che Windows trasmette come Ctrl+Alt. Il disegno non deve scambiarlo per «Ctrl tenuto», e servono prefissi che non richiedano AltGr.
8. **Tasti F.** Vanno tenuti quelli di AutoCAD, con un'alternativa modificatore+lettera per i portatili. F10 e F11 hanno già un significato (menu in GNOME, schermo intero in Qt).
9. **Polilinea.** Backspace o Ctrl+Z dentro il comando toglie l'ultimo vertice; «C» o un clic sul primo punto chiude la figura; Invio o tasto destro la termina; Esc procede a passi: svuota il campo, poi annulla il segmento, poi esce dal comando.
10. **Coordinate, non vincoli.** Gli agganci danno coordinate, come in AutoCAD; i legami permanenti si creano solo a richiesta.
11. **Vista 3D.** Stesse tolleranze sui punti proiettati, più l'aggancio «su faccia» per posare su falde e facciate.
12. **Navigazione.** Rotella per lo zoom sul cursore, tasto centrale per spostare la vista, Spazio+trascinamento sul touchpad; scorrimento fluido e gesti a due dita [V KDE]; su Niri il tasto Mod col tasto centrale appartiene al compositor [V].

## 3. Programmi FV di riferimento

Versioni: PV\*SOL premium 2026 R8 (22/09/2026), PVsyst 8.1.7 (30/09/2026), Sunny Design 6.x (manuale dalla 6.20).

Fonti: https://help.aurorasolar.com, https://help-center.helioscope.com, https://support.opensolar.com, i PDF di https://knowledge-center.solaredge.com, https://3d-help.valentin-software.com/pvsol/en/, https://www.pvsyst.com/help/, https://manuals.sma.de/SDesign/en-US/ e https://www.acca.it/software-fotovoltaico.

Legenda: S sì, P parziale, N no, nt non trovato. Le celle sono [V] salvo dove indicato [I].

| Funzione | Aurora | HelioScope | OpenSolar | SolarEdge | PV\*SOL | PVsyst | Sunny Design | Solarius |
|---|---|---|---|---|---|---|---|---|
| Tetto dal contorno, linee interne automatiche | S | N (solo piani) | S | S | S (tipi parametrici, estrusione) | P (solidi da comporre) | S (tipi da elenco) | S (BIM) |
| Bordi con tipo (gronda, colmo, displuvio, compluvio) | S | P | S (a colori) | S | S (spigoli numerati) | N | P | nt |
| Modello automatico | S (AI, LIDAR, drone) | P (adatta al LIDAR) | S (3D Google/Nearmap) | P (AI) | S (DSM Google; LiDAR solo Germania) | P (terreno) | P | P (terreno) |
| Formati importati | immagini, GeoTIFF, DSM | immagini, KMZ, .hor | immagini, .hor | DXF 2D a layer | 9 formati 3D | 3DS, DAE, PVC2 | OBJ, DAE (versione Pro) | DXF, DWG, IFC, SKP |
| Ostacoli con altezza e fascia di rispetto | S | S (anche simili, altezza dall'ombra) | S (libreria) | P | S | S | S | S |
| Distanza dai bordi, lato per lato | S (anche per località) | P (uguale su tutti i lati) | S (modelli per CAP) | S | S (per spigolo e attorno agli ostacoli) | N | P | nt |
| Percorsi antincendio, corridoi | S (automatici, IFC USA) | N | N | N | S | N | S (ogni N file) | nt |
| L'ombra esclude i moduli | S | S | P | P | P | N | P | P |
| Riempimento automatico | S (anche fino a un obiettivo di kWh) | S | S | S | S | S | S | S |
| Distanza tra le file calcolata | nt | S (4 grandezze collegate) | N | nt | S (solstizio, ore 12) | P | P | S |
| Est-ovest | nt | S | S | S [I] | S | S | S | nt |
| A terra / inseguitori | S / nt | S / S | S / solo calcolo | S [I] / nt | S / P | S / S | N / N | S / P |
| Pensiline / facciate | P / nt | S / con un espediente | nt | nt | N / S | N / S | N / N | S / S |
| Stringhe a mano / automatiche | S / S | N / S | S / S | S / S | S / S | S / S | S / S | N / S |
| Verifica tensioni con le temperature | P | S | S | P | S (70, 15, -10 °C) | S (60, 20, -10 °C) | P | P |
| Unifilare | S (Europa) | S (DXF) | S (modello italiano) | nt | S (con cartiglio) | P | S | S (DXF, DWG) |
| Formati esportati | DXF a layer | DXF, DAE | DXF, SVG | DXF | DXF, JSON | PDF | PDF, OBJ | DXF, DWG, IFC |

**Soluzioni UX da copiare [V]**
1. **Il bordo dice cos'è.** Con un clic uno spigolo diventa gronda, colmo, displuvio o compluvio; in OpenSolar ogni tipo ha un colore. Distanze e orientamento dei moduli si adeguano da soli (Aurora, OpenSolar, SolarEdge).
2. **Spigoli numerati** (PV\*SOL). Il numero sul disegno corrisponde alla riga della tabella delle distanze; c'è «tutti i lati», ci sono preset per tipo di montaggio, e la stessa distanza si applica attorno agli ostacoli.
3. **Regole per luogo, con precedenza.** In Aurora la regola del comune prevale su quella dello stato; in OpenSolar i modelli per CAP scelgono anche il tipo di montaggio in base alla pendenza.
4. **Vincoli normativi come oggetti a sé.** In Aurora i percorsi antincendio sono separati dalle distanze dai bordi e si posano in automatico; gli errori si segnalano a colori senza bloccare: giallo per una distanza non rispettata, rosso per una sovrapposizione.
5. **Distanza tra le file con quattro grandezze collegate**: distanza, rapporto tra lunghezza e altezza, GCR e ore senza ombra in un giorno scelto; modificandone una si aggiornano le altre (HelioScope).
6. **Ombra che si spiega.** HelioScope toglie i moduli in ombra tra le 10 e le 14 del solstizio; OpenSolar ha una griglia di 12 mesi per 24 ore (un clic su un'ora mostra le ombre di quel momento); PVsyst mostra la vista dal sole con F6.
7. **Stringhe disegnate passando sui moduli**, con il colore che dice subito se sono corrette: in Sunny Design rosso se libera, giallo se collegata, verde se corretta. Ogni modulo ha un codice unico (I.M.S.P in PV\*SOL, 1A.1.3 in Sunny Design); in PV\*SOL le scelte fissate con un segnaposto restano anche quando si ricalcola.
8. **Strumenti per i dati che mancano:** scala di un'immagine da due punti e una misura nota; altezza di un ostacolo stimata dalla sua ombra e ricerca degli ostacoli simili (HelioScope, SolarEdge); estrusione dal modello di superficie, con la quota sotto il cursore (PV\*SOL).
9. **Più soluzioni a confronto.** Sunny Design mette le alternative una accanto all'altra; Solarius propone solo le combinazioni elettriche valide.
10. **Scambio con il CAD.** SolarEdge importa il DXF associando i layer e riconosce l'orientamento dei moduli da un triangolo disegnato; Aurora esporta il DXF con i layer a scelta; HelioScope passa la scena a PVsyst.

**Da evitare:** in PVsyst il tutorial ufficiale ammette che «the 3D tool is not fully safe in PVsyst (sorry...)» [V], il piano dei moduli va staccato a mano dal tetto [V], le modifiche manuali si perdono quando si rigenera una zona [V]; in PV\*SOL impostazioni sepolte in profondità [I] e ombre da ricalcolare a mano [V].

## 4. Sistemi di montaggio

Le celle sono [V], salvo dove indicato [I]. «n/p» vuol dire non pertinente.

| Categoria | Inclinazione | Interspazi, passi, blocchi | Distanza dai bordi | Pesi e limiti |
|---|---|---|---|---|
| 1. Complanare su falda (ganci, lamiera grecata, aggraffata, fibrocemento) | quella della falda; 5-75° (K2), tegole 10-60° (Esdec) | moduli a 12 mm; binari a 1/4 del modulo dai bordi; sbalzo 50-300 mm o fino a 1/3 della campata; giunti di dilatazione ogni 12-17,6 m | almeno 30 cm da colmo, gronda e lati (Esdec) | passo dei ganci dal programma del costruttore |
| 2. Integrato nel tetto | 12-50° (GSE); almeno 20° (Renusol) | sovrapposizioni 95-170 mm; telo sottotegola obbligatorio | nt | 2,8-3,7 kg/m² senza moduli |
| 3. Tetto piano, zavorrato verso Sud | 5-30°, di solito 10-15° | file distanti almeno 45 cm a 5°, 75 a 15°, 104 a 30° (Sun Ballast); passo 1,3-2,4 m; blocchi fino a 15 m, giunto 140 mm (K2) | 0,6 m (K2); 1/5 dell'altezza dell'edificio (Valk, Esdec) | blocchi da 16-70 kg; 10-30 kg/m² con la zavorra (Sika); tetto inclinato al massimo 3-5° |
| 4. Tetto piano, zavorrato est-ovest | 10-15° | passo della coppia di file 2,1-3,1 m; giunti 66-500 mm; blocchi fino a 16 m | 0,6 m | circa 15 kg/m² |
| 5. Tetto piano con ancoraggi o misto | tetto fino a 10° | campata degli ancoraggi dal calcolo | 0,6 m | fino a 3° solo zavorra, 3-5° misto, 5-10° solo ancoraggi (K2); attrito misurato in almeno 5 punti, si usa il valore minimo |
| 6. Facciata | 90° oppure 50-75° (Schletter) | nt | nt | tasselli con ETA; vetro stratificato sopra le zone di passaggio |
| 7. Frangisole | lamelle fisse o mobili | lamelle fino a 600 mm, campata fino a 4 m (Colt) | n/p | nt |
| 8. Pensiline e carport | 5-30° | luce fino a 10,3 m, altezza libera circa 3 m (K2); sbalzo di 5 m (Schletter) | n/p | fondazioni da progettare |
| 9. Balaustre | 90° | ganci su corrimano fino a 50 mm di diametro (Solar-Hook) | n/p | spinte orizzontali da NTC 3.1 [I] |
| 10. A terra, fisso | 20-35° | tavole 2P, 3P, 4L, 6L; bordo basso a 0,7-0,8 m [I]; GCR secondo la latitudine [I] | n/p | pali battuti, viti, plinti |
| 11. Inseguitori | ±50-60° | GCR 25-50%; asse a 1,3-1,8 m; arretramento automatico contro l'ombra (backtracking) | n/p | pendenza Nord-Sud del terreno 3-17% |
| 12. Agrivoltaico | fino a 20° (rialzato); 90° (verticale) | file a 3-20 m (REM Tec); almeno 8 m (Next2Sun) | n/p | altezza 4-6 m; nel verticale, bordo basso a circa 1 m |

**Fonti principali:** Esdec ClickFit Evo tegole (12/2022); K2 SingleRail (10/2026); Renusol VS+ (01/2023); GSE In-Roof (06/2024); Sun Ballast (09/2024, copia Wayback); K2 S-Dome (09/2026); Van der Valk ValkPro L10 Sud; Sika SolarMount (03/2026); K2 protocollo d'attrito (05/2024); Nextracker NX Horizon (2023, copia Wayback); REM Tec (2023, copia Wayback); Next2Sun (FAQ agrivoltaico). Gli indirizzi completi sono nel rapporto originale della ricerca.

**Cosa serve al progettista [V]:** della copertura il tipo, la portata, l'isolante e la distanza tra le travi; del luogo vento e neve, esposizione, altezza dell'edificio, distanza dal mare (Van der Valk vuole almeno 500 m) e sismicità; per le zavorre l'attrito tra appoggi e guaina; la distanza dal parafulmine (Esdec chiede almeno 0,5 m); per il vento, la fascia di bordo vale 1/5 dell'altezza secondo le zone della EN 1991-1-4.

**Programmi dei costruttori [V]:** K2 Base (distinta, relazione statica, piano delle zavorre); Schletter Configurator (solo Windows; vento e neve dal CAP; esporta in DXF); Esdec Calculator, ValkPVplannerPro, Renusol Configurator. PV\*SOL manda il layout a K2 Base e a Renusol e riceve indietro distinta e relazione statica.

**Campi della libreria dei montaggi [I]:**
- **Identità:** categoria, costruttore e modello, fonte con edizione, [V] o [I].
- **Geometria:** disposizione dei moduli (1P, 2P, 3L, 4L); inclinazione minima, massima e predefinita, oppure «segue la falda»; distanza tra moduli, sbalzi, altezza dalla copertura o dal suolo; distanza dai bordi per tipo di bordo; blocco massimo e giunto di dilatazione; passo tra le file o GCR, con il criterio usato; corridoi ogni N file.
- **Inseguitori:** rotazione, backtracking, pendenze ammesse.
- **Carichi:** peso proprio in kg/m², elementi di zavorra, attrito, pendenza massima senza ancoraggi.
- **Valori predefiniti:** 12 mm tra moduli; 0,30 m dai bordi su falda; sul tetto piano il maggiore tra 0,6 m e 1/5 dell'altezza; inseguitori a ±60° con GCR 0,35.

**Norme collegate, solo dove guardare:**
- zavorre: NTC 2018 §7.2.4 e CEI 82-25/3, punto 6.2;
- vento: CEI TR 82-74;
- categorie e distanze antincendio: DCPREV 14030/2025;
- complanarità e balaustre: D.Lgs. 190/2024, Allegato A;
- posa: D.Lgs. 199/2021, Allegato III, Sezione C;
- agrivoltaico: Linee guida MiTE di giugno 2022.

## 5. Funzioni che possono sfuggire

1. **Pannello «Problemi».** Verifiche continue che non bloccano, ciascuna con «Correggi» e il collegamento all'oggetto (Solarius lo fa [V]).
2. **Profili di regole per luogo e committente**, con precedenze e fonte datata. Le 26 regole della libreria Utilità Fotovoltaico R02 sono un buon punto di partenza [I].
3. **Dati del sito dal comune**: vento, neve, altitudine e sismicità [I].
4. **Livelli cartografici:** catasto WMS dell'Agenzia delle Entrate (licenza da verificare) [I]; ortofoto nazionali e regionali, sagome degli edifici da OpenStreetMap, vincoli e aree idonee per gli impianti a terra [I].
5. **Modelli di superficie (DSM):** import GeoTIFF e adattamento delle falde; il LiDAR del Ministero copre solo alcune aree, con licenza CC BY 4.0 [I]; Google Solar API è a pagamento, 0,075 USD a richiesta secondo PV\*SOL [V].
6. **Orizzonte lontano.** PVGIS 5.3 calcola il profilo dell'orizzonte e ne accetta uno personalizzato, in JSON, fino a 30 chiamate al secondo [V]. Anche l'import dei file .hor [V].
7. **Scambio con PVsyst tramite PVCollada 2.0**, formato aperto con specifica su GitHub. Da PVsyst 8.1.5 importa tavole, inseguitori e terreno, e così apre alla simulazione richiesta dalle banche [V].
8. **Altri scambi** [I]: DXF con lo standard di layer dell'ufficio; import DXF con associazione dei layer; IFC per il coordinamento BIM; file di progetto aperto e con numero di versione.
9. **Collegamento ai programmi dei costruttori** per distinta e relazione statica [V].
10. **Mappa dei carichi sulla copertura**: peso proprio più zavorre, area per area [I].
11. **Giunti e lunghezze massime come vincoli di posa**: 12-17,6 m su falda, 15-16 m sul tetto piano [V].
12. **Corridoi e fasce generati in automatico**: corridoi ogni N file; fasce attorno a lucernari, evacuatori di fumo e parafulmini [V/I].
13. **Effetto dell'ombra sulla produzione elettrica**, calcolato modulo per modulo (PV\*SOL, PVsyst) [V] e aggiornato in background a ogni modifica [I].
14. **Temperature di verifica visibili e modificabili.** PVsyst prende la minima dall'anno climatico tipico (TMY) [V].
15. **Codice unico** per inverter, MPPT, stringa e modulo, uguale su tavole, unifilare ed etichette [V].
16. **Varianti di progetto** e immagini catalogate per la relazione (PV\*SOL) [V].
17. **Prestazioni.** PV\*SOL arriva a 10.000 moduli [V]. In Qt Quick 3D servono istanze ripetute di un solo modello di modulo, nel 2D l'indice spaziale [I].
18. **Salvataggio automatico** (PVsyst ogni 5 minuti) e annulla su ogni modifica [V].
19. **Impianti a terra e agrivoltaico:** tavole che seguono il terreno [V]; controllo delle pendenze ammesse dagli inseguitori [V]; bifacciale, riflettanza del suolo e altezza da terra [I].
20. **Tastiera e numeri all'italiana**: virgola decimale, «;» come separatore, AltGr [I].
