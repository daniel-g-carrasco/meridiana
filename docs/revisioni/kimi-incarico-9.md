# Incarico 9 per Kimi: clienti e commesse, e il progetto che viaggia da solo (R150)

Sei al lavoro su Meridiana (Python, PySide6 6.12, Qt Quick 3D, pvlib). La richiesta è R150 di docs/richieste.md; il
progetto del lavoro è la sezione 5 dello studio 20 (docs/studio/20-inizio-progetto/README.md), con le decisioni di
Daniel del 26/10/2026 nella riga R150, che cambiano lo studio in due punti:
- il registro di clienti e commesse è un database SQLite «fatto bene, forse più rapido e più organizzato», non i file
  JSON dello studio;
- il progetto «esce con tutto ciò che gli serve per essere autonomo»: si scambia con altri utenti senza perdere gli
  elementi di catalogo personalizzati (moduli, inverter, ottimizzatori fatti o modificati dal progettista).
Il file della commessa nelle cartelle sul server solo dopo un sì per cartella, mai per le commesse riservate. Il Nuovo
progetto dell'incarico 8 è in `lavoro`: collega cliente e commessa lì.

## Dove lavori, come si prova
Come negli incarichi precedenti (docs/revisioni/kimi-incarico-7.md, «Dove lavori» e «Come si prova»), su un ramo
kimi-incarico-9 preso da origin/lavoro. Commit che finiscono con «(R150, point N)». Nessun nome vero di clienti o
commesse in codice, prove o documenti: il repository è pubblico.

## Punti
1. Il progetto autonomo, prima di tutto, con una prova che lo dimostra: un progetto con un modulo, un inverter e un
   ottimizzatore personalizzati, salvato, aperto con un catalogo vuoto in un'altra cartella XDG: tutto come prima. Il
   file oggi porta già le schede (Project.modules, energy.inverters[].record, gli sfondi in base64): trova cosa manca
   (allegati della relazione, logo del profilo, file meteo importati, altro) e fallo viaggiare o dillo chiaro
   all'apertura. Se serve, «Esporta pacchetto» che mette tutto in un file solo.
2. Il registro SQLite (studio 5.2, 5.3 con SQLite): clienti, commesse, collegamenti ai progetti e alle cartelle;
   schema con versione e migrazioni, scritture sicure (transazioni, nessuna perdita se il programma si ferma a metà),
   una copia di sicurezza; prove.
3. La finestra (studio 5.6): dove si vedono e si scelgono cliente e commessa, nel Nuovo progetto e nella pagina File;
   nel sistema grafico.
4. Il file della commessa nelle cartelle (studio 5.4, 5.5) solo dopo il sì per cartella; importazione ed
   esportazione del registro con anteprima e unione per id, nessun doppione silenzioso.

## Fine
docs/revisioni/kimi-incarico-9-lavori.md come i precedenti; riga R150, CHANGELOG, manuale. Suite intera e ruff verdi.
Poi fermati: Claude rivede i commit prima che entrino in lavoro. Prima si prova, poi si afferma.


## La prova vera, in una sessione nascosta (aggiunto il 26/10/2026 sera)
Daniel vuole che tu apra il programma e lo provi davvero, oltre alle prove automatiche. Mai sullo schermo del laptop,
che Daniel usa: apri Meridiana in un display Wayland nascosto, un GNOME senza schermo che c'è già sul sistema:
`dbus-run-session -- gnome-shell --headless --wayland --virtual-monitor 1600x1000 --wayland-display meridiana-prova`
(in background; controlla con --help le opzioni esatte), poi il programma con QT_QPA_PLATFORM=wayland
WAYLAND_DISPLAY=meridiana-prova e le cartelle XDG_CONFIG_HOME, XDG_STATE_HOME, XDG_CACHE_HOME, XDG_DATA_HOME in una
cartella nuova sotto /tmp. Se nel tuo ramo c'è già tools/real_session.sh (lo scrive l'incarico 11), usa quello. Lì
il programma gira con la piattaforma vera, la scheda grafica vera e le animazioni vere: guidalo con uno script Python
dentro il processo (QTest per clic, tasti e rotella), fotografalo con grab() della finestra in docs/revisioni/foto, e
prova così ogni cosa che hai fatto, come la userebbe Daniel. Alla fine chiudi il programma e il gnome-shell nascosto.
Il tuo modello legge le immagini (K3.1 Pro): guarda tu le fotografie. Se il gnome-shell nascosto non parte, scrivi
l'errore nel tuo esito e continua offscreen.


## La base (27/10/2026, notte: questa sezione vale più di quello che dicono sopra «Dove lavori» e il lanciatore)
Daniel ha chiesto che il lavoro vada avanti da solo nella notte: non aspetti più il via di Claude. Parti da il ramo kimi-incarico-8 (il Nuovo progetto), che sta sopra kimi-integra (incarichi 5, 6, 7 uniti). Leggi prima i file degli incarichi 8 e 12 in docs/revisioni. Quel lavoro non è ancora verificato da Claude: se trovi un difetto che ti blocca, correggilo in un commit a parte e scrivilo. Il codice è cambiato da quando questo incarico è stato scritto: prima di ogni punto guarda com'è oggi; se un punto è già fatto o non ha più senso, scrivilo nel tuo file di esito con il perché, invece di rifarlo.


## Attenzione, la sessione nascosta (27/10/2026 mattina: vale più di quello che c'è scritto sopra)
La ricetta con `dbus-run-session -- gnome-shell --headless ...` scritta sopra è pericolosa: usa il runtime di Daniel
(/run/user/1000) e alla fine smonta il portale dei documenti di Flatpak del suo desktop, e le sue app Flatpak non si
aprono più (è successo il 26 e il 27/10). Usa **solo** `tools/real_session.sh` nella versione con XDG_RUNTIME_DIR
privato sotto /tmp (contiene `export XDG_RUNTIME_DIR="$root/runtime"`; se la tua copia non ce l'ha, prendila da
origin/lavoro). Mai `dbus-run-session`, `gnome-shell` o `mutter` lanciati a mano. Dopo ogni prova controlla
`findmnt /run/user/1000/doc`: se il montaggio manca, scrivilo subito nell'esito.
