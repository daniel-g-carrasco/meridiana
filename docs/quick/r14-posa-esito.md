# R417 e R418: la posa dei moduli, esito (ramo `r14-posa`, 05/11/2026)

## Cosa c'è adesso

Nuova sezione **Posa dei moduli** nelle Proprietà del sottocampo (solo Qt Quick), con due campi: **Allineamento** e **Potenza richiesta**. Il nucleo è in `src/meridiana/layout.py` (`_arranged_rows`, `_fit_target`).

- **Allineati:** griglia unica, colonne dritte; sui lati inclinati resta il pezzo di modulo in meno, le colonne non si spostano. Sceglie origine lungo e attraverso le file che fa stare più moduli; a parità, quella più centrata (su un rettangolo, le stesse posizioni di prima). Predefinito dei sottocampi disegnati ora.
- **Sfalsati di mezzo modulo:** due griglie a mezzo modulo; ogni fila sta su quella che ne tiene di più, e resta sulla griglia della fila precedente a parità. Due spostamenti di mezzo modulo fanno un posto intero, quindi le griglie restano due in tutto.
- **Liberi:** ogni fila sfrutta tutto il suo spazio, senza gruppi VVF le file possono stare più distanti del passo, mai più vicine. Cerca le file con la programmazione dinamica sulle altezze utili. Una fila si appoggia alle colonne della griglia quando il suo spazio lo permette: nella foto di Daniel erano tutte sfasate per nulla, ora ne resta sfasata una sola, quella che guadagna un modulo.
- **Come salvato:** il comportamento di prima, per i sottocampi già salvati. Compare nell'elenco solo per loro, e cambiandolo non si torna indietro se non con Annulla.

## Moduli e kWp per modo (misurato, modulo 2278 x 1134 mm da 475 W)

| Forma | Posa | Come salvato | Allineati | Sfalsati | Liberi |
|---|---|---|---|---|---|
| Rettangolo 30 x 18 m | file 10° su piano | 125 (59,38) | 125 (59,38) | 125 (59,38) | 125 (59,38) |
| Rettangolo | falda 20° az. 10° | 165 (78,38) | 165 (78,38) | 168 (79,80) | 169 (80,27) |
| Trapezio foto | file 10° su piano | 71 (33,73) | 72 (34,20) | 72 (34,20) | 73 (34,67) |
| Trapezio foto | falda verticali | 106 (50,35) | 118 (56,05) | 118 (56,05) | 118 (56,05) |
| Trapezio foto | falda orizzontali | 115 (54,62) | 112 (53,20) | 114 (54,15) | 117 (55,57) |
| Trapezio foto | est-ovest | 64 (30,40) | 98 (46,55) | 98 (46,55) | 98 (46,55) |
| Trapezio foto | a terra 2V | 28 (13,30) | 56 (26,60) | 56 (26,60) | 56 (26,60) |
| L | falda verticali | 248 (117,80) | 246 (116,85) | 250 (118,75) | 254 (120,65) |
| L | file 10° su piano | 169 (80,27) | 169 (80,27) | 169 (80,27) | 169 (80,27) |
| Tetto 120 x 90 m | file 10° su piano | 2369 (1125,27) | 2472 (1174,20) | 2472 (1174,20) | 2472 (1174,20) |
| Tetto | falda verticali | 3834 (1821,15) | 3813 (1811,17) | 3831 (1819,72) | 3837 (1822,57) |
| Tetto | est-ovest | 3312 (1573,20) | 3456 (1641,60) | 3456 (1641,60) | 3456 (1641,60) |
| Tetto | 9 lucernari | 2301 (1092,97) | 2403 (1141,42) | 2403 (1141,42) | 2409 (1144,27) |
| Tetto | regole VVF | 2024 (961,40) | 2116 (1005,10) | 2116 (1005,10) | 2116 (1005,10) |

