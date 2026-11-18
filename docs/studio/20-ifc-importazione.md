# 20. Importare un modello IFC per il fotovoltaico, in modo efficiente

Daniel, 25/10/2026: «Vai con gli IFC. Ma l'import è possibile farlo? So che è un tema delicato perché se il modello
in ingresso è complesso può anche bloccare o rendere molto lenti gli import. Noi non abbiamo bisogno di dettagli per
fare gli FV, quindi troviamo una buona ed efficiente strada per farlo».

Questo studio misura le strade per leggere un IFC su campioni pubblici di dimensione e complessità crescenti, dice che
cosa ne ricava Meridiana, le confronta con i voti e raccomanda la strada costruita nel programma (R91). Lo studio 15
(sezione 5.2) aveva già provato l'esportazione e un lettore prototipo; qui si misura e si costruisce.

Le prove sono in `docs/studio/20-prove/` (gli script, `campioni.json` con fonte e licenza di ogni file,
`risultati.json` con tutte le misure, le piante in `piante/`). I file grandi stanno fuori dal repository, in
`%USERPROFILE%\dev\meridiana-prove\ifc-2026-10-25\campioni`; nel repository ci sono solo i due campioni piccoli di
buildingSMART (CC BY 4.0) usati dai test.

## In breve

1. **Sì, si può, ed è veloce se si legge solo ciò che serve** [V, misure della sezione 3].
   - Leggere tutto il modello, con la geometria di ogni oggetto e i fori delle aperture (strada a), costa da 2,6 a 31 s e
     fino a 1,3 GB sui modelli d'architettura di 2-50 MB, e più di 5 minuti sugli impianti di un edificio (53 MB).
   - Leggere solo coperture e ciò che sta sopra, con le forme semplici prese direttamente dal file e il resto fatto da
     IfcOpenShell (strada c), costa da 0,3 a 3,3 s e meno della metà della memoria, **con lo stesso risultato**; 11 s
     su un file sintetico di 230 MB, quasi tutto per aprirlo.
   - Esempi: Schependomlaan (47 MB, ArchiCAD) da 22,6 s e 601 MB a 3,3 s e 192 MB; la palestra di Amersfoort (2,8 MB,
     Revit) da 20,4 s e 1,3 GB a 0,42 s e 67 MB.
2. **Il pericolo vero non è solo la lentezza.** IfcOpenShell è C++: un suo crollo, dentro la finestra, la chiude.
   - Nella 0.9.0.post1 cade in due casi trovati qui: i suoi thread su un file aperto in modo pigro, e l'iteratore
     lasciato a metà [V, 3.5].
   - I file di prova di IfcOpenShell nati da crolli e cicli infiniti delle versioni passate non cadono più con la 0.9,
     ma la strada a ci mette 185 s su uno e più di 300 s su un altro [V, sezione 4]. Che ne arrivino di nuovi è
     probabile [I].
   - Per questo la lettura gira **in un processo a parte**: la finestra lo guarda, mostra la barra e Annulla, lo ferma
     oltre 180 s o oltre metà della memoria del PC; se cade o si blocca, lo rilancia una volta **senza** l'iteratore,
     con le sole forme semplici, e dice che cosa ha lasciato fuori.
3. **Che cosa ottiene Meridiana**: edifici con il contorno, la quota di gronda e il tetto riconosciuto (piano, una
   falda, due falde o padiglione con le testate, altrimenti falde libere con inclinazione e orientamento esatti), le
   esclusioni con l'altezza (camini, lucernari, impianti, alberi), il parapetto dei tetti piani, il sito e il nord
   (conversione di mappa UTM, oppure latitudine e longitudine, oppure niente). Andata e ritorno di un progetto di
   Meridiana: contorni, falde, quote, tipi di tetto e ostacoli tornano uguali al millimetro [V, test].
4. **Voti** (sezione 5): c con b come riserva, in un processo a parte, voto 5; leggere tutto (a) voto 2; solo i
   riquadri (d) voto 2; le altre librerie (web-ifc, xBIM, un lettore STEP scritto da noi) voto 1-3.
   **Raccomandazione: c+b in un processo a parte**, quella costruita.

## 1. La domanda: che cosa serve al fotovoltaico

Serve:
- la posizione del modello sulla Terra e il nord;
- per ogni edificio il contorno, la quota del terreno e la quota di gronda;
- le falde: il contorno in pianta, l'inclinazione, l'orientamento, la quota;
- ciò che sta sulle coperture e fa ombra o toglie posto: camini, lucernari, impianti, parapetti, torrini; gli alberi.

