# Esito incarico 24, R192-R197, 28/10/2026

## R192, sfumature

Ho fotografato nella sessione nascosta R161, R177 e una via di mezzo sul pannello Inverter scorso a metà, sul Bilancio e
sull'elenco del progetto, in chiaro e scuro. Le 18 foto sono `foto/kimi24-sfumature-{r161,r177,middle}-*.png`.

Ho scelto e realizzato la via di mezzo: 12 px, piena solo sul filo esterno, poi 42 %, 10 % e trasparente. Gli 8 px
d'aria di R177 restano. Il contenuto non raggiunge la linea della scheda e non c'è velo quando è fermo in cima. La
prima voce torna leggibile molto prima che con R177. Modulo condiviso: `src/meridiana/ui/fades.py`.

## R193, scritte troncate

La riproduzione ha trovato la CER con 32 px disponibili e 34 necessari dopo il passaggio a testo Grande. Il controllo
automatico ha trovato anche dettagli nei risultati dei Consumi, note e titoli delle consegne creati dopo la costruzione
della finestra. `grow_label` in `ui/style.py` aggiorna l'altezza delle etichette a capo con larghezza e carattere;
`ui/inspector.py` aggancia lo stesso meccanismo a tutte le consegne dinamiche.

`tests/finestra/test_labels.py` attraversa tutte le sei fasi, la pagina File e ogni sua sezione, chiaro e scuro, testo
Medio e Grande, larghezze 1000 e 1600 px. Ogni etichetta a capo visibile deve avere altezza sufficiente al suo testo.
Al termine il testo Medio globale viene ripristinato, così le prove successive non ne ereditano la misura.

## R194, sezioni con spunta

`SectionGate` in `ui/style.py` è il meccanismo unico: dichiara se i campi sono scrivibili con spunta accesa o spenta,
li attenua nell'altro stato e cambia il suggerimento per spiegare perché. Non modifica i valori.

Sezioni applicate:
- CER: quota condivisa, prezzo zonale, TRASE, contributo e zona;
- LID dalla scheda del modulo: il valore manuale è acceso solo togliendo la spunta;
- azimut automatico: il valore manuale è acceso solo togliendo la spunta.

I valori restano nel progetto. I calcoli economici continuano a escludere la CER quando `community` è falso. Le foto
`foto/kimi24-cer-spenta-chiaro.png`, `foto/kimi24-cer-spenta-scuro.png` e `foto/kimi24-cer-accesa-chiaro.png` mostrano
i due stati e l'etichetta intera. Quella scura comprende l'intera finestra: il `grab()` del solo pannello su Wayland
non compone correttamente i testi nativi, mentre la finestra completa li mostra leggibili.

## R195, salvataggi

`ui/save_status.py`, nella barra di stato: arco piccolo durante la scrittura, poi «Salvato alle HH:MM» per Ctrl+S o
«Salvato in automatico alle HH:MM» per la copia di recupero. Se fallisce, l'arco si ferma e l'errore esistente resta.
`foto/kimi24-salvataggio-barra.png` è presa dopo un salvataggio reale del progetto di prova.

## R196, meteo autonomo

Anno tipo e orizzonte PVGIS sono conservati grezzi in `Project.climate`, nel formato 15 con migrazione e file campione
`tests/formati/file/progetto-v15.meridiana`. Il progetto si apre e calcola senza cache e senza rete. All'apertura, o
quando il sito cambia, `ClimateJob` scarica in sottofondo solo i dati mancanti, senza avviare un anno energetico con
layout incompleti. `session.edit` li mette nel progetto e il normale salvataggio li conserva.

Di nuovo solo oltre 250 m, con una banca dati non riconosciuta o a richiesta esplicita. I 250 m evitano scarichi per
piccole correzioni delle coordinate sotto la risoluzione utile dei dati. Il permesso di usare la rete e il refresh sono
distinti: apertura e Calcola non ripetono il meteo valido; il comando PVGIS esplicito lo aggiorna. Senza rete il
programma lo dice e usa i dati che ha.

Misura su un sito di prova: 695.739 byte per anno tipo e orizzonte, circa 0,66 MiB. Il file completo del progetto di
prova era 1.067.089 byte. Non ho fatto una chiamata PVGIS reale: lo scarico automatico e il refresh sono provati con
lavori e dati simulati, senza rete, come richiede la suite.

## R197, Meridio

Il nome sta sul lato opposto alla maniglia. Le opzioni sono veri `QPushButton` con hover, presenti solo fra un turno e
l'altro. Testo e gruppo prendono l'altezza necessaria; il pannello agganciato basso continua a nasconderle. Il fumetto
cresce col contenuto entro l'area, senza spostare la coda dal personaggio.

Le istruzioni non chiedono più il permesso per la proposta. Il modello chiama subito `propose_fix` o `propose_edit`, la
finestrella compare e solo Daniel applica o scarta. La conversazione con provider finto, ripetuta sul caso che prima
chiedeva permesso, verifica la proposta immediata e il progetto invariato. Anche una vecchia frase «Vuoi che te lo
proponga?» non fa più comparire «Sì, proponimelo».

Foto lette: `foto/kimi24-meridio-proposta-chiaro.png`, `foto/kimi24-meridio-proposta-scuro.png` e
`foto/kimi24-meridio-hover.png`. Tutte e tre le opzioni e i pulsanti Scarta/Applica sono interi nei due temi.

## Moduli condivisi cambiati

- `ui/fades.py`: sfumatura unica per pagine, pannelli ed elenchi;
- `ui/style.py`: crescita delle etichette e `SectionGate`;
- `ui/save_status.py`: stato comune dei salvataggi;
- `ui/assistant.py`: opzioni e adattamento del fumetto;
- `ui/inspector.py`: consegne dinamiche;
- `energy/meteo.py`, `energy/pipeline.py`, `model.py`: clima dentro il progetto e regole di riuso;
- `ui/window.py`: `ClimateJob` separato dal calcolo energetico e attività di salvataggio nella barra comune.

Aggiornati anche `docs/design/sistema-grafico.md`, `docs/funzionalita.md`, `docs/progetto.md`, `docs/richieste.md`,
`CHANGELOG.md` e `po/it.po`.

## Verifiche

Ogni punto ha avuto una prova rossa prima della correzione e verde dopo. I giri reali sono stati fatti solo con
`tools/real_session.sh`, runtime privato sotto `/tmp`, e chiusi senza processi lasciati attivi. Il montaggio
`/run/user/1000/doc` è rimasto presente. Nei giri il 3D ha scritto il timeout dello scheletro nel renderer software;
le pagine fotografate per questo incarico non dipendono dal 3D.

Verifica finale sulla versione fotografata, con `QT_QPA_PLATFORM=offscreen` e un processo per gruppo:
- `nucleo`: 814 prove, OK, 4 saltate;
- `calcoli`: 193 prove, OK;
- `formati`: 60 prove, OK;
- `esterni`: 6 prove, tutte saltate perché le risorse esterne non sono configurate;
- `widget`: 340 prove, OK, 1 saltata;
- `finestra`: 144 prove, OK.

Totale: 1.557 prove, 11 saltate, nessun fallimento. `python -m ruff check src tests tools`: «All checks passed!».
`python tools/compile_po.py` ha compilato il catalogo e `msgfmt --check po/it.po` è pulito, senza voci fuzzy.
Le due prove di geometria della barra e del testo che cadevano sotto carico passano isolate e nella sequenza completa
dopo il ripristino del testo Medio nei test delle etichette.
