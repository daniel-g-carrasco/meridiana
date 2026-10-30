# Rapporto L: traduzioni italiane dopo la tranche R07 (30/10/2026)

File toccato: solo `po/it.po` (aggiunta in coda, 47 voci, nessuna riga esistente cambiata o tolta: `git diff` del po
ha 0 righe rimosse) e il compilato `locale/it/LC_MESSAGES/meridiana.mo` prodotto da `tools/compile_po.py`.
Nessun git, nessun altro file del progetto.

## 1. Che cosa ho rivisto

- Scansione AST di `src/meridiana/**/*.py` (script nello scratchpad della sessione, `scan_msgids.py`): chiamate
  `_()`, `N_()`, `ngettext()` (singolare e plurale), `pgettext()` (contesto), anche come attributo (`i18n._`),
  con concatenazioni di letterali (`"a" "b"` e `"a" + "b"`). Il po è letto con il `parse()` di `tools/compile_po.py`.
- Esito prima delle aggiunte: 3696 chiavi nel codice, 3712 nel po, **47 mancanti**, 0 fuzzy, 0 vuote, 0 doppie,
  63 voci del po non usate dal codice, 5 chiamate non letterali (sotto, §6).
- Esito dopo: 3759 voci nel po, **0 mancanti**, 0 fuzzy, 0 vuote, 0 doppie, 63 non usate (invariate: non cancellate).
- Il po è in CRLF: il blocco è stato accodato in CRLF (controllo con `od -c`). Nessun trattino lungo nel po.

## 2. Voci aggiunte (47: 38 semplici, 9 con plurale)

Fonti: E §5, F §8, I §5, M §5 dei rapporti in `build/claude-r07/`; dove non c'era proposta ho tradotto io nello stile
del po. Le voci con segnaposto hanno il flag `#, python-brace-format` così `msgfmt --check-format` confronta i campi.

Barra della produzione e finestra (E, I):
- `Production: {what} ({n} of {total})` → `Produzione: {what} ({n} di {total})`
- `Production stopped: the values are those of the last computation.` → `Calcolo della produzione fermato: i valori sono quelli dell'ultimo calcolo.`
- `Note: {notes}` → `Nota: {notes}`
- ngettext `Plant > Strings: the string was cleared; its modules stay laid. Use Draw or Propose to start again. Undo restores the previous wiring.` / `Plant > Strings: all {n} strings cleared; ...` → `Impianto > Stringhe: eliminata la stringa; i suoi moduli restano posati. Usa Disegna o Proponi per ricominciare. Annulla ripristina i collegamenti precedenti.` / `Impianto > Stringhe: eliminate tutte le {n} stringhe; i moduli restano posati. Usa Disegna o Proponi per ricominciare. Annulla ripristina i collegamenti precedenti.`

Pagina Produzione e Meridio (mie):
- `{n} of {total} modules connected` → `{n} moduli collegati su {total}` (stessa resa della vecchia voce «connected modules»)
- `Fetch from PVGIS` → `Scarica da PVGIS` (il po dice già «Scarica il meteo da &PVGIS»)
- `Choose a model from your provider account.` → `Scegli un modello del tuo account presso il fornitore.`
- `The cloud model is not configured: {why}` → `Il modello cloud non è configurato: {why}`

Finestrella delle marche (M):
- `Favourites` → `Preferiti`
- `Search…` → `Cerca…`
- `Add to favourites (Ctrl+D)` → `Aggiungi ai preferiti (Ctrl+D)`
- `Remove from favourites (Ctrl+D)` → `Togli dai preferiti (Ctrl+D)`
- `Search a manufacturer` → `Cerca una marca`
- `All manufacturers` → `Tutte le marche`
- `No model of {maker} in the catalogue has the datasheet data the sizing needs.` → `Nessun modello di {maker} nel catalogo ha i dati di scheda tecnica che servono al dimensionamento.`
- `Sizable instead: {brands}.` → `Si possono dimensionare invece: {brands}.`

Riepilogo degli inverter attivi, `plant_page.py` (E):
- ngettext `{active} of {total} inverter with strings` / `... inverters ...` → `{active} di {total} inverter con stringhe` (entrambe)
- ngettext `on {n} input` / `on {n} inputs` → `su {n} ingresso` / `su {n} ingressi`
- `no strings` → `nessuna stringa`
- `and {n} more` → `e altri {n}`

