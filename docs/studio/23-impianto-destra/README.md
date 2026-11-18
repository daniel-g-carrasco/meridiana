# Studio 23: la scheda di destra della fase Impianto (R296, R297, R298, R307, R308)

Fable FP, 02/11/2026. Solo studio: nessuna riga di programma cambiata. I bozzetti sono in `bozzetti.html` (una pagina
sola, si apre nel browser); le foto dello stato di oggi in `foto/`. [V] verificato (come), [I] dedotto.

## 1. Il compito della scheda, da capo

La scheda di destra risponde alle domande del progettista nell'ordine del lavoro (R277). Per ogni sottoscheda:

| Sottoscheda | Le domande, in ordine | Comandi che servono qui |
|---|---|---|
| **Pannelli** | Quale sottocampo ho selezionato e com'è posato (fila, passo, orientamento)? Quanti moduli e kWp in tutto? | la scheda del sottocampo (le Proprietà prestate); senza selezione, una frase e i totali |
| **Inverter** | Quali inverter ho, quanti, come si chiamano, in che ordine? Per ciascuno: potenza, MPPT, quante stringhe porta, è a posto? Qual è il DC/AC di ognuno e dell'impianto? | Catalogo (aggiungi), Scegli in automatico; su ogni inverter: rinomina, sposta, scheda tecnica, stringa questo inverter, svuota, togli |
| **Accumulo** | Che batteria, quante, accoppiamento AC o DC? | Configura |
| **Stringhe** | Su ogni ingresso dell'inverter in lavorazione: quante stringhe, su quante ne prende, vanno bene? Quale stringa è quale (nome, colore in pianta, moduli)? La stringa scelta regge le verifiche, con quali numeri e articoli? | Stringa in automatico, Disegna una stringa, Cancella tutte; «+» su un ingresso; sulla stringa scelta: ridisegna, sposta, elimina |

«Stringhe» sta dentro Inverter perché ha bisogno dei due: moduli e inverter (R277, decisione 2c dello studio 22).

## 2. Che cosa non va oggi (foto in `foto/`, prese offscreen su un impianto di prova: 736 moduli da 450 W, 2 × Huawei SUN2000-100KTL-M2 da 100 kW e 10 MPPT, 36 stringhe; testi in inglese perché l'ambiente di prova non carica le traduzioni)

1. **Pannelli chiuso resta alto tutta la colonna** (`foto/02-pannelli-chiuso.png`, schermata 35 di Daniel). [I] Causa dal
   codice: `PlantSide._opened` dà lo *stretch* 1 della colonna alla sezione aperta; chiudendola con un clic nessun'altra
   si apre, lo stretch resta suo e il gruppo vuoto si allunga. Serve uno stretch finale della colonna quando nessuna
   sezione è aperta.
2. **Il testo libero tocca il bordo** (`foto/01-pannelli-aperto.png`, `foto/06-accumulo.png`, schermata 36). [V] Il
   layout delle tre sezioni ha margini 0 (`inner.setContentsMargins(0, 0, 0, 0)`) e la frase di Pannelli e «No battery»
   di Accumulo sono messe lì direttamente; i gruppi interni dell'inspector hanno invece il loro padding. È un problema
   di regola, non di frase: il corpo di una sezione deve avere i margini del sistema grafico (12 ai lati, 8 sopra e sotto).
3. **Inverter in tre gruppi che dicono la stessa cosa** (`foto/04-inverter-pagina-intera.png`, `05-...`): «Inverter
   attivi» (testo), «Inverter in lavorazione» (un menu a tendina più due righe), «Tutti gli inverter» nascosto sotto un
   pulsante in fondo alle stringhe, con l'elenco per *modello* (× 2) e non per inverter fisico. Non si rinomina, non si
   ordina, non si vede la scheda tecnica, si toglie solo il modello intero.
