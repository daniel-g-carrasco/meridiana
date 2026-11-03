ESITO: verde per i modelli; resta una prova delle stringhe rossa fuori ambito

# Modelli 3D, secondo giro, R368

## Metodo e foto

[V] Il ramo era già allineato a `base-r10`. Non c'erano commit R368 precedenti. Il formato resta 25: nessun tipo è stato
aggiunto, rinominato o migrato. Sono stati toccati soltanto `props.py`, `mesh.py`, la galleria e le sue prove, oltre alle
foto e a questo esito. `po/it.po` e `docs/richieste.md` non sono stati modificati.

[V] La galleria ora inquadra ognuno dei 25 tipi da vicino. Le foto iniziali in chiaro e scuro sono in
`docs/revisioni/foto/modelli-R02/prima/`; quelle dei modelli cambiati sono in `dopo/`, con lo stesso nome. Le scene
`auto`, `lineari`, `galleria` e `realistica` aggiungono viste frontali e dall'alto. Le quattro foto `reale-*` vengono dalla
finestra del programma, non dalla sola galleria.

[V] Ho aperto e confrontato tutte le foto iniziali nei due temi. Ho aperto le foto finali dei modelli cambiati e delle scene
d'insieme. Il giudizio seguente viene dalle foto, non soltanto dalle prove verdi.

## Cosa è cambiato

- **Auto**: profilo laterale estruso con passaruota concavi veri, non ruote appoggiate a un parallelepipedo. Berlina e SUV
  hanno cabine diverse: la prima più bassa e inclinata, il secondo più alto e verticale. Vetri scuri, montanti, cofano e
  baule, specchietti, maniglie, fari, fanali e griglia. Ruote a 24 lati, cerchio chiaro sulla faccia esterna e mozzo scuro.
- **Pino**: eliminati i tre coni separati. Una sola chioma a ombrello, larga, con lobature radiali e verticali; fusto nudo,
  inclinato e aperto in rami sotto la chioma. La vista frontale della galleria mostra bene la ramificazione.
- **Corrimano**: la sezione passa da 0,025 a 0,05 m. L'esperimento nella stessa scena ha mostrato che il vecchio spessore
  era sotto-campionato dalla mappa d'ombra e produceva macchie; quello nuovo dà un'ombra pulita. La membrana da 0,02 m e
  l'opzione senza corrimano non cambiano.
- **Altra vegetazione**: latifoglia e arbusto hanno chiome non più perfettamente rotazionali; conifera continua invece di tre
  coni sovrapposti; siepe con sommità e spigoli smussati; palma con tronco curvo e fronde pennate, archi e foglioline.
- **Persone**: torso affusolato, arti con gomiti e ginocchia, mani arrotondate, scarpe e postura camminata. Il worker ha un
  elmetto con tesa. Altezze, larghezze e profondità restano quelle richieste.
- **Ostacoli**: camino con bocca scura incassata e cornice; sfiato con base, condotto, sotto scuro e cappello; lucernario con
  vetro inclinato; macchina con due ventole e griglia; serbatoio con base, spallamento e fasce; vano scala con porta e gradino;
  ascensore con due porte metalliche. I livelli delle griglie e delle porte sono separati: le prime foto finali avevano moiré
  da facce coplanari, corretto e coperto da due nuove prove.

## Cosa ho lasciato

- `dome_skylight`: cupola e base erano già leggibili da vicino.
- `antenna` e `dish`: asta, elementi, specchio e supporti erano già distinti e senza intersezioni visibili.
- `opening` e `other`: restano volumi generici, perché non rappresentano un oggetto specifico da dettagliare.
- Il vecchio costruttore puntuale `obstacle("walkway")` conserva la sua forma; il camminamento realmente usato come percorso
  passa da `mesh.path_triangles()`, dove è stata corretta l'ombra.

## Triangoli prima e dopo

[V] Conteggi ottenuti dagli array `positions` dei costruttori predefiniti, divisi per tre. La voce `walkway` qui è il modello
puntuale predefinito; una spezzata ha un conteggio dipendente dal suo contorno, ma il cambio di spessore non aggiunge triangoli.

| Tipo | Prima | Dopo |
|---|---:|---:|
| broadleaf | 104 | 200 |
| conifer | 104 | 344 |
| pine | 368 | 560 |
| shrub | 104 | 200 |
| hedge | 64 | 92 |
| palm | 120 | 664 |
| chimney | 24 | 72 |
| vent | 64 | 192 |
| skylight | 24 | 24 |
| dome_skylight | 60 | 60 |
| plant | 56 | 292 |
| antenna | 108 | 108 |
| dish | 156 | 156 |
| tank | 80 | 384 |
| stairwell | 36 | 84 |
| elevator | 36 | 72 |
| walkway | 156 | 156 |
| opening | 12 | 12 |
| other | 12 | 12 |
| adult | 264 | 520 |
| walking | 264 | 520 |
| child | 264 | 520 |
| worker | 296 | 600 |
| compact | 816 | 1176 |
| suv | 816 | 1176 |