Cause del dimensionamento, `sizing.py` (F):
- `nominal AC power` → `potenza CA nominale`
- `number of MPPT` → `numero di MPPT`
- `MPPT minimum voltage` → `tensione minima MPPT`
- `MPPT maximum voltage` → `tensione massima MPPT`
- `FIMER took over ABB's solar inverter business on 2 March 2020` → `FIMER ha rilevato il ramo inverter fotovoltaici di ABB il 2 marzo 2020`
- ngettext `{name}: {n} model with complete data, {lo} to {hi} kW` / `... models ...` → `{name}: {n} modello con dati completi, da {lo} a {hi} kW` / `{name}: {n} modelli con dati completi, da {lo} a {hi} kW`
- ngettext `{field} missing in {n} record` / `... records` → `{field} manca in {n} scheda` / `{field} manca in {n} schede` (F proponeva «record»; il po chiama «scheda» la voce di catalogo)
- `None of the {n} inverters of {maker} in the catalogue can be sized: {missing} (for example {model}). Meridiana does not invent missing datasheet values.` → `Nessuno dei {n} inverter di {maker} nel catalogo si può dimensionare: {missing} (per esempio {model}). Meridiana non inventa i dati che mancano nelle schede.`
- `These records come from the CEC list of the California Energy Commission, which gives no MPPT count and no current per input` → `Queste schede vengono dalla lista CEC della California Energy Commission, che non dà né il numero di MPPT né la corrente per ingresso`
- `, for the US market (grid {volts} V), not for a 230/400 V grid` → `, per il mercato USA (rete {volts} V), non per una rete 230/400 V`
- `no SolarEdge optimizer of the catalogue takes {module} (Pmax {p} W, Voc {voc} V, Isc {isc} A): {why}` → `nessun ottimizzatore SolarEdge del catalogo accetta {module} (Pmax {p} W, Voc {voc} V, Isc {isc} A): {why}`
- `{group}: {n} modules on one plane, a string needs at least {lo} even with {opt} ({source})` → `{group}: {n} moduli sullo stesso piano, una stringa ne vuole almeno {lo} anche con {opt} ({source})` (F diceva «falda»; il po rende «plane» con «piano», e vale anche a terra)
- `no series length of {module} fits the MPPT window {vmin} to {vmax} V within {vdc} V (cell from {cold} to {hot} °C, lowest {tmin} °C)` → `nessun numero di {module} in serie sta nella finestra MPPT da {vmin} a {vmax} V entro {vdc} V (cella da {cold} a {hot} °C, minima {tmin} °C)`
- `{group}: {n} modules, a string needs {lo} to {hi} in series (MPPT from {vmin} V, module Vmp {vmp} V at {hot} °C of cell)` → `{group}: {n} moduli, una stringa ne vuole da {lo} a {hi} in serie (MPPT da {vmin} V, Vmp del modulo {vmp} V con la cella a {hot} °C)`
- `{module}: no input takes even one string: the input current limits ({limits}) are below the module's Imp {imp} A or Isc x 1.25 = {i} A` → `{module}: nessun ingresso prende nemmeno una stringa: i limiti di corrente degli ingressi ({limits}) sono sotto la Imp del modulo {imp} A o Isc x 1,25 = {i} A`
- `string` → `stringa`
- ngettext `{n} combination could not be decided within {k} search steps: {which}.` / `{n} combinations could not be decided within {k} search steps each: {which}.` → `{n} combinazione non si è potuta decidere entro {k} passi di ricerca: {which}.` / `{n} combinazioni non si sono potute decidere entro {k} passi di ricerca ciascuna: {which}.`
- `Why:` → `Perché:`
- ngettext `and {n} other` / `and {n} others` → `e {n} altro` / `e altri {n}`
- ngettext `• and {n} more` / `• and {n} more` → `• e {n} altro` / `• e altri {n}`
- `Other names in the catalogue: {brands}.` → `Altri nomi nel catalogo: {brands}.`
- `No complete string proposal is possible with these inverters: some modules cannot be strung by any of them, whatever their quantity.` → `Con questi inverter non è possibile una proposta completa di stringhe: alcuni moduli non possono andare in stringa su nessuno di essi, qualunque sia la quantità.`
- ngettext `{n} combination ranked before this one could not be decided within the search limit: {which}` / `{n} combinations ranked ...` → `{n} combinazione prima di questa in classifica non si è potuta decidere entro il limite di ricerca: {which}` / `{n} combinazioni prima di questa in classifica non si sono potute decidere entro il limite di ricerca: {which}`
- `No valid combination was found among those decided, and not every combination could be decided: this is not a proof that none exists.` → `Nessuna combinazione valida tra quelle decise, e non tutte si sono potute decidere: non è la prova che non ne esista una.`