4. **La tabella degli ingressi** (`foto/03-inverter-colonna.png`): 7 colonne in 340 px, «MPP…» troncato, Isc nascosta,
   angoli squadrati (il gruppo le toglie la cornice morbida, `soft_edges=False`), lo stato solo come segno. Sotto, l'elenco
   ripete per ognuno dei 10 ingressi le stesse cinque righe («7-25 in series, max 1 in parallel, 2 physical inputs share
   this MPPT, 18 kWp, 2 strings to be checked»): 20 righe uguali prima di arrivare alle stringhe.
5. **I comandi in fondo**: Proponi, Completa, Ricomincia stanno dopo 60 righe di elenco, con la frase «i comandi seguenti
   valgono per tutto l'impianto»; «Dimensiona» è dentro «Tutti gli inverter»; strategia e moduli in serie in un gruppo
   a parte, «Proposta e verifiche».
6. **Il rapporto DC/AC**. [V] Dal codice: il campo «DC/AC ratio when sized by itself» (0,50-2,00, passo 0,05, default
   1,10, `plant_page.py` riga 384) lo usa solo `_size_inverters` (il modello con il rapporto «più vicino a quello
   chiesto», `window.py` riga 4224) e `InverterSpec.sized_for` per l'inverter fittizio quando nessuno è scelto
   (`energy/components.py` riga 467). Sull'impianto vero il rapporto è calcolato (`energy/plant.dcac`) e mostrato sulla
   scala del taglio, ma il taglio compare solo dopo il calcolo dell'anno: l'impianto di prova a 1,66 non riceve alcun
   avviso. Daniel dice «di solito 110-130»; PVsyst consiglia 1,25-1,30 per perdite di sovraccarico trascurabili
   (studio 06, righe 2005 e 2863, dall'aiuto di PVsyst); nel settore 1,1-1,3 è il valore tipico citato (glossario
   SurgePV, ricerca web); OpenSolar segnala sotto 0,75 e sopra 1,50 (ricerca web).

## 3. Come lo fanno gli altri (3 ricerche web, 02/11/2026; il resto dagli studi 06 e 08 già in `docs/studio`)

- **PVsyst** [V studio 06, righe 1204-1219 e 1293-1294; studio 08, righe 1593-1605]: nel dialogo System ogni
  sotto-campo (sub-array) ha inverter, numero di MPPT usati, moduli in serie e stringhe in parallelo; il «Pnom ratio»
  è mostrato con un colore e un avviso; gli ingressi sbilanciati vogliono due sub-array trascinati sugli inverter;
  per SolarEdge e Huawei il dialogo «String configuration» costruisce l'elenco degli **inverter fisici** e vi
  attribuisce le stringhe, modificabile. [V web] Un tutorial di Canal Solar conferma la pratica di un sub-array per
  MPPT con conteggi diversi (canalsolar.com.br/en/pvsyst-inverter-with-multiple-mppt-inputs/).
- **Aurora Solar** [V web, help.aurorasolar.com, articolo 13139582090131 «Stringing and Connecting»]: AutoStringer
  si lancia dal pulsante in basso nella barra di destra, **si sceglie l'inverter** e si stringano i moduli
  tracciati; usa i dati elettrici di moduli, inverter e ottimizzatori. [I] L'unità di lavoro è l'inverter, come
  chiede Daniel.
- **HelioScope** [V web, help-center.helioscope.com, articolo 8198326521491 «Stringing in HelioScope»]: lunghezza
  minima e massima della stringa dalle temperature (ASHRAE) o data a mano; stringatura automatica per MPPT con un
  limite di ripartizione 70/30 della potenza fra i due MPPT; i moduli che non entrano restano fuori e lo dice.
- **SolarEdge Designer**: non trovato nelle 3 ricerche; non ne parlo.

## 4. Proposta (dettagli e testi in `bozzetti.html`)

1. **Pannelli e Accumulo**: chiuso = solo intestazione, lo spazio libero va in fondo alla colonna; il testo libero
   in stile `description` con i margini del corpo della sezione; sotto la frase i totali dell'impianto (moduli, kWp,
   sottocampi).
