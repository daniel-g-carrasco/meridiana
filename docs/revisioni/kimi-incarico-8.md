# Incarico 8 per Kimi: il Nuovo progetto che parte dal posto (R148)

Sei al lavoro su Meridiana (Python, PySide6 6.12, Qt Quick 3D, pvlib). La richiesta è R148 di docs/richieste.md; il
progetto del lavoro è la sezione 3 dello studio 20 (docs/studio/20-inizio-progetto/README.md, «iniziare dal posto»),
che hai scritto tu, con le decisioni di Daniel del 26/10/2026 scritte nella riga R148. Le mappe dell'incarico 6 (fonti
senza buchi, stradale e ortofoto, il mondo offline) sono già in `lavoro`: usale, non rifarle. Le regole di casa sono in
CLAUDE.md (leggi tutto) e il sistema grafico in docs/design/sistema-grafico.md: valgono anche per te.

Le decisioni (riga R148): prima il posto, poi i dati facoltativi, «Crea e disegna»; Nominatim solo sul pulsante
«Cerca», i suggerimenti mentre si scrive solo dai comuni ISTAT e dai progetti locali; coordinate decimali,
gradi-primi-secondi, link di Google Maps, OpenStreetMap e Apple, UTM WGS84, ED50 e Gauss-Boaga (Roma40) subito; dati di
rete facoltativi (distributore, POD, tensione e connessione, potenze, codice della pratica; CEI 0-21 o 0-16 dalla
tensione); progetto riservato: nomi e indirizzi non escono mai, le coordinate per mappe e meteo dopo una conferma per
progetto, mai Claude.

## Dove lavori, come si prova
Come negli incarichi precedenti (leggi docs/revisioni/kimi-incarico-7.md, sezioni «Dove lavori» e «Come si prova»:
valgono uguali), su un ramo kimi-incarico-8 preso da origin/lavoro. Commit che finiscono con «(R148, point N)».
Nessuna richiesta vera a Nominatim o ad altri servizi nelle prove (server finti); i comuni ISTAT dal file ufficiale,
incluso nel programma con fonte, data e licenza scritte.

## Punti
1. Il lettore delle coordinate (studio 3.5): una funzione senza Qt che da un testo incollato dà il punto o dice perché
   no; decimali, DMS, i link, UTM WGS84, ED50 e Gauss-Boaga con il datum giusto (pyproj se c'è già fra le
   dipendenze, altrimenti dillo e proponi); testi ambigui rifiutati con il motivo. Prove su punti noti con le
   coordinate scritte da fonti ufficiali (scrivi le fonti).
2. La pagina Nuovo progetto (studio 3.3): un solo campo (indirizzo, comune, coordinate o link), la mappa con il
   segno, «Crea e disegna»; i dati facoltativi dopo; i suggerimenti locali (ISTAT e progetti recenti) mentre si
   scrive, Nominatim solo con «Cerca»; nel sistema grafico, nella pagina File o dove la proposta dello studio la
   mette.
3. I dati di rete facoltativi (studio 3.6) nel progetto, con la scelta della regola tecnica dalla tensione; il formato
   del progetto cresce con migrazione, file congelato e prove.
4. Il progetto riservato (studio 3.7, decisione di Daniel): nessun nome o indirizzo esce; le coordinate solo dopo una
   conferma per progetto; Meridio non usa Claude. Prove che nessuna richiesta parte prima della conferma.

## Fine
docs/revisioni/kimi-incarico-8-lavori.md come i precedenti (commit, prove, fotografie offscreen in chiaro e scuro,
cosa provare sullo schermo, cosa non fatto); righe R148 del registro, CHANGELOG, manuale. Suite intera e ruff verdi.
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
Daniel ha chiesto che il lavoro vada avanti da solo nella notte: non aspetti più il via di Claude. Parti da il ramo kimi-integra: il ramo lavoro (c207d1b) con gli incarichi 5 (Meridio), 6 (le mappe) e 7 (le Impostazioni dentro File, il passo delle file, le Proprietà riusate) uniti da Kimi nell'incarico 12, e gli strumenti della prova vera. Leggi prima docs/revisioni/kimi-incarico-12-esito.md e i file degli incarichi 5, 6 e 7 in docs/revisioni. Quel lavoro non è ancora verificato da Claude: se trovi un difetto che ti blocca, correggilo in un commit a parte e scrivilo. Il codice è cambiato da quando questo incarico è stato scritto: prima di ogni punto guarda com'è oggi; se un punto è già fatto o non ha più senso, scrivilo nel tuo file di esito con il perché, invece di rifarlo.


## Attenzione, la sessione nascosta (27/10/2026 mattina: vale più di quello che c'è scritto sopra)
La ricetta con `dbus-run-session -- gnome-shell --headless ...` scritta sopra è pericolosa: usa il runtime di Daniel
(/run/user/1000) e alla fine smonta il portale dei documenti di Flatpak del suo desktop, e le sue app Flatpak non si
aprono più (è successo il 26 e il 27/10). Usa **solo** `tools/real_session.sh` nella versione con XDG_RUNTIME_DIR
privato sotto /tmp (contiene `export XDG_RUNTIME_DIR="$root/runtime"`; se la tua copia non ce l'ha, prendila da
origin/lavoro). Mai `dbus-run-session`, `gnome-shell` o `mutter` lanciati a mano. Dopo ogni prova controlla
`findmnt /run/user/1000/doc`: se il montaggio manca, scrivilo subito nell'esito.
