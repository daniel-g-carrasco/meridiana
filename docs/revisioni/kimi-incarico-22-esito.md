# Esito incarico 22: dimensionamento e ingressi delle stringhe, 28/10/2026

## Che cosa è cambiato

- [V] Il dimensionamento può combinare modelli di potenze diverse della stessa marca. Una combinazione viene accettata
  solo se la proposta associata mette tutti i moduli in stringhe valide. Il criterio è scritto in
  `src/meridiana/energy/sizing.py` e nell'esito del comando: prima meno inverter, poi meno modelli diversi, poi il
  rapporto DC/AC più vicino a quello richiesto. Fonte del catalogo e nome del modello servono solo a parità assoluta.
- [V] Inverter e stringhe proposte entrano nello stesso passo di annulla. Le stringhe non vengono più scelte sul solo
  rapporto DC/AC: finestre MPPT, Uoc a freddo, correnti e numero di stringhe per ingresso sono verificati subito.
- [V] Ogni MPPT del pannello destro mostra da subito quattro righe: moduli in serie ammessi, massimo parallelo,
  potenza, numero di stringhe e stato con simbolo. Il suggerimento spiega il motivo. Il «+» attiva l'ingresso per
  disegnare la prima stringa o un'altra uguale in parallelo. Le verifiche controllano anche stessa lunghezza, tipo di
  modulo e orientamento. I testi seguono la tavolozza attiva anche cambiando tema.
- [V] Il formato del progetto resta il 14: le stringhe in parallelo erano già rappresentate come più `runs` sullo
  stesso ingresso. Non servono migrazione, nuovo file campione o riga in BROUGHT.

## Errori riprodotti e corretti

1. [V] **Nessun modulo posato.** Il vecchio comando sceglieva comunque un inverter e scriveva DC/AC 0. Ora dice che
   prima serve la potenza DC dei moduli e non cambia il progetto. Prova:
   `PhaseRow.test_sizing_without_modules_laid_says_why_and_changes_nothing`.
2. [V] **Modelli diversi, ma lunghezza decisa sul primo.** Con un inverter da 1000 V e uno da 500 V, la proposta
   metteva stringhe di 24 moduli anche sul secondo: Umpp a freddo 817 V, oltre il limite, range ammesso 6-14. Ora la
   lunghezza viene valutata solo sugli inverter compatibili. Prova rossa prima della correzione, poi verde:
   `AutomaticErrors.test_mixed_inverter_models_do_not_put_a_long_string_on_a_narrow_input`.
3. [V] **Ingresso esplicito sovraccaricato.** Su un ingresso da una sola stringa il vecchio codice ne metteva tre e
   lasciava 0 moduli fuori, con corrente oltre limite. Ora ne mette una, lascia 24 moduli fuori e spiega la
   correzione. Prova: `AutomaticErrors.test_an_explicit_input_never_receives_more_strings_than_its_current_allows`.
4. [V] **Corrente operativa ignorata.** Con Imp 13,4 A e limite 26 A, due paralleli davano 26,8 A. La proposta ora
   rispetta sia il limite operativo sia quello di cortocircuito e ne ammette una. La stringa manuale conserva
   l'avviso energetico se il progettista supera il valore operativo. Prova:
   `AutomaticErrors.test_parallel_capacity_uses_operating_and_short_circuit_current`.
5. [V] **Fusibile ignoto.** Il progetto `capannone()` usa il modulo generico senza fusibile massimo. La proposta
   automatica si ferma a due paralleli invece di produrre una verifica non concludibile. Anche quando 1,1 × Isc max
   supera il fusibile massimo, il terzo parallelo non viene proposto.
6. [V] **Un solo modello e nessuna verifica di stringatura.** Il vecchio dimensionamento ordinava i modelli solo per
   errore DC/AC. Ora prova le combinazioni in ordine di criterio e scarta quelle con moduli fuori stringa o verifiche
   non valide. Prove in `tests/calcoli/test_sizing.py` per un sottocampo, due orientamenti, moduli elettricamente
   grandi e piccoli e le marche reali Huawei, SMA e Sungrow.
7. [V] **Finestra MPPT ignota, ma ingresso verde.** Le stringhe erano gialle mentre il riepilogo dell'ingresso diceva
   «corretta». Ora anche l'ingresso è «da verificare». Prova rossa prima della correzione:
   `ParallelStrings.test_an_input_without_a_known_mppt_window_is_to_be_checked`.
8. [V] **Riepilogo ambiguo e testo scuro su fondo scuro.** Il conteggio dopo il numero dell'ingresso si leggeva come
   un numero unico e la riga di potenza e stato era tagliata. Il conteggio è nella riga di stato, potenza e stato
   stanno su righe separate e il disegno standard segue la tavolozza. Prove in `widget/test_string_list.py` e foto
   riprese dopo la correzione.
9. [V] **Glifo di conferma non presente in Inter.** La prova `finestra.test_glyphs` ha riprodotto il carattere mancante.
   Gli stati del riepilogo ora usano le icone vettoriali di `ui/marks.py`, non un simbolo testuale. La prova mirata
   è tornata verde prima della ripetizione dell'intero gruppo.

## Formule e dati di partenza

I dati sono quelli delle schede del modulo e dell'inverter nel catalogo. Le temperature sono quelle del sito. Prima
dell'anno tipico si usano 60 e 20 °C di cella e -10 °C per Uoc, scelta di progetto già dichiarata, non una norma.
Ogni passo è nel `Record` del piano, con valori e fonti.

