# Incarico 7, lavori e prove (27/10/2026)

Ramo `kimi-incarico-7`, partito da `origin/lavoro` a c207d1b. Interprete verificato:
`/var/home/daniel/dev/meridiana-kimi/src/meridiana/__init__.py`.

## Punto 1, R133: Impostazioni dentro File

Commit `3f38bee` (`Move settings into File with immediate changes and undo (R133, point 1)`).

Ho scelto una voce «Impostazioni» con sette sottovoci nell'elenco a sinistra di File: Aspetto, Navigazione, Tastiera,
Assistente, Relazione, Mappe e Riservatezza. È la forma più vicina alle altre pagine di File e lascia tutta la larghezza
ai controlli, senza una seconda barra di linguette. La vecchia finestra Preferenze non c'è più.

Ogni modifica è applicata e salvata subito, tema e colore dopo il solito `settled`, il testo con
`theme.change_text_size`. Le altre sezioni seguono il percorso che prima veniva eseguito con OK. «Annulla l'ultima
modifica» conserva fino a 30 stati mentre la pagina vive e resta nella sezione corrente. «Ripristina i valori
predefiniti di questa sezione» chiede conferma in una riga della pagina, senza dialogo. Il comando, Ctrl+, e i rimandi
aprono la sezione richiesta.

Prove:

- [V] Rosso prima sulla copia di c207d1b: con le nuove prove, la vecchia `Preferences` è un `QDialog` e non ha
  `changed`, un fallimento e un errore. Verde dopo: 5 test di `widget.test_preferences`, 11 viaggi mirati della
  finestra per tutte le sezioni, applicazione, salvataggio, scorciatoia, annullamento del tema e profili.
- [V] Il ripristino è confermato nella pagina e può essere annullato; nessuna finestra Preferenze.
- [V] Suite completa prima del commit: 1.473 test verdi, 11 saltati, ruff e `msgfmt --check` puliti.

## Punto 2, R172: giorno e ore nel sottocampo

Commit `3586f8b` (`Move the sun window from Site to each sub-field (R172, point 2)`).

Il gruppo è sparito dal Sito. Con passo «Dal sole», il gruppo «Passo delle file» del sottocampo mostra se la finestra è
il predefinito del progetto o propria, giorno e ore. Modificarli scrive `params.window` del sottocampo in un solo passo.
«Usa per tutti i sottocampi» copia i valori in `Project.sun_window` e toglie le finestre proprie degli altri sottocampi,
sempre in un solo passo di Annulla. I progetti vecchi non cambiano formato né comportamento: senza `params.window`,
`fill_params` usa come prima il valore del progetto.

Le verifiche delle ombre, quelle delle file a mano e `assistant.tools.read_selection` usano la finestra effettiva del
sottocampo. Meridio legge anche `window_from_project`.

Prove:

- [V] Rosse prima: gruppo ancora nel Sito, testo delle ombre sul 21/12 del progetto invece del 20/11 del sottocampo e
  finestra assente dalla lettura di Meridio. Verdi dopo, con posa diversa fra finestra propria e predefinito,
  Annulla e Ripeti, uso per tutti, testi delle verifiche e aiuto.
- [V] I 59 test dei formati e la prova esistente della posa col valore del progetto restano verdi.
- [V] Suite completa prima del commit: 1.477 test verdi, 11 saltati, ruff e catalogo puliti. La prima corsa aveva
  trovato due aiuti oltre 350 caratteri, abbreviati e riprovati prima della corsa verde.
- Il ramo non contiene il lavoro dell'incarico 5 su R170. Ho cambiato solo la scelta della finestra `w`; il testo delle
  verifiche, compresa la formulazione precedente sugli orari, non è stato riscritto, così l'unione non incontra una
  seconda modifica della stessa frase.

## Punto 3, R2: Proprietà riusate

Commit `363feec` (`Reuse Properties pages between objects of the same shape (R2, point 3)`).

L'id dell'oggetto non fa più parte della forma della pagina. Edifici, sottocampi, sottocampi complanari ed esclusioni
con gli stessi campi tengono lo stesso widget e aggiornano solo i valori. Cambia il tipo o la forma e la pagina viene
costruita come prima. Lo scorrimento non si muove. All'oggetto nuovo il testo non confermato viene sostituito, così
nessun valore dell'oggetto precedente può restare o essere confermato per errore.

