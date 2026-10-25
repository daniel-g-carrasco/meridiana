# Revisione Kimi 4: testi e traduzioni

Data: 25/10/2026. Ramo: `kimi-revisione`.

## Metodo e esiti generali

Ho esaminato le chiamate `_()`, `ngettext()` e `pgettext()` nei sorgenti, le chiamate con messaggi dinamici, i
principali testi Qt, `po/it.po` e `tools/compile_po.py`. Ho generato un POT temporaneo con la stessa riga di
`xgettext` usata dal progetto, senza modificare `po/it.po`, e ho confrontato msgid, contesti e plurali.

[V] Esiti del controllo automatico:

- `msgfmt --check --statistics po/it.po`: **3.161 messaggi tradotti**, nessun errore;
- POT temporaneo: 3.057 voci compresa l'intestazione; PO attivo: 3.162 compresa l'intestazione;
- msgid presenti nei sorgenti ma assenti nel PO: **0**;
- voci attive nel PO non più presenti nei sorgenti: **105**;
- fuzzy: **0**; non tradotte: **0**; stesso msgid e contesto con traduzioni diverse: **0**;
- una voce già commentata come obsoleta, `po/it.po:5736-5737`;
- chiamate dinamiche a `_()`: `checks.py:261,264` e `ui/properties.py:884`. Sono importanti perché xgettext non può
  vedere il testo contenuto nelle variabili;
- ricerca di U+2014 in tutta la copia: solo l'asserzione `tests/nucleo/test_assistant_persona.py:55` che lo vieta.
  **Nessun trattino lungo trovato** in codice, PO o documenti.

Il risultato «nessun msgid mancante» vale per le stringhe che xgettext vede. Le prime due osservazioni mostrano
perché il controllo dei messaggi dinamici resta necessario.

## Osservazioni, dalla più grave

### 1. Due note di posa e un errore di area restano in inglese anche in italiano

- **File e righe**: `src/meridiana/layout.py:40-41` (`BALLAST_WARNING`), `:372` (area sotto 1 m²), `:409`
  («no room left inside the margins»); visualizzazione dinamica in `src/meridiana/checks.py:256-264` e
  `src/meridiana/ui/properties.py:881-884`.
- **Che cosa succede**: le note vengono passate a `_()` soltanto quando vengono mostrate. Questo rende traducibile la
  chiamata, ma xgettext non estrae il loro testo letterale dai punti in cui nasce. Il PO non contiene nessuno dei
  tre msgid, quindi gettext restituisce l'inglese.
- **Scenario concreto A**: un sottocampo con montaggio `tilted_ballasted` produce la nota `BALLAST_WARNING`.
  Nelle Verifiche e nelle Proprietà, con il programma in italiano, il testo resta: «Ballast alone is not a restraint
  on a roof slab ... anchors or tie-downs are needed.»
- **Scenario concreto B**: un contorno fra 0,5 e 1 m² supera il rifiuto iniziale della finestra, ma non quello della
  posa. Il risultato d'errore contiene «the area encloses less than 1 m2», mostrato nelle Proprietà e nel
  suggerimento dell'albero. Se non resta spazio nei margini, la nota è «no room left inside the margins».
- **Gravità**: media. Sono messaggi utente in una lingua diversa da quella scelta, proprio dove servono per capire
  perché la posa non è valida.
- **Prova**: [V] lettura dei tre messaggi e dei punti di visualizzazione; [V] ricerca assente nel PO; [V] chiamata a
  gettext con il catalogo compilato che restituisce tutti e tre invariati in inglese. [V] `tests/nucleo/test_layout.py:60`
  verifica la presenza della nota in inglese nei dati, non la traduzione in italiano.
- **Correzione proposta**: importare `_` in `layout.py` e marcare i tre testi alla fonte:
  `BALLAST_WARNING = _("...")`, `raise ValueError(_("the area encloses less than 1 m2"))` e
  `notes + [_("no room left inside the margins")]`. Aggiungere le traduzioni italiane con l'aggiornamento del PO e
  una prova che carica il catalogo italiano e verifica tutte le note di una posa in questi tre casi. Non cambiare
  regole, soglie o risultati della posa.
