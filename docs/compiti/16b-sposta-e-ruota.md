# Compito per una sessione cloud: sposta e ruota, in pianta e nel 3D (studio 16, tema B)

Bozza del 23/10/2026, da lanciare dopo la decisione di Daniel. Lo studio è `docs/studio/16-modellazione.md`, sezione B; la prova in `docs/studio/16-prove/gizmo.py`. Regole di lavoro come in `docs/compiti/fase-2.md`: ramo `sposta-e-ruota` da `lavoro`, richiesta di unione in bozza verso `lavoro`, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano. Prima il test, poi il codice.

**Deciso da Daniel il 23/10/2026** («Tutti i punti proposti vanno bene!»): Ctrl durante lo spostamento fa una copia; M a Sposta e Misura passa a D; le maniglie solo con lo strumento attivo. Nessuna libreria nuova: CGAL resta fuori dal programma, come oracolo delle prove.

**Decisioni di Daniel da leggere prima** (B.8): Ctrl durante lo spostamento = copia (proposto) o scatti; M a Sposta e Misura su D; il gizmo solo con lo strumento attivo (proposto) o a ogni selezione.

## Passo 1: il nucleo e la pianta

1. `src/meridiana/move.py`, senza Qt: `translate(project, kind, oid, dx, dy)` e `rotate(project, kind, oid, cx, cy, degrees)` che restituiscono una funzione `change(p)` per `edit()`; spostano con l'oggetto ciò che gli appartiene (edificio: sottocampi, esclusioni e falde libere che lo citano; sottocampo: i moduli tolti a mano restano, l'azimut esplicito ruota); rifiutano con il motivo (`ValueError` tradotto) una falda libera che esce dall'edificio o un sottocampo che cambia falda; un'esclusione che esce cambia `building` con `_host`.
   - Test in `tests/test_move.py`: un edificio ruotato di 90° attorno al baricentro porta con sé sottocampi ed esclusioni e tiene `eave_side`; un sottocampo con `azimuth` esplicito ruota l'azimut; i rifiuti con il motivo; la chiave di posa cambia.
2. Lo strumento Sposta in pianta (`ui/plan.py`): tasto M (Misura passa a D in `shortcuts.py`, con la migrazione delle impostazioni `CONFIG_VERSION + 1` per chi aveva M su Misura); con un oggetto selezionato: punto base con gli agganci dello `Snapper`, anteprima del contorno durante il movimento, secondo punto con gli agganci o valore digitato («3» = 3 m lungo la direzione del cursore, «3;2» = est e nord, Tab passa da distanza ad angolo), Invio applica; Ctrl tenuto al rilascio = copia (`Project.duplicate` con lo scarto scelto); Esc esce; frecce = 10 cm, Maiusc+frecce = 1 m, Ctrl+frecce = 1 cm solo con lo strumento attivo; una sola istantanea al rilascio.
   - Test offscreen in `test_plan.py` e `test_window.py`: premere M, cliccare due punti e trovare l'edificio spostato di quel vettore con i suoi sottocampi; un valore scritto; Ctrl al rilascio che copia; Esc che non cambia nulla; un solo passo di annullamento.
3. Ruota nello stesso strumento: «R» durante Sposta o il grip sul contorno: centro (il baricentro, o il punto cliccato), angolo con gli agganci polari a 15° (5° con Ctrl, 90° con Maiusc) o scritto; la stessa anteprima.
   - Test: ruotare un sottocampo di 30° scrive 30 nell'angolo e ruota l'azimut esplicito.
4. Grip (studio 16, B3): al centro dell'oggetto selezionato una maniglia che sposta trascinando, sul contorno una che ruota; Invio o Spazio cicla i modi come i grip di AutoCAD. Test: il trascinamento della maniglia centrale equivale a Sposta.

## Passo 2: il gizmo nel 3D

5. In `ui/qml/Scene.qml` il nodo `gizmo`: tre frecce (`#Cylinder` più `#Cone`, x rossa, y verde, z blu nei colori del tema con l'alone), tre quadratini dei piani, tre anelli (un cilindro piatto con un foro: una `QQuick3DGeometry` di 48 segmenti in `mesh.py`), scala legata alla distanza della camera come `pivotScale` (120 px), visibile solo con lo strumento Sposta attivo e una selezione; posizione dal centro della selezione (`_centre_3d`).
6. La scelta della maniglia in Python sullo schermo (`screen_pick` della prova, con `camera.Camera.project`), tolleranza 8 px; il trascinamento vincolato con `axis_drag` e `ring_angle` della prova; il corpo dell'oggetto con `View3D.pick` come oggi; durante il gesto si muove un'anteprima (una copia del nodo), al rilascio `move.translate`/`rotate` in un'istantanea; il campo numerico accanto al gizmo (un `QLineEdit` sopra il `QQuickWidget`, Tab tra x, y, z e angolo, come i manipolatori di DIALux).
   - Test offscreen in `test_views_navigation.py`: con una selezione e lo strumento attivo, un `press` sul pixel della freccia x e un `move` di 50 px spostano l'edificio solo lungo est, della quantità attesa a 1 mm; un `press` sull'anello e un movimento ruotano di un angolo atteso a 0,1°; il valore digitato; nulla senza lo strumento.
7. I passi nel 3D come in pianta (Ctrl scatti o copia secondo la decisione, Maiusc fine); frecce della tastiera con lo strumento attivo; Esc.
8. Documenti e traduzioni: `funzionalita.md`, `CHANGELOG.md`, `progetto.md`, `12a-convenzioni-ux.md` (la mappa dei tasti con M e D), `po/it.po`.

**Da lasciare alla sessione locale**: la sensazione del trascinamento con il mouse vero, il pick sulle frecce sottili con la GPU, i colori delle frecce sull'ortofoto, il tasto M sulla tastiera italiana con il fuoco nell'albero.
