# Integrazione del sistema Quick

04/11/2026. [V] API usate dalla shell e dalle prove di questo ramo.

## Avvio e sorgenti condivise

`python -m meridiana.quick <progetto>` apre la shell. `QuickWindow(project, cache, theme={...})`
riceve un progetto e una cartella cache espliciti. Non legge le preferenze personali e non salva il progetto.
`legacy=True` conserva il prototipo per confrontare le misure precedenti, senza cambiare i Widgets.
`python -m meridiana.quick.gallery` apre la galleria dei controlli.

`install_theme(engine, options)` registra il percorso QML e il provider dell'engine.
`install_controls(engine)` aggiunge le icone, in modo idempotente. Import:

```qml
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Shell
```

I contratti dettagliati sono in `tema-api.md` e `controlli-api.md`.
`Theme.options` espone una copia reattiva delle scelte correnti; `Theme.status` legge i colori semantici
da `theme_colors.STATUS`. Le opzioni valide restano quelle di `Theme.configure`.
Il provider di tema non si condivide fra due engine. Su Windows l'accento di sistema segue la palette viva;
su Linux segue il lettore `SystemAccent` esistente. Non viene modificato il tema globale dei Widgets.

## Comandi e pagine

`ShellController` legge fasi, gruppi e strumenti da `phases.py`; menu e scorciatoie da `shortcuts.py`.
La label breve del comando resta quella della fase, la descrizione e i tasti restano quelli del catalogo.
Le stringhe visibili passano da `i18n`, comprese le tre nuove traduzioni della fascia e di Meno movimento.

Una pagina collega un comando con `shell.register_command(id, handler)` dopo aver creato il suo adattatore.
Finché il comando non ha un handler, menu e strumenti lo mostrano disattivato. Non si finge di averlo eseguito.
`shell.trigger(id)` restituisce falso per un comando assente e mostra una nota nella fascia.
Undo, redo, varianti e modifiche del progetto usano la sessione esistente.

`Workbench.planSource` e `Workbench.view3dSource` sono URL QML. Vuoti, caricano rispettivamente la pianta
del prototipo e il segnaposto 3D. Il contesto espone `backend`, `shell`, `L` e `mascotSource`.
Il ramo Pianta deve registrare i suoi handler e adattare le operazioni `fit`, `tool`, `zoom` del contenitore;
il ramo 3D deve installare il proprio provider. Non devono importare o modificare il prototipo.

## Schede, gesti e aiuto

`DockPanel` mantiene il contenuto vivo quando viene nascosto, raggruppato o spostato. `zone` vale `left`,
`right`, `bottom` o `floating`; `opened` controlla la chiusura. Il workspace decide il pannello attivo del gruppo.
Le schede flottanti sono interne alla finestra. Bordo laterale e inferiore della finestra e angolo delle
schede flottanti sono trascinabili. La zona di rilascio viene accettata dopo `Motion.DWELL`, il riassetto usa
`Motion.CAREFUL`. Posizione, anteprima e interpolazione sono QML; non ci sono callback Python per passo.

Alt viene gestito in QML negli scope della pagina, della barra, della fascia e dell'aiuto. AltGr non lo apre.
Il punto interrogativo sposta Meridio accanto a Proprietà e apre il fumetto a sinistra. Esc e la croce lo
riportano alla posizione precedente. La conversazione completa e il Meridio agganciato appartengono al ramo
successivo; questa shell offre il personaggio flottante e l'aiuto contestuale delle fasi.

## Prove e catture

`tools/quick_shell_capture.py --matrix --theme light` produce 24 stati per la scala impostata nell'ambiente.
Ripetere per scuro e scale 1 e 2. `--states file,selection` limita una rigenerazione ai due stati.
Le catture usano una finestra senza cornice solo durante la prova, per ottenere anche 3840 x 2160 pixel
fisici sul desktop isolato. L'avvio ordinario conserva la barra del titolo di Windows.

`quick.capture.grab` controlla le dimensioni fisiche e assegna il DPR reale alla QImage: il renderer software
offscreen può restituirla con DPR 1 anche quando la finestra è a DPR 2. Non cambia né ridimensiona i pixel.
Il pacchetto imposta prima della prima finestra `QSG_SOFTWARE_RENDERER_FORCE_PARTIAL_UPDATES=0`, salvo
override diagnostico esplicito: evita i residui software senza cambiare Direct3D 11.

`tools/quick_widgets_reference.py` produce il riferimento isolato. `tools/quick_comparison.py` rifiuta
dimensioni, DPR, fixture, numero di moduli e warning incoerenti prima di incorporare i PNG nel singolo HTML.
