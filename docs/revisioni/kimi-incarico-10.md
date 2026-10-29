# Incarico 10 per Kimi: Meridio trova e apre i progetti (R151)

Sei al lavoro su Meridiana (Python, PySide6 6.12, Qt Quick 3D, pvlib). La richiesta è R151 di docs/richieste.md; il
progetto del lavoro è la sezione 6 dello studio 20 (docs/studio/20-inizio-progetto/README.md), con le decisioni di
Daniel del 26/10/2026 nella riga R151: Meridio cerca solo nell'indice sul PC, Claude non vede mai l'elenco dei
progetti, prima di aprire un progetto mostra percorso e revisione e chiede. Il registro di clienti e commesse
dell'incarico 9 (SQLite) è in `lavoro`: l'indice si appoggia lì.

## Dove lavori, come si prova
Come negli incarichi precedenti (docs/revisioni/kimi-incarico-7.md, «Dove lavori» e «Come si prova»), su un ramo
kimi-incarico-10 preso da origin/lavoro. Commit che finiscono con «(R151, point N)». Nessuna chiamata vera a un modello
nelle prove: provider e host finti, come le prove dell'assistente che ci sono.

## Punti
1. L'indice locale (studio 6.4): i progetti delle cartelle conosciute, con i dati che servono per cercarli (luogo,
   potenza, cliente e commessa dal registro, data, revisione), aggiornato senza rallentare il programma; prove.
2. Gli strumenti di Meridio (studio 6.3, 6.5): cercare, «l'ultimo capannone simile» (la stessa serie contata una
   volta, il motivo del risultato), aprire con conferma, percorso e revisione mostrati; mai aprire da solo, il lavoro
   in mano salvato o chiesto prima.
3. La riservatezza (studio 6.6): il cloud non riceve l'indice né i nomi; il filtro è nel programma, non nel modello;
   prove che nessun nome o percorso riservato esce nei messaggi a Claude.
4. Ricordare cosa c'è da fare (studio 6.7), solo locale.

## Fine
docs/revisioni/kimi-incarico-10-lavori.md come i precedenti; riga R151, CHANGELOG, manuale. Suite intera e ruff verdi.
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
Daniel ha chiesto che il lavoro vada avanti da solo nella notte: non aspetti più il via di Claude. Parti da il ramo kimi-incarico-9 (clienti e commesse), sopra l'8 e sopra kimi-integra. Leggi prima i file degli incarichi 9, 8 e 12 in docs/revisioni. Quel lavoro non è ancora verificato da Claude: se trovi un difetto che ti blocca, correggilo in un commit a parte e scrivilo. Il codice è cambiato da quando questo incarico è stato scritto: prima di ogni punto guarda com'è oggi; se un punto è già fatto o non ha più senso, scrivilo nel tuo file di esito con il perché, invece di rifarlo.


## Attenzione, la sessione nascosta (27/10/2026 mattina: vale più di quello che c'è scritto sopra)
La ricetta con `dbus-run-session -- gnome-shell --headless ...` scritta sopra è pericolosa: usa il runtime di Daniel
(/run/user/1000) e alla fine smonta il portale dei documenti di Flatpak del suo desktop, e le sue app Flatpak non si
aprono più (è successo il 26 e il 27/10). Usa **solo** `tools/real_session.sh` nella versione con XDG_RUNTIME_DIR
privato sotto /tmp (contiene `export XDG_RUNTIME_DIR="$root/runtime"`; se la tua copia non ce l'ha, prendila da
origin/lavoro). Mai `dbus-run-session`, `gnome-shell` o `mutter` lanciati a mano. Dopo ogni prova controlla
`findmnt /run/user/1000/doc`: se il montaggio manca, scrivilo subito nell'esito.
