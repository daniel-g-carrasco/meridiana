# Allineamento Meridiana alle correzioni Qt di Quotario

29/10/2026. Base Meridiana `fce08b9` (integrazione e revisione incarichi 9 e 10), template `3f2d069c18fdb61f039b983756ad824d21149c7b`, precedente `9acb7a857adecdbe57874282c48e84e21ee463c7`, Quotario `8f1f0876b87368e3446bad8311052d257d60685c`.

[V] Confrontato il delta completo del template: 13 moduli runtime, compreso il nuovo DocumentTabs. I repository template e Quotario non sono stati modificati. Conservate le loro modifiche estranee; conservata e inclusa la correzione popup già presente in entrambe le copie Meridiana.

## Delta applicati

| Requisito | Trasferimento e personalizzazioni conservate |
|---|---|
| Tabelle: selezione, righe alternate e separatori | `ui/shared_tables.py`: selezione uniforme, senza marker laterale o outline Fusion; modelli, ordinamento e delegati applicativi conservati |
| Quattro angoli e sfumature | Cornice Qt antialias senza `QWidget.render()` durante paint; sfondo degli antenati rispettato. Modalità table in `fades.py`, colore Base e ultimo pixel coperto. Conservate altezza 12 px e curva R192 di Meridiana nelle sfumature generali |
| Intestazione e scrollbar | Gutter continuo sotto la testata, scrollbar che parte dopo la testata, padding della freccia; cornice e separatori coerenti |
| Ultima riga | Linea sotto l'ultima riga effettiva visibile, senza estendere i separatori nel vuoto |
| Consumer tardivi | Installazione esplicita nei costruttori di catalogo, grafici, confronto varianti e scorciatoie; mantenuto `install_data_tables` per le altre vere tabelle |
| Navigazione | PhaseHeader compatto, hover simmetrico e cifre centrate sul segno visibile; API per nascondere fasi, cache coerente, menu e navigazione circolare che saltano le nascoste. Id, numeri dei tasti, pagine, barre, stato obsoleto e callback Meridiana conservati |
| Aiuti | Componente condiviso da 28 px `ui/help.py`, collegato all'HelpBox da `RowHelpButton`; il selettore CSS è distinto. Gli aiuti già presenti nei titoli e nelle tessere restano da 16 px. F1, popup e testi del nucleo conservati |
| Pagina File | Colonna fissa dell'icona, aggiornamento al cambio palette/stile, spaziatura e distanza dal pulsante come nel template; sezioni Meridiana, recenti e registro Kimi conservati |
| Selectbox | Correzione locale conservata: margini aggiornati al focus; cinque prove popup mirate. Nessun elenco lungo reso non scorrevole |
| Checkbox A | Mixin condiviso nei due stili già esistenti, nessun proxy extra. Indicatore 16 px, raggio 4, allocazione 22, riga 28, fuoco 2; tutti gli stati Qt, Group e WrappedCheck. Token numerici del design invariati |

## Delta non applicabili

- `DocumentTabs`: Meridiana ha un progetto per finestra. I tab dei dock appartengono a QMainWindow e al suo stato salvato; quelli dei grafici e delle preferenze cambiano pagina; VariantBar sceglie una variante. Nessuno di questi è una barra di documenti aperti. Non sono stati sostituiti.
- Stili CSS `document-tabs` e `document-close`: non introdotti senza un consumer.
- `project-tree`, `checks-tree`, StringList e navigazioni con testata nascosta: esclusi dal trattamento delle tabelle; conservati SectionDelegate, MarkDelegate, selezione e comandi specifici.
- Campi DCF, manodopera, SAL e analisi prezzi: propri di Quotario, fuori dal porting.

## Provenienza e manifest

`template-sync-qt_R01.json` e `template-sync-qt-tables_R02.json` sono nuovi manifest format 2 per implementazioni adattate. Registrano separatamente SHA-256 upstream e consumer, con CRLF normalizzati a LF. Nessun file personalizzato viene dichiarato identico all'upstream. I manifest precedenti sono intatti. Il nuovo `tools/check_template_alignment.py` verifica questi hash in sola lettura; nessuna sincronizzazione automatica.

## Verifiche mirate e fotografie

[V] Prima delle correzioni le nuove regressioni erano rosse. Tabelle: 15 prove nelle sei combinazioni chiaro/scuro e DPR 1/2/2,5 (90 esecuzioni), più 41 prove esistenti. Checkbox/fasi: 12 prove nuove alle tre scale, più 18 esistenti. Aiuti, tessere e ciclo delle fasi: tre prove nuove. Le misure raster campionano pixel fisici secondo il DPR.

[V] Fotografie in `docs/revisioni/foto/template-ux-20261029-R02`: modello, File e File stretto nei sei contesti tema/scala; sei gallerie, sei tabelle e sei tavole checkbox con fuoco. Ispezionate le tavole comparative di tutte le schermate dell'app e delle gallerie; le immagini dei due domini sono state ispezionate anche dai rispettivi implementatori. Ricontrollati direttamente File stretto chiaro, tabella scura e checkbox chiara al 250%. Primo tentativo fotografico durante l'animazione scartato dalla consegna; le immagini finali attendono il termine dell'entrata della pagina File.

## Diagnosi distinta dal porting

