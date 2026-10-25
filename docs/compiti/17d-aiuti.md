# Compito per una sessione cloud: gli aiuti accanto alle cose (studio 17, tema E)

Bozza del 23/10/2026, da lanciare dopo la decisione di Daniel. Lo studio è `docs/studio/17-interfaccia.md`, sezione E, con i testi d'esempio in E.6; il bozzetto `docs/studio/17-prove/E-aiuti.html`. Le regole di lavoro sono quelle di `docs/compiti/fase-2.md` («Come lavorare»): ramo `aiuti` da `lavoro`, richiesta di unione in bozza verso `lavoro`, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano alla fine. Dopo `17a` (il riquadro e lo stile del «?»).

**Decisioni di Daniel da leggere prima di cominciare** (dallo studio, E.7): il «?» per gruppo o anche per campo; quali campi hanno la frase sotto; il manuale nel repository o in rete. La bozza è scritta su: «?» per gruppo e per i riquadri dei risultati, frasi sotto quattro campi, manuale in `docs/manuale/` aperto come file.

**Deciso da Daniel il 23/10/2026:** **E3** («forse», poi «ci sta!» alla forma proposta qui sotto), il pannello d'aiuto che segue il fuoco, non E1. Lo studio (E.7) lo sconsigliava come pannello fisso per i 70-90 px che costa sempre: si fa come riquadro in fondo alle Proprietà, aperto per impostazione, che si chiude e si riapre (Ctrl+? e il «?» di E1 accanto ai titoli dei gruppi lo riaprono sul punto giusto). I testi restano in `help.py`. Il manuale nel repository (bozza) è ancora da confermare.

**Modifiche dalla revisione completa del 23/10/2026** (`docs/design/interfaccia.md`, sezione 6.4; `docs/studio/18-revisione-completa.md`, sezione 4): da modificare: il blocco «Deciso» dice E3 ma i passi costruiscono E1: il passo 3 va riscritto sul riquadro in fondo al pannello di destra (tre righe più il titolo, richiudibile, nascosto sotto 480 px di pannello, i «?» lo aprono sul punto giusto); F1 e Maiusc+F1 al posto di Ctrl+? (che resta alle scorciatoie); il manuale letto dentro il programma (design 5.1).

## Passo 1: i testi nel nucleo

1. `src/meridiana/help.py`: `Help(short, text, source, manual, pedigree)` e `TEXTS: dict[str, Help]` con gli identificatori dei gruppi e dei campi (`subfield`, `subfield.mounting`, `subfield.row_gap`, `subfield.shade_free`, `production.specific_yield`, `production.pr`, `production.losses`, `production.pvgis`, `economics.self_consumption`, `economics.self_sufficiency`, `economics.npv`, `economics.prices`, `checks.fail`, `checks.warn`, `checks.info`, `checks.source`, …); i testi dallo studio (E.6), riletti da Daniel; tutte le stringhe in `_()`; le fonti con i nomi di `rules.py`.
   - Test in `test_help.py`: `short` al massimo 75 caratteri, `text` al massimo 350 caratteri e cinque righe; ogni `source` esiste tra le fonti di `rules.py`; ogni `manual` è un'àncora presente in `docs/manuale/*.md`; nessun testo cita un articolo di norma che non sia già in `rules.py`.
2. `docs/manuale/`: un capitolo per scheda (modello, producibilità, consumi, bilancio, verifiche) con le àncore usate da `help.py`; prosa breve in italiano; ogni numero dice da dove viene.

## Passo 2: i widget

3. `ui/help.py`: `HelpButton(id)` (un `QToolButton` piatto di 16 px con il «?», suggerimento `short`) e `HelpPopover` (un `QFrame` figlio della finestra, 280 px, con `text`, la fonte e tre collegamenti: «Manuale ›» con `QDesktopServices.openUrl` sul file, «Come è calcolato ›» che cambia scheda e scorre al record (`PedigreeView`), «Chiedi a Meridio ›» che apre la chat con la domanda); si chiude con Esc, con un clic fuori e con il «?» stesso; uno solo aperto per volta. `HintLabel(id)`: la frase `short` attenuata sotto un campo. Lo stesso `text` in `setWhatsThis` del widget, così Maiusc+F1 e il «?» della finestra mostrano la stessa cosa.
   - Test offscreen: il clic sul «?» apre il riquadro con la fonte; Esc lo chiude; il collegamento a «Come è calcolato» cambia scheda; `whatsThis()` del campo è il testo di `help.py`.
4. `ui/properties.py`: il «?» nel titolo dei gruppi Sottocampo, Distanze e margini, Vigili del fuoco, Connessione e obblighi, Passo dal sole, Lati; le frasi sotto Tra le file, Fuori dalle ombre, Giorno di progetto, Prezzi (in Economia). `ui/energy_pages.py`: il «?» accanto ai riquadri dei risultati e ai titoli dei grafici. `ui/checks_page.py`: il «?» accanto ai filtri dei livelli. La barra degli strumenti: suggerimenti estesi (nome, frase, scorciatoia) con `QToolTip` in HTML.
   - Test: ogni `HelpButton` creato nella finestra ha il suo testo in `TEXTS` (un giro sui widget della finestra offscreen); nessun `setToolTip` che ripete il testo del menu a tendina resta (`properties.py`, righe 72-73 e 162).
5. Documenti: `docs/funzionalita.md` (gli aiuti), `CHANGELOG.md`, `docs/progetto.md` appendice A, `docs/richieste.md` (R24 chiusa); `po/it.po` e `msgfmt --check`.

**Da lasciare alla sessione locale**: la rilettura dei testi da parte di Daniel (sostanza e fonti), l'apertura del manuale su Windows (associazione dei `.md`).
