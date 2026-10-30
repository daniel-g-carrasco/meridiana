# Passaggio operativo a Claude: Meridiana R07

Data di chiusura: 30 ottobre 2026. Questo documento conserva il lavoro interrotto per esaurimento della quota degli agenti Codex. Daniel chiede di chiudere il passaggio e far continuare Claude senza perdere il contesto. NON è una dichiarazione di completamento o consegna di R07.

## Mandato di Daniel

Continua e termina TUTTI i punti rimasti in `docs/richieste.md`, comprese le aggiunte successive e le nuove segnalazioni in fondo a questo documento. Non sostituire la lista con l'ultimo messaggio. Modifica, verifica, integra su Windows, costruisci i pacchetti e installa l'ultimo Flatpak sul laptop via SSH. Riporta nel template Qt le correzioni comuni. Decisioni di direzione già approvate: non chiedere nuovamente il permesso di procedere.

Il nuovo formato `.mer` è un archivio unico di progetto e risorse. Daniel ha esplicitamente detto che NON serve aprire i vecchi `.meridiana`, mai usati produttivamente. Il formato è già implementato nella tranche precedente: non ridisegnarlo da zero.

Le operazioni automatiche devono rispettare i limiti fisici/elettrici. Cercare davvero le combinazioni possibili, senza inventare dati mancanti o fingere valida una configurazione impossibile. Ogni modifica al progetto è annullabile. I moduli scollegati non producono energia. Dati sconosciuti e fonti non verificate rimangono dichiarati tali.

## Dove lavorare e cosa preservare