[V] Limite di tempo del tema già superato nella base `9c3317f`: 2.583 QWidget figli contro i circa 1.100 del vecchio commento del test. Reset stylesheet vuoto e riapplicazione: 0,880 + 0,726 s; runtime `fce08b9` 0,662 + 0,655 s, con 2.656 figli. Dopo dispose, zero widget residui in entrambi. `ensurePolished` costa circa 2 ms. Cambio tema reale 4,1-5,6 s sul runtime senza profiler; circa il 99% del profilo è in `QApplication.setStyleSheet`, non nei callback dei nuovi componenti. Nessuna soglia allargata o test di tempo disabilitato.

[V] Il log storico `build/ux-combo-diagnostic-20261029.log` termina con access violation durante la prova della relazione, stack in pyparsing. Il gruppo finestra isolato dell'integrazione Kimi ha completato la stessa prova senza crash. Questo confronto non dimostra una correzione: la suite monolitica finale viene eseguita con faulthandler per verificare la sequenza originale.

L'avviso `Slot 'TableStyle::' not found` non è stato riprodotto nelle prove mirate; non è dichiarato risolto.

Gli esiti della suite completa, il commit e la distribuzione dei due checkout sono aggiunti dopo la verifica finale.

[V] Verifica mirata Linux/WSL, Python 3.13 e Qt 6.12: 30 prove dei componenti (checkbox, fasi, aiuti/tessere, popup e tabelle) superate. La prova di finestra non è stata eseguita in quell'ambiente minimale perché manca pandas; non è dichiarata una suite Linux completa. Il self-test Windows dal launcher sorgente è passato: energia, PDF e screenshot, zero fallimenti in 20,27 s. Nuovo launcher `bin/meridiana-windows.cmd`, che usa il virtualenv del checkout o quello condiviso della copia principale.

## Diagnosi del giro monolitico e isolamento delle prove

[V] Il primo giro monolitico del porting si è interrotto con exit Windows -1073741819 durante `finestra.test_window.Window.test_opened_laid_out_with_nothing_to_save_a_damaged_file_said_and_saved_and_opened_again`, nella creazione di una seconda MainWindow. Lo stack si ferma in `Chart.__init__`, chiamata `QTableWidget()`, prima dell'installazione del nuovo stile. Non è lo stesso punto del crash storico della relazione. Il modulo `finestra.test_window` isolato ha poi completato tutte e 25 le prove in 255,713 s.

[V] Stress dedicato con dump diagnostico a 180 s: arresto al ciclo 13, immediatamente dopo il dump, stavolta in `theme_colors.py`. Stesso candidato senza dump periodico, conservando `-X faulthandler`: 20 cicli e 40 MainWindow in 201,55 s, exit 0. I 201,55 s del candidato includono attese intenzionali con eventi elaborati per superare il momento diagnostico di 180 s: non sono un benchmark di avvio. La baseline `fce08b9` ha completato 20 cicli e 40 finestre in 98,81 s, senza raggiungere il suo timer 180 s. Nei run riusciti: zero QWidget dopo ogni cleanup, GDI 0 e USER finali 24. Nessuna crescita massiva dei contatori GUI.

[I] La correlazione con `faulthandler.dump_traceback_later` è sostenuta da questi esperimenti, ma la causa nativa non è dimostrata. La parola Timeout nei log è il timer diagnostico programmato e non prova un blocco del test. Non è stato modificato il codice dell'applicazione per mascherare questo fenomeno. Il giro finale usa soltanto `-X faulthandler`, senza dump periodici. La stabilità generale oltre gli scenari provati non è garantita da questi risultati.

[V] Il gruppo widget ha individuato una contaminazione fra prove: i nuovi test checkbox/fasi cambiavano `cfg.theme` del tema condiviso e non lo ripristinavano. Riprodotta esattamente con la sequenza di 14 prove checkbox/fasi/tabelle, prima rossa e poi verde dopo cleanup del tema. Nessuna asserzione di resa o palette è stata indebolita. In esecuzioni contemporanee sono state superate anche alcune soglie strette di tempo (catalogo 0,413 s contro 0,4; grafico 65 ms contro 50; animazione del personaggio). Questi risultati sono riportati come tali, senza modificare i limiti.

## Esito finale della suite Windows

[V] Giro monolitico senza timer periodico: 1.688 prove in 1.690,200 s, 8 saltate e un solo fallimento. Nessun crash o errore funzionale delle prove. Il fallimento è `finestra.test_theme.ThemeOfTheWindow.test_the_sheet_goes_on_the_whole_window_quickly_and_it_draws_in_both_themes_with_the_screenshots_kept`: 2,428 s contro 1 s per reset vuoto e riapplicazione globale. Il limite era già violato sulla base, ma questo risultato non esclude un costo aggiuntivo dei nuovi controlli: l'ottimizzazione resta aperta e non si dichiara la suite interamente verde. Nessuna soglia modificata. Gli otto salti sono i sei test esterni non abilitati e due salti già previsti dai gruppi nucleo/widget.

[V] Nella stessa esecuzione sono passati sia la prova della relazione del log storico sia il journey nel quale era avvenuto l'arresto del primo giro. Nessun avviso `Slot 'TableStyle::' not found` osservato, senza dichiararne risolta la causa. Il log completo resta nel checkout di integrazione, `ux-suite-completa-r02-no-timer.log`.

[V] Ruff su tutto il repository, `git diff --check`, catalogo italiano compilato e verificatori dei due manifest superati. Trenta prove mirate Linux/WSL superate. Trentasei fotografie finali prodotte e ispezionate. Il codice è pronto per il commit locale e l'aggiornamento dei due checkout, con il limite prestazionale sopra esplicito; nessun push o rilascio.
