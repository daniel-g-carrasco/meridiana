# Compito per una sessione cloud: tetti a falde su piante qualsiasi (studio 16, tema A)

Bozza del 23/10/2026, da lanciare dopo la decisione di Daniel. Lo studio è `docs/studio/16-modellazione.md`, sezione A; le prove in `docs/studio/16-prove/scheletro.py` e il riferimento in `scheletro-riferimento.json`. Le regole di lavoro sono quelle di `docs/compiti/fase-2.md` («Come lavorare»): ramo `tetti-a-falde` da `lavoro`, richiesta di unione in bozza verso `lavoro` con i punti come caselle, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano alla fine. Prima il test che fallisce, poi il codice.

**Deciso da Daniel il 23/10/2026** («Tutti i punti proposti vanno bene!»): pendenza predefinita 35 % (19,3°), con la scelta del tipo di copertura (tegole, coppi, lamiera) che cambia il valore proposto, e come fonte il manuale ANDIL 2025, pag. 7; le pendenze diverse per falda dopo (il passo 4 solo se lo chiede); sulle L le testate sui due bracci. Nessuna libreria nuova: CGAL resta fuori dal programma, come oracolo delle prove.

**Decisioni di Daniel da leggere prima di cominciare** (dallo studio, A.9): la pendenza predefinita (proposta 35 %, 19,3°); se le testate di una L stanno sui due bracci; se le pendenze per lato (scheletro pesato) servono subito.

## Passo 1: lo scheletro dritto nel nucleo

1. `src/meridiana/skeleton.py`, Python puro, senza librerie nuove: lo scheletro dritto di un poligono semplice (4-30 vertici) con aritmetica esatta (`fractions.Fraction`) sugli eventi; eventi di lato e di divisione (Felkel e Obdržálek 1998), eventi simultanei trattati insieme; le facce come anelli, una per lato, nell'ordine dei lati, con l'altezza (distanza dalla gronda) in ogni nodo. Niente fori in questo passo.
   - Test: le 306 piante di `docs/studio/16-prove/scheletro-riferimento.json` (le facce esatte di CGAL): stesse facce (stessi anelli entro 1 mm, stesse altezze), nell'ordine dei lati; un rettangolo dà il tetto di oggi (`roofs.gable` e `roofs.hip` sui test di `test_roofs.py`); vertici allineati e lati di lunghezza quasi nulla puliti prima (come `shapely.simplify(0)`).
   - Un test di tempo: una pianta di 20 lati sotto 50 ms.
2. Le testate: `skeleton.roof(ring, gables: set[int])` spinge i lati di testata lungo le gronde vicine prima dello scheletro, ritaglia le facce sulla pianta e scarta la faccia della testata (`extended_for_gables` e `gable` della prova). Test: le 12 prove della prova (6 piante × padiglione e due falde), più una testata storta (trapezio).

## Passo 2: i tetti del modello

3. `roofs.gable` e `roofs.hip` su qualsiasi pianta con lo scheletro; `Roof.edges: list[str]` («eave» o «gable» per lato) e `Roof.ridge_height: float | None`; `tilt` da `ridge_height` con `slope_from_heights` quando è data (la quota vince, la pendenza si ricalcola e si mostra). Le falde in `Pitch` con `name` «falda del lato n».
   - Test: una L a due falde con le testate sui bracci dà 4 falde, copertura intera, compluvio nell'angolo; il padiglione 6; `exact` non serve più (togliere l'avviso del rettangolo e il suo test).
4. Formato 6: `FORMAT_VERSION = 6`, migrazione 5 → 6: `edges` dai tetti di oggi (due falde: i due lati del rettangolo minimo perpendicolari a `ridge_along` o al lato lungo diventano «gable», gli altri «eave»; padiglione: tutti «eave»); `ridge_along` resta per un giro di versione e poi va via; per le piante non rettangolari il file apre con un avviso nella barra (`Project.load` ritorna già `notice`) e i `SubField.pitch` sono rimappati sulla falda che contiene il baricentro del sottocampo (o la più vicina).
   - Test in `test_model.py`: un file di versione 5 con una L a due falde apre, avverte, e i sottocampi stanno sulla falda giusta; un file rettangolare apre senza avviso e posa gli stessi moduli (le chiavi di posa uguali).
5. Ombre: `system.obstacles_of` considera le altre falde dello stesso edificio per tutti i tipi di tetto, non solo «free». Test in `test_nearshade.py`: un braccio di una L fa ombra sull'altro al mattino del 21 dicembre.

## Passo 3: la finestra

6. Proprietà > Tetto: per i tetti a due falde e a padiglione la lista dei lati con «gronda / testata» (combo per lato, come il gruppo «Lati») e «Scegli sulla pianta» (il `pick_edge` che c'è già, con lo scopo «gable»); «Quota del colmo» accanto a «Pendenza»; la pendenza predefinita del nuovo tetto 35 % con il suggerimento che ne dice la fonte (le schede dei produttori, studio 16 A.8).
   - Test offscreen in `test_window.py`: cliccare un lato come testata cambia il tetto e si annulla; scrivere la quota del colmo cambia la pendenza.
7. Pianta e 3D: freccia di pendenza per faccia (c'è già per falda), il colmo evidenziato al passaggio; il 3D con i timpani (nessun codice nuovo in `mesh.py` se i muri salgono già fino al tetto: verificarlo con un test che conti i triangoli dei muri di una testata).
8. Menu Disegna > «Edificio da modello…»: rettangolo, L, T, U, trapezio con le quote in una finestra (lati modificabili dopo con il gruppo «Lati»); il cortile resta per il passo 4.
   - Test: ogni modello dà una pianta valida con le quote scritte; un modello posato su un sito con ortofoto sta dove si è cliccato.
9. Documenti: `docs/funzionalita.md` (tetti su piante qualsiasi), `CHANGELOG.md`, `docs/progetto.md` appendice A con la riga datata; `po/it.po` aggiornato e controllato con `msgfmt --check`.

## Passo 4 (solo se Daniel lo chiede)

10. I fori (cortile): scheletro con i contorni interni; il modello «cortile».
11. Lo scheletro pesato: una pendenza per lato (`Roof.slopes: list[float | None]`), velocità del fronte proporzionale a 1/tan; test contro CGAL 6 (il riferimento va rigenerato con `create_interior_weighted_straight_skeleton_2`, che la 5.6 di apt non ha: lo fa la sessione locale, o si ricava a mano su casi semplici).

**Da lasciare alla sessione locale**: la resa a occhio dei timpani nel 3D vero, la scelta sulla pianta con il mouse, l'apertura dei progetti di Daniel con l'avviso.