- **Rischio della correzione**: basso. Le prove che leggono le note in inglese continuano a passare con
  `LANGUAGE=en`; quelle in italiano devono provare il testo tradotto, non soltanto la chiamata a `_()`.

### 2. Altri messaggi che arrivano all'utente non passano da `_()`

- **File e righe**:
  - `src/meridiana/underlay.py:60-67`: due punti coincidenti o distanza nulla;
  - `src/meridiana/model.py:623-829`: validazione del progetto; `:986`, `:1053`, `:1113-1118`: variante, ombre e
    formato del file;
  - `src/meridiana/pvsyst/pvobject.py:97`, `project.py:207`, `:222`, `:361`, `records.py:49`: file PVsyst;
  - `src/meridiana/energy/meteo.py:129`, `:149-151`, `:183`, `:224-231`: meteo e orizzonte;
    `src/meridiana/energy/pvgis.py:62`, `:70`: risposta PVGIS;
  - `src/meridiana/services/geocoding.py:37-45`: risposta di ricerca;
  - `src/meridiana/viewaids.py:20`, `roofs.py:78`, `tiles.py:540-556`: altri valori che possono arrivare a un
    messaggio dell'interfaccia.
- **Che cosa succede**: le eccezioni hanno testo inglese non registrato. I chiamanti mostrano `str(error)` o lo
  inseriscono in un messaggio tradotto, lasciando la parte decisiva in inglese.
- **Scenario concreto**:
  - si mette in scala un'immagine scegliendo due volte lo stesso punto: `_change_underlay`
    (`ui/window.py:1728-1736`) mostra «two distinct points and a distance above zero are needed»;
  - si apre un file che non è un progetto: `open_path` (`ui/window.py:4434-4441`) mostra «not a Meridiana project»;
  - si importa un file PVsyst non valido: `_import_pvsyst_project` (`:4122-4126`, `:4144-4147`) mostra l'eccezione
    non tradotta;
  - la cache dell'orizzonte è danneggiata o PVGIS risponde in modo inatteso: il messaggio tecnico compare nella
    pagina Producibilità e nelle Verifiche;
  - il servizio di geocodifica restituisce una struttura inattesa: `SiteDialog.show_answer` riceve il testo
    dell'errore (`ui/site_dialog.py:81-100`).
- **Gravità**: media. Non impedisce l'uso, ma rende errori e cause incomprensibili a chi ha scelto l'italiano.
- **Prova**: [V] lettura dei messaggi e dei percorsi di visualizzazione; [V] ricerca assente nel PO; [V] gettext
  restituisce invariati «two distinct points...», «not a Meridiana project», «made by a newer Meridiana...»,
  «damaged horizon profile» e «not a list of places». Non ho eseguito ogni percorso di errore: quelli elencati
  come collegamento fra eccezione e interfaccia sono verificati staticamente, non tutti end-to-end.
- **Correzione proposta**: marcare i messaggi alla fonte, mantenendo invariati percorsi delle chiavi e segnaposto.
  Per esempio `_("two distinct points and a distance above zero are needed")`, `_("not a Meridiana project")` e
  `_("made by a newer Meridiana (format {version}); update the program to open it")`. Fare l'inventario completo
  delle righe elencate, non soltanto dei due esempi. Aggiungere prove per un file non progetto, due punti
  coincidenti, un PVsyst non valido e una cache danneggiata, tutte con il catalogo italiano.
- **Rischio della correzione**: medio, perché molte prove confrontano messaggi inglesi. Vanno aggiornate solo le
  asserzioni che riguardano la traduzione, mantenendo identici tipo di eccezione, chiavi e valori nei segnaposto.

### 3. La galleria contiene decine di testi italiani non traducibili

- **File e righe**: `src/meridiana/ui/gallery.py:108`, `:122-154`, `:168-179`, `:197-237`, `:248-261`,
  `:277-283`, `:300-317`.
- **Che cosa succede**: titolo della finestra, schede, pulsanti, etichette, gruppi, esempi e stati sono letterali
  italiani senza `_()`. Non sono soltanto nomi tecnici o dati: includono comandi e spiegazioni dell'interfaccia.