Limiti di famiglia e massimo effettivo:

| Famiglia | Limite prima | Limite dopo | Massimo effettivo dopo | Motivo |
|---|---:|---:|---:|---|
| Alberi | 400 | 700 | 664, palma | fronde pennate e chiome irregolari |
| Persone | 300 | 600 | 600, worker | arti articolati, torso e tesa |
| Auto | 850 | 1600 | 1176 | passaruota, ruote a 24 lati e dettagli |
| Ostacoli | 200 | 400 | 384, tank | fasce, spallamento e sezioni più rotonde |

[V] Scena ripetibile di 200 oggetti, ottenuti ciclando su tutti i 25 tipi nello stesso ordine prima e dopo:

| Misura | Prima | Dopo |
|---|---:|---:|
| Triangoli | 35.264 | 65.568 |
| Array posizioni, normali e colori | 3,632 MiB | 6,753 MiB |
| Costruzione in questo run | 1,217 s | 2,288 s |

I tempi sono misure singole su questo laptop, non un benchmark statistico. Il costo maggiore viene da auto, persone e palma.

## Prove

- [V] Prove mirate `nucleo.test_props`, `nucleo.test_linear_props`, `nucleo.test_props_project`: **63 prove verdi**.
  Comprendono dimensioni anche non predefinite, array finiti, normali, assenza di triangoli degeneri, volumi dei componenti,
  ombre contenute, rotazioni, palette e scene della galleria.
- [V] Ogni nuovo comportamento geometrico ha avuto una prova rossa prima dell'implementazione. Le correzioni visive successive
  hanno mantenuto quelle prove e sono state fotografate di nuovo.
- [V] Controllo aggiuntivo di tutti i 25 tipi a 0,5 e 2 volte le misure predefinite: **50 casi con ingombro esatto, nessun
  errore**.
- [V] `python -m ruff check src tests tools`: verde.
- [V] `tools/compile_po.py`: catalogo generato correttamente, senza modificare `po/it.po`.
- [V] Gruppo `nucleo`: **1242 prove verdi, 5 saltate** in 80,794 s.
- [V] Gruppo `calcoli`: **294 prove verdi** in 33,858 s.
- [V] Gruppo `formati`: **96 prove verdi** in 2,653 s.
- [V] Gruppo `widget`: **793 prove verdi, 1 saltata** in 213,064 s.
- [V] Gruppo `finestra`: **383 prove, 2 fallimenti** in 1015,130 s. `test_assistant_chat...test_without_the_local_server...`
  fallisce sulla visibilità del pannello, ma ripetuto da solo è verde in 2,208 s. `test_window.Stringing...given_up` trova
  «The project changed during string search» invece di «all 4 strings cleared» e resta rosso anche da solo in 3,607 s. È lo
  stesso ambito e lo stesso messaggio del fallimento già registrato nel primo giro; nessun file delle stringhe è stato toccato.
- [V] `finestra.test_props_workflow`: **4 prove verdi** in 5,150 s.

## Prova reale

[V] Script guidato dentro `tools/real_session.sh`, con runtime privato. Ha aperto `capannone()` con 15 oggetti: quattro
alberi, due auto, tre persone, cinque ostacoli sul tetto e un camminamento con corrimano. Il layout di 104 moduli è finito,
la vista 3D è disegnata e la finestra è stata chiusa. Foto complete e ritagli della vista in chiaro e scuro nei file
`reale-chiaro-*` e `reale-scuro-*`. Il portale documenti del desktop è rimasto montato.

## Nuovi msgid

Nessuno. `po/it.po` non è stato toccato.

| msgid | msgstr |
|---|---|

## Cosa non mi convince ancora

- La resa resta volutamente low poly e piatta: su latifoglia, arbusto e pino si vedono ancora facce e una struttura radiale.
  È molto migliore dei paralumi iniziali, ma non è una chioma fotorealistica.
- Nella finestra reale gli oggetti sono piccoli quando si inquadra tutto il capannone; i dettagli vanno giudicati dalle foto
  ravvicinate della galleria, che usa la stessa `View3D`.
- Non ho verificato Windows né tempi di fotogramma su una scheda grafica diversa. La misura di 200 oggetti sopra riguarda
  geometria, memoria degli array e costruzione Python, non il frame rate della GPU.

## Commit

- `db4007c`: galleria ravvicinata e foto iniziali.
- `0191bcb`: auto e pino.
- `9edf2ba`: ombra del corrimano.
- `9f36954`: vegetazione e persone.
- `833429e`: ostacoli e separazione delle superfici.
- `2cd37dc`: scene complete e foto dalla finestra reale.
