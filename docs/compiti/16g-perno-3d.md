# Compito per una sessione cloud: il perno della vista 3D (studio 16, tema G)

Bozza del 23/10/2026, da lanciare dopo la decisione di Daniel. Lo studio è `docs/studio/16-modellazione.md`, sezione G. Regole di lavoro come in `docs/compiti/fase-2.md`: ramo `perno-3d` da `lavoro`, richiesta di unione in bozza verso `lavoro`, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano. Prima il test, poi il codice.

**Deciso da Daniel il 23/10/2026** («Tutti i punti proposti vanno bene!»): il mirino al passaggio con il tasto del gesto tenuto; per il resto le proposte dello studio. Nessuna libreria nuova: CGAL resta fuori dal programma, come oracolo delle prove.

**Decisioni di Daniel da leggere prima** (G.5): il mirino al passaggio solo con il tasto del gesto tenuto (proposto) o con il mouse fermo 400 ms; il predefinito del perno («sotto il cursore» di oggi o «centro della finestra» con il mirino fisso).

1. Il mirino in `ui/qml/Scene.qml` al posto della pallina: tre anelli ortogonali (una `QQuick3DGeometry` ad anello in `mesh.py`, 48 segmenti, riusabile dal tema B) e un punto al centro, scala `pivotScale` (circa 16 px), colore d'accento del tema con l'alone (`theme_colors`), sopra tutto (`depthTest` spento sul materiale), non `pickable`, senza ombre.
   - Test offscreen in `test_views_navigation.py`: il mirino è visibile durante l'orbita e invisibile dopo (le proprietà del backend); immagine offscreen in chiaro e in scuro.
2. Il mirino al passaggio (`ui/view3d.py`, `navigation.py`): con il tasto del gesto d'orbita dello stile tenuto (Maiusc in AutoCAD, Ctrl in CAD, letto da `Style`) e il mouse che si muove, QML passa il pick a `backend.hover(mods, x, y, hit…)` e il backend mette il mirino sul punto che diventerà il perno (`camera.pivot` con il colpo, il terreno o il bersaglio); si ferma sul perno alla pressione; sparisce al rilascio del tasto; spento da una preferenza accanto a «Perno» («Mostra il perno al passaggio»), con `CONFIG_VERSION + 1`.
   - Test: con Maiusc tenuto e un `move` il mirino compare sul terreno sotto il cursore; senza Maiusc no; con la preferenza spenta no.
3. «Fissa il perno qui»: il clic centrale breve (già «ricentra») lascia il mirino per 1 s (timer, fermo con meno movimento) e, con il perno «centro della finestra», il mirino resta sul bersaglio sempre; con «sotto il cursore» non resta (mentirebbe).
   - Test: con `pivot_mode = "centre"` il mirino è visibile a riposo sul bersaglio; con `"cursor"` no.
4. Il perno che resta sullo schermo (studio 16, G5): se il perno proiettato esce dalla vista, torna al centro della vista alla stessa profondità (`camera.pivot`), come «Safe 3D Navigation».
   - Test in `test_camera.py`: un perno fuori dalla vista viene riportato al centro alla stessa distanza lungo lo sguardo.
5. Documenti e traduzioni: `funzionalita.md`, `CHANGELOG.md`, `progetto.md`, `po/it.po`.

**Da lasciare alla sessione locale**: il costo del pick a ogni movimento con il tasto tenuto sul progetto grande (lo studio 12 misura 0,2-1 ms per fotogramma di disegno), la leggibilità del mirino sull'ortofoto e sui moduli scuri.
