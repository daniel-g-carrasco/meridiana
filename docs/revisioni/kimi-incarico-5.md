# Incarico 5 per Kimi: i problemi che Daniel ha trovato parlando con Meridio (26/10/2026)

Sei al lavoro su Meridiana, il programma di Daniel Grasso per progettare impianti fotovoltaici (Python, PySide6 6.12,
Qt Quick 3D, pvlib). Meridio è il suo assistente (src/meridiana/assistant: tools.py, persona.py, conversation.py,
context.py). Daniel ci ha parlato (modello Claude Haiku 5.5) sul progetto di prova di un capannone con due
sottocampi, «Copertura» (188 moduli) e «Sottocampo 2» (15 moduli su «Uffici»), e ha incontrato i problemi qui sotto:
è la richiesta R170 di docs/richieste.md. Le regole di casa sono in CLAUDE.md (leggi tutto, comprese «How Meridiana
runs» e «Diagnosing a failure»): valgono anche per te.

La conversazione, in breve (le frasi tra virgolette sono quelle vere):
- Daniel: «Come sistemo "Copertura: gli ostacoli tolgono il 3,3%…"?». Meridio legge le verifiche e propone la
  correzione della verifica: «Tenere i moduli fuori dalle ombre degli ostacoli il 21/12, dalle 10,0 alle 14,0 ora
  solare: 130 moduli invece di 188». Daniel la applica.
- Meridio stesso nota: «Nella catena delle perdite, le ombre degli ostacoli pesano l'1,04% dell'irraggiamento annuo,
  mentre il controllo riporta il 3,3%. Non so dire dai dati che ho letto da dove venga la differenza».
- Meridio consiglia, per tenere 188 moduli, di «allargare la fascia di rispetto attorno agli ostacoli»: la fascia
  toglie moduli, non li tiene. L'idea viene dal testo della verifica (checks.py, il `detail` della verifica delle
  ombre degli ostacoli), che Meridio ha letto male.
- Daniel: «possiamo tornare indietro?». Meridio: «Io non posso annullare modifiche, quindi lo fai tu».
- Daniel: «La posa di "Sottocampo 2" va bene?». Meridio chiama read_checks (due volte) e risponde: «l'elenco dei
  controlli di posa è tornato vuoto, pur dicendo che ci sono 5 avvisi "da controllare" e 13 informazioni. Non so dire
  perché l'elenco non arrivi». Poi elenca i parametri del sottocampo con le chiavi interne: «Passo delle file:
  calcolato dal sole (modalità "sun")», «l'opzione "shade_free" è disattivata».

## Dove lavori
- Nella cartella ~/dev/meridiana-kimi, su un ramo nuovo kimi-incarico-5 preso da origin/lavoro (il lanciatore lo crea
  prima di avviarti; controlla con git status e git log). I rami degli incarichi precedenti non si toccano più.
- Sistema immutabile: non installare nulla (niente dnf, rpm-ostree, sudo, flatpak, pip). Non scrivere fuori dalla tua
  cartella; non leggere ~/.ssh, ~/.gnupg, credenziali, chiavi API, altri repository, e nemmeno i progetti e le
  cartelle vere di Meridiana di Daniel (~/.config/meridiana, ~/.local/state/meridiana, ~/.cache/meridiana).
- Nessuna chiamata vera a un modello (né Claude né il modello locale): le prove usano i provider finti e gli host
  finti che le prove dell'assistente hanno già (tests/*/test_assistant*.py).
- Push disattivato: non provarci, non cambiare i remote. Mai merge su altri rami, rebase, reset --hard, force.
- Un commit per punto, identità Daniel Grasso <code@danielgrasso.com>, messaggio in inglese che finisce con
  «(R170, point N)»: il cruscotto segna fatto un punto solo se un commit lo nomina. Nessuna attribuzione AI.
- Mai il trattino lungo, né nel codice né nei testi.

## Come si prova
- Interprete ~/fvtest/venv314/bin/python con PYTHONPATH=src della tua cartella (controlla meridiana.__file__); il
  catalogo con ~/fvtest/venv314/bin/python tools/compile_po.py; ruff con python -m ruff check src tests tools.
- Prove offscreen, un gruppo per processo, dalla cartella tests: QT_QPA_PLATFORM=offscreen python -m unittest
  discover -s <gruppo> -t . per nucleo, calcoli, formati, esterni, widget, finestra.
- Mai la finestra sullo schermo; cartelle XDG temporanee in /tmp. Nessun dialogo modale vero nelle prove (mock).
- Il progetto di prova è quello che le prove usano già (_fixtures.capannone, tests/fixtures); se serve un caso come
  quello di Daniel (un sottocampo grande vicino a ostacoli alti, uno piccolo su un altro edificio), costruiscilo nelle
  prove.