Ottimizzatori, `optimizers.py` (F):
- `{name}: DC power within the Synergy unit's maximum` → `{name}: potenza CC entro il massimo dell'unità Synergy`
- `At most one optimizer with a single module in the string` → `Al più un ottimizzatore con un solo modulo nella stringa`
- `{n} optimizers with a single module: either one, or all of them` → `{n} ottimizzatori con un solo modulo: o uno, o tutti`

Già presenti nel po, quindi non aggiunte, le voci citate dai rapporti `{n} module in no string` (F),
`No inverter with a nominal AC power and a complete MPPT datasheet is available.` (F), `All` (M), `Stopped.` (A),
`PVGIS: {what} ({n} of {total})` e `Size the inverter by itself` (I).

## 3. Voci del po che il codice non usa più (63, NON cancellate)

Da togliere o tenere decide Claude/Daniel; alcune sono vecchie varianti dei testi di oggi:
- `{n} of {total} connected modules` (sostituita da `{n} of {total} modules connected`)
- `Plant > Strings: all {n} strings cleared; the modules stay laid. ...` come voce semplice (oggi è il plurale della ngettext nuova)
- `PVGIS stopped: the values are those of the last computation.` (sostituita da «Production stopped…», rapporto I)
- `I need a language model to answer you. Choose one on this PC for local work, or connect a provider account. This guide works without a model. ...` (vecchia guida di Meridio)
- `Inverters sized: {what}, DC/AC {r}. All {n} modules have a valid string. Choice: {criterion}.`
- `Download Kokoro's model (two files, about 350 MB) ... Nothing of yours is sent.` (senza la licenza)
- `No complete string proposal was found within the voltage, current and input limits. The assignment is heuristic; ...`
- `No inverter combination can string every module within the voltage, current and input limits. Change the module count, the brand or the DC/AC ratio.`
- `Connected {n} strings; {m} modules remain unconnected. Review the selected inverters and inputs. Undo restores the previous wiring.`
- `String assignment completed: {n} strings. Undo restores the previous wiring.`
- `Inverters: one efficiency curve for the whole system, clipped at the nominal AC power of all the inverters together; ...` e la variante `... of the connected inverters together; ...`
- Serie «Claude» prima dei fornitori generici: `Claude model`, `Claude key`, `No Claude key yet.`, `Claude key in the system's keyring: {key}`, `Your Anthropic API key (it goes to the system's keyring, never to a file):`, `No keyring on this system: Claude cannot be used.`, `Withdraw the consent to send questions to Claude, given on {date}`, `Claude, with your key and after your consent: for the hard questions`, `Claude refused the key: check it in Settings > Assistant.`, `No network: Claude cannot be reached. The question goes to the local model.`, `Send this question to Claude?`, `No Claude key in the system's keyring (Settings > Assistant): the question goes to the local model.`, `The local model, on this PC: nothing leaves it (the default)`
- Modello locale: `No local model on this PC`, `A few steps give {name} a model of his own on this PC: one program and one command. The guide is in Settings > Assistant.`, `Show me how`, `Questions ready: press 1, 2, 3`
- Batteria: `Battery`, `Choose a ba&ttery from the catalogue…`, `Choose the battery`, `A battery from the catalogue for the balance`
- Stringhe e inverter: `{n} inputs`, `{a} A of DC current in all, taken as {b} A an input`, `Meridiana finds no string to propose: {why}`, `the inverter does not take these modules in series`, ngettext `{n} string proposed by Meridiana ({strategy}): yours now, nothing changes it by itself.`, `No string to add: the modules in no string are too few for a string, or the inputs take no more. ...`, ngettext `{n} string added for the modules that were in none; yours stayed as they were.`, `Every string deleted: draw yours with «+» on an input of the list on the right, or «Draw».`, `Yes, propose it`, `strings not alike on this input (PVsyst asks for identical strings on an MPPT)`, `Delete all`, `Components`, `A new string on input {k} of inverter {n}: then click its modules on the plan in order ({takes})`, `As many inverters as the DC/AC ratio asks, all like the first of the list; without one, Meridiana sizes one at that ratio`, ngettext `Inverter sized: {n} x {maker} {model}, DC/AC {r}.`, `{name}\n{kw} kW AC · {n} inputs · {strings}`, `Modules on each optimizer: two in series where the optimizer takes them`
- Testi lunghi di metodo: `The obstacles of the scene (exclusions with a height, parapets, the other buildings) cast their shadows ...` (versione vecchia), `Two steps are estimates, not measurements: ...`, `SolarEdge allows a string across several roof planes, but it can lose additional energy. ...`, `Electrical shading uses the Martinez-Moreno estimate ...`, `Optimizers: string and module compatibility checks use the supported SolarEdge tables; ...`
- Varie: `Hi, I am {name}, Meridiana's assistant. I read your project ... when a figure comes fro…` (variante vecchia della presentazione), `The project's name, its address and the file's name are replaced by placeholders; the coordinates are rounded to about 1 km.`, `A .meridiana file, from wherever it is.`, `Add the buildings`, `Reserved project: names and addresses never leave this PC`, `Allow online map tiles for this project: the area shown leaves this PC`, `The files stay where they are: the project keeps their place, relative to its own file`, `Finish`