- **Scenario concreto**: si avvia `python -m meridiana.ui.gallery` con l'inglese come lingua. Il titolo resta
  «Meridiana: sistema grafico» e i pulsanti restano «Calcola», «Togli i moduli», «Non ora», «Scarica»; le schede
  e gli aiuti restano in italiano. La galleria non può servire da esempio fedele di un template multilingua.
- **Gravità**: bassa. È una galleria di sviluppo, non il percorso principale, ma è anche la vetrina del sistema
  grafico e l'esempio per altri programmi.
- **Prova**: [V] scansione dei letterali e lettura della galleria. Esempi non coperti dalla scansione iniziale a una
  sola parola, come `QPushButton("Pulsante")`, sono stati inclusi nella revisione manuale.
- **Correzione proposta**: sostituire i testi visibili con msgid inglesi e `_()`, poi aggiungere le traduzioni
  italiane nel PO. Non basta avvolgere l'italiano attuale in `_()`: `i18n.py` dichiara i sorgenti in inglese.
  Nomi di colori, icone, chiavi tecniche e valori numerici non vanno tradotti.
- **Rischio della correzione**: basso per il funzionamento; medio per il numero di voci da tradurre e per eventuali
  schermate della galleria usate come riferimento, che dovranno essere rifatte.

### 4. Il PO conserva 105 voci attive non più usate e una già obsoleta

- **File e righe**: `po/it.po` nel complesso; esempi `:18-19` (`usage: ... [FOLDER...]` sostituito da
  `... [PROJECT]`), `:3203-3204` (`Fix` sostituito da `Fix…`), `:5038-5043` (`Undo` e `Redo`),
  `:9132-9133` (`Start again`); voce già obsoleta `:5736-5737`.
- **Che cosa succede**: il catalogo attivo contiene traduzioni di versioni precedenti che nessuna chiamata attuale
  estrae. Non causano msgid mancanti e non producono errori, ma aumentano rumore e possibilità di riusare per
  errore una formulazione superata. Una voce è già marcata obsoleta da `#~`.
- **Scenario concreto**: chi traduce cerca «Redo the strings automatically» o vecchie descrizioni della
  stringatura e trova testi che non esistono più nel programma, senza capire se siano ancora da mantenere.
- **Gravità**: bassa. Nessun effetto visibile dimostrato; è debito del catalogo.
- **Prova**: [V] confronto POT/PO con contesti e plurali: 105 voci attive in più rispetto ai sorgenti.
  [V] `msgattrib --obsolete` mostra la singola voce commentata. Ho anche verificato che `_()` abbia soltanto tre
  chiamate dinamiche, tutte analizzate, quindi la pulizia non deve cancellare note usate dinamicamente senza prima
  confrontarle con il loro testo reale.
- **Correzione proposta**: dopo approvazione, eseguire `python3 tools/compile_po.py --update` su Linux, rivedere le
  voci spostate tra gli obsoleti e poi rimuovere gli obsoleti con `msgattrib --no-obsolete`, conservando un diff
  leggibile. Non cancellare semplicemente le 105 voci alla cieca: se una stringa è usata dinamicamente va prima
  confermata alla fonte. La voce già commentata può essere eliminata senza effetti sulle traduzioni caricate.
- **Rischio della correzione**: basso per il funzionamento; medio per la perdita accidentale di traduzioni ancora
  utili se il confronto statico venisse applicato senza revisione umana.

### 5. Due incoerenze lessicali sono verificate; altre apparenti sono contesti corretti

- **File e righe**: `po/it.po:111-112`, `:220-221`, `:1250-1251`, `:6429-6430`, `:9431-9432` per «layout»;
  `:10214-10221` per le colonne «Rows, linear», «Obstacles, linear» e «Rows, electrical», originate in
  `src/meridiana/ui/report_chapters.py:481-488`.
- **Che cosa succede**:
  - la posa dei moduli è chiamata prevalentemente «posa», ma «Layout» diventa «Disposizione» e alcuni messaggi
    usano «disposizione del sottocampo». Il comando corrispondente è «Posa i moduli» e gli errori parlano di «posa»;
  - le colonne dell'ombra sono tradotte «File, lineare», «Ostacoli, lineare» e «File, elettrico». Manca il plurale
    e il riferimento all'ombra o all'effetto, quindi le intestazioni sono poco naturali e poco chiare.
