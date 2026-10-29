# Allineamento Meridiana al template Qt di Quotario

> Esecuzione per componenti, con prove prima delle modifiche e revisione indipendente finale.

**Obiettivo:** trasferire tutti i delta condivisi applicabili di `qt-app-template` da `9acb7a8` a `3f2d069`, conservando le personalizzazioni Meridiana e gli incarichi Kimi integrati in `fce08b9`.

**Architettura:** adattamento mirato dei moduli gemelli; nessuna sostituzione delle navigazioni o dei delegati applicativi. Nessuna dipendenza nuova e nessuna modifica ai token numerici decisi da Daniel.

**Specifica:** richiesta allegata del 29/10/2026, dieci punti UX; fonti `qt-app-template/docs/correzioni-ux-20261029.md`, `sistema-grafico.md`, `da-dove-viene.md`, `quotario/docs/revisioni/ux-20261029-R01.md` e `sincronizzazione-template.md`.

## Vincoli

Solo offscreen. Conservare popup locali e loro documentazione. Template e Quotario sono sorgenti in sola lettura per questo lavoro; preservare tutte le loro modifiche estranee. Nessun push o rilascio. Manifest nuovi con hash effettivi, precedenti intatti. Codice e commit in inglese, documentazione italiana, nessun trattino lungo.

## Passi

- [x] Tabelle: aggiornare `ui/shared_tables.py` e `ui/fades.py`; agganci espliciti in catalogo, grafici, varianti e scorciatoie. Prove su selezione, quattro angoli, testata/gutter, ordinamento e ultima riga. Conservare tutti i delegati applicativi e le navigazioni escluse.
- [x] Checkbox e fasi: nuovi componenti/stili dal template, conservando Group e ScrollStyle; adattare PhaseHeader e navigazione finestra. Prove di stati, fuoco integro, testo a capo, scale 1/2/2,5, fasi nascoste e tasti.
- [x] Aiuti e File: distinguere gli aiuti di riga da 28 px dai titoli da 16 px, conservare HelpBox/F1; aggiornare tessere e cambio tema. Valutare DocumentTabs senza sostituire dock o varianti. Aggiornare galleria.
- [x] Verifiche: prove mirate, fotografie sintetiche chiare/scure a scale 1/2/2,5, ispezione reale delle immagini; Ruff e suite complete. Diagnosticare crash report e avviso Slot TableStyle senza dichiararli risolti senza prova. Riconsiderare il limite di tempo del tema, che fallisce anche nella base precedente.
- [x] Consegna: rapporto con delta/non applicabili, manifest revisionati con versioni e hash, commit locale dopo verifiche, aggiornamento delle due copie Windows e launcher verificato.

## Rischi da verificare

Tabelle create dopo l'avvio o con colonne assegnate successivamente; parent con colore diverso ai quattro angoli; stati checkbox dentro Group; fase corrente nascosta con pagina/azioni coerenti; aiuti di titolo accidentalmente ingranditi; vecchi metodi e segnali di Meridiana da mantenere.
