# Incarico 4 per Kimi: disegnare una stringa sapendo dove si è, e salti che non si confondono (26/10/2026)

Sei al lavoro su Meridiana, il programma di Daniel Grasso per progettare impianti fotovoltaici (Python, PySide6 6.12,
Qt Quick 3D, pvlib). Due richieste di docs/richieste.md, R142 e R134: leggile parola per parola, con R114-R119 (la
stringatura a mano, compito 23: docs/compiti/23-stringatura.md) e R117 (i salti tratteggiati attorno ai moduli
saltati). Le regole di casa sono in CLAUDE.md (leggi tutto, comprese «How Meridiana runs» e «Diagnosing a failure»):
valgono anche per te.

## Dove lavori
- Nella cartella ~/dev/meridiana-kimi, su un ramo nuovo kimi-incarico-4 preso da origin/lavoro (il lanciatore lo crea
  prima di avviarti; controlla con git status e git log). I rami kimi-incarico-3 e kimi-revisione non si toccano più.
- Sistema immutabile: non installare nulla (niente dnf, rpm-ostree, sudo, flatpak, pip). Non scrivere fuori dalla tua
  cartella; non leggere ~/.ssh, ~/.gnupg, credenziali, altri repository, e nemmeno i progetti e le cartelle vere di
  Meridiana di Daniel (~/.config/meridiana, ~/.local/state/meridiana, ~/.cache/meridiana).
- Push disattivato: non provarci, non cambiare i remote. Mai merge su altri rami, rebase, reset --hard, force.
- Un commit per punto, identità Daniel Grasso <code@danielgrasso.com>, messaggio in inglese che nomina la richiesta
  (per esempio «... (R142)»): il cruscotto segna fatto un punto solo se un commit lo nomina. Nessuna attribuzione AI.
- Mai il trattino lungo, né nel codice né nei testi.

## Come si prova
- Interprete ~/fvtest/venv314/bin/python con PYTHONPATH=src della tua cartella (controlla meridiana.__file__); il
  catalogo con ~/fvtest/venv314/bin/python tools/compile_po.py; ruff con python -m ruff check src tests tools.
- Prove offscreen, un gruppo per processo, dalla cartella tests: QT_QPA_PLATFORM=offscreen python -m unittest
  discover -s <gruppo> -t . per nucleo, calcoli, formati, esterni, widget, finestra.
- Mai la finestra sullo schermo (Daniel lo usa): offscreen e cartelle XDG temporanee in /tmp.
- Il progetto di prova è quello che le prove usano già (_fixtures.capannone, tests/fixtures); non i progetti di Daniel.
- Le prove della finestra non devono mai aprire un dialogo modale vero (QInputDialog, QMessageBox): sostituiscili con
  mock, come fanno le prove che ci sono; un dialogo vero blocca la suite senza dire niente.
- Testi dell'interfaccia: msgid in inglese nel codice, italiano in po/it.po, nessuna voce fuzzy, msgfmt --check pulito.
- Fotografie offscreen prima e dopo in docs/revisioni/foto/ (nome kimi4-...), per far vedere a Daniel il risultato.

## Punti

1. R142, «non si capisce per quale inverter, quando disegno una stringa, la sto disegnando e come sono messo».
   Oggi (window.py: _start_draft, _draft_changed, _draft_finished; plant_page.py: show_string; plan.py: start_draft,
   la stringa in disegno) mentre si disegna ci sono già il conteggio nella striscia della pagina Impianto («nuova
   stringa 1.2: 5 moduli, mancano 3 (da 8 a 12)») e il suggerimento nella barra: Daniel non li vede, quindi non
   bastano. Una sessione precedente aveva cominciato (non salvato): la patch è in
   ~/dev/kimi-incarico-3-r142-a-meta.patch (show_draft con marca e modello dell'inverter e l'ingresso); leggila,
   riprendi quello che serve, il resto scartalo. Il risultato deve dire, sempre visibile mentre si disegna e dove
   l'occhio già guarda (sulla pianta, vicino al puntatore o all'ultimo modulo cliccato, oltre che nel pannello):
   - per quale inverter (numero, marca e modello) e quale ingresso;
   - quanti moduli ha la stringa e quanti l'ingresso ne accetta (da ... a ...), con lo stato come le etichette delle
     stringhe (la pillola di R167: ChipItem con swatch=True, simboli della finestra di ui/symbols.py, colori di
     stato): mancano, giusto, troppi; per un inverter con ottimizzatori il conteggio senza il giudizio;
   - come finire e come annullare (Invio o doppio clic, Backspace, Esc), in poche parole.
   Nell'elenco degli inverter a destra l'ingresso su cui si disegna è messo in evidenza, finché si disegna. La stringa
   in disegno ha il colore che avrà finita. Niente che si muova a ogni passo del mouse ridisegnando la scena intera
   (docs/prestazioni: si aggiorna solo l'oggetto che cambia). Prove: il testo e lo stato giusti con 0, pochi, giusti,
   troppi moduli; l'ingresso evidenziato e poi non più a stringa chiusa o annullata; la pillola che segue l'ultimo
   modulo; nessun dialogo.

2. R134, «quando ci sono sovrapposizioni di salti stringa devono essere distinguibili l'una dall'altra, in esempio
   in screenshot formano un triangolo e vanno a coincidere nel vertice in basso». Causa probabile, da verificare con
   una prova rossa prima: string_paths.Router.route riporta ogni via sugli spigoli veri dei moduli (le righe con
   `edges`), quindi i salti di stringhe diverse che girano attorno allo stesso modulo passano per lo stesso punto e
   per gli stessi tratti, e i tratteggi (plan.py: _string_paths, _string_items, _draw_wiring) si sovrappongono.
   Rendili distinguibili senza perdere quello che R117 ha dato (il salto non passa mai sopra un modulo non suo, si
   vede quale modulo è saltato). Proposte da valutare, scegli e spiega: corsie (ogni salto che condivide tratti o
   vertici con un altro spostato di lato di qualche pixel sullo schermo, a ogni ingrandimento, restando nello spazio
   tra i moduli; i salti di una stessa stringa nella stessa corsia); salti che non convergono nello stesso vertice
   (punti di passaggio diversi per stringhe diverse); il colore più leggibile del tratteggio di ogni stringa e un
   passo del tratteggio diverso. La geometria resta in string_paths.py senza Qt e con le sue prove (tests/calcoli o
   dove sono quelle di string_paths); il disegno in plan.py. Prove: due o tre stringhe i cui salti girano attorno allo
   stesso modulo non hanno più vertici né tratti in comune (distanza minima sullo schermo, a due ingrandimenti); un
   salto non entra in nessun modulo; i salti di una stringa sola restano come prima. Fotografie prima e dopo con il
   caso del triangolo ricostruito sul progetto di prova.

## Fine
Scrivi docs/revisioni/kimi-incarico-4-lavori.md: per ogni punto il commit, cosa è cambiato, le prove (rossa prima,
verde dopo), le fotografie, cosa Daniel deve provare sullo schermo, cosa non hai fatto e perché. Aggiorna le righe
R142 e R134 di docs/richieste.md e CHANGELOG.md. Suite intera e ruff verdi alla fine, con i numeri. Poi fermati:
Claude rivede i commit prima che entrino in lavoro.

Lavora in autonomia sui due punti senza chiedere conferme. Prima si prova, poi si afferma.
