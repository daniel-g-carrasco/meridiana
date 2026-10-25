# Compito per una sessione cloud: la scheda Impianto, gli inverter e l'editor delle stringhe (studio 16, tema D)

Bozza del 23/10/2026, da lanciare dopo la decisione di Daniel. Lo studio è `docs/studio/16-modellazione.md`, sezione D. Regole di lavoro come in `docs/compiti/fase-2.md`: ramo `impianto` da `lavoro`, richiesta di unione in bozza verso `lavoro`, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano. Prima il test, poi il codice. Le chiavi stabili dei moduli del tema C aiutano ma non sono necessarie: senza, le stringhe a mano si riferiscono alle chiavi di oggi e cadono quando la posa cambia (si dice).

**Deciso da Daniel il 23/10/2026** («Tutti i punti proposti vanno bene!»): la scheda si chiama «Impianto», fra Modello e Producibilità; le verifiche in diretta con le condizioni di PVsyst (60, 20 e -10 °C); ottimizzatori e microinverter dopo. Nessuna libreria nuova: CGAL resta fuori dal programma, come oracolo delle prove.

**Decisioni di Daniel da leggere prima** (D.7): il nome della scheda («Impianto» proposto); le condizioni di progetto per le verifiche in diretta prima della simulazione (PVsyst 60/20/-10 °C proposte); ottimizzatori e microinverter subito o dopo.

**Modifiche dalla revisione completa del 23/10/2026** (`docs/design/interfaccia.md`, sezione 6.4; `docs/studio/18-revisione-completa.md`, sezione 4): da modificare: la scheda Impianto è la fase 2 della riga delle fasi; l'elenco degli inverter con gli MPPT è l'ispettore del pannello di destra (una sola disposizione), non una colonna dentro la pagina; i pannelli flottanti per inverter (R12) solo nella modalità di stringatura, Meridio nell'angolo opposto; `TABS` e `_show_inspector` passano da `phases.py` (17b riscritto); l'inverter per ingresso MPPT nella simulazione arriva con `18d-calcoli.md`.

## Passo 1: la scheda Impianto e gli inverter

1. Modello: `energy["inverters"]` = lista di `{record, count, name}`; i sottocampi citano inverter e ingresso in `params["inverter"]` e `params["mppt"]` oppure «automatico»; `system.inverter_of` diventa `system.inverters_of` (lista di `InverterSpec`) con il primo della lista al posto dell'inverter unico; i progetti con `energy["inverter"]` di oggi si leggono come lista di uno (è un dizionario di differenze: nessuna versione del formato). «Dimensiona da solo» su più inverter con il rapporto DC/AC, uguali tra loro.
   - Test in `test_energy.py`: due inverter diversi con i sottocampi assegnati danno la potenza AC somma; un progetto di ieri apre e simula uguale.
2. La distribuzione delle stringhe sugli ingressi con la regola di PVsyst (stringhe identiche per ingresso, spalmate 3 + 3 + 4), le verifiche per inverter e ingresso (`stringing.plan` già per ingresso; in più il rapporto DC/AC per inverter e lo sbilanciamento tra ingressi come avviso), i moduli fuori stringa per inverter.
   - Test in `test_stringing.py`: 10 stringhe su 3 MPPT danno 3, 3, 4; un inverter sovraccarico oltre il 3 % dà un «fail» (soglia di programma, detta come tale, non norma).
3. La scheda «Impianto» tra Modello e Producibilità (`ui/window.py`, `ui/plant_page.py`): a sinistra la pianta nel modo stringhe (la stessa `PlanView`, con W sempre acceso), a destra gli inverter (lista, «Aggiungi dal catalogo…», «Dimensiona da solo», quanti, per ciascuno gli MPPT con le stringhe), sotto le voci delle Verifiche dell'area «strings»; il gruppo «Inverter» di Producibilità diventa un rimando con il riassunto e un pulsante «Vai all'Impianto»; l'ispettore di destra segue la scheda (c'è già).
   - Test offscreen in `test_window.py`: la scheda esiste con Ctrl+Tab, il rimando porta alla scheda, scegliere un inverter dal catalogo lo aggiunge alla lista e la Producibilità lo riassume.

## Passo 2: l'editor delle stringhe

L'editor è una **modalità di stringatura dedicata** (R12 di `docs/richieste.md`, idea di Daniel). Sopra la pianta c'è un pannello flottante per ogni inverter, con:
- i suoi ingressi e MPPT;
- per ogni ingresso le stringhe che accetta, quelle collegate e il loro stato (verifica soddisfatta o no, ingresso usato o libero), sempre con colore, icona e parola.

Si entra e si esce dalla modalità con un pulsante della scheda Impianto. Fuori dalla modalità la pianta torna normale.

4. Modello: `energy["strings"]` diventa `{"auto": bool, "runs": [{"inverter", "mppt", "modules": ["sottocampo/chiave", …]}], "n_series", "per_mppt"}`; con `auto` vero il contenuto è la proposta ricalcolata (`suggest` e `assign` con le strategie: una fila per stringa, a U su due file, avanti e indietro, una fila per MPPT); toccando una stringa `auto` diventa falso; «Rifai in automatico» con conferma.
   - Test in `test_stringing.py`: le strategie su una posa di 3 file × 8 moduli danno gli ordini attesi; una stringa a mano sopravvive a uno spostamento della fila (chiavi stabili) e viene detta persa se la fila sparisce.
5. I gesti in pianta: con una stringa scelta nell'elenco (o nuova su un ingresso), clic sui moduli in ordine o trascinamento sopra («si collega quando il puntatore passa il centro», Sunny Design); clic destro toglie; trascinando l'estremo si allunga; un modulo preso da un'altra stringa le viene tolto con l'avviso nella barra; Esc chiude la stringa.
   - Test offscreen: tre clic fanno una stringa di tre; il trascinamento su cinque moduli ne prende cinque; il clic destro ne toglie uno; annulla.
6. Colori e semaforo: una tinta per stringa da `theme_colors` (8-10 tinte distinte dal colore scelto, con i contrasti verificati come i colori degli stati) e il semaforo: rosso fuori finestra o senza ingresso, giallo collegata e da verificare, verde corretta; contorno rosso ai moduli fuori stringa; legenda nella scheda.
   - Test in `test_theme_colors.py`: le tinte restano distinte tra loro e dagli stati (distanza OKLab sopra la soglia dello studio 13) per i colori pronti e 100 a caso.
7. Verifiche in diretta: a ogni modifica `stringing.plan` per le stringhe toccate (pochi millisecondi) con la temperatura di cella dalla simulazione se c'è, altrimenti le condizioni di progetto scelte, con la fonte nel pedigree; le voci nella pagina Verifiche e nella scheda.
8. Relazione: l'elenco delle stringhe per inverter e ingresso con i moduli (già c'è la mappa) e le verifiche per ingresso; `funzionalita.md`, `CHANGELOG.md`, `progetto.md`, `po/it.po`.

**Da lasciare alla sessione locale**: i colori delle stringhe sull'ortofoto e sullo sfondo scuro, il trascinamento sui moduli con il mouse vero, il confronto con PVsyst su un progetto importato (stesse stringhe nel Module Layout).
