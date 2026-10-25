# Compito 19r: la relazione ripensata (R61)

Daniel, 24/10/2026: «usa come esempio una delle tante relazioni che ho fatto tipo quelle di SolarEdge ma
ripensale affinché siano fatte come si deve. Essendo che è un progetto che diventerà pubblico, non voglio che
compaiano nomi o cose varie. Per i capitoli direi che al momento ci sta come hai fatto».

## Il riferimento, letto e lasciato fuori

Sono state lette soltanto la struttura e l'ordine di due relazioni SolarEdge Designer di Daniel: nessun nome,
indirizzo, codice impianto o dato entra nel programma, nei test o nei documenti.

| SolarEdge Designer | Cosa fa bene | Cosa manca o va fatto meglio |
|---|---|---|
| Panoramica del sistema e risultati della simulazione (pag. 1) | i numeri chiave in alto | nessuna immagine della posa, nessuna fonte del meteo nella pagina |
| Energia mensile stimata (pag. 2) | tabella e grafico mese per mese | nessun confronto con un secondo calcolo (PVGIS) |
| Moduli FV (pag. 3) | per campo: modello, potenza, supporto, azimut, inclinazione | niente distanze, file, ombre |
| Progettazione elettrica (pag. 4-7) | inverter, stringhe per inverter, moduli per stringa | nessuna verifica di tensione scritta, nessun riferimento CEI 64-8/7 |
| Parametri di simulazione (pag. 8) | luogo, rete, fuso, stazione meteo | perdite e modelli elencati senza fonte né formula |

## I capitoli (il bozzetto, confermato)

1. **Sintesi**: kWp, moduli, inverter, energia dell'anno tipo, producibilità specifica, indice di prestazione,
   autoconsumo e risparmio se calcolati; la pianta della posa.
2. **Sito e dati climatici**: coordinate (non l'indirizzo, se l'utente non lo vuole), meteo PVGIS con la serie e la
   data di scarico, irraggiamento e temperatura, orizzonte.
3. **Coperture e posa**: per sottocampo l'area, i moduli, il montaggio, orientamento e inclinazione, le distanze,
   il passo delle file con la regola usata, le esclusioni; la pianta per sottocampo.
4. **Impianto elettrico**: inverter (modello, potenza, MPPT), stringhe per ingresso con i moduli, le tensioni
   verificate (Uoc a freddo, Umpp a caldo e a freddo, correnti) con gli articoli della CEI 64-8/7, il rapporto DC/AC e
   l'energia tagliata sulla sua scala (R62).
5. **Producibilità**: mese per mese con il confronto PVGIS, la cascata delle perdite, le ombre.
6. **Consumi e bilancio**: se ci sono dati, l'autoconsumo e lo scambio, la mappa dell'anno (R63).
7. **Economia**: se calcolata.
8. **Verifiche e norme**: ogni verifica con il suo esito e la sua fonte.
9. **Parametri e metodi** (il «Come è calcolato» di ogni numero): modelli, perdite, soglie, con fonte e formula.
10. **Allegati**: schede dei componenti dal catalogo, il registro dei calcoli.

## L'identità

- Nessun nome nel programma. In Preferenze > Relazione l'utente scrive una volta: nome e titolo, ordine e numero
  di iscrizione, recapiti, logo (file scelto da lui, copiato nella cartella dei dati); più profili, per esempio
  «studio» e «libero professionista», scelti per progetto.
- La lingua della relazione è quella del progetto (italiano; l'inglese per i progetti con il Regno Unito).
- Copertina, intestazione e piè di pagina dal profilo; senza profilo, solo il nome del progetto e la data.

## Come si fa

- `report.py` costruisce già il PDF a pagine: si riordina nei capitoli sopra, ogni capitolo una funzione che
  riceve i dati della variante e restituisce i suoi blocchi (testo, tabella, grafico, immagine).
- Le tabelle della relazione sono documento, non schede dell'interfaccia: lì restano tabelle (R79 vale per le
  schede).
- L'anteprima nella fase Relazione mostra le pagine come usciranno, con l'elenco dei capitoli da accendere o
  spegnere.
- Prove: un progetto di prova senza nomi veri, ogni capitolo presente quando ha dati e assente quando non ne ha,
  nessuna stringa del profilo nel PDF senza profilo, la relazione in inglese con il progetto in inglese.

## Fatto (24/10/2026 sera, ramo `grafica`)

Daniel, 24/10/2026: «quello di SolarEdge rimane uno dei possibili template, non per forza la relazione di default».

- **Due modelli** (`reports.py`), scelti per progetto nella fase Relazione:
  - **Completa**, il predefinito: copertina, indice con le pagine, i dieci capitoli sopra, ognuno su pagina nuova;
  - **Sintetica**: l'ordine delle relazioni dei programmi degli inverter (panoramica e risultati, energia mese per
    mese, moduli per sottocampo, progetto elettrico, parametri di simulazione), senza indice, in 4-5 pagine.
  Nel programma nessun marchio: il modello si chiama «Sintetica».
