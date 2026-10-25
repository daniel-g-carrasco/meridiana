# Compito per una sessione cloud: la sessione senza Qt e la propagazione delle modifiche (revisione 18)

Bozza del 23/10/2026 dalla revisione completa (`docs/studio/18-revisione-completa.md`, sezione 4, ordine 2; il progetto è `docs/studio/18-prove/A-architettura.md`, sezione 9, da leggere per intero). Le regole di lavoro sono quelle di `docs/compiti/fase-2.md`: ramo `sessione` da `lavoro`, richiesta di unione in bozza, un commit per passo spinto subito, registro aggiornato. Da lanciare dopo `18a-fondamenta.md` e **prima** dei compiti 16a-g, che nasceranno sulla sessione (decisione di Daniel: domanda 1 dello studio 18).

**Il metodo è lo «strangler»** (A §9.3): il modulo nuovo accanto al vecchio; i chiamanti spostati uno alla volta; i 637 test passano come sono (gli attributi della finestra restano come alias finché un test li usa); il vecchio cancellato quando nessuno lo importa; mai due implementazioni oltre un rilascio.

## Passo 1: la pipeline energetica nel nucleo (1 giorno)
1. `energy/pipeline.py`: `EnergyJob._compute` e `_strings` (`ui/window.py:134-283`) spostati tali e quali in `compute(project, results, cache, fetch) -> EnergyResult` (una dataclass al posto del dizionario `out`); `EnergyJob.run` lo chiama; `_variant_figures` e `CompareJob` lo chiamano senza istanziare i lavori.
2. Test del nucleo sull'anno sintetico di `tests/_energy.py`: la pipeline intera senza Qt, con `count_out_of_shadows` e la seconda `simulate` misurate (il compito 18c le toglie).

## Passo 2: `session.py` (2 giorni)
3. `ProjectSession` senza Qt: `project`, `results`, `layout_keys`, `energy`, `generation`, `selection`, `undo` (le istantanee di oggi, con il `try/except` che ripristina `before` se `change` solleva: difetto 3 di A), `dirty`, `autosave`; la pila con un limite detto.
4. `MainWindow` la crea e le delega: `edit()` della finestra diventa `self.session.edit(...)` più il ridisegno; gli attributi di oggi come proxy; i 59 test della finestra passano; nascono i test della sessione (annulla con ripristino, varianti, revisioni).
5. `SiteDialog` in `ui/site_dialog.py` con la geocodifica in `services/geocoding.py` (senza Qt).

## Passo 3: chiavi per oggetto ed eventi per argomento (2 giorni)
6. `geometry_key(building)` (anello, altezza, tetto, parapetto); `layout_key(sf)` = campi del sottocampo + chiave di geometria dell'edificio ospite + esclusioni dell'ospite + sito + finestra solare, e le chiavi di geometria di tutti gli edifici solo con `shade_free`; `energy_key` = chiavi di posa + energia + consumi + economia (A §9.2). Una rinomina non muove nulla; un'altezza riposa solo i sottocampi che la vedono.
7. `session.changed(topics)` con gli argomenti `project:geometry`, `layout:<id>`, `energy`, `selection`, `checks`; `_show_tree`, `_show_3d`, `_show_checks`, le pagine iscritte ai loro argomenti; `_layout_done` ridisegna solo i sottocampi cambiati; `arrays_of` con gli ostacoli calcolati una volta per progetto; `MarkDelegate` senza `ResizeToContents` sulla colonna.
8. **Accettazione misurata**: sul progetto generato da `docs/studio/18-prove/A-architettura-prove.py` (20 edifici, 40 sottocampi), rinominare un edificio sotto 100 ms sul filo della finestra, nessuna posa, nessun calcolo dell'anno; cambiare un'altezza riposa solo i sottocampi interessati. Il test lo misura offscreen con una soglia larga e lo script stampa i numeri per la prova sul PC.

## Passo 4: il modello tipizzato (2 giorni)
9. `Building` con id stabile, `Roof(edges per lato, ridge_height, free_pitches con id)` e la cache delle falde invalidata dalla chiave di geometria; `SubField.pitch` come riferimento al lato di gronda; `removed` con id di modulo (non più `riga:posto`); `EnergySettings`, `ConsumptionSettings`, `EconomicsSettings` dataclass con `from_dict` che dice le chiavi ignote; una sola rappresentazione delle varianti (`model.py:283-290`).
10. Versione 7 del file con la migrazione da 6 e i file d'esempio di ogni versione (dal 18a); `app_version` letto o tolto.
11. `model.py` non importa più `energy` (`model.py:388`): `shade_free` riceve la funzione d'ombra dalla sessione.

## Passo 5: la chiusura
12. `docs/progetto.md` sezione 2 riscritta sulla nuova struttura (ui / session / core / io / services) con la mappa dei moduli completa; `docs/richieste.md`; il diario.

## Da provare sul PC di Daniel
- La prova della rinomina e dell'altezza sui progetti di Rho (188 e 4.682 moduli) sullo schermo vero.
- L'annulla dopo una modifica che fallisce (un valore impossibile): il progetto torna com'era.
