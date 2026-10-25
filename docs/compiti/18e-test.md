# Compito per una sessione cloud: la suite dei test riorganizzata (revisione 18)

Bozza del 23/10/2026 dalla revisione completa (`docs/studio/18-revisione-completa.md`, sezione 2.D; il rapporto `docs/studio/18-prove/D-test.md` sezioni 6 e 7). Regole di `docs/compiti/fase-2.md`: ramo `test` da `lavoro`, un commit per passo, mai un test tolto senza averlo sostituito con uno del nucleo o del widget che prova la stessa cosa. A tappe: i passi 1-3 subito, il passo 4 dopo `18b-sessione.md`.

## Passo 1: le dieci aggiunte (D §7.3)
1. Un file `.meridiana` per ogni versione 1-7 e un `config.json` per ogni versione 1-9 in `tests/formati/`, scritti una volta e congelati, con il test che li apre e confronta (già iniziato nel 18a: qui completo, con i file danneggiati, troncati e di una versione futura).
2. Le risposte vere di PVGIS 5.3 registrate (`get_pvgis_tmy`, `get_pvgis_horizon`, `PVcalc`) in `tests/calcoli/riferimenti/` con un README che dice da dove vengono, e i loro errori (403, risposta corta, colonne mancanti).
3. Un test che disegna edificio, sottocampo ed esclusione nella finestra e li trova nel progetto, con l'annulla; la pagina delle proprietà di un'esclusione.
4. La relazione con inverter, stringhe, cablaggio e regole, con il controllo delle sezioni.
5. La scrittura atomica che fallisce a metà, la cartella in sola lettura, il `.bak` che non si rinomina.
6. Le fonti accanto ai valori normativi nei test (norma, edizione, articolo, pagina: l'elenco è in `B-norme-citazioni.md` §2 e §3).
7. `COVERAGE_CORE=sysmon` scritto in `CLAUDE.md` accanto al comando dei test.

## Passo 2: da togliere o sistemare (D §7.4)
8. `Sides(Drawing)` che fa girare otto test due volte; le asserzioni sul tempo di parete in `test_catalog_dialog.py`; i test sulle costanti e sui pixel; i rami che tacciono senza fuoco (`qWaitForWindowActive` o `skipTest`); le attese fisse sostituite da condizioni; i percorsi del PC di Daniel solo con la variabile d'ambiente nel gruppo esterni; `unittest.main()` a metà di `test_assistant.py`.
9. Lo stato globale ripristinato a fine modulo (`addModuleCleanup`): palette, foglio di stile, traduzioni di Qt, `SystemAccent.motion`, ambiente.

## Passo 3: la struttura
10. Le cartelle `nucleo/`, `calcoli/`, `formati/`, `widget/`, `finestra/`, `esterni/` (D §7.1) con `_setup.py` e `_fixtures.py` (i progetti d'esempio: capannone, casa a falde, con ostacoli; l'anno sintetico); `discover` che le trova; il CI che lancia nucleo, calcoli, formati e widget su Linux e Windows, la finestra offscreen su Linux.

## Passo 4: la finestra ridotta (dopo 18b)
11. Da 148 a 50-55 test con la `MainWindow` vera: una fixture unica `window(project, cfg)` che apre, aspetta la posa e garantisce `dispose`; `EnergyPages` con un calcolo per classe; i test di logica spostati nel nucleo (la sessione) o nei widget. Obiettivi: nucleo, calcoli e formati sotto 20 s; tutto sotto 2 minuti offscreen e 4 minuti sul secondo schermo.

## Da provare sul PC di Daniel
- La suite intera sul Samsung dopo ogni passo: i tempi nel diario.