Non serve: l'interno (stanze, porte, finestre delle pareti, scale, arredi), gli impianti dei piani, le aperture nei
muri, i materiali, le proprietà, le quantità. In un modello d'architettura sono quasi tutto: nello Schependomlaan, 3.822
oggetti, le coperture sono 62 [V].

Il costo della lettura ha tre parti:
- **aprire il file** (il parser STEP): cresce con la dimensione del file, qualunque cosa si legga dopo;
- **fare la geometria** (tassellare): cresce con il numero e la complessità degli oggetti fatti, e i fori delle
  aperture (sottrazioni booleane) sono la parte più cara;
- **analizzare**: trovare i piani delle falde e gli ostacoli, in Python.

## 2. Le strade

| Strada | Che cosa fa | Che cosa dà a Meridiana |
|---|---|---|
| a. Tutto | L'iteratore di IfcOpenShell su ogni oggetto, con i fori delle aperture, 8 thread: il punto di partenza | tutto, poi si sceglie |
| b. Solo il necessario | L'iteratore solo su coperture, solai o pareti degli edifici senza tetto, oggetti sopra le coperture; senza i fori, coordinate del mondo. b8: file aperto per intero e 8 thread; b1: file aperto in modo pigro e un thread | contorni, falde, quote, ostacoli |
| c. Forme lette dal file | Come b, ma le forme semplici si leggono direttamente: estrusioni di poligoni, rettangoli e cerchi, Brep a facce piane, insiemi di facce, anche dentro gli oggetti mappati. Il resto (booleane, ritagli, curve) va a b. File aperto in modo pigro, un thread | come b, più in fretta |
| d. Solo i riquadri | I soli punti delle forme, senza fare facce | contorno a rettangolo e altezza; niente falde |

Due scelte attraversano le strade:
- **apertura pigra** (`ifcopenshell.open(..., lazy=True)`): un passaggio veloce indicizza il file e
  ogni oggetto si legge solo quando serve. Su un modello di cui servono le coperture costa un terzo dell'apertura
  piena [V, 3.3];
- **thread**: l'iteratore ne usa quanti se ne chiedono; ma sul file pigro cade (3.5), quindi b1 e c usano un thread.

## 3. Le prove

### 3.1 I campioni

| Nome | MB | Programma | Schema, unità | Georiferimento | Fonte e licenza |
|---|---|---|---|---|---|
| meridiana-misto | 0,2 | Meridiana | IFC4, m | latitudine, longitudine, mappa UTM 32N | esportazione di Meridiana (capannone piano con parapetto, casa a capanna, villa a padiglione, tettoia monofalda, 110 moduli, camino, impianto, evacuatore, albero) |
| meridiana-25 | 4,5 | Meridiana | IFC4, m | come sopra | esportazione di Meridiana: 25 capannoni, 2.900 moduli |
| bs-architecture | 0,14 | IFC manager for SketchUp | IFC4, mm | solo mappa, EPSG:32760, scala 0,001, asse X a 60° | buildingSMART, Sample-Test-Files, CC BY 4.0 |
| bs-hvac | 0,11 | idem | IFC4, mm | idem | idem: solo impianti |
| location | 2,8 | Revit 2020 | IFC4, mm | latitudine, longitudine, mappa EPSG:28992 (Amersfoort) | buildingSMART community, «Example project location», CC BY 4.0 |
| duplex | 2,3 | Revit 2011 | IFC2X3, m | latitudine, longitudine | buildingSMART community, Duplex Apartment, CC BY 4.0 |
| clinic-arch | 12,4 | Revit 2011 | IFC2X3, m | latitudine, longitudine | buildingSMART community, Medical-Dental Clinic, CC BY 4.0 |
| esplanades | 11,6 | ArchiCAD 22 | IFC2X3, mm | latitudine e longitudine al minuto; il sito posato in coordinate L-EST97 (538.451; 6.591.615 m) | buildingSMART community, Esplanades, CC BY 4.0 (c) Esplan |
| great-court | 3,6 | Grasshopper (Geometry Gym) | IFC2X3 | nessuno | IfcOpenShell/files, licenza non dichiarata: solo misurato |
| schependomlaan | 47,0 | ArchiCAD 18 | IFC2X3, mm | latitudine, longitudine | buildingSMART community, TU Eindhoven: uso scientifico e accademico, solo misurato |
| root-compleet | 8,5 (47 dentro lo zip) | ArchiCAD | IFC2X3 in .ifczip | idem | idem |
| clinic-plumbing | 53,3 | Revit 2011 | IFC2X3, m | latitudine, longitudine | Medical-Dental Clinic, impianti idraulici, CC BY 4.0 |
| clinic-plumbing-x4 | 230 | sintetico | IFC2X3 | idem | il precedente quattro volte nello stesso file (`misura_ifc.py --sintetico`), solo in locale |
| ios-infinite-loop, ios-timeout, ios-segfault, ios-proxy-36mb | 1,6; 0,2; 0,2; 34,6 | Revit, Simplebim | IFC2X3 | - | IfcOpenShell/files: i file che fecero girare all'infinito, rallentare o cadere IfcOpenShell; licenza non dichiarata, solo misurati |
| troncato, non-ifc, vuoto | 1,1; 0; 0 | sintetici | - | - | il Duplex tagliato a metà, un testo, un file vuoto |