- Worktree di sviluppo: `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10`, branch `integra-kimi-9-10`.
- HEAD/base R07: `23bd7a9dcb30b3e7b7decfba8cef895176c785a4`. Tutte le modifiche R07 sono sul disco, NON committate.
- Runtime Windows e relativo venv: `C:\Users\Grasso\dev\meridiana`; secondo checkout `C:\Users\Grasso\dev\meridiana-lavoro`. Entrambi sono ancora a 23bd7a9, quindi NON hanno le modifiche R07.
- Python: `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`.
- Template: `C:\Users\Grasso\dev\qt-app-template`, base `acd4ab3108d3c69850a7b87192885c1d69e0efc1`. Port R07 parziale e non committato.
- Nel template erano GIÀ modificati `CLAUDE.md`, `README.md`, e non tracciato `docs/dal-template-gtk.md`: non attribuirli a R07, non sovrascriverli o includerli indiscriminatamente nei commit.
- Molti log e foto non tracciati precedenti sono presenti nel worktree. MAI `git add .`, `git clean`, reset o checkout distruttivi. Staging esplicito.
- Backup del passaggio: `build\handoff-claude-20261030-R01\`, con diff, stato, sorgenti nuovi/modificati ed evidenze. È una copia di sicurezza, non un checkout su cui lavorare.
- I rapporti A/B/C/D e i brief sono in `build\overnight-r07\`; il backup li conserva anche se build è ignorata da Git.

Leggi prima CLAUDE.md/AGENTS.md dei percorsi e skill `nuova-app`; per norme/schede, `archivi-tecnici` e archivio locale PRIMA del web. Memorie di Daniel all'indice `C:\Users\Grasso\.claude\projects\c--Users-Grasso\memory\MEMORY.md`: leggere note pertinenti e verificarle. Codex non ha modificato quelle memorie. Se sei Claude, segui le regole proprie della memoria senza perdere le note esistenti.

Risposte e documentazione in italiano; codice/commenti/commit in inglese; niente trattino lungo U+2014; niente attribuzione AI. Git Daniel Grasso `<code@danielgrasso.com>`. Nessuna pubblicazione/tag/release Meridiana autorizzata implicitamente. Commit e integrazione locali, pacchetti e SSH autorizzati. Push del template privato autorizzato dalla skill nuova-app. Non leggere chiavi private o fare chiamate API a pagamento per provare.

## Ultima consegna vera: R06, da non rifare

Commit applicativo `36fc0a0ad50733587ea16440a6df23ce6e4a4ec3`; documenti consegna `41fe0c3`; le successive registrazioni richieste arrivano a 23bd7a9. R06 ha aggiornamenti firmati opt-in Windows, allegati Meridio, catalogo personale, accumulo AC/DC equivalente, feedback bug e tour iniziale. Documenti in `docs/revisioni/servizi-cataloghi-consegna-20261029-R06.md` e `ricevuta-consegna-20261029-R06.json`.

Pacchetti conservati in `dist/packages-20261029-R06`. Freeze definitivo `build/source-manifest-20261029-R17.json`, 353 file, SHA256 `c19960fa2b64464a0e9498eed9ff48ec0e420d58a9e4494641a7e7957f8c79a3`. Flatpak R06 installato sul laptop: OSTree `350ae0a8fc1f9c981ecf6ceb68e43841445b4ae7ed4f33de46989b88708b2dd0`, bundle SHA256 `97363a4ac79f2fc3723c3d3a7dc75fff825bb113c33efbe0ca4c37295cc9480d`.

Attenzione ai nomi: vecchi build/flatpak-r07-driver.sh, source-manifest-R07, windows-bundle-R07 ecc. NON sono la nuova tranche funzionale R07. Erano revisioni intermedie della consegna precedente. Scegli nuovi nomi senza sovrascrivere. Gli ultimi driver R06 veri sono `build/flatpak-r10-driver.sh`, `build/windows-package-R06-final.py`, bundle Windows R16, freeze R17.

Limiti R06: accumulo equivalente sul bus AC, non recupero del clipping DC né controlli proprietari completi; audit strutturale cataloghi non verifica di tutte le schede originali. Non nascondere questi limiti.

## Stato R07 per lotto: implementato non significa consegnato

Piano: `docs/superpowers/plans/2026-10-29-restanti-r07.md`. Registro: `build/overnight-r07/progress.md` (più vecchio di questo handoff). Gli agenti hanno finito A/B/C/E e parte F; revisione indipendente e integrazione totale sono state interrotte dalla quota. Nessun agente sta proseguendo utilmente.

### A: R259/R260 provider, configurazione, voce

Rapporto completo `a-report.md`. Nuovi `assistant/setup.py`, `ui/assistant_setup.py`; modifiche provider/local/speech/chat/voice/preferences/persona e ricette pacchetti. Sette fornitori: OpenAI, Anthropic, Qwen, Gemini, Kimi, Mistral, DeepSeek; alias legacy claude. Profili privi di segreti, chiavi nel keyring, consenso per destinatario/endpoint. Menu disabilita modelli non configurati. Guida locale/cloud dentro chat e Impostazioni, rilevamento RAM e raccomandazione, nessun download automatico dei pesi.

Config 22 -> 23 per `assistant_cloud_profiles: dict[str,dict[str,str]]`, migrazione e nuova fixture `tests/formati/file/config-v23.json` già aggiunte. Vecchie fixture intatte. `AssistantSetup.configured(str)`, layoutChanged; Impostazioni usa copia temporanea e liveChanged, senza reimpostare Gemini a local quando cambia la voce.

Kokoro: sul laptop il log reale riportava `ModuleNotFoundError: kokoro_onnx` nel vecchio Flatpak; pesi presenti `~/.local/opt/kokoro`, suo venv con link rotto; runtime valido `~/fvtest/kokoro-venv/bin/python`. Sintesi sintetica effettiva 1,67 s, 49664 campioni/24 kHz. Windows da sorgente 4,59 s, 97280 byte PCM, niente riproduzione audio. Nuovo modulo Flatpak python3-kokoro.json pin x86/arm CPython3.13; spec Windows include runtime ONNX/Kokoro/phonemizer/espeak, NON pesi. app.main ha `--kokoro-worker` prima di QApplication. Verificare realmente i nuovi pacchetti, non dedurre dai test sorgente.

LLM Linux: saluto sintetico con vero system e 22 tool, 3433 token ingresso: primo testo 13,48 s, completamento 13,91 s. Il blocco originale dell'utente NON riprodotto. Memoria 30 GiB, circa 4,4 liberi e 6,9 swap, Gemma4 caricato 16 GB: pressione memoria è ipotesi, non causa provata. Aggiunti progresso/annullamento/timeout. Nessuna API a pagamento contattata.

Test finali A: 34 mirati verdi, 9 Impostazioni/finestra verdi con PATH PySide6, chat 22 verdi; Ruff verde. Importante finding NON ancora corretto/verificato definitivamente: reviewer ha visto che dopo configurazione Anthropic, il menu aggiorna `assistant_cloud_model`, mentre `setup.profile()` privilegia `assistant_cloud_profiles['anthropic']['model']`. Riprodurre selezione di un modello diverso e correggere con regressione. Il reviewer è stato interrotto prima del report: non considerare review approvata.

### B: R242/R261/R263 touchpad, bussola, calendario

Rapporto `b-report.md`. File navigation.py, ui/plan.py, view3d.py, day_picker.py, plan_overlays.py. PixelDelta ora usato direttamente anche senza fase; TouchPad identificato; fallback angle-only sintetico più rapido; mouse wheel invariata; precisione QPointF, NativePanGesture, profondità di pan mantenuta nella sequenza.

Riprodotto su Windows vero DPR2,5: eventi wheel ravvicinati usando pick del frame precedente spostavano il punto da (300,25;250,75) a (276,45;234,54). Correzione ricostruisce il punto alla profondità pick sul raggio della camera CORRENTE, errore residuo ~1e-10. Non applicare correzioni DPR inventate. N bussola a raggio18,5 dentro disco. Popup mese con veri angoli trasparenti; spin anno aveva altezza28 dentro slot23. L'utente aveva scritto «angolo»: ambiguità anno/angolo documentata, non cancellare la richiesta di verifica del secondo controllo.

110 prove a scala1/1,5/2, 11 su Windows reale2,5, Ruff verde; foto/JSON prima-dopo in b-*. Test fisico Linux ancora da fare in integrazione.

### C: R248/R249/R252/R253/R254/R257 movimento e scorrimento

Rapporto `c-report.md`. Scrollbar inset coerente (PAD fuori CardDock, già interno nei dock), fade automatico su QScrollArea, File/Impostazioni crossfade110ms e uscita110ms, riduzione movimento live. Nuovo ui/dock_motion.py: preview basata su QMainWindow invisibile di misura, nessun restoreState sul layout reale, nessun processEvents dentro il solver. Snapshot spostati/ritagliati senza scalare glifi. Target split/tab/bordi, cancellazione Esc, placeholder dimensioni finali. Pulsanti bordo e croci animati/reversibili.

motion.collapse anima altezza reale e ripristina vincoli; animate_tree(sections_only=True) usa SectionVeil110ms per gruppi, mantiene dettagli immediati per vecchio R125. File preserva Meridio durante tour con property guidedTourActive.

54 prove mirate verdi; 16 HiDPI verdi. Vecchio test hover Checks a2,5 fallisce uguale anche caricando HEAD: problema QTest hover, non soglia allentata. Rivedere i difetti reali, non confondere questo limite test con problema applicativo.

### D: R250/R251/R258/R262/R264/R265 avvio e tour nel fumetto

Rapporto `d-report.md`. `app.prepare_workspace`: recupero e file esplicito prioritari, prima volta Nuovo, successivi Apri, nessuna apertura implicita last_project; apertura esplicita fallita -> Apri. open_path ora bool.

TourDialog incorporato come Qt.Widget nel vero assistant.panel, chat_content nascosta temporaneamente e ripristinata. 13 passi, ultimo Nuovo con invito a progettare. Ripristino stato aperto/agganciato/abilitato. Guard A impedisce introduzione/setup/voce mentre tour attivo. Corretto errore osservato nelle foto: open_file_page è un toggle; se già aperto, passo finale usa show_section('new') invece di chiuderlo. Guide label non più distribuite con enormi spazi; pulsante finale breve Start.

Spotlight: geometria limitata alla finestra, ring/penna interni anche per target y=0. Titolo Meridio centrato sopra controlli; CornerGrip esplicitamente specchiata quattro angoli, trascinamento ad angolo opposto fisso. Conversazione utente a destra78%, assistente sinistra90%, autori distinti. Suggerimenti in questions_content con motion.collapse, testo mantenuto.

Nuovo tool read_navigation e helper assistant/navigation_help.py: profilo, orbita/pivot effettivi, binding reali (non F hardcoded). Comando offline «Come mi muovo in 3D?»; WindowHost.navigation_settings() aggiunto da A. Nessun calcolo nel widget.

45 prove iniziali avvio/spotlight/tour/config/formati verdi; poi29 widget/tour verdi; ultime13 con drag quattro angoli e comando reale verdi. Script d-verify.py attraversa tutti13passi e controlla visibilità. Ultime foto vengono rigenerate dallo stesso script; screenshot intermedi documentano anche difetti poi corretti. Non trattare ogni PNG come stato finale.

### E: R243/R244/R245/R246/R247/R255/R256 impianto e risultati

Agente interrotto DOPO annuncio freeze, PRIMA scrittura e-report.md: rapporto finale assente. Brief e-window-hooks.md e foto e-real-250-R02-* presenti. Modificati plant_page.py, energy_pages.py, charts.py, status_pill.py, phases.py, energy/pipeline.py; nuovo energy/calculation_basis.py frozen dataclass. Riepilogo risultato cattura effettivi moduli connessi da sim.arrays, inverter da sim.inverters, batteria operativa/capacità/contributo da snapshot job ed econ. NON ricostruire dai conteggi progetto mutato.

Root ha applicato page.show_basis(self.energy.get('basis')) in _show_energy_forms e da out in _energy_done. Copre nuovo/apertura/varianti e conserva vecchio contesto quando risultato stale. Verificare tutti percorsi cache/reset.

Reset stringhe QAction esistente aggiunto toolbar Start again, singolo undo; status destinazione Impianto > Stringhe/Inverter attivi, numeri e annullamento. Root ha omesso Ctrl+2 hardcoded perché rimappabile. Nuovo riepilogo inverter sopra selettore; StringList property row-pills e tema con sfondo trasparente per delegate; simboli pillola leggermente piccoli, più spazio a destra del numero. Stacked bar meno invadenti. Riga meteo usa Flow per evitare minimo880px che tagliava riepilogo a384px.

Ultimo messaggio agente:54test mirati scala2 verdi,2pipeline reali verdi,7widget Windows2,5 verdi; viaggi PlantPhase/Stringing finali verdi (reset/undo e messaggi assertati), import lazy verde. tests/finestra/test_window.py aggiorna solo toolbar e tre assert messaggi. Ruff verde. Rieseguire mirati per conferma autonoma e poi integrazione finale.

### F: R238 cataloghi, lavoro parziale

Nessun f-report.md finale. Nuovo `tools/audit_catalog_sources.py`, test `tests/nucleo/test_catalog_sources.py` (4 verdi secondo agente), risultato `build/overnight-r07/f-cec-audit-R01.json`, script f-fetch-sources.py. Fonte locale CEC-SAM/audit-20261029-R01 sotto archivio cataloghi; script documenta commit SAM esatto `cba319ded1c32a7f5b3ac76545a29e1f7181d238` e hash CSV.

Ultimo esito dichiarato: tutti21640moduli identici;2343inverter coincidono con trasformazioni/arrotondamenti import esistenti (NON identità bit). Le4incoerenze Imp12,46 > Isc12,27 sono già nella fonte SAM. NON correggerle inventando valori. Restano bloccate in selezione.

Recuperate189URL schede curate:157PDF,29errori,3HTML; archivio locale conhash/URL. Disponibilità del PDF NON equivale a verifica campi. Agente stava riverificando34campi Huawei e riconciliando vecchi aperti. File f-huawei-0/1.png presenti. Completare rapporto con fonti precise e limiti. Non dichiarare24262schede rilette.

## Template Qt: port sul disco ma NON pronto

Copiati/adattati cards, panel_buttons, motion, scrollbars, fades, day_picker, spotlight, conversation_view, status_pill e nuovo dock_motion. Import neutri; tooltip chiusura genericizzato; stile `_qtkit_scroll_style` coerente. Nuovi compass.py (solo bussola neutra) e gestures.py (classificatore puro wheel/touchpad); theme row-pills; i18n; FilePage cambio sezione e uscita animati. Supporto test wait_settled, test_shared_motion_r07 e test_gestures_compass_r07.

ULTIMA SUITE TEMPLATE:171test,4fallimenti, log `build/overnight-r07/template-full-before-review.log` nel worktree Meridiana:

1. test_behaviours fade attende16px, ora12px: aggiornare convenzione se intenzionale e verificare visivamente, non cambiare alla cieca.
2. scrollbar attende Size.SCROLLBAR10, ora16 con inset: distinguere gutter riservato e thumb reale; coprire no spostamento contenuti.
3. test_file_entrance reopening/closing: DUE veli visibili anziché uno. Questo può essere bug reale nuova uscita `motion.leave` non tracciata/cancellata al reopen. Correggere lifecycle e regressione, non allentare l'assert.
4. status_pill numero atteso width-8, ora width-10 per richiesta: aggiornare aspettativa coerente e verificare centratura reale.

Ruff prima dei test segnalava solo QFontMetrics unused in nuovo compass, già rimosso. Traduzioni template nuove aggiunte; suite repository poi senza fallimenti. Nessuna galleria finale ancora eseguita. Mancano docs port, allineamento manifest/hash e commit. Manifest consumer attuale è `template-sync-qt_R05.json` (23mapping, upstream acd4ab3), tabelle `template-sync-qt-tables_R06.json`. Crea nuova revisione o aggiorna secondo convenzione motivando; non dichiarare allineamento mentre hash vecchi. `tools/check_template_alignment.py --upstream ... --manifest ...` verifica sola lettura.

## Nuove segnalazioni notturne: PRIORITÀ prima della consegna

Foto originali:

`C:\Users\Grasso\Elettrico\.codex-remote-attachments\01a186ec-2027-79f1-9627-82a120e19c65\0c581e24-4391-4c13-9c94-635cdbf27b6c\1-111524.jpg`

stessa cartella `2-111523.jpg`, `3-111522.jpg`.

Daniel: Production rimane bloccata a «PVGIS: the electrical network (3 of 4)»,50%, produzione0. Foto mostrano2016moduli,907,20kWp,84stringhe su42ingressi,5xHuawei SUN2000-100KTL-M2/500kW AC. Scheda Power mostra invece824,8kW AC e CC/CA1,10: possibile risultato precedente/stale, da verificare. Check «Unconnected modules produce no energy» non prova che tutti2016siano scollegati. La UI mostra anche stringhe corrette: non attribuire0solo ai moduli scollegati senza riprodurre.

- R266: diagnosticare blocco reale pipeline/rete elettrica con impianto grande; capire se calcolo lungo, loop, job invalidato, lock o risultati stale. Raccogliere via SSH log/autosalvataggio di quel progetto in sola lettura e copiarli in area diagnosi. Non terminare processi utente né alterare progetto originale. La scritta «PVGIS» potrebbe essere etichetta generica del progresso, non chiamata rete responsabile. Prova prestazione riproducibile e cancellazione, poi correggere.
- R267: scelta automatica inverter non trovava combinazioni per SolarEdge e ABB. Verificare ricerca, filtri, dati mancanti, quantità/MPPT, correnti, limiti e requisito ottimizzatori. Cercare combinazioni valide reali; se nessuna con vincoli/dati disponibili, spiegare causa specifica e alternative, non inventarne una. Nuova diagnosi non ancora iniziata.
- R268: lista marche nella scelta automatica invade tutta l'altezza schermo; sostituire con ricerca compatta e altezza limitata, preferiti persistenti/selezionabili. Definire preferiti utente separati dal progetto, migrazione config se nuovi campi. Mantenere accessibilità a tutte le marche. Portare componente generico nel template.

## Ordine operativo consigliato per Claude

1. Leggi questo file, rapportoA/B/C/D, briefE/F, lista richieste e statoGit; verifica backup. Non rifare ricerche/documenti già presenti.
2. Riprendi revisioneA-D interrotta: candidato bug Anthropic sopra; sicurezza consenso allegati/cronologia, cambioendpoint, tool; timer/latecallback; tour conFile e layout; docking stato non mutato. Poi reviewE eF. Non considerare la mera esecuzione di test come code review.
3. Priorità nuova Production e ricerca ABB/SolarEdge: riproduci su copia del progetto reale, con norme/datasheet locali dove necessari. Completa UX marche/preferiti e registra decisioni.
4. Chiudi template4fail, allineamento e galleria chiaro/scuro; port lezioni wizard/provider/voce almeno come contratto documentato se non componenti generici.
5. Completa traduzioni: AST scan `_`, `ngettext`, `pgettext`. Root ha aggiunto68stringhe circa e compilato; ultime mancanti note: `The cloud model is not configured: {why}`, `Choose a model from your provider account.`, `Request cancelled in Meridio`, `Fetch from PVGIS`, `{n} of {total} modules connected`. Riestrai: elenco può non essere esaustivo. Nessun xgettext Windows che riscriva tutto il PO; append mirato e GNU msgfmt --check --check-format.
6. Test mirati per modifiche; poi suite app completa UNA VOLTA al consolidamento. Non rilanciare tutta suite per ogni ritocco. Vecchia soglia tema1s sensibile caricoCPU falliva anchebaseline: provaquieta, nonallentaretest. PATHQtQuick3D obbligatorio. Test API conmock, nessuncostoreale.
7. Aggiorna docs/richieste con evidenze reali, docs/progetto e reportconsegna; commit espliciti senza logvecchi, ff runtimeWindows solo puliti e sorgenti verificati, traduzioni compilate. Nessunpushpubblico implicito.
8. Freeze unico sorgenti conhash, Windows portable+installer e Flatpak nuovi, verifiche native. Windows pacchetto deve provare workerKokoro frozen; Flatpak nuovo runtimeKokoro deve importare/sintetizzare con pesi giàlocali. Installa viaSSH fw13 e controlla hash/OSTree/frame3D/rotazione/touchpad, preservando processiutente. Rapporto onesto di ogni limite residuo.

## Comandi e consegna

PowerShell: `PYTHONUTF8=1` e ogni read_text/write_text encoding='utf-8' (sistema cp1252). Test dalla worktree con PYTHONPATH=`tests;src`, QT_QPA_PLATFORM=`offscreen`, PATH anteposto `C:\Users\Grasso\dev\meridiana\.venv\Lib\site-packages\PySide6`. `python -m ruff check --select F,E9,B .`; `python tools/compile_po.py --python`; `python -m unittest discover -s tests/<gruppo> -t tests` per nucleo/calcoli/formati/widget/finestra. Testesterni solo dove autorizzati/performance mirata.

SSH: `ssh -o BatchMode=yes -o ConnectTimeout=8 fw13`, host lucciola, userdaniel. Flatpak user `io.github.daniel_g_carrasco.meridiana`, KDE6.11. Ambiente nativo da verificare: XDG_RUNTIME_DIR=/run/user/1000, WAYLAND_DISPLAY=wayland-1, DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus, NIRI_SOCKET=/run/user/1000/niri.wayland-1.1878.sock (può cambiare). Non forzarecompositor/preferenze. Per test3D esporre modalità3D: sotto1000pxlayout nasconde vista, nonconfondere conGPUnonfunzionante.

WSL openSUSE-Tumbleweed; basebuild `/home/daniel/meridiana-flatpak-20261029-172631`. Driverultimo `build/flatpak-r10-driver.sh`, prossimipercorsi nuovi r11 o data30; dipendenzeKokoronuove richiedono downloadprima cache, non usare --disable-download troppo presto. Windows PyInstaller in build/packaging-tools, Inno build/inno-compiler/ISCC.exe. Verificatori `tools/check_desktop_windows.py`, `tools/check_native_flatpak_view.py`. Preserva semprepacchetti precedenti.

Il passaggio finale a Daniel deve distinguere: codiceimplementato, testpassati, pacchetti realmenteinstallati, limiti. Questa R07 al momento del passaggio NON è installata su Windows né sul laptop, NON è revisionata completamente, e il template ha4testrossi noti.

## Ultimo controllo di chiusura

Ruff applicativo su src, tests e audit_catalog_sources ha individuato una lambda con variabile di ciclo non fissata nel nuovo audit. Corretto il binding esplicito; 4 test audit verdi e Ruff finale verde. Nessuna suite app completa o nuovo pacchetto eseguiti. Backup finale `build/handoff-claude-20261030-R01/stato-lavoro-R07-finale.zip`, indice `contenuto-finale-sha256.json`; il primo ZIP resta come snapshot precedente.