- **Tensione a vuoto massima:**
  `KU = 1 + (alphaUoc / 100) × (Tmin - 25)`; `Uoc max = Ns × KU × Uoc STC`. Il limite è il minore fra massima
  tensione DC dell'inverter e tensione massima di sistema del modulo. Fonte: CEI 64-8/7:2024-07, Allegato B, B.1,
  p. 109 **[da verificare da Claude]**.
- **Tensione MPP:** `Umpp(T) = Ns × Umpp,mod(1000 W/m², T)`, calcolata col modello a un diodo del modulo alla cella
  più calda e più fredda. La stringa deve restare nella finestra MPPT in entrambi i casi. Se il modello non è
  disponibile, il ripiego lineare è dichiarato nel codice.
- **Corrente di cortocircuito per ingresso:** `Isc in = Np × KI × Isc STC`, con `KI >= 1,25`. Le stringhe uguali in
  parallelo sommano le correnti. Fonte: CEI 64-8/7:2024-07, Allegato B, B.2, p. 109 **[da verificare da Claude]**.
  Si verifica anche `Iin = Np × Imp` contro la massima corrente operativa dell'ingresso dalla scheda dell'inverter.
- **Potenza per ingresso:** `PDC in = Ns × Np × PSTC`. È la somma delle potenze nominali dei moduli.
- **Range della serie:** il massimo è il minimo intero fra i limiti Uoc e MPPT a freddo; il minimo è il primo intero
  che porta Umpp a caldo dentro la finestra MPPT. Se il range è vuoto, nessuna proposta viene forzata.
- **Protezioni dei paralleli:** le disuguaglianze esistenti per il fusibile restano visibili. Riferimento già usato
  dal codice: CEI 64-8/7:2024-07, 712.431.101 e 712.431.102 **[da verificare da Claude]**.

## Tre casi con i numeri

Modulo di prova: 450 W, Vmp 33,6 V, Imp 13,4 A, Voc 40,1 V, Isc 14,1 A, coefficiente Voc -0,25 %/°C. Inverter:
1100 V DC, MPPT 180-1000 V, 16 A operativi e 20 A di cortocircuito per ingresso. Temperature: -10 °C per Uoc, 60 e
20 °C di cella. Range calcolato: 6-25 moduli in serie.

1. **Dodici moduli, una stringa.** `KU = 1 + 0,0025 × 35 = 1,0875`;
   `Uoc max = 12 × 1,0875 × 40,1 = 523,305 V`. Umpp vale 366,176 V a 60 °C e 408,444 V a 20 °C.
   `Isc in = 1,25 × 14,1 = 17,625 A`, dentro 20 A. `P = 12 × 450 = 5.400 W`. Tutte le verifiche passano.
2. **Dodici moduli per stringa, due paralleli.** Le tensioni restano 523,305 V e 366,176-408,444 V.
   `Isc in = 2 × 1,25 × 14,1 = 35,25 A`, oltre 20 A: errore. `Iin = 2 × 13,4 = 26,8 A`, oltre 16 A: avviso di
   perdita se disegnato a mano. `P = 12 × 2 × 450 = 10.800 W`. La proposta automatica ammette quindi una sola stringa.
3. **Numero primo, 23 moduli.** Con range 6-10, nessuna lunghezza intera divide 23. La correzione più piccola è
   aggiungere 1 modulo: 24 = 3 stringhe da 8, per 10.800 W. Togliere 2 moduli darebbe 21 = 3 stringhe da 7; a parità
   di distanza il programma preferisce aggiungere. Il dettaglio propone anche il cambio di inverter o ingresso.

## Prova reale e fotografie

[V] Nella sessione grafica nascosta, avviata solo con `tools/real_session.sh` e runtime privato, ho aperto
`capannone()`, aggiunto un inverter con quattro MPPT e premuto la proposta a serpentina. Risultato: 128 moduli, 8
stringhe da 16 su 4 ingressi, ognuno da 14,40 kWp, nessun modulo fuori e tutti gli stati corretti. Il «+»
dell'ingresso 2 ha attivato il disegno, poi Esc lo ha chiuso e ne ha tolto l'evidenziazione. Le esecuzioni finali in
chiaro e scuro si sono chiuse regolarmente. Alla fine non restano processi nascosti e `findmnt /run/user/1000/doc`
mostra ancora il portale montato.

Le foto sono state aperte e controllate. Testi completi in tutti i casi, senza sovrapposizioni, fondi chiari e scuri
corretti:

- [chiaro, testo Medio](foto/kimi22-ingressi-chiaro-medio.png)
- [chiaro, testo Grande](foto/kimi22-ingressi-chiaro-grande.png)
- [scuro, testo Medio](foto/kimi22-ingressi-scuro-medio.png)
- [scuro, testo Grande](foto/kimi22-ingressi-scuro-grande.png)

## Verifiche

- [V] `nucleo`: 805 prove, 4 saltate, OK.
- [V] `calcoli`: 193 prove, OK.
- [V] `formati`: 60 prove, OK.
- [V] `esterni`: 6 prove saltate perché mancano i dati esterni facoltativi, OK.
- [V] `widget`: 325 prove, 1 saltata, OK.
- [V] `finestra`: 134 prove, OK.
- [V] `ruff check src tests tools`: OK.
- [V] `msgfmt --check po/it.po`: OK. Traduzioni complete, nessuna voce `fuzzy`.
- [V] Interprete verificato: `meridiana.__file__` dentro `src` di questa copia.