Da leggere così: il guadagno grosso sui trapezi viene dall'origine delle file, non dallo sfalsamento (la prima fila non parte più dal punto più basso del lato inclinato). Allineati può dare meno del vecchio modo quando la griglia unica pesa, come sulla L e sulla falda orizzontale: è il prezzo delle colonne dritte.

Nella finestra vera, sul contorno della foto a falda verticale: come salvato 98, allineati 112, sfalsati 112, liberi 113.

Le foto stanno in `docs/quick/r14-posa/`, finestre vere sul desktop separato con `tools/quick_native_input.py`, guardate una per una: `come-salvato.png`, `allineati.png`, `liberi.png`, `sfalsati-orizzontali.png` (104 contro 98 degli allineati), `obiettivo-20kwp.png`, `vertice-trascinato-allineati.png`.

## Potenza richiesta

- **Arrotondamento (deciso da Daniel):** il più vicino anche se supera; a parità di scarto quello che non supera; almeno uno. 45 kWp con 475 W: 94,7, quindi 95 moduli, 45,13 kWp. Prova: `TargetPower` in `tests/nucleo/test_placement.py`.
- **Posizioni (confermato da Daniel):** file vicine, solo l'ultima in parte con una sequenza continua, dalla serie di file meno in ombra, a parità dalla prima fila. L'ombra è stimata senza calcolo orario con le aree d'ombra degli ostacoli (`energy.system.shadow_exclusions`, già esistente): finestra di progetto con peso 1, stessa giornata con due ore in più per parte con peso 0,25 (`model.TARGET_WINDOWS`). Pesi e finestre sono una mia scelta, non vengono da una norma.
- La scheda dice «42 moduli, 19,95 kWp, dei 112 che questo sottocampo contiene»; se non ci stanno, «Mancano 77 moduli: questo sottocampo ne contiene al massimo 112, 53,20 kWp» (numeri visti in prova, la seconda frase solo come testo del programma, non in foto).
- Tavole, pile e coppie est-ovest restano intere: il conteggio è il più vicino possibile, per esempio 102 con tavole da 6 e 100 chiesti.
- I moduli tenuti conservano le chiavi della posa intera, quindi quelli tolti a mano e le stringhe restano su di loro. I tolti a mano non contano nel numero.
- **Obiettivo di progetto su più sottocampi:** non fatto. Quale sottocampo riempire per primo è una scelta di progetto: proposta nel riepilogo, non implementata.

## Compatibilità dei progetti vecchi

- `params` senza `alignment` vale «come salvato». Prova: 32 combinazioni forma e posa più una con moduli tolti, confrontate con impronte (chiavi e angoli a 6 decimali) prese dal codice prima della modifica. Tutte identiche (`SavedProjectsStayTheSame`).
- File congelato `tests/formati/file/progetto-v25.meridiana`: si apre, nessuna chiave nuova, `layout_key` senza le parole nuove. Tutti i formati da 1 a 25 si aprono (`tests/formati`).
- **Formato non aumentato, resta 25.** `alignment` e `target_kwp` sono voci facoltative di `params`, dizionario che già viaggia intero. Motivi: un Meridiana precedente legge il file, ignora le voci e le conserva salvando (dedotto dal codice, non provato con una versione vecchia), e il ramo `r14-ifc` è già a 26, quindi un secondo aumento darebbe un conflitto. Effetto da sapere: un Meridiana precedente mostrerebbe quei sottocampi posati alla vecchia maniera. Se preferite la regola stretta di `model.py`, è un passaggio di una riga da aggiungere dopo l'unione.
- Un file con `alignment` sconosciuto o `target_kwp` non valido viene rifiutato con il percorso della chiave, come gli altri errori (`_check_placement`).

## Tempi (misurati su questo PC con altri agenti al lavoro, migliore di 3)