### 3.2 Come si è misurato

- PC di Daniel: Windows 11, Intel i7-12700H (14 core, 20 thread), 32 GB; Python 3.12.6; IfcOpenShell 0.9.0.post1;
  shapely 2.2.0, numpy 2.5.4.
- Ogni prova è un processo a parte (`misura_ifc.py`), come nel programma: il tempo dentro il processo, il picco di
  memoria del processo (picco del working set, letto con l'API di Windows), il processo ucciso oltre 300 s o oltre
  8 GB. Tre ripetizioni, la mediana; i file sintetici e quelli rotti una volta sola.
- **Rumore**: durante le misure altri due agenti facevano girare le loro suite sullo stesso PC. I tempi sono quindi un
  po' più alti e un po' più variabili del PC a riposo [V: in quelle ore quattro prove di velocità della suite, del
  catalogo e dello scheletro, sono fallite una volta e passate la volta dopo]. Il confronto tra strade vale, perché le
  strade di uno stesso campione sono state misurate una dopo l'altra.
- I tempi comprendono l'importazione di IfcOpenShell (circa 0,1 s) e l'analisi in Python (piani e ostacoli).

### 3.3 Tempi e memoria

Mediana di tre prove, picco di memoria del processo.

| Campione | MB | apertura piena | apertura pigra | a | b8 | b1 | c | d |
|---|---|---|---|---|---|---|---|---|
| meridiana-misto | 0,2 | 0,17 s, 46 MB | 0,12 s, 46 MB | 0,40 s, 64 MB | 0,30 s, 64 MB | 0,32 s, 61 MB | 0,26 s, 54 MB | 0,23 s, 53 MB |
| meridiana-25 | 4,5 | 0,32 s, 74 MB | 0,19 s, 62 MB | 3,44 s, 102 MB | 0,77 s, 88 MB | 0,61 s, 80 MB | 0,41 s, 72 MB | 0,34 s, 72 MB |
| bs-architecture | 0,1 | 0,12 s, 46 MB | 0,11 s, 45 MB | 0,47 s, 67 MB | 0,23 s, 60 MB | 0,22 s, 60 MB | 0,24 s, 53 MB | 0,22 s, 53 MB |
| bs-hvac | 0,1 | 0,11 s, 46 MB | 0,10 s, 45 MB | 0,43 s, 65 MB | 0,20 s, 52 MB | 0,18 s, 52 MB | 0,24 s, 52 MB | 0,20 s, 52 MB |
| location | 2,8 | 0,21 s, 59 MB | 0,17 s, 54 MB | 20,38 s, 1300 MB | 0,77 s, 80 MB | 1,02 s, 72 MB | 0,42 s, 67 MB | 0,40 s, 66 MB |
| duplex | 2,3 | 0,20 s, 60 MB | 0,13 s, 54 MB | 2,58 s, 127 MB | 0,51 s, 74 MB | 0,28 s, 69 MB | 0,28 s, 62 MB | 0,31 s, 62 MB |
| clinic-arch | 12,4 | 0,68 s, 128 MB | 0,26 s, 91 MB | 18,50 s, 351 MB | 3,52 s, 159 MB | 5,18 s, 135 MB | 2,11 s, 130 MB | 1,17 s, 107 MB |
| esplanades | 11,5 | 0,75 s, 121 MB | 0,36 s, 83 MB | 28,34 s, 235 MB | 2,30 s, 136 MB | 4,90 s, 108 MB | 1,37 s, 106 MB | 1,21 s, 94 MB |
| great-court | 3,6 | 0,33 s, 68 MB | 0,25 s, 59 MB | 8,79 s, 124 MB | 0,35 s, 72 MB | 0,25 s, 67 MB | 0,32 s, 67 MB | 0,25 s, 67 MB |
| schependomlaan | 47,0 | 2,47 s, 336 MB | 0,89 s, 174 MB | 22,57 s, 601 MB | 4,67 s, 336 MB | 6,58 s, 207 MB | 3,27 s, 192 MB | 1,69 s, 177 MB |
| root-compleet | 8,5 | 2,45 s, 319 MB | 1,00 s, 169 MB | 31,48 s, 575 MB | 4,86 s, 319 MB | 5,71 s, 205 MB | 2,74 s, 189 MB | 1,50 s, 172 MB |
| clinic-plumbing | 53,2 | 3,89 s, 417 MB | 1,23 s, 245 MB | fermato a 300 s | 4,39 s, 417 MB | 1,81 s, 245 MB | 1,89 s, 245 MB | 1,78 s, 245 MB |
| clinic-plumbing-x4 | 230,1 | 23,80 s, 1556 MB | 8,57 s, 837 MB | fermato a 300 s | 14,74 s, 1556 MB | 7,63 s, 836 MB | 11,34 s, 837 MB | 10,10 s, 837 MB |
| ios-infinite-loop | 1,6 | 0,21 s, 56 MB | 0,14 s, 54 MB | 44,45 s, 237 MB | 4,28 s, 214 MB | 4,46 s, 216 MB | 0,75 s, 80 MB | 0,62 s, 79 MB |
| ios-timeout | 0,2 | 0,11 s, 46 MB | 0,10 s, 46 MB | fermato a 300 s | 0,67 s, 78 MB | 0,68 s, 77 MB | 0,25 s, 56 MB | 0,26 s, 56 MB |
| ios-segfault | 0,2 | 0,13 s, 46 MB | 0,12 s, 46 MB | 5,07 s, 128 MB | 0,23 s, 61 MB | 0,20 s, 60 MB | 0,20 s, 53 MB | 0,18 s, 53 MB |
| ios-proxy-36mb | 34,6 | 2,30 s, 248 MB | 0,64 s, 161 MB | 185,42 s, 1613 MB | 2,19 s, 248 MB | 0,79 s, 161 MB | 0,79 s, 161 MB | 0,87 s, 161 MB |
| troncato | 1,1 | 0,18 s, 52 MB | 0,13 s, 50 MB | 0,56 s, 74 MB | 0,32 s, 70 MB | 0,29 s, 67 MB | 0,30 s, 67 MB | 0,23 s, 57 MB |
| non-ifc | 0,0 | errore | errore | errore | errore | errore | errore | errore |
| vuoto | 0,0 | errore | errore | errore | errore | errore | errore | errore |

Letture:
- **a costa da 7 a 50 volte c** sui modelli veri. Il grosso sono i fori delle aperture e i tanti oggetti che al
  fotovoltaico non servono: sulla palestra di Revit 20,4 s e 1,3 GB per due coperture piane.
- **b8 contro b1**: con il file aperto per intero l'iteratore usa 8 thread; con l'apertura pigra uno solo. Sui modelli
  dove si fanno le pareti (clinic-arch, senza tetto) i thread contano (3,5 s contro 5,2 s); dove si fanno solo le
  coperture conta l'apertura (Schependomlaan: 4,7 s contro 6,6 s, ma 336 contro 207 MB).
- **c** è la più veloce dove ci sono coperture: legge dal file le estrusioni e i Brep senza IfcOpenShell e fa con
  l'iteratore solo il resto (ritagli, booleane). Sullo Schependomlaan legge direttamente 645 forme su 647.
- **d** è la più veloce in assoluto, ma non dà le falde.
- **L'apertura pigra** costa da un terzo alla metà dell'apertura piena, in tempo e in memoria (Schependomlaan: 0,89 s e
  174 MB contro 2,47 s e 336 MB). Sul .ifczip IfcOpenShell la ignora: estrae il file e lo apre per intero (codice di
  `ifcopenshell.open`); Meridiana lo estrae da sé e lo apre in modo pigro.

### 3.4 Che cosa ottiene Meridiana

Edifici, falde (quante inclinate), ostacoli trovati da ogni strada; b8 e b1 danno lo stesso.

| Campione | a | b | c | d |
|---|---|---|---|---|
| meridiana-misto | 4 ed., 8 falde (7 incl.), 8 ost. | 4 ed., 8 falde (7 incl.), 8 ost. | 4 ed., 8 falde (7 incl.), 8 ost. | 1 ed., 1 falde (0 incl.), 7 ost. |
| meridiana-25 | 25 ed., 25 falde (0 incl.), 50 ost. | 25 ed., 25 falde (0 incl.), 50 ost. | 25 ed., 25 falde (0 incl.), 50 ost. | 1 ed., 1 falde (0 incl.), 50 ost. |
| bs-architecture | 1 ed., 2 falde (2 incl.), 0 ost. | 1 ed., 2 falde (2 incl.), 0 ost. | 1 ed., 2 falde (2 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |
| bs-hvac | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. |
| location | 1 ed., 2 falde (0 incl.), 0 ost. | 1 ed., 2 falde (0 incl.), 0 ost. | 1 ed., 2 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |
| duplex | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |
| clinic-arch | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |
| esplanades | 1 ed., 16 falde (0 incl.), 29 ost. | 1 ed., 16 falde (0 incl.), 29 ost. | 1 ed., 16 falde (0 incl.), 29 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |
| great-court | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. |
| schependomlaan | 3 ed., 22 falde (14 incl.), 21 ost. | 3 ed., 22 falde (14 incl.), 21 ost. | 3 ed., 22 falde (14 incl.), 21 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |
| root-compleet | 3 ed., 22 falde (14 incl.), 21 ost. | 3 ed., 22 falde (14 incl.), 21 ost. | 3 ed., 22 falde (14 incl.), 21 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |
| clinic-plumbing | - | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. |
| clinic-plumbing-x4 | - | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. |
| ios-infinite-loop | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |
| ios-timeout | - | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |
| ios-segfault | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |
| ios-proxy-36mb | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. | 0 ed., 0 falde (0 incl.), 0 ost. |
| troncato | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. | 1 ed., 1 falde (0 incl.), 0 ost. |

Le piante di ciò che entra in Meridiana con la strada c (falde colorate per inclinazione, esclusioni in grigio, tipo di
tetto e quota di gronda su ogni edificio) sono in `20-prove/piante/`. In parole:
- **meridiana-misto**: i quattro edifici tornano con il loro tipo (piano con parapetto di 0,8 m, monofalda di 10°,
  capanna di 30° con le testate dove erano, padiglione di 25°), le quote di gronda, camino, evacuatore, impianto,
  albero [V, test di andata e ritorno].
- **bs-architecture** (SketchUp): due falde di 45° verso est e ovest, con le gronde a 1,9 e 3,3 m: non è una capanna
  che lo scheletro rifà, quindi falde libere. La copertura è appesa a un secondo IfcSite, fuori dall'edificio: viene
  assegnata all'edificio di cui copre pareti e solai.
- **location** (Revit 2020): la palestra in due corpi piani, a 6,39 e 3,60 m; i pannelli delle finestre alte non sono
  lucernari (stanno sotto il bordo della copertura) e restano fuori.
- **duplex** (Revit 2011): una copertura piana di 135 m² a 6,46 m.
- **clinic-arch** (Revit 2011): **nessuna copertura e nessun solaio** nel modello d'architettura (stanno nel modello
  strutturale): l'edificio viene dalle pareti, 2.624 m², piano alla quota della loro sommità.
- **esplanades** (ArchiCAD 22): la copertura piana di 994 m² a 16,97 m con il parapetto di 0,83 m, il torrino a 17,87
  m; 14 piccole coperture a quote loro (balconi, pensiline, 32 m² in tutto) lasciate fuori; i 175 pannelli solari già
  disegnati («Päikesepaneel», proxy) riconosciuti dal nome e lasciati fuori.
- **schependomlaan** (ArchiCAD 18): tre corpi a falde libere di 65° con gli abbaini piani, 22 falde, lucernari e
  parapetti sulle coperture.
- **great-court**: la copertura vetrata del British Museum è fatta di IfcPlate e IfcMember fuori da ogni edificio e
  da ogni IfcRoof: nessun edificio, detto («nessuna copertura, nessun solaio, nessuna parete»). È giusto: non è un
  tetto su cui posare moduli.
- **bs-hvac**, **clinic-plumbing** e il suo quadruplo, **ios-proxy-36mb**: solo impianti o oggetti generici, nessun
  edificio: detto.
- **ios-infinite-loop**, **ios-timeout**, **ios-segfault**, **troncato**: un edificio dalle pareti o dai solai che ci
  sono.

### 3.5 Le trappole trovate

| Trappola | Prova | Che cosa fa Meridiana |
|---|---|---|
| IfcOpenShell 0.9.0.post1: l'iteratore con più thread su un file aperto in modo pigro cade (Windows, «heap corruption» 0xc0000374) o non fa niente | [V] Schependomlaan con 20 thread: il processo cade in `initialize()`; Building-Architecture: 0 forme | sul file pigro un thread solo |
| L'iteratore con più thread lasciato a metà cade quando viene distrutto (segfault, uscita 139) | [V] `initialize()` con 20 thread, poi uscita: cade; con un thread no | l'iteratore si porta sempre fino in fondo |
| `.ifczip`: `ifcopenshell.open` estrae il file e lo apre per intero, senza `lazy` | [V] codice di `ifcopenshell.open`; root-compleet: apertura «pigra» 3,07 s contro 3,37 s della piena prima della correzione, 1,00 s contro 2,45 s dopo | lo zip si estrae prima, e si apre pigro |
| Revit 2020 scrive Est e Nord della IfcMapConversion in millimetri e dichiara i metri (MapUnit) | [V] location: 149.626.315 «m»; il README del campione dice 149.692 m | oltre la Terra in metri, si leggono come millimetri, e si dice |
| La conversione di mappa e il TrueNorth non dicono lo stesso nord | [V] bs-architecture: asse X della mappa a 60°, TrueNorth su +Y (anche nello studio 15) | il progettista sceglie nel riquadro, proposta la mappa |
| La copertura appesa a un secondo IfcSite, fuori dall'edificio | [V] bs-architecture | va all'edificio di cui copre pareti e solai (più di un terzo) |
| Il modello d'architettura senza coperture né solai | [V] clinic-arch | contorno e altezza dalle pareti |
| Le rampe delle scale sono IfcSlab LANDING | [V] clinic-arch: 3 «coperture» a 2,1 m | i LANDING non sono coperture |
| Un parapetto in quattro pareti: l'involucro convesso dei quattro è tutta la copertura | [V] meridiana-misto, prima della correzione | si uniscono solo gli ostacoli vicini che restano compatti (i pannelli di una fila), mai i parapetti |
| Coperture piane a qualche centimetro l'una dall'altra (guaina, lastre) | [V] esplanades: 14 pezzi a 16,10 m e la copertura a 16,97 m | sotto i 30 cm sono una copertura; i pezzi sotto 8 m² a una quota loro restano fuori, detti |
| Il sito posato in coordinate nazionali (L-EST97) | [V] esplanades: IfcSite a (538.451; 6.591.615) | latitudine e longitudine valgono per il punto del sito: si misura da lì |
| La latitudine di ArchiCAD e di FreeCAD è arrotondata al minuto o al secondo | [V] esplanades: 59°26', 24°45'; studio 15: FreeCAD tronca al secondo | la mappa, se c'è, vince; altrimenti il progettista sposta gli edifici |
| Su Windows il python.exe di un ambiente virtuale è un lanciatore: l'interprete è un suo figlio, il lanciatore tiene 4 MB qualunque cosa faccia il figlio | [V] la memoria vista dal processo padre durante le misure: 4 MB per ogni prova; un figlio di 214 MB sotto un lanciatore di 4 MB | la finestra guarda la memoria del processo e dei suoi figli (`procmem.rss(pid, tree=True)`); uccidere il lanciatore chiude anche il figlio [V] |
| Un file tagliato rimanda a oggetti che non ci sono | [V] troncato: `AttributeError` su un posizionamento senza punto | posizionamento mancante = origine, la forma che non si fa contata e detta |

## 4. Robustezza

| Caso | File | Che cosa succede [V] | Che cosa fa Meridiana |
|---|---|---|---|
| File tagliato a metà | troncato (Duplex) | IfcOpenShell lo apre senza dire nulla; mancano gli oggetti a cui altri rimandano. Il lettore cadeva su un posizionamento senza punto (`AttributeError`), prima della correzione | posizionamento mancante = origine, forme mancanti contate: un edificio dai solai rimasti e «32 elementi di cui non si è potuta fare la forma» |
| Un testo con l'estensione .ifc | non-ifc | «Unable to parse IFC SPF header» | «non è stato possibile leggere il file», nella finestra; niente aggiunto |
| File vuoto | vuoto | «Unable to open file for reading» | idem |
| Il muro che faceva girare IfcOpenShell all'infinito | ios-infinite-loop | con la 0.9 finisce: a in 44 s, c in 0,75 s (il muro letto dal file) | un edificio dalle pareti |
| Il muro lentissimo da fare | ios-timeout | a fermato a 300 s; c in 0,25 s | idem |
| Il solaio che faceva cadere IfcOpenShell | ios-segfault | con la 0.9 non cade più | un edificio dal solaio |
| Il proxy di 36 MB che faceva cadere IfcOpenShell | ios-proxy-36mb | a: 185 s e 1,6 GB; c: 0,79 s e 161 MB | nessun edificio, detto |
| Gli impianti di un edificio (53 MB) | clinic-plumbing | a fermato a 300 s tre volte su tre; c in 1,9 s | nessun edificio, detto |
| Un file enorme (230 MB) | clinic-plumbing-x4 | apertura piena 23,8 s e 1,56 GB, pigra 8,6 s e 837 MB; a fermato a 300 s; c 11,3 s, quasi tutto apertura | la barra si muove senza percentuale mentre il file si apre; nessun edificio, detto |
| IfcOpenShell che cade o si blocca | simulato nei test (`os._exit(139)`, un processo che dorme) | il processo finisce senza risultato, o passa il tempo | un secondo tentativo con le sole forme semplici; altrimenti il motivo nella finestra, che resta viva [V, test] |
| Il processo che mangia memoria | simulato nei test (300 MB contro 100 permessi) | - | fermato, con il motivo [V, test] |

Altri casi:
- **Unità**: millimetri (bs-architecture, location, esplanades, schependomlaan) e metri (duplex, clinic): la forma letta
  dal file si scala con l'unità del progetto, quella dell'iteratore esce già in metri [V, stesse quote con le due
  strade].
- **Georiferimento**: con la mappa su un sistema UTM (WGS84, ETRS89, RDN2008, IGM95) la posizione viene dalla mappa;
  con una mappa su un sistema che Meridiana non converte (Amersfoort, Gauss-Boaga) dalla latitudine e longitudine del
  sito, e si dice; senza niente, gli edifici vanno nell'origine del sito. Il nord dalla mappa (asse X più convergenza)
  o dal TrueNorth; se non tornano entro un grado, sceglie il progettista [V, test].
- **Modelli enormi**: il tempo di apertura cresce con il file (vedi clinic-plumbing-x4); oltre i 180 s, o oltre metà
  della memoria, la finestra ferma la lettura e dice di esportare solo l'edificio.

## 5. Confronto e voti

Voti da 1 a 5, 5 il migliore; «fatica» 5 = poca; «voto» il giudizio complessivo.

| Famiglia, strada | Efficacia per il FV | Velocità | Robustezza | Fatica | Voto | Note |
|---|---|---|---|---|---|---|
| IfcOpenShell, a: tutto | 5 | 1 | 2 | 5 | 2 | 2,6-31 s e fino a 1,3 GB sui modelli d'architettura, oltre 300 s sugli impianti; più oggetti fatti, più occasioni di cadere |
| IfcOpenShell, b8: il necessario, 8 thread | 5 | 3 | 3 | 4 | 3 | file aperto per intero: memoria alta sui file grandi |
| IfcOpenShell, b1: il necessario, pigro | 5 | 3 | 3 | 4 | 3 | lento dove si fanno molte pareti |
| **IfcOpenShell, c (+b)**: forme lette dal file, il resto all'iteratore, pigro | **5** | **5** | **4** | **3** | **5** | la più veloce con le falde; la lettura diretta delle forme è codice nostro da tenere |
| IfcOpenShell, d: solo riquadri | 2 | 5 | 4 | 4 | 2 | niente falde: serve solo come anteprima o come ultima risorsa |
| Il processo a parte (per qualunque strada) | - | - | **5** | 4 | **5** | un crollo o un ciclo infinito non toccano la finestra; Annulla vero; si misura la memoria [V, test] |
| IfcConvert (la riga di comando di IfcOpenShell) in OBJ o glTF, poi lettura | 3 | 2 | 3 | 3 | 2 | stesse cadute dell'iteratore, nessuna classe IFC né Pset nei file in uscita, un file in più [I] |
| web-ifc (That Open Company, C++ e WASM, MPL-2.0) | 4 | 4 | 3 | 1 | 2 | veloce, ma senza Python: servirebbe Node.js o WASM accanto al programma [I] |
| xBIM (.NET) | 4 | 3 | 3 | 1 | 1 | serve il runtime .NET; licenza CDDL [I] |
| Un lettore STEP nostro, in Python | 3 | 3 | 3 | 1 | 1 | niente booleane né curve: le forme con ritagli restano fuori (2 su 647 nello Schependomlaan, di più in altri modelli [I]); tutto a carico nostro |
| FreeCAD senza interfaccia | 3 | 1 | 2 | 2 | 1 | usa IfcOpenShell, ma 800 MB e un altro programma |
| SDK commerciali (ODA IFC SDK) | 5 | 4 | 4 | 1 | 1 | a pagamento, C++, licenza incompatibile con un programma GPL distribuito [I] |
| Chiedere all'architetto un IFC filtrato (solo edificio) | 5 | 5 | 5 | 5 | 4 | non dipende da noi; resta il consiglio nei messaggi di Meridiana |

**Raccomandazione: IfcOpenShell con la strada c, la b come riserva per le forme non semplici, l'apertura pigra, in un
processo a parte con tempo e memoria massimi e il secondo tentativo senza iteratore.** È quella costruita (sezione 6).

## 6. Che cosa è stato costruito

- `src/meridiana/ifc_read.py`: la lettura (strade a, b, c, d e «semplice», cioè c senza iteratore). Struttura dagli
  IfcRel (non dagli attributi inversi, che sul file pigro costano tutto il file); candidati: coperture, poi solai, poi
  pareti; ostacoli filtrati prima dalla quota del loro posizionamento (le migliaia di tubi dei piani sotto non si
  guardano); piani delle falde: facce rivolte in alto raggruppate per piano (1°, 5 cm), tagliate dove un altro piano sta
  sopra, tenute sopra 1 m² e 50 cm di larghezza.
- `src/meridiana/ifc_import.py`: posizione e nord (3.5), il sistema del progetto, il riconoscimento dei tetti (piano,
  una falda, capanna o padiglione rifatti dallo scheletro e confrontati falda per falda, altrimenti falde libere), le
  esclusioni e il parapetto, il riassunto (preso, approssimato, lasciato fuori), una sola modifica.
- `src/meridiana/ifc_worker.py`: il processo a parte; `src/meridiana/procmem.py`: la memoria di un processo e dei suoi
  figli.
- `src/meridiana/ui/ifc_import.py`: `IfcReading` (QProcess, barra, Annulla, 180 s, metà della memoria fino a 8 GiB,
  secondo tentativo) e `IfcImportDialog` (dove vanno gli edifici, il nord, l'anteprima, le tre liste).
- `src/meridiana/ifc_export.py`: l'esportazione IFC4 (studio 15, 5.2). I moduli scritti come entità dirette e non con
  le chiamate di `ifcopenshell.api`: sui 25 capannoni con 2.900 moduli lo script intero (posa, stringhe, file) 3,5 s
  contro 11,3 s del prototipo, l'esportazione da sola 2,8-3,2 s [V, due prove, PC carico]; il file è valido per
  `ifcopenshell.validate` [V, test].
- Formato del progetto e configurazione: **invariati** (gli edifici importati sono edifici di Meridiana come gli altri).

## 7. Limiti e cose aperte

- **Cortili e fori**: Meridiana non ha ancora i fori nei contorni (compito 16a, passo 4): un edificio a corte entra con
  il contorno esterno, i fori delle falde si contano tra gli approssimati.
- **Falde libere**: una falda che non scende verso un suo lato (un triangolo ruotato) prende la pendenza verso il lato
  più vicino: lo scarto si dice.
- **Il terreno**: la quota zero è il piano dell'edificio a quota zero o appena sotto; con piani interrati o quote
  assolute il progettista controlla l'altezza di gronda.
- **Sistemi di mappa**: solo UTM su WGS84, ETRS89, RDN2008, IGM95. Gauss-Boaga e ED50 vogliono il cambio di datum:
  oggi si usa la latitudine del sito. Da fare se un architetto italiano li usa [I].
- **Il programma impacchettato**: il processo a parte si lancia con il Python che fa girare Meridiana
  (`python -m meridiana.ifc_worker`); un pacchetto PyInstaller dovrà avviarlo con un argomento del proprio eseguibile.
- **Da provare sul PC di Daniel**: un IFC vero di un architetto (non quelli di commessa: restano sul server), la lettura
  con il puntatore e la finestra veri, la vista 3D degli edifici importati (offscreen la scena 3D non si disegna).

## Fonti

- IfcOpenShell 0.9.0.post1, PyPI: https://pypi.org/project/ifcopenshell/0.9.0.post1/ ; il codice di `ifcopenshell.open`
  (parametri `lazy`, `bypass_types`, il ramo `.ifcZIP`) e di `ifcopenshell.geom.iterator`, letti nel pacchetto
  installato.
- buildingSMART, Sample-Test-Files: https://github.com/buildingSMART/Sample-Test-Files (CC BY 4.0, commit
  80d976a9b193a26a8e928c3e79bff67af1de68a8).
- buildingSMART community, Community-Sample-Test-Files: https://github.com/buildingsmart-community/Community-Sample-Test-Files
  (CC BY 4.0 per Duplex, Clinic, Esplanades, Example project location; Schependomlaan per uso scientifico e accademico).
- IfcOpenShell, file di prova: https://github.com/IfcOpenShell/files
- web-ifc: https://github.com/ThatOpen/engine_web-ifc (MPL-2.0); xBIM: https://github.com/xBimTeam/XbimEssentials
- IFC4 ADD2 TC1, IfcMapConversion e IfcProjectedCRS: https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/
- Karney, C. F. F. (2011), «Transverse Mercator with an accuracy of a few nanometers», J. Geodesy 85, 475-485
  (le serie di Krüger usate in `geo.to_utm` e `geo.from_utm`).
- Studio 15, sezione 5.2 (esportazione, prototipo del lettore, regole per i file di terzi).
