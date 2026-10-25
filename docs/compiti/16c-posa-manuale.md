# Compito per una sessione cloud: posa manuale dei moduli, file ed esplosione (studio 16, tema C)

Bozza del 23/10/2026, da lanciare dopo la decisione di Daniel. Lo studio è `docs/studio/16-modellazione.md`, sezione C. Regole di lavoro come in `docs/compiti/fase-2.md`: ramo `posa-manuale` da `lavoro`, richiesta di unione in bozza verso `lavoro`, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano. Prima il test, poi il codice. Dipende dal tema B per lo strumento Sposta (si può cominciare dal passo 1 senza).

**Deciso da Daniel il 23/10/2026** («Tutti i punti proposti vanno bene!»): la posa automatica resta il primo gesto; cambiando modulo con le file a mano si adatta da sola se le misure coincidono entro 2 cm, altrimenti chiede; i moduli esplosi restano nel loro sottocampo. Nessuna libreria nuova: CGAL resta fuori dal programma, come oracolo delle prove.

**Decisioni di Daniel da leggere prima** (C.6): la posa automatica resta il primo gesto (proposto); cambio di modulo con file a mano: adattare se le misure coincidono entro 2 cm, altrimenti chiedere (proposto); i moduli esplosi restano nel loro sottocampo (proposto).

**Modifiche dalla revisione completa del 23/10/2026** (`docs/design/interfaccia.md`, sezione 6.4; `docs/studio/18-revisione-completa.md`, sezione 4): da modificare: lo strumento Fila nel gruppo Disegna della barra della fase (tasto da fissare nel registro delle scorciatoie: L è libera); lo stato «file a mano» nel Risultato della posa e come voce da sapere nelle Verifiche; costruito sulla sessione di `18b-sessione.md` (id di modulo al posto di `riga:posto`).

## Passo 1: le file come oggetti (nessun gesto nuovo)

1. In `layout.py` una `Row` (identificatore stabile, origine in pianta, direzione lungo la fila, numero di posti, passo tra i moduli, livelli della tavola, gruppo VVF) e `compute` che restituisce anche `Result.rows`; i `PlacedModule` derivano dalle file con `layout.modules_of(rows, module, params, surface)`; la chiave del modulo diventa «fila:posto» con l'identificatore della fila.
   - Test in `test_layout.py`: per ogni caso di oggi i moduli sono gli stessi (angoli, centri, quote) passando dalle file; i 23 progetti PVsyst importati (`test_pvsyst.py`) posano ancora esattamente gli stessi moduli.
2. `SubField.rows: list` e `SubField.manual: bool` nel modello; formato +1 con la migrazione (vuoto = come oggi); `removed` passa alle chiavi nuove (migrazione delle chiavi vecchie «riga:posto» per posizione, con avviso se non corrispondono); `Project.fill` con `manual` vero ricostruisce il risultato dalle file salvate senza rigenerarle; la chiave di posa include le file.
   - Test in `test_model.py`: un sottocampo manuale non cambia moduli quando cambia il passo; un file vecchio apre con `rows` vuoto e posa come prima.

## Passo 2: i gesti sulle file

3. Strumento «Fila» (tasto da scegliere in `shortcuts.py`, senza conflitti: proposta «L», libera): primo clic l'inizio, il secondo la fine con gli agganci e le lunghezze digitate del disegno (`_apply_typed`); la fila prende il modulo, il passo e l'orientamento del sottocampo; se il sottocampo era automatico diventa manuale con l'avviso di PVsyst nella barra («le file ora sono tue: Riposa in automatico le rifà»); rossa durante il gesto se esce dall'area o copre un'esclusione (PV\*SOL), accettata comunque.
4. Selezione di una fila in pianta: un clic sul modulo seleziona il modulo, un secondo clic sulla stessa fila seleziona la fila (livelli di selezione), evidenza al passaggio come per i sottocampi; menu contestuale: «Togli la fila», «Aggiungi una fila in coda», «Accorcia / allunga» (trascinando l'estremo), «Riposa in automatico» (annullabile, con conferma se ci sono file a mano), «Esplodi».
5. Sposta e ruota (tema B) sulle file: `move.py` sposta una fila dentro il sottocampo, la chiave di posa cambia, le stringhe sulle chiavi stabili restano.
6. Le regole VVF e le ombre come verifiche per i sottocampi manuali (`checks.py`): gruppi dalle impronte delle file unite a meno di 2 m, «gruppo di {m} m oltre i 20», «corridoio di {m} m sotto i 2», «{n} moduli sull'esclusione {nome}», «{n} moduli in ombra nel giorno di progetto» (con `count_out_of_shadows`), ognuna con la fonte e «Correggi» = riposa in automatico.
   - Test in `test_checks.py` e `test_window.py`: una fila trascinata su un lucernario produce la voce; una fila lunga 26 m con le regole VVF produce la voce con i metri.

## Passo 3: esplodi e i singoli moduli

7. «Esplodi» su una fila o sul sottocampo: ogni modulo diventa una fila di un posto (stessa chiave: «fila:0» con l'identificatore del modulo); sposta, ruota di 90° (doppio clic, come Aurora), Canc; i moduli esplosi non escono dal sottocampo (rifiuto con il motivo).
   - Test: esplodere e spostare un modulo di 30 cm cambia solo quello; Canc lo toglie; annulla ripristina la fila.
8. Stringhe, 3D, relazione e confronto delle varianti leggono `Result.modules` come oggi: un test per ciascuno che un sottocampo manuale ed esploso dia le stesse uscite di uno automatico con gli stessi moduli.
9. Documenti e traduzioni: `funzionalita.md` (la riga «Posa a mano» da ○ a ✔), `CHANGELOG.md`, `progetto.md`, `po/it.po`.

**Da lasciare alla sessione locale**: il gesto della fila con il mouse vero sull'ortofoto, i due livelli di selezione con il clic vero, la velocità con il progetto da 4.682 moduli esploso.
