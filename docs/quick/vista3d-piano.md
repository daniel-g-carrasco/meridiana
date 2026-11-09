# Vista 3D Quick e modelli liberi: piano, 04/11/2026

Specifica: incarico r12-vista3d e `CONTESTO.md`. Esecuzione autorizzata integralmente senza domande.
Architettura: `mesh.project_scene` resta il riferimento; geometrie Quick3D caricate sul thread GUI,
istanze native Qt senza virtuali Python nel render loop. Camera e gesti continui in JavaScript,
proprietà del progetto attraverso `ProjectSession.edit`. Modelli decorativi separati dalle ombre di calcolo.
Stack: Python 3.12, PySide6/Qt 6.12, QML Quick3D, numpy.

## Vincoli

- Solo le parti assegnate al ramo; `ui/`, nucleo e dati personali in sola lettura.
- Tema da r12-sistema quando compare `tema-pronto.txt`; nessun push, tag o release.
- Persone intere, Casual 5.776 triangoli; licenza esplicita CC0 per ogni originale.
- Bozzetti R375 soltanto, nessuna decisione d'inserimento anticipata.
- Finestre vere D3D11, scale 1/2, foto ispezionate; distinguere rendering da presentazione sul monitor.

## Traguardi e prove

- [ ] Backend `scene.py` e `scene_geometry.py`: snapshot identico al nucleo, istanze native,
  selezione, sole, sessione, preview R365 e commit/annulla. Test differenziali e undo.
- [ ] `Viewport.qml`, camera e navigazione: tutti i profili da `navigation.STYLES`, pan/orbita/zoom,
  cubo completo, Home, modi vista. Prove numeriche contro camera.py e input Qt reali.
- [ ] `models_bake.py`, `scene_assets.py`, `data/models`: originali e fonti, bake statico,
  pose e caricamento condiviso. Test licenze, hash, colori, normali, triangoli e cache.
- [ ] Integrazione dei modelli nella vista: 200 auto e 200 persone come istanze,
  invarianti di `props.shadow_solid` e produzione, immagini vicino/lontano chiaro/scuro.
- [ ] HTML autonomo con tre idee disegnate per R375.
- [ ] Merge tema, integrazione tramite adattatore nelle parti proprie; lint, gruppo formati,
  suite vista3d, foto e misure. Revisione indipendente e `vista3d-esito.md`.

## Attenzioni della revisione

Progetto vuoto, geometria degenerata, undo durante preview, oggetti su tetto inclinato,
scala dispositivo diversa da pixel logici, istanze trasparenti e prospettiva/ortografica.
Ogni prova deve mostrare anche moduli e ombre: una scena vuota veloce non vale.

## Registro

[V] Worktree isolato r12-vista3d, pulito all'avvio. Il segnale del tema manca all'avvio.
[V] La vista corrente usa QuickImage, non QQuickWidget; preview3d è un'anteprima QPainter separata.
Scelta attuativa: lavoro parallelo su bake, cubo/bozzetti e matematica della navigazione,
con proprietà di file disgiunte. Integrazione e verifica GPU a cura della sessione principale.