- Testi dell'interfaccia e di Meridio: msgid in inglese, italiano in po/it.po, nessuna voce fuzzy, msgfmt --check.

## Punti (ognuno: prima una prova rossa che mostra il difetto, poi la correzione)

1. read_checks (assistant/tools.py). I conteggi che restituisce sono di tutto il progetto anche quando l'elenco è
   filtrato per area o per livello: Meridio li ha presi per i conteggi del filtro. Restituisci i conteggi del filtro e
   quelli di tutto il progetto con nomi che non si confondono; aggiungi un filtro per oggetto (l'id di un sottocampo,
   di un edificio, come in project_summary), così che «la posa di Sottocampo 2 va bene?» trovi le verifiche che
   riguardano quel sottocampo in tutte le aree; con un elenco vuoto, il risultato dice che per quel filtro non c'è
   niente. Aggiorna descrizione e schema dello strumento.

2. La verifica delle ombre degli ostacoli (checks.py, «the obstacles take {pct}% of the irradiance»):
   - le ore della finestra solare scritte come orari, 10:00 e 14:00 (10:30 per 10,5), non «10,0»; cerca tutti i testi
     che scrivono project.sun_window e correggili tutti;
   - la correzione dice il suo prezzo: i moduli tolti, in numero e in quota del sottocampo, accanto alla perdita per
     ombre che evita (per esempio «130 moduli invece di 188, 31 % in meno, per un'ombra del 3,3 %»); se togliere
     moduli costa più di quello che l'ombra fa perdere, la verifica lo dice e la correzione non si presenta come la
     soluzione ovvia;
   - il `detail` spiega bene le tre strade: la correzione (via i moduli in ombra nel giorno di progetto), spostare il
     sottocampo, una fascia di rispetto più larga attorno agli ostacoli (toglie solo i moduli accanto agli ostacoli,
     di solito meno della correzione, e non ne tiene di più).

3. Il 3,3 % della verifica e l'1,04 % della catena delle perdite. Trova i due numeri nel codice (energy/simulate.py:
   `obstacle_shading` per ogni array, _obstacles_step, il passo della catena che Meridio legge con read_results), e
   riproducili su un progetto di prova. Ipotesi da verificare: la verifica usa la perdita di un solo array (un
   sottocampo su un tetto a due falde diventa più array, uno per falda) e la chiama con il nome del sottocampo,
   mentre la catena dà la perdita dell'impianto intero; oppure le due quote hanno basi diverse (irraggiamento senza
   ombre delle file, irraggiamento totale). Correggi il difetto se c'è; in ogni caso ogni numero dice di che cosa è la
   quota (del sottocampo o della falda, dell'impianto), con una prova che i due numeri tornano tra loro.

4. Le chiavi interne. read_selection e project_summary danno i parametri con le chiavi e i valori del codice
   (pitch_mode «sun», shade_free, mounting «coplanar», «portrait»): Meridio li ha ripetuti a Daniel. Accanto alle
   chiavi (che servono a propose_edit) dai i nomi e i valori come li scrive la finestra, nella lingua
   dell'interfaccia (ui/properties.py ha già i nomi dei campi); nella persona di Meridio una regola: al progettista
   si parla con i nomi della finestra, mai con le chiavi.

5. Tornare indietro. Meridio non può annullare: aggiungi uno strumento che propone «Annulla» (e «Ripeti») come una
   card, con il testo del passo che annulla (ui/undo.py: undoText, redoText), applicata dal progettista con un clic
   come le altre proposte; Meridio non annulla mai da solo. Aggiorna la persona («posso proporti di annullare»),
   le prove dello strumento con l'host finto e della card.

6. Le risposte di Meridio dopo questi cambi: con il provider finto, ripeti i passi della conversazione di Daniel
   (le chiamate agli strumenti che Meridio fa e i risultati che riceve) e controlla che i risultati non lascino più
   spazio agli errori di sopra: conteggi del filtro, orari, prezzo della correzione, base delle quote, nomi della
   finestra, card di annulla. Scrivi nel rapporto cosa resta affidato al modello (un modello piccolo come Haiku può
   ancora ragionare male) e se conviene suggerire un modello diverso come predefinito per Meridio.

## Fine
Scrivi docs/revisioni/kimi-incarico-5-lavori.md: per ogni punto il commit, cosa è cambiato, le prove (rossa prima,
verde dopo), cosa Daniel deve provare parlando con Meridio, cosa non hai fatto e perché. Aggiorna la riga R170 di
docs/richieste.md e CHANGELOG.md. Suite intera e ruff verdi alla fine, con i numeri. Poi fermati: Claude rivede i
commit prima che entrino in lavoro.

Lavora in autonomia dal punto 1 al 6 senza chiedere conferme. Prima si prova, poi si afferma.
