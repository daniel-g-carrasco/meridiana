# Sistema Quick: piano di esecuzione, 04/11/2026

Specifica: `CONTESTO.md` e incarico r12-sistema di Daniel. Esecuzione continua autorizzata, nessuna pubblicazione.

Architettura: sorgenti Widgets in sola lettura. Moduli QML Theme, Controls e Shell separati; backend Python per token, traduzioni, comandi e sessione. Gesti continui nel QML. Pianta e vista 3D con punti di integrazione per i rispettivi rami.

## Vincoli

- Unica fonte delle misure: `ui/design.py`; dei colori: `theme_colors.py`; font e icone dai servizi esistenti.
- Italiano tramite i18n, niente testi di prodotto nei QML; Plex, condensato della barra, grey/indigo predefiniti.
- Scrittura solo in questo worktree; nessun push, tag o release. Commit espliciti per traguardo.
- Prove vere Direct3D 11, scale 1 e 2, chiaro/scuro; screenshot ispezionati. Nessuna soglia allargata.

## Contratti tra le parti

`backend/tokens.py`: `ThemeTokens(QObject)`, `install_theme(engine, theme=None) -> ThemeTokens`.
Singleton QML `import Meridiana.Theme; Theme`: mappe `colors`, `space`, `radius`, `type`, `size`, `line`, `motion`, `layout`, `bar`, `icon`, `text`; proprietà `fontFamily`, `barFontFamily`, `dark`, `reducedMotion`, `textSize`; `configure(options)` aggiorna tutto e `measureText(text, style, condensed)` misura. `tokens` conserva i nomi piatti del prototipo.

Controls: tipi QML Button, ToolButton, SplitButton, Menu, MenuItem, ComboBox, TextField, NumberField, CheckBox, Segments, Tabs, Badge, ToolTip, ScrollBar, Card, Section, SplitHandle, Table, Tree, List, Dialog, EmptyState, ProgressBar, Icon, Label. Tutti da Theme, nessuna palette duplicata. API e galleria documentate prima del segnale di disponibilità.

Shell: fasi e gruppi da `phases.py`, etichette e scorciatoie da `shortcuts.py`; dispatch ai comandi del bridge e segnale per i rami esterni. Nessun comando mancante finge di funzionare. Schede riusabili e componenti sostituibili di pianta, 3D, proprietà e verifiche.

## Passi e verifiche

- [ ] Tema: test parità di ogni token, ogni accento e fondo chiaro/scuro, cambio vivo dimensione/carattere/movimento; prova QML; commit e `stato/tema-pronto.txt`.
- [ ] Controlli: test eventi e focus, galleria con stati e foto; R364, R379, R394; commit e `stato/controlli-pronti.txt`.
- [ ] Difetto pianta: riprodurre `5098 != 0` a scala 2, individuare causa con controllo pixel e regressione D3D11; escludere Quick come interfaccia dalla prova nucleo.
- [ ] Shell e Modellazione: barra fasi e coda, strumenti, schede ridimensionabili/chiudibili/raggruppabili/trascinabili, menu Alt, Meridio, stato, sessione reale; test di comandi e transizioni.
- [ ] Confronto autonomo HTML con immagini incorporate Widgets/Quick, matrice temi/scale/misure/stati, differenze esplicite.
- [ ] Verifica finale lint, formati, prove Quick e import senza Qt; revisione indipendente; stato, diario, richieste ed esito.

## Rischi da provare

Aggiornamento del singleton con più motori QML; testo grande nei controlli stretti; DPR nel ritaglio delle catture; menu e dialoghi senza finestre transitorie native; trascinamento schede senza callback Python per fotogramma.