L'elenco completo con contesto e plurali è nel JSON della scansione (scratchpad della sessione, `scan2.json`, chiave
`unused`); non l'ho copiato nel repo perché non è un file di progetto.

## 4. Esito di msgfmt e del compilatore

- `wsl -d openSUSE-Tumbleweed -- msgfmt --check --check-format --statistics -o /dev/null po/it.po` (da
  `/mnt/c/Users/Grasso/dev/meridiana-integra-kimi-9-10`): **`3759 translated messages.`**, exit 0, nessun fuzzy,
  nessun non tradotto, nessun errore di formato [verificato].
- `python tools/compile_po.py --python` (Python del venv `C:\Users\Grasso\dev\meridiana`): scrive
  `locale\it\LC_MESSAGES\meridiana.mo` (481.597 byte), exit 0; il suo controllo dei `{segnaposto}` non segnala nulla
  [verificato].
- `python -m unittest nucleo.test_i18n` → 10 OK [verificato].

## 5. Controllo a campione nel programma (offscreen, LANGUAGE=it)

Modulo di prova nello scratchpad (`test_campione_it.py`, usa `tests/_setup.py` come le prove del progetto; ambiente
delle regole, `PYTHONPATH=tests;src`, PySide6 nel PATH). 4 prove, **4 OK in 11 s** [verificato]:
- barra della produzione: `win._energy_step(gen, 2, 4, "la rete elettrica")` senza job in corso → etichetta
  `Produzione: la rete elettrica (3 di 4)`; `win._cancel_pvgis()` → stato della pagina
  `Calcolo della produzione fermato: i valori sono quelli dell'ultimo calcolo.`;
- finestrella delle marche (`NameDialog`): segnaposto `Cerca…`, intestazioni `Preferiti` / `Tutti`, tooltip
  `Aggiungi ai preferiti (Ctrl+D)`;
- guida di Meridio (`AssistantSetup`): prima etichetta `Per risponderti mi serve un modello linguistico. Scegli locale o
  cloud: ti guiderò io. ...`; `Il modello cloud non è configurato: x`;
- pagina Produzione: pulsante `Scarica da PVGIS`; plurali `su 2 ingressi`, `1 di 3 inverter con stringhe`,
  `5 moduli collegati su 8`, `MPPT manca in 1 scheda`.

## 6. Limiti e cose non verificate

- Chiamate `_()` con argomento non letterale, che la scansione non può confrontare con il po: `checks.py:288` e
  `:291` (`_(note)`), `ui/properties.py:962` (`_(n)`): traducono note prodotte altrove (posa). Non ho verificato che
  ogni nota possibile abbia la sua voce nel po (dedotto: le note sono letterali marcati nei moduli di calcolo, dato
  che `layout.py` e `model.py` usano `N_`/`_`). Le due in `i18n.py` sono le definizioni stesse.
- Le 63 voci inutilizzate restano nel po: non cancellate, come chiesto.
- Non ho rigenerato il `.pot` né usato `xgettext`/`msgmerge`: il blocco è accodato a mano senza commenti `#:` di
  posizione, come le aggiunte precedenti in coda al po.
- Non ho eseguito la suite intera né prove di altri lotti; le prove delle regole (temi, fluidità) non riguardano il po.
- Le cause di dimensionamento di `sizing.py` sono state viste solo tramite `_()`/`ngettext()` diretti nella prova
  campione, non facendo girare un dimensionamento reale.
