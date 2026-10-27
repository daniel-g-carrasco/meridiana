# Incarico 5: lavori per R170

Data: 26/10/2026. Ramo `kimi-incarico-5`. Nessun modello vero chiamato, nessun push, nessuna installazione. Le prove
usano il progetto finto, il provider finto e la finestra offscreen; le cartelle XDG sono temporanee sotto `/tmp`.

## Punto 1: filtri e conteggi delle verifiche

Commit `8f60e94`, «Separate filtered check counts and add object filtering (R170, point 1)».

`read_checks` restituisce `filtered_counts` per l'elenco ottenuto e `project_counts` per l'intero progetto. Il nuovo
`object_id` filtra sottocampo, edificio o esclusione; un edificio comprende i suoi oggetti. Un elenco vuoto dichiara
che il filtro non ha trovato nulla. Descrizione e schema sono aggiornati.

- [V] Rosso prima: contro la base `2053deb`, la nuova prova non trova `checks` perché `object_id` non è accettato.
- [V] Verde dopo: filtro per sottocampo in aree diverse, conteggi distinti, elenco vuoto e schema controllati.
- Da provare parlando con Meridio: «La posa di Sottocampo 2 va bene?» deve leggere gli avvisi e le informazioni di
  quel sottocampo, senza attribuirgli i conteggi dell'impianto.

## Punto 2: testo e prezzo della correzione delle ombre

Commit `02367f5`, «Explain solar times and the cost of obstacle shade fixes (R170, point 2)».

Gli orari sono `10:00`, `14:00` e, per le mezze ore, `10:30`, sia nella correzione automatica sia nel dettaglio della
posa a mano. La proposta dice moduli rimanenti, moduli iniziali, quota rimossa e perdita per ombre. Se la quota dei
moduli tolti supera quella dell'irraggiamento perso, invita a confrontare e non presenta la correzione come ovvia.
Il dettaglio distingue correzione, spostamento e fascia di rispetto; quest'ultima toglie moduli, non ne conserva.

- [V] Rosso prima: sulla base comparivano `10.5` e soltanto «130 modules instead of 188».
- [V] Verde dopo: due prove per orari, costo, tre alternative e correzione più costosa dell'ombra.
- Da provare: la domanda originale su «Copertura», leggendo la proposta in italiano prima di applicarla.

## Punto 3: la base del 3,3 % e dell'1,04 %

Commit `0336231`, «Reconcile obstacle shade across arrays and the plant (R170, point 3)».

Il difetto riprodotto era l'aggregazione: la verifica prendeva un solo array e lo presentava con il nome del
sottocampo; la catena pesa tutto l'impianto. Ora la verifica aggrega tutti gli array del sottocampo con peso pari
alla potenza STC. Dichiara la quota dell'irraggiamento annuo del sottocampo dopo le ombre lontane. `read_results`
dichiara che ogni passo della catena riguarda l'impianto e riporta anche le quote dei singoli array con la loro base.

- [V] Rosso prima: due array dello stesso sottocampo, perdite 8 % e 0 %, davano «Copertura est: 8 %» invece del 4,8 %
  complessivo; i risultati non avevano il campo `basis`.
- [V] Verde dopo: una simulazione oraria con un array grande ombreggiato e uno piccolo libero dimostra che il passo
  `near` dell'impianto coincide con la media pesata delle quote degli array a parità di base, con 12 cifre decimali.
- Da provare: confrontare la nuova percentuale della verifica con la catena sul progetto del capannone, tenendo
  presente che `near` comprende anche le ombre tra le file.

## Punto 4: nomi e valori della finestra

Commit `66e5278`, «Give Meridio the Properties panel names and values (R170, point 4)».

Il nuovo nucleo `fields.py` condivide con Proprietà e Annulla i nomi dei campi, dei montaggi e dei modi del passo.
`read_selection` aggiunge `params_display`; `project_summary` aggiunge i nomi leggibili accanto ai valori tecnici,
necessari soltanto a `propose_edit`. La persona vieta a Meridio di parlare al progettista con chiavi e valori codificati.

- [V] Rosso prima: mancavano `params_display` e la regola della persona.
- [V] Verde dopo: «row pitch / From the sun», «out of the shadows / no», «Coplanar on the pitch» e «Portrait» sono
  restituiti dagli strumenti; Proprietà usa le stesse tabelle condivise.
