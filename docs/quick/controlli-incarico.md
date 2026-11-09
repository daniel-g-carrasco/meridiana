# Controlli Quick: incarico esecutivo

Specifica principale: `CONTESTO.md`, secondo traguardo dell'incarico r12-sistema. Leggere `tema-api.md` prima di iniziare.

Creare `Meridiana.Controls` sotto `src/meridiana/quick/qml/Meridiana/Controls/`, `gallery.py`, backend `controls.py` (icone/i18n se utile), prove `tests/quick/sistema/test_controls.py`, documentazione `controlli-api.md`, rapporto `stato/controlli-rapporto.md`. Non modificare app.py, bridge.py, Shell o ui/. La galleria deve installare tema e provider tramite una funzione `install_controls(engine)` riusabile da app.py.

Tipi richiesti: Button, ToolButton (icona e parola), SplitButton (due parti R364), Menu, MenuItem, ComboBox, TextField, NumberField (unità e virgola italiana), CheckBox, Segments (pista scorrevole come ui/segments.py), Tabs, Badge, ToolTip, ScrollBar, Card, Section, SplitHandle, Table (R394), Tree, List, Dialog, EmptyState, ProgressBar, Icon, Label. Stati normale/hover/premuto/attivo/disabilitato/focus, tastiera e accessibilità. Tutti dal singleton Theme: palette, font, misure. Label.textStyle per stile e condensed per la barra. Button.text e tip, ToolButton.iconName e mode ('under','beside','icons'). SplitButton.model con voci {text,icon,enabled}, segnale chosen(index), onClicked comando principale. Card.title, closable, closed(), area contenuto default e header extra. Segments.model di {text,id}, currentIndex, activated(index). Le altre API devono essere documentate.

Icone da ui/icons.py (SVG) via QQuickImageProvider, nessun duplicato. Testi galleria in Python con i18n; QML senza stringhe visibili hardcoded. Testi di stato della galleria in italiano possono essere traduzioni in Python. Tooltip R379: sola opacità 90/60ms, immediato passando al seguente, zero movimento. Fonte unica per questi due tempi: sono nuove scelte, non esistono ancora in design.Motion. Non modificare ui/.

Tabella R394: niente numeri riga/angolo, fascia fino al bordo, solo righe orizzontali, scrollbar sottile a sovrapposizione solo quando serve, unità sotto il titolo, totale fermo, stato vuoto con comando. Supportare modelli realistici e righe selezionabili.

Eseguire galleria con `python -m meridiana.quick.gallery`; opzioni --shot/--theme/--state/--large-text se utili per matrice. Prove eventi Qt ai controlli, focus, menu, unità numerica e validation; foto D3D11 scale 1/2 chiaro/scuro per tutti i controlli e stati. Guardare le immagini. `quick.capture.grab` normalizza DPR anche software. Non cambiare soglie per farle passare.

Arrivare presto ad un primo gruppo verificato e committato, con il marker `stato/controlli-pronti.txt` che dichiara esattamente cosa è già disponibile e cosa si completa dopo. Poi continuare fino a completare tutti i controlli. Git add e commit semplici, separati, staging solo file propri. Il controller lavora alla shell in parallelo. Nessun altro agente da lanciare.
