# Incarico 7 per Kimi: le Impostazioni dentro File, il passo delle file nel sottocampo, le Proprietà riusate (26/10/2026)

Sei al lavoro su Meridiana, il programma di Daniel Grasso per progettare impianti fotovoltaici (Python, PySide6 6.12,
Qt Quick 3D, pvlib). Le richieste sono R133, R172 e R2 di docs/richieste.md: leggile parola per parola, con le
decisioni di Daniel scritte nelle loro righe. Le regole di casa sono in CLAUDE.md (leggi tutto, comprese «How
Meridiana runs» e «Diagnosing a failure»), il sistema grafico in docs/design/sistema-grafico.md: valgono anche per te.

## Dove lavori
- Nella cartella ~/dev/meridiana-kimi, su un ramo nuovo kimi-incarico-7 preso da origin/lavoro (il lanciatore lo crea
  prima di avviarti; controlla con git status e git log). I rami degli incarichi precedenti non si toccano più.
- Sistema immutabile: non installare nulla (niente dnf, rpm-ostree, sudo, flatpak, pip). Non scrivere fuori dalla tua
  cartella; non leggere ~/.ssh, ~/.gnupg, credenziali, chiavi, altri repository, e nemmeno i progetti e le cartelle
  vere di Meridiana di Daniel (~/.config/meridiana, ~/.local/state/meridiana, ~/.cache/meridiana).
- Push disattivato: non provarci, non cambiare i remote. Mai merge su altri rami, rebase, reset --hard, force.
- Un commit per punto, identità Daniel Grasso <code@danielgrasso.com>, messaggio in inglese che finisce con la
  richiesta del punto e «point N» (per esempio «(R133, point 1)»): il cruscotto segna fatto un punto solo se un
  commit lo nomina. Nessuna attribuzione AI. Mai il trattino lungo, né nel codice né nei testi.

## Come si prova
- Interprete ~/fvtest/venv314/bin/python con PYTHONPATH=src della tua cartella (controlla meridiana.__file__); il
  catalogo con ~/fvtest/venv314/bin/python tools/compile_po.py; ruff con python -m ruff check src tests tools.
- Prove offscreen, un gruppo per processo, dalla cartella tests: QT_QPA_PLATFORM=offscreen python -m unittest
  discover -s <gruppo> -t . per nucleo, calcoli, formati, esterni, widget, finestra.
- Mai la finestra sullo schermo; cartelle XDG temporanee in /tmp. Nessun dialogo modale vero nelle prove (mock).
- Testi dell'interfaccia: msgid in inglese, italiano in po/it.po, nessuna voce fuzzy, msgfmt --check pulito.
- Fotografie offscreen prima e dopo in docs/revisioni/foto/ (nome kimi7-...), in chiaro e in scuro.
- Un cambio del formato delle impostazioni o del progetto ha la sua migrazione, il suo file campione congelato in
  tests/formati/file e la riga in BROUGHT (vedi come è stato fatto il formato 21 delle impostazioni, text_size).

## Punti

