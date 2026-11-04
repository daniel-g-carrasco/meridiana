# Incarico per Codex: perché Meridiana è rallentata (R372), 04/11/2026

Daniel: «indaga». Il compito è **trovare le cause con misure**, non correggere. Il metro è un programma agile come VS Code
(obiettivi in `docs/prestazioni/README.md`). Scrivi in italiano l'esito; codice, commenti e commit in inglese; mai il trattino lungo.

## Cosa è stato misurato

Sul Dell, 3840x2160 al 200 %, progetto `%USERPROFILE%\dev\meridiana-prove\Prova capannone Rho.meridiana`, una sola misura per parte:
`docs/prestazioni/2026-11-03/tutto-schermo-6042b8a.json` contro `docs/prestazioni/2026-10-25/base-schermo-correzioni-4.json` (commit
92c760e). Blocco peggiore / somma dei blocchi, in ms:

| Gesto | 25/10 | 03/11 |
|---|---|---|
| Fase Consumi, prima apertura | 53 / 53 | 479 / 985 |
| File, chiusura (la prima di due) | 30 / 30 | 450 / 672 |
| Fase Produzione, prima apertura | 0 / 0 | 280 / 341 |
| Fase Impianto, prima apertura | 68 / 169 | 136 / 210 |
| Bordo del pannello destro, trascinato | 34 / 378 | 81 / 1768 |
| Finestra ridimensionata | 50 / 582 | 78 / 899 |

Tornando su Produzione, Consumi ed Economia il bordo destro costa 1,6-2,0 s di blocchi su circa 2,5 s.

Ipotesi di chi ha misurato, **non verificate, non darle per vere**: pagine costruite al primo uso; il peso aggiunto al pannello
destro. In passato: la `QQuickWidget` del 3D pesava su tutta la finestra sul 4K (`--no-3d` è la prova A/B).

## Cosa consegni

`docs/revisioni/codex-velocita-esito.md`, con:

1. Per ognuno dei sei gesti: la causa, come l'hai dimostrata (il profilo, il numero, la prova A/B), e quanto pesa in ms. Distingui
   sempre **misurato**, **dedotto**, **non verificato**. Se una causa non l'hai trovata, scrivilo.
2. Da quale commit è peggiorato, se riesci a stabilirlo (bisezione con `tools/fluidity.py --sequence edges` su worktree temporanei tuoi).
3. Una proposta di correzione per ogni causa, ordinate per guadagno e rischio, con il guadagno misurato su una prova se l'hai fatta.
4. Le prove lanciate e il loro esito, comandi compresi. Ripeti ogni misura che citi almeno tre volte e dai mediana e scarto: una sola
   misura per parte non basta a concludere, e fra le due date è cambiata anche la macchina di mezzo (driver, carico).

## Dove lavori e regole

- Cartella `C:\Users\Grasso\dev\meridiana-wt-r10-velocita`, ramo `r10-velocita`. Leggi prima `CLAUDE.md` del repository.
- Python: `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`, con `PYTHONUTF8=1`, `PYTHONPATH=tests;src` e la cartella
  `.venv\Lib\site-packages\PySide6` in `PATH`. Prove: `python -m unittest discover -s tests/<gruppo> -t tests`.
- Misure: `python tools/fluidity.py --out <file> [--on-screen] [--no-3d] [--sequence base|charts|edges|all]`, solo con il progetto di
  prova. Senza `--on-screen` si misura solo il lavoro del programma; `--on-screen` è permesso solo se il sandbox lo consente, e copre lo
  schermo per un minuto. Se la finestra vera non può aprirsi qui, dillo e misura fuori schermo, dichiarandolo.
- Le correzioni di prova restano in commit piccoli su questo ramo, separate dalle misure, con la parola `Trial:` nel messaggio. **Non
  toccare altri rami, non fare push, niente tag né release.** La decisione su cosa unire è di Daniel e di Claude.
- MAI `git add .`, `git clean`, reset o checkout distruttivi: staging esplicito. Commit senza attribuzione AI.
- Non toccare: le cartelle di avvio `dev\meridiana` e `dev\meridiana-lavoro` (solo la loro `.venv`, in lettura), i dati veri di
  Meridiana (`%LOCALAPPDATA%\Meridiana`), il disco `I:`, `C:\Users\Grasso\.claude` (sola lettura). Niente chiamate a pagamento.
- `src/meridiana/props.py`, `mesh.py`: li sta cambiando Kimi. Non servono per questo lavoro.
- Non fermarti a chiedere: se manca una decisione, scrivi cosa hai scelto e perché nell'esito.