| Caso | Come salvato | Allineati | Sfalsati | Liberi |
|---|---|---|---|---|
| 700 moduli su piano (715-762) | 13 ms | 32 ms | 40 ms | 22 ms |
| 20 000 moduli a falda | 239 ms | 316 ms | 287 ms | 290 ms |
| 20 000 moduli, 30 lucernari | 243 ms | 616 ms | 592 ms | 586 ms |
| con 45 kWp su 20 000 (l'ultimo caso) | 184 ms | 576 ms | 526 ms | 512 ms |

Progetto con 6 ostacoli e ombre, 13 274 moduli possibili, 500 kWp: 558 ms, contro 245 ms senza obiettivo; la differenza sono le due finestre d'ombra. Il calcolo gira nel processo a parte di `shell_compute.worker`, che non ho toccato: il thread principale non aspetta (letto dal codice; il tempo a schermo non l'ho misurato).

**Un limite:** cambiando allineamento con moduli tolti a mano, il sottocampo si ricalcola una volta **sul thread principale** per riportarli al loro posto (`manual.removed_on_alignment`): 583 ms su 13 274 moduli. Succede solo in quel caso. Se conta, va spostato nel lavoro in background.

## Gesti provati nella finestra vera (messaggi nativi, desktop separato)

- Vertice trascinato in allineati: da 112 a 99 moduli, una sola famiglia di colonne dopo il gesto, una sola voce di annulla.
- Doppio clic su un lato, 20 m digitati: lato da 14 a 20 m, forma conservata, da 46 a 67 moduli, colonne dritte, una voce di annulla.
- **Trascinare un lato non esiste, in nessuno dei due programmi.** Provato: premere e trascinare sul lato di un sottocampo in Quick non cambia nulla; nei Widgets il codice ha solo il doppio clic e la targhetta, che aprono il campo della lunghezza. È il gesto che corrisponde a «se premo sul lato». Se Daniel intende un trascinamento vero, è un lavoro nuovo, non fatto.

## Non fatto o solo in parte

- **Widgets:** nessun campo nelle Proprietà, e i sottocampi disegnati nei Widgets nascono ancora «come salvato» (`src/meridiana/ui/window.py:3114`, una riga: `params=model.new_params(mounting)`). Non toccati per regola del ramo. Il nucleo però rispetta le voci se presenti.
- Sottocampi nati da import IFC, PVsyst e pensiline: restano «come salvato». Il ramo IFC è di un altro agente.
- Cambiando allineamento, le stringhe a mano che citano chiavi di moduli non vengono riportate: si comportano come quando si cambia un altro parametro della posa. Da decidere se servono.
- In liberi con passo fisso in metri o GCR, le file possono stare più lontane del valore: `Result.pitch` resta quello nominale, quindi il calcolo dell'energia usa un passo più stretto di quello reale in quei punti (dedotto dal codice, a favore di sicurezza).
- Prove: `tests/quick/proprieta/test_properties_native.py` e simili richiedono `MERIDIANA_QUICK_NATIVE=1`, non lanciate: 5 prove saltate.

## Suite

- `tests/nucleo`: 1282 prove, 1 saltata. Falliscono 2 prove a tempo di `test_catalog` (classificazione sotto 0,2 s e caricamento sotto 0,4 s, misurati 0,22 e 0,50 s): non ho toccato il catalogo, la prima da sola passa, la seconda da sola no (0,47 s); la prima fallisce anche sul ramo `r14-catalogo`, senza il mio codice (0,25 s), con la macchina carica di altri agenti. Non è una prova che dipenda da questo lavoro, ma non l'ho vista verde. Nella stessa corsa `test_help` falliva per il testo d'aiuto troppo lungo: accorciato, da solo passa con `test_i18n`.
- `tests/quick/proprieta`: 65 prove, 5 saltate, verdi. `tests/formati`: 96 verdi. `test_stringing`, `test_global_stringing`: verdi. Lint `ruff --select F,E9,B` sui file toccati: pulito.
- `finestra` e `widget`: non lanciate.
