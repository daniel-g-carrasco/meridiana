# Riferimento Widgets nativo

`baseline-v1` conserva la prima matrice completa: 24 combinazioni, 35 stati
ciascuna. `popolati-v1` contiene 36 immagini aggiuntive con consumi, investimento
e accumulo espliciti. `smoke-v2` è il primo campione usato dal confronto HTML.
I file compressi sono JSON UTF-8 ordinati, gzip con timestamp zero. I PNG sono
in `build/riferimento/<run>/<caso>/`; ogni JSON contiene l'hash della sua foto.

## Quale riferimento usare per le stringhe

Per `plant-strings` dei casi Rho usare **`stringhe-v3`**. Nella prima matrice
il selettore della vista passava correttamente a diagramma, ma le sette schede
inverter lo lasciavano sotto il viewport: la foto mostrava ancora gli inverter
e le stringhe sulla pianta. Il nuovo riferimento scorre fino al diagramma,
senza cambiare progetto, anno calcolato o dati delle stringhe. Conserva gli
stessi nomi di caso e scenario, nelle 12 combinazioni di tema, scala e misura.

I vecchi file non sono stati sovrascritti. Per tutti gli altri stati usare
`baseline-v1`; per consumi e accumulo espliciti usare anche `popolati-v1`.
La verifica `test_baseline` richiede la matrice e questi riferimenti integrativi.

La prova diagnostica `stringhe-v2`, prima del calcolo, non è un riferimento
consegnato: il programma mostrava zero stringhe nella vista dei risultati.
È conservata soltanto sotto `build/quick-parity/diagnostic-canonical/`.

La foto attesta uno stato statico. Il numero di richieste censite, la presenza
di un file o la percentuale di pixel diversi non certificano la parità Quick.
Leggere `docs/quick/compat/ispezione-visuale.md` per l'ambito guardato realmente.