- **Capitoli** (`ui/report_chapters.py`): una funzione per capitolo; un capitolo senza dati non si scrive (niente
  capitoli vuoti), uno spento dal progettista neppure, e la numerazione segue quelli scritti. Pianta dei moduli e
  pianta delle stringhe (ogni stringa nel suo colore, con etichetta e percorso), nord e scala; grafici mensili, cascata
  delle perdite, bilancio mese per mese, mappa dell'autoconsumo ora per ora, flussi di cassa; tabelle di documento.
- **Chi firma**: profili in Preferenze > Relazione (nome e titolo, albo, studio, recapiti, logo copiato nella
  cartella dei dati), uno predefinito per i progetti che non scelgono; senza profilo la relazione dice solo progetto
  e data. Copertina disegnata a tutta pagina, intestazione (studio, progetto) e piè di pagina (relazione, data,
  «pagina n di N») dalla seconda pagina.
- **Fase Relazione** (`ui/report_page.py`): i quattro comandi in alto (vanno a capo in una finestra stretta),
  l'anteprima delle pagine fatta un passo alla volta, a destra modello, firma, committente, revisione, indirizzo sì
  o no, capitoli da accendere e spegnere (grigi, con il perché, quando mancano i dati); ogni scelta è una modifica del
  progetto, annullabile (formato 11: `Project.report`, comune alle varianti).
- **La lingua** della relazione è quella del programma: per una relazione in inglese si mette Meridiana in inglese
  (Preferenze > Aspetto) e si esporta. Una lingua per progetto chiederebbe di rifare verifiche e calcoli nella lingua
  della relazione, perché i loro testi nascono già tradotti.
- Prove: `tests/widget/test_report.py` (13: ordine dei capitoli dei due modelli, indice con le pagine giuste,
  capitoli spenti o senza dati, profilo solo dove scelto, PDF e anteprima), `tests/finestra/test_phase_bar.py`
  (anteprima, scelte annullabili, profili con il logo), formati e impostazioni (progetto 11, impostazioni 16).

Restava (24/10): gli allegati con le schede tecniche vere (oggi i dati dal catalogo), il registro dei calcoli come
allegato a parte, le immagini della posa in 3D.

## Fatto (25/10/2026, ramo `relazione2`)

- **Allegati** (fase Relazione, a destra sotto i capitoli). «Aggiungi file PDF…»: schede tecniche di moduli,
  inverter, ottimizzatori, certificati. Per ciascuno: il nome nella relazione (un campo; vuoto, vale il nome del
  file), il file con le sue pagine o il motivo per cui resta fuori (non trovato, non leggibile, protetto da una
  password), su e giù, togli; ogni gesto è una modifica annullabile.
  - Nel PDF vengono dopo l'ultimo capitolo (dopo gli Allegati nella Completa, in fondo nella Sintetica), ciascuno
    preceduto da una pagina «Allegato n: nome» con il file e le pagine. Nell'indice, sotto i capitoli, con la pagina
    vera del PDF unito; il piè «pagina n di N» conta anche le pagine degli allegati, che restano come sono, senza
    intestazione.
  - Unione con pypdf 6.21 (BSD-3-Clause, puro Python): in `requirements.txt`, `ATTRIBUTIONS.md`,
    `tools/cloud-setup.sh`, installato nella venv comune. [V] Dei 400 PDF di cataloghi di costruttori letti il 25/10
    sul PC di Daniel, 29 sono cifrati con AES contro le modifiche: pypdf li apre solo con il pacchetto `cryptography`, che Meridiana
    non chiede. Quelli entrano disegnati pagina per pagina da QtPdf (PDFium) a 200 dpi, e la pagina che li precede lo
    dice.
  - L'anteprima mostra le pagine vere degli allegati con QtPdf: le prime 8 di ciascuno, poi una pagina «altre n
    pagine»; il conteggio in alto dice le pagine del PDF.
  - Prima di esportare, un allegato mancante o illeggibile è detto con il motivo, e si sceglie se esportare senza.
  - Nel progetto: `Project.report["attachments"]`, `{path, title}`. In memoria i percorsi sono assoluti; nel file
    sono relativi alla cartella del progetto (`reports.portable` in `Project.save`, `reports.resolved` in
    `Project.load`), con «/»; assoluti se il file sta su un altro disco. Una cartella spostata con le sue schede le
    ritrova; un «Salva come» altrove le riscrive relative alla cartella nuova.
  - **Nessun formato nuovo** (resta il 12): `report` è un dizionario che le versioni 11 e 12 tengono intero e
    risalvano senza perdere nulla; una versione vecchia esporta la relazione senza allegati. Il formato 15 riservato
    non serve.
  - Il pannello di destra della fase Relazione ora sta nella sua scheda: una riga del modulo che non ci sta va sotto
    la sua etichetta, il titolo lungo di un elaborato su due righe (prima il bordo destro, con «Profili…» e gli
    stati, era tagliato di 29 px). I pulsanti delle righe sono le icone Lucide `arrow-up`, `arrow-down`, `x`.
