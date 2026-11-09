# Theme Quick: contratto per gli altri rami

04/11/2026. Fonte delle misure: `ui/design.py`. Fonte dei colori: `theme_colors.derive`.
Font registrati dal servizio esistente `ui/theme.py`, compresa la variante condensata.
Il codice dei Widgets resta in sola lettura.

## Installazione

```python
from meridiana.quick.backend.tokens import install_theme

theme = install_theme(engine)
engine.load(...)
```

`install_theme(engine, theme=None) -> ThemeTokens` aggiunge il percorso QML e la proprietà di contesto
`themeTokens`. Il secondo argomento può essere un dizionario di opzioni oppure un `ThemeTokens` già creato.
Il motore conserva il riferimento Python. Chiamarlo ancora sullo stesso motore restituisce il medesimo provider;
un dizionario aggiorna le opzioni. Sostituire il provider già installato con un altro oggetto dà `ValueError`.
Due motori hanno temi indipendenti. Nessuna modifica alle scale globali, alla palette o al font dei Widgets.

```qml
import Meridiana.Theme

Rectangle {
    color: Theme.colors.card
    radius: Theme.radius.CARD
    implicitHeight: Theme.size.CONTROL
    Text {
        text: model.label
        font.family: Theme.fontFamily
        font.pixelSize: Theme.text.body.size
        font.weight: Theme.text.body.weight
        color: Theme.colors[Theme.text.body.tone]
    }
}
```

## Mappe e valori

| Proprietà | Contenuto |
|---|---|
| `colors` | Tutti i token di `derive`, con `plan`, `d3`, `chart` annidati. Colori in formato Qt `#aarrggbb`, già convertiti da CSS. |
| `space`, `radius`, `type`, `size`, `line`, `motion`, `layout`, `bar`, `icon` | Tutte le costanti pubbliche delle rispettive classi `design`, con chiavi MAIUSCOLE. `SCALE` è una sequenza; `Bar.ICON` e `Bar.STEP` restano mappe. |
| `text` | Stili per nome minuscolo: `display`, `heading`, `title`, `strong`, `body`, `description`, `control`, `secondary`, `caption`, `label`, `group`; alias `button` di `strong`. Ogni stile ha `size`, `weight`, `tone`, `caps`. |
| `tokens` | Mappa piatta compatibile con `D` del prototipo: colori principali, prefisso `plan_` e misure esistenti. |
| `fontFamily`, `barFontFamily` | Famiglia principale e condensata; con Inter entrambe sono Inter. |
| `dark`, `reducedMotion`, `textSize` | Modalità risolta, movimento ridotto, scelta della dimensione. |
| `revision` | Numero crescente; permette alle misure di testo in binding di aggiornarsi. |

Le costanti di `type` e le dimensioni di `text` seguono la scelta del testo. Non scalare nuovamente per il DPR:
sono pixel logici. Con movimento ridotto le durate di animazione e scrittura sono zero;
`motion.DWELL` resta un'attesa e `motion.TYPING_CHARS` resta un conteggio.
Le durate specifiche dei tooltip R379 saranno nei controlli: non sostituiscono le durate generali di `design.Motion`.

## Configurazione viva

```qml
Theme.configure({
    theme: "dark",
    accent: "indigo",
    backgrounds: "grey",
    font: "plex",
    textSize: "large",
    reducedMotion: true
})
```

La stessa mappa si passa a `theme.configure(...)` da Python. Ogni chiave è facoltativa.
Predefiniti R390/R391: `light`, `indigo`, `grey`, `plex`, `medium`, movimento normale.

- `theme`: `light`, `dark`, `system`; segue i cambi del sistema quando selezionato.
- `accent`: chiave di `theme_colors.PRESETS`, `system`, oppure colore `#rrggbb`.
- `backgrounds`: `meridiana`, `tinted`, `grey`.
- `font`: `plex`, `inter`.
- `textSize`: `small`, `medium`, `large`.
- `reducedMotion`: booleano.

Alias Python: `text_size`, `reduced_motion`; `dark: true/false` seleziona il tema esplicito.
Chiavi o valori sconosciuti danno `ValueError` senza modificare il tema. Una configurazione identica non emette segnali.
Un aggiornamento valido emette un solo `changed`; tutte le mappe sono già aggiornate prima del segnale.

## Misura del testo

`Theme.measureText(text, style = "body", condensed = false)` restituisce
`{width, height, ascent, descent}` in pixel logici. Usa `QFontMetricsF` con famiglia, peso,
maiuscole e spaziatura dello stile. `width` è l'avanzamento di una riga, non una misura di testo a capo.
Per il testo impaginato usare `Text.implicitWidth`, `Text.implicitHeight` o `TextMetrics` nel QML.
Questa chiamata serve per preparare una disposizione; non chiamarla a ogni fotogramma di un trascinamento.

## Verifica

`tests/quick/sistema/test_theme.py`: tutte le 54 palette, comprese le trasparenze; tutte le scale e le tre
dimensioni; Plex e Inter; misure di tutti i casi provati; due motori indipendenti; aggiornamento QML vivo;
configurazione non valida; pixel e catture della finestra Quick.
La prova grafica è un campione del tema: il confronto estetico dei controlli completi appartiene alla loro galleria.