1. R133, le Impostazioni dentro File. Oggi le preferenze sono una finestra a parte (ui/preferences.py: Aspetto,
   Navigazione, Tastiera, Privacy, Meridio, Mappe, Relazione). Daniel ha deciso: una pagina Impostazioni dentro la
   pagina File (ui/file_page.py, quella che si srotola, con le sue sezioni a sinistra), ogni modifica vale subito e
   si può annullare, niente pulsante «Applica» né «OK/Annulla». Quindi:
   - le stesse pagine di oggi diventano sezioni di File (una voce «Impostazioni» con le sue sottovoci, o una voce per
     gruppo: scegli e spiega), con il tipo di righe, gruppi e spazi del sistema grafico;
   - ogni scelta si applica appena cambia (il tema e il colore lo fanno già con un breve ritardo, `settled`; la
     dimensione del testo con theme.change_text_size; le scorciatoie, la navigazione, Meridio, le mappe, la relazione
     con quello che oggi fa window._preferences all'«OK»), e si salva;
   - «annullare»: un modo semplice e visibile di tornare indietro (per esempio «Annulla l'ultima modifica» in cima
     alla pagina finché la pagina è aperta, e «Ripristina i valori predefiniti» per sezione con una conferma
     disegnata nella pagina); proponi la forma più semplice che funziona e scrivila;
   - il comando Preferenze (menu, scorciatoia, ingranaggio se c'è) apre questa pagina, alla sezione chiesta (oggi
     `_preferences(page)`); la finestra Preferenze sparisce. Le prove di oggi che usano `_preferences(..., run=...)`
     vanno portate sulla pagina, senza perdere quello che verificano.
   Prove: ogni sezione applica e salva; l'annullamento; la scorciatoia; nessun dialogo modale.

2. R172, il passo delle file dal sole nel sottocampo. Oggi «Passo delle file dal sole» (giorno, dalle, alle: il giorno
   e le ore senza ombre tra le file) sta nelle proprietà del Sito (ui/properties.py, gruppo `Row pitch from the sun`)
   e Daniel ha chiesto «cosa c'entra?». Deciso: va nel sottocampo, sotto «Passo delle file», quando il passo è
   calcolato dal sole; il valore del progetto (Project.sun_window) resta il predefinito dei sottocampi. Il modello lo
   permette già: un sottocampo può avere la sua finestra (`window` nei suoi params; Project.fill_params usa quella del
   progetto quando manca). Quindi:
   - nelle proprietà del sottocampo, con il passo dal sole, il giorno e le ore, del sottocampo o (detto) quelli del
     progetto; modificarli scrive quelli del sottocampo, come un passo di annulla;
   - dal Sito il gruppo sparisce; il valore del progetto si cambia dove ha senso (proponi: nella pagina Impostazioni
     del progetto se c'è, oppure con «Usa per tutti i sottocampi» dal sottocampo);
   - le verifiche e i testi che leggono project.sun_window per un sottocampo (checks.py: la verifica delle ombre degli
     ostacoli e quella delle file; assistant/tools.py) usano la finestra del sottocampo;
   - attenzione all'incarico 5 (R170): ha cambiato il testo della verifica delle ombre (orari 10:00); se il tuo ramo
     non lo ha ancora, scrivi la tua parte in modo che si unisca senza sorprese e dillo nel rapporto.
   Prove: un progetto vecchio si apre uguale (stessa posa, stesse verifiche); il sottocampo con la sua finestra posa
   diverso da quello senza; annulla e ripeti.

3. R2, le Proprietà riusate. Oggi la pagina delle proprietà non si ricarica sullo stesso oggetto, ma si ricostruisce
   passando a un altro oggetto dello stesso tipo (docs/richieste.md R2; ui/properties.py, `shape` e il riuso già
   fatto per lo stesso oggetto). Misura prima quanto costa il passaggio fra due sottocampi, due edifici, due falde
   (millisecondi, offscreen, sul progetto di prova grande), poi riusa la pagina fra oggetti dello stesso tipo e della
   stessa forma, aggiornando solo i valori; lo scorrimento resta dov'era. Misura dopo, scrivi i numeri. Nessun
   valore dell'oggetto di prima deve restare nella pagina dell'oggetto nuovo: prove su ogni tipo.

## Fine
Scrivi docs/revisioni/kimi-incarico-7-lavori.md: per ogni punto il commit, cosa è cambiato, le prove (rossa prima,
verde dopo), le misure, le fotografie, cosa Daniel deve provare sullo schermo, cosa non hai fatto e perché. Aggiorna le
righe R133, R172, R2 di docs/richieste.md, CHANGELOG.md e il manuale (docs/manuale) dove parla delle preferenze. Suite
intera e ruff verdi alla fine, con i numeri. Poi fermati: Claude rivede i commit prima che entrino in lavoro.

Lavora in autonomia dal punto 1 al 3 senza chiedere conferme. Prima si prova, poi si afferma.


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