- **Scenario concreto**: in Verifiche si apre l'area «Disposizione», mentre il comando per produrre lo stesso
  risultato è «Posa i moduli». Nella relazione, la tabella dell'ombra mostra intestazioni che sembrano riferirsi a
  un attributo elettrico generico invece che all'ombra lineare e al suo effetto elettrico.
- **Gravità**: bassa. Non cambia il significato dei calcoli, ma riduce la leggibilità dei concetti principali.
- **Prova**: [V] confronto dei msgid e dei messaggi nella relazione. [V] invece «Pitch» ha due traduzioni corrette
  per contesto: `pgettext("rows", "Pitch")` è «Passo» e `pgettext("roof", "Pitch")` è «Falda»
  (`po/it.po:4611-4613`, `:5062-5064`). Anche «Production» come fase («Producibilità») e «production» come energia
  («produzione») non sono conflitti: sono concetti diversi.
- **Correzione proposta**: usare «Posa» per il msgid `Layout` e rivedere i quattro messaggi collegati, senza
  cambiare «disposizione» quando indica la finestra o una variante di disposizione. Per le colonne proporre
  «File, ombra lineare», «Ostacoli, ombra lineare» e «File, effetto elettrico», che conservano il significato e
  risolvono anche il numero. In alternativa, la forma minima «File, lineari», «Ostacoli, lineari»,
  «File, effetto elettrico».
- **Rischio della correzione**: basso. Solo `msgstr`, nessun cambiamento di comportamento o di msgid richiesto.

## Script di controllo usato

Questo è il nucleo del controllo ripetibile. Scrive soltanto in `/tmp` e non aggiorna il catalogo. La scansione delle
chiamate dinamiche serve a non dichiarare obsolete stringhe che xgettext non può vedere.

```bash
tmp=$(mktemp -d /tmp/meridiana-po-XXXXXX)
sources=$(python3 -c 'from pathlib import Path; print(" ".join(sorted(p.as_posix() for p in Path("src/meridiana").rglob("*.py"))))')
xgettext --language=Python --keyword=_ --keyword=ngettext:1,2 \
  --keyword=pgettext:1c,2 --keyword=N_ --from-code=UTF-8 \
  --package-name=meridiana --output "$tmp/current.pot" $sources
msgfmt --check --statistics po/it.po
```

```python
import ast
import sys
from pathlib import Path

sys.path.insert(0, "tools")
import compile_po

pot = compile_po.parse(Path(sys.argv[1]).read_text(), "current.pot")
po = compile_po.parse(Path("po/it.po").read_text(), "it.po")

def key(entry):
    return entry.get("msgctxt"), entry["msgid"], entry.get("msgid_plural")

source_keys = {key(e) for e in pot}
po_keys = {key(e) for e in po}
print("Missing:", source_keys - po_keys)
print("Stale:", po_keys - source_keys)

for path in Path("src/meridiana").rglob("*.py"):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id not in {"_", "ngettext", "pgettext", "N_"}:
            continue
        args = node.args[:1] if node.func.id != "ngettext" else node.args[:2]
        if node.func.id == "pgettext":
            args = node.args[1:2]
        if any(not isinstance(arg, ast.Constant) or not isinstance(arg.value, str) for arg in args):
            print(f"{path}:{node.lineno}: dynamic {ast.unparse(node)}")
```

Il comando completo per compilare e provare il catalogo senza toccare i sorgenti è:

```bash
mkdir -p /tmp/meridiana-locale/it/LC_MESSAGES
msgfmt --check --output-file /tmp/meridiana-locale/it/LC_MESSAGES/meridiana.mo po/it.po
```

## Ordine consigliato

1. Tradurre le tre note di `layout.py` e i messaggi utente del punto 2, con prove in italiano.
2. Correggere le intestazioni dell'ombra e uniformare «Layout» a «Posa» dopo conferma di Daniel.
3. Rendere la galleria realmente bilingue.
4. Aggiornare e ripulire il PO con revisione umana, poi ripetere `msgfmt --check` e la suite.

Nessun file di codice o di traduzione è stato modificato per questo rapporto.