- Da provare: chiedere i parametri di «Sottocampo 2» in italiano e controllare che compaiano «Passo delle file»,
  «Dal sole», «Fuori dalle ombre degli ostacoli» e i valori della finestra.

## Punto 5: Annulla e Ripeti

Commit `1c15e4a`, «Offer undo and redo as designer-applied cards (R170, point 5)».

`propose_undo` propone una card con il testo di `undoText` o `redoText`. Non modifica la cronologia. Soltanto il clic
su Applica chiama lo stesso `UndoBridge` del menu. Se non c'è un passo nella direzione chiesta, lo strumento lo dice.
La persona spiega che Meridio può proporre, mai annullare o ripetere da solo.

- [V] Rosso prima: lo strumento non esisteva e nella finestra non compariva alcuna card.
- [V] Verde dopo: host finto mai chiamato per applicare; nella finestra reale offscreen il clic annulla 20° a 15° e
  poi ripete 15° a 20°, senza creare una modifica fuori dalla cronologia. La card italiana è stata fotografata e
  guardata: «Proposta: Annulla», «Passo: Cambia inclinazione», «Scarta» e «Applica», senza tagli o sovrapposizioni.
- Da provare: dopo una proposta applicata chiedere «possiamo tornare indietro?», leggere il passo e cliccare; poi
  chiedere «ripeti».

## Punto 6: la conversazione ripetuta e i limiti del modello

Il commit che contiene questo rapporto ha messaggio «Replay Daniel's conversation with unambiguous tools (R170,
point 6)».

La nuova prova `DanielConversation` guida Claude Haiku finto attraverso verifica, proposta, catena delle perdite,
annulla, due letture del piccolo sottocampo, selezione e riepilogo. Controlla i JSON effettivamente consegnati al
modello: conteggi del filtro e del progetto, `10:00` e `14:00`, 130 contro 188 e 31 %, fascia che non conserva moduli,
base del sottocampo e dell'impianto, nomi dei parametri, proposta di annulla non applicata. [V] La stessa prova è
rossa sulla base e verde dopo.

Resta affidato al modello il ragionamento linguistico: scegliere gli strumenti e il filtro giusto, confrontare i
numeri, non contraddire il dettaglio e formulare il consiglio. Le risposte ora gli danno dati espliciti, ma un modello
piccolo come Haiku può ancora ragionare male. Non è stata cambiata l'impostazione predefinita: qui non è stata fatta
una valutazione comparativa reale e Sonnet costa molto di più. [I] Per ragionamenti progettuali complessi conviene
usare Sonnet, già offerto come «per le domande difficili»; Haiku resta ragionevole per letture e operazioni correnti.
Da provare sul progetto vero con entrambi, senza assumere che la prova finta misuri la qualità del ragionamento.

## Verifica finale

- [V] Controllo del rosso iniziale: sei casi del nucleo falliti sulla base `2053deb`, più la card assente nella
  finestra. Worktree temporaneo rimosso dopo la prova.
- [V] `ruff check src tests tools`: nessun errore.
- [V] `tools/compile_po.py` e `msgfmt --check`: catalogo italiano compilato, nessuna voce fuzzy.
- [V] `meridiana.__file__` verificato dentro `src` di questo checkout.
- [V] Suite finale, un gruppo per processo, offscreen: `nucleo` 794 con 4 saltate, `calcoli` 176, `formati` 59,
  `widget` 307 con 1 saltata, `finestra` 130. Totale 1.466 prove, 1.461 verdi e 5 saltate.
- [V] Gruppo `esterni`: 6 prove saltate perché gli esempi PVsyst e le prove di tempo esterne non erano abilitati.
  Nessuna prova esterna eseguita.

## Cosa non è stato fatto

- Nessuna chiamata a Claude o al modello locale, come richiesto. La qualità delle risposte di Haiku o Sonnet sul
  progetto reale resta quindi da verificare; qui è verificato il contenuto che ricevono.
- Nessuna prova sul progetto reale di Daniel né sullo schermo. La card è stata provata e guardata offscreen.
- Nessuna modifica al modello predefinito, perché manca un confronto reale e la scelta incide anche sul costo.
- Nessun push, merge o rebase: i sei commit restano per la revisione di Claude.
