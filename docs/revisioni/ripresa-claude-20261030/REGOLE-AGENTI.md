# Regole per gli agenti della ripresa R07 (Claude, 30/10/2026)

Leggi prima: `docs/revisioni/PASSAGGIO-CLAUDE-20261030-R01.md` (il passaggio di Codex), il tuo rapporto di lotto in
`build/overnight-r07/` se ne hai uno, `CLAUDE.md` della cartella e `docs/richieste.md` (le righe del tuo compito).

## Dove e come
- Cartella: `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10` (ramo `integra-kimi-9-10`). La tranche R07 è sul disco,
  NON committata: è il lavoro da rivedere, non un errore. Non ripristinare versioni vecchie.
- **Tocca solo i file del tuo compito** (elencati nel tuo incarico). Altri agenti lavorano in parallelo sugli altri
  file. Se ti serve una modifica fuori dai tuoi file (in particolare `src/meridiana/ui/window.py` e `po/it.po`), NON
  farla: scrivila nel rapporto con file, riga e testo esatto, la applica Claude.
- **Git: niente commit, add, stash, reset, checkout, clean, restore.** Solo lettura (`git diff`, `git log`, `git show`).
- Python: `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`. Ambiente per le prove (Git Bash):
  `export PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen PYTHONPATH="tests;src" PATH="/c/Users/Grasso/dev/meridiana/.venv/Lib/site-packages/PySide6:$PATH"`
  poi dalla cartella: `python -m unittest <moduli>` (moduli mirati: NON la suite intera). Lint:
  `python -m ruff check --select F,E9,B <file tuoi>`. In Python apri sempre i file con `encoding="utf-8"`.
- Le prove di tempo (temi entro 1 s, alcune di fluidità) possono cadere sotto carico perché altri agenti lavorano in
  parallelo: ripetile da sole prima di concludere che c'è un difetto; non allentare soglie.
- Mai finestre sullo schermo di Daniel (offscreen). Nessuna chiamata API a pagamento: per i fornitori cloud solo mock.
  Non leggere chiavi o credenziali. Niente rete salvo quando il compito lo dice.

## Che cosa si chiede
- Una **revisione vera**: leggere il codice cambiato (`git diff 23bd7a9 -- <file>` e i file nuovi), cercare difetti
  reali (logica, casi limite, timer e callback tardivi, stato non ripristinato, sicurezza e consenso), non solo far
  girare le prove. Per ogni difetto: riprodurlo con una prova che fallisce, correggerlo, la prova passa.
- Le correzioni piccole e mirate; nessuna riscrittura non richiesta. Codice e commenti in inglese, nello stile del file.
  Mai il trattino lungo (U+2014). Testi dell'interfaccia sempre con `_()` (o `ngettext`): elenca nel rapporto ogni
  msgid nuovo o cambiato, con la traduzione italiana proposta.
- Distinguere sempre: **verificato** (con quale prova o misura), **dedotto**, **non verificato**.

## Rapporto
Scrivi il rapporto in italiano in `build/claude-r07/<sigla>-rapporto.md` (la sigla è nel tuo incarico) con:
1. che cosa hai rivisto (file, righe);
2. difetti trovati: descrizione, riproduzione, correzione, prova (nome del test);
3. difetti sospetti non confermati;
4. modifiche richieste a file non tuoi (window.py, po, altri), con testo esatto;
5. msgid nuovi e traduzioni proposte;
6. prove eseguite e risultato (comandi);
7. limiti e cose non verificate.
Il messaggio finale che restituisci è un riassunto di 10-20 righe del rapporto, con il suo percorso.