- **Registro dei calcoli**. Casella «Esporta anche il registro dei calcoli» (scelta del progetto, annullabile):
  accanto al PDF due file.
  - `<nome> - registro dei calcoli.csv`: le 8.760 ore dell'anno tipo, con l'ora locale e lo scarto da UTC,
    irraggiamento globale orizzontale e sul piano (W/m²), temperatura dell'aria e delle celle (°C), energia prodotta e,
    con i consumi, consumata, autoconsumata, immessa, prelevata (kWh). In testa righe «#»: progetto, variante, data,
    convenzione dell'ora, meteo, base dei consumi, e per ogni colonna l'unità, il significato e la fonte. In italiano
    «;» e virgola decimale, in inglese «,» e punto; UTF-8 con il segno iniziale, così Excel legge «°» e «²».
    `energy/register.py`, senza Qt; la temperatura delle celle è la media pesata sulla potenza dei campi, presa dal
    primo passaggio della simulazione (`Simulation.parts`), senza toccare `simulate.py`.
  - `<nome> - come è calcolato.pdf`: il capitolo «Parametri e metodi» da solo, con le formule, sotto il titolo
    «Registro dei calcoli» (lo stesso codice della relazione, `export_steps(..., only="methods")`).
  - Lo strumento «CSV» della barra della fase Relazione, previsto per questo compito, esporta il registro da solo;
    l'elaborato «Serie orarie (CSV)» ha ora il suo stato (da fare, fatto, da rifare).
- **Immagini 3D della posa**. Due assonometrie, viste parallele da sud-est e da sud-ovest, 30° dall'alto: carta
  bianca, edifici chiari e neutri con gli spigoli disegnati, moduli nel blu della pianta, ombre leggere di un sole a
  sud-ovest. Affiancate prima della pianta nella Sintesi (Completa) e nella Panoramica (Sintetica).
  - Rese senza finestra (`ui/report_3d.py`, `qml/ReportScene.qml`): una `QQuickWindow` guidata da un
    `QQuickRenderControl` disegna la scena in una texture dell'RHI (Direct3D 11 su Windows), che si rilegge come
    immagine, sul thread della finestra. La vista 3D della finestra non si tocca. Il renderer resta per il processo:
    la prima immagine costa circa 0,7 s (gli shader), le successive circa 0,1 s per le due viste; le immagini della
    stessa scena restano in memoria.
  - Provata prima una `QQuickView` nascosta con `grabWindow()`: ogni presa rifaceva il dispositivo (circa 1 s) e la
    seconda presa della stessa vista tornava vuota.
  - Sulla piattaforma offscreen di Qt, senza `QT_QUICK_BACKEND=rhi`, Qt Quick usa il disegno software e il 3D non
    si disegna: lì la relazione lascia fuori le immagini, e una riga nel log lo dice. Le prove della suite girano
    così; la prova vera delle immagini gira in un processo suo con `QT_QUICK_BACKEND=rhi`.
- Prove: `tests/widget/test_report.py` (+8: allegati in coda con l'indice e le pagine giuste nelle due forme,
  mancante e non PDF lasciati fuori, protetto disegnato, anteprima con le prime pagine e il conteggio, percorsi
  relativi e altro disco; registro ora per ora con il bilancio, CSV in inglese e in italiano letto da pandas,
  «Come è calcolato» da solo; immagini 3D nella Sintesi e nella Panoramica, e fuori senza il renderer),
  `tests/widget/test_report_3d.py` (immagini vere in un processo con l'RHI: bianco agli angoli, il blu dei moduli,
  due viste diverse, la cache, il renderer tenuto), `tests/nucleo` (camera assonometrica, scena del progetto, stato
  dell'elaborato CSV), `tests/finestra/test_phase_bar.py` (+2: allegati come modifiche annullabili e avviso
  all'esportazione; registro accanto alla relazione e CSV da solo).

Resta:

- le immagini 3D sul portatile Linux (OpenGL o Vulkan su Wayland): non provate;
- la relazione esportata dal programma vero sul PC di Daniel, con la vista 3D della finestra accesa: provato solo
  offscreen con `QT_QUICK_BACKEND=rhi` (la vista della finestra e il renderer insieme, nessun errore);
- la tessera «Serie orarie» nella pagina File (lo strumento c'è nella barra della fase Relazione);
- se Daniel vuole gli allegati cifrati AES vettoriali invece che disegnati: aggiungere `cryptography`
  (Apache-2.0 o BSD) ai requisiti.