2. **Inverter: un elenco solo, per inverter fisico** (bozzetto I-A, schede): numero, nome modificabile (F2 o doppio
   clic), modello · kW · MPPT, stringhe · moduli · kWp · DC/AC suo con il segno di stato; maniglia per l'ordine (o
   Sposta su/giù); menu ⋯ con Rinomina, Sposta, Scheda tecnica, Stringa questo inverter, Svuota le sue stringhe, Togli.
   La scheda evidenziata è l'inverter che Stringhe mostra. In testa i totali (kW AC, kWp, DC/AC colorato), sotto
   «Catalogo…» e «Scegli in automatico…». Spariscono «Inverter attivi», «Inverter in lavorazione», «Tutti gli
   inverter» e il pulsante «Gestisci tutti gli inverter».
3. **Stringatura di un inverter** (bozzetto S-1): dal menu ⋯ si apre un pannellino sotto la scheda: moduli da usare
   (selezionati in pianta, un sottocampo, quelli senza stringa), **rapporto DC/AC voluto** (1,25 proposto, verde fra
   1,10 e 1,30), moduli in serie (suggerito), percorso; anteprima con quello che Meridiana farà e perché si ferma
   («DC/AC 1,51: sopra l'1,25 chiesto…»); Applica = un passo di Annulla. La selezione a riquadro dei moduli (altro
   agente) alimenta «moduli da usare».
4. **Stringhe**: il bozzetto B (griglia di ingressi a schede, i 10 MPPT come i morsetti sull'inverter, stato a colpo
   d'occhio, stringa scelta evidenziata) con la «stringa scelta» del riquadro F (barre di margine Uoc, Umpp, Isc e
   verifiche con articolo). Alternativa seria il D (tabella piatta raggruppata con i numeri). I comandi in testa.
5. **Parole**: Dimensiona → **Scegli in automatico…**; Proponi + Completa + «Proposta e verifiche» → **Stringa in
   automatico…** con le opzioni dentro (su cosa, sostituisci o completa, percorso, moduli in serie, DC/AC);
   Ricomincia → **Cancella tutte le stringhe**; «Proposta e verifiche» → **Condizioni delle verifiche** (solo
   temperature). I testi completi sono nella tabella in fondo a `bozzetti.html`.

## 5. Domande aperte (poche)

1. **Stringhe: B (schede) o D (tabella)?** Raccomando B: con 10 MPPT i numeri in colonna non entrano in 360 px (lo
   mostra la tabella di oggi); i numeri stanno nella stringa scelta e nel suggerimento. D se Daniel vuole leggere Uoc e
   Umpp di tutte le stringhe senza cliccare.
2. **Stringatura automatica: pannellino inline (S-1) o finestrella (S-2)?** Raccomando S-1 per l'inverter singolo e la
   stessa finestrella S-2 per «tutto l'impianto» dalla barra; stessi campi, stesso testo.
3. **Il DC/AC fuori da 1,10-1,30 va solo colorato o anche segnalato nelle Verifiche?** Raccomando colore e frase sulla
   riga dell'inverter subito, e la verifica vera (percentuale tagliata) solo dopo il calcolo dell'anno, com'è oggi:
   PVsyst stesso lo tratta come criterio di dimensionamento, non come errore.
4. **Rinominare o riordinare gli inverter cambia i nomi delle stringhe (1.3.2 → 2.3.2)?** Raccomando sì con un avviso
   nella barra di stato: il numero della stringa è la posizione fisica, non un'etichetta.

## Cosa non ho fatto

- Nessuna modifica al programma, nessuna prova nuova: solo le foto con uno script di prova (`foto_impianto.py` nello
  scratchpad, non nel repo).
- SolarEdge Designer non verificato. La tabella degli ingressi oggi non la rifaccio: è sostituita dai bozzetti.