Misure offscreen sul progetto `generated(20, 2, 1)`: 20 edifici, 40 sottocampi, 30 passaggi misurati dopo 4 di
riscaldamento, `app.processEvents()` compreso. La colonna «dopo» usa l'ultima corsa, senza ricostruzioni.

| Passaggio | Prima, mediana | Dopo, mediana | Ricostruzioni dopo la prima |
|---|---:|---:|---:|
| Due sottocampi | 57,370 ms | 1,773 ms | 0 |
| Due edifici | 24,354 ms | 0,843 ms | 0 |
| Due sottocampi complanari | 44,541 ms | 1,495 ms | 0 |

Prove:

- [V] Rosse prima: nuovo widget sia per gli edifici sia per le esclusioni. Verdi dopo su ogni tipo, anche nomi,
  altezze, inclinazioni, tipo di esclusione, distanze, lati e testo non confermato; scorrimento 249 → 249 nel banco.
- [V] Suite completa prima del commit: 1.479 test verdi, 11 saltati, ruff e catalogo puliti.

## Fotografie e giro guidato

In `docs/revisioni/foto/`:

- `kimi7-preferenze-prima-chiaro.png` e `kimi7-preferenze-prima-scuro.png`: vecchia finestra, offscreen da c207d1b.
- `kimi7-impostazioni-chiaro.png` e `kimi7-impostazioni-scuro.png`: nuova pagina File.
- `kimi7-sottocampo-chiaro.png` e `kimi7-sottocampo-scuro.png`: giorno, ore e comando nel sottocampo.

[V] Ho aperto tutte le immagini: controlli leggibili, nessuna sovrapposizione o parola tagliata, i due temi coerenti.
Il 3D vuoto è il limite noto dell'offscreen, non una scena da giudicare.

[V] Giro guidato con QTest sul progetto `capannone()`, 19 controlli tutti verdi in `esito.json`: finestra e posa,
Ctrl+, tema applicato e salvato, annullamento del tema, navigazione e suo annullamento, finestra propria del
sottocampo, uso per tutti, Annulla e Ripeti, valori del nuovo oggetto e riuso della stessa pagina.

**Prova Wayland non riuscita.** GNOME Shell nascosto è partito con monitor virtuale 1600 x 1000 e GPU AMD, ma persino
una `QApplication([])` minima con `QT_QPA_PLATFORM=wayland` è rimasta ferma prima di stampare «after app». Ho provato
una sessione D-Bus, Fusion, rendering software e buffer condiviso: stesso blocco. Non è stata raggiunta la creazione
della finestra Meridiana. Ho quindi eseguito lo stesso giro offscreen come previsto dall'incarico. Programma, GNOME e
servizi avviati sono stati chiusi; nessun processo della prova è rimasto acceso.

## Documenti e formato

Aggiornati `docs/richieste.md` (R133, R172, R2), `CHANGELOG.md`, `docs/progetto.md`, il manuale e il sistema grafico.
Nessun cambio di formato delle impostazioni o del progetto, quindi nessuna migrazione o nuovo file congelato.
Catalogo italiano compilato, nessuna voce fuzzy, `msgfmt --check` pulito.

## Da provare sullo schermo di Daniel

- Ctrl+, le sette voci a sinistra, annullamento e ripristino con conferma; tema, dimensione del testo, scorciatoie e
  barra della fase.
- Giorno e ore di due sottocampi diversi, posa diversa, «Usa per tutti i sottocampi» e Annulla/Ripeti.
- Passaggi ripetuti fra due oggetti dello stesso tipo, anche dopo aver iniziato a scrivere senza confermare, e lo
  scorrimento delle Proprietà.
- La piattaforma Wayland reale, che qui non ha superato l'inizializzazione di Qt.

Non ho verificato download, portachiavi o servizi di rete reali. I 6 test di `esterni` sono saltati come previsto;
gli altri 5 salti sono quelli già previsti da nucleo e widget. Non restano parti del codice richieste non fatte.
