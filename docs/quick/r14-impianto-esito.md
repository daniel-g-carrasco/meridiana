# Ramo r14-impianto: scheda destra di Impianto e controllo dei confini (05/11/2026)

Parole di Daniel: «a volte i testi nella scheda a destra sforano fino a sovrapporsi al punto più basso dell'intera finestra. In particolare andrebbe fatto un controllo di confini, come avevamo fatto in versione non quick» (R406); «come mai inoltre la scheda a destra di Impianto sembra non centrare nulla con quella non quick?» (R407).

Legenda: [V] visto o misurato, con come; [I] dedotto.

## Perché Impianto era diversa (R407)

La gerarchia c'era già, tre sezioni con dentro gli inverter: la struttura era stata portata, il disegno no. Tre cause, in ordine di quanto si vedevano.

1. **La sezione era fatta a mano, e i gruppi interni non sapevano di essere dentro un gruppo.** [V] `PlantSide.qml` usava un `Rectangle` con un pulsante, non `M.Section`, e non diceva `sectionControl`. `M.Section` decide di essere «annidato» (R343: un titolo su una riga sottile, niente cornice) guardando i genitori: non trovando niente, Stringhe, Condizioni e Sottocampo selezionato si disegnavano con cornice e fascia grigia e con i loro margini, una scheda dentro la scheda. Lo stesso per il modulo Proprietà prestato ai Pannelli (`PropertyForm`, `CollapsibleSection`). È quello che dava a colpo d'occhio l'impressione di un'altra scheda.
2. **`PlantInverters.qml` era riassunta dal vecchio, non copiata.** [V] Confronto riga per riga con `ui/plant_page.py`, elenco sotto. Mancavano la riga di stato delle stringhe e il riassunto accanto all'inverter; i testi erano altri («Scegli dal catalogo…» invece di «Aggiungi un inverter dal catalogo…»), le condizioni erano numeri nudi invece della frase; le campiture dei segni di stato erano monocrome; le stringhe avevano un pallino invece del quadratino; il campo temperatura stava sotto l'etichetta.
3. **La pagina non aveva il bilancio dello spazio dei Widgets.** [V] Nessun posto tenuto per la barra (R100), nessuna aria per le sfumature, nessuna sfumatura. Le schede degli ingressi di una riga non erano alte uguali.

Il presentatore (`plant_presenter.py`) aveva già parte dei testi, ma la pagina non li usava.

## Cosa è cambiato

- `PlantSide.qml`: riscritta su `PlantSide` dei Widgets, con la stessa testa di `M.Section`, il `?` con il suo bordo e la stessa divisione dello spazio (`room_for`).
- `PlantInverters.qml`, `PlantInverterCard.qml`, `PlantInputCards.qml`, `PlantDiagram.qml`, `PlantClipScale.qml`, `PlantMargin.qml`, nuovi `PlantFormRow.qml` (`make_form`: etichetta e campo sulla stessa riga finché ci stanno), `PlantCommand.qml` (`wrap_button`, parole e tooltip del comando della finestra), `PlantStringMenu.qml` (`_string_actions`), `PlantStrip.qml` (la striscia in alto a destra, con la stringa scelta e quella in disegno, R70, R298, R181).
- `plant_presenter.py`: tutte le frasi di `ui/plant_page.py`, con gli stessi msgid. La prova `tests/quick/impianto/test_plant_side.py` le confronta con le funzioni dei Widgets.
- `Controls/ScrollPage.qml`: `FitArea` con `QScrollArea`. Riusabile.
- Le frasi del backend (`plant.message`) vanno sulla barra di stato: stavano sotto le sezioni, ed era proprio il difetto di Daniel (sotto).

### Inventario, stato per stato

Foto affiancate, Widgets a sinistra e Quick a destra, in `docs/quick/confronto/r14-impianto/`.

| Stato | Elemento nei Widgets | Prima in Quick | Ora |
|---|---|---|---|
| Pannelli, niente selezione | frase, sezione alta quanto serve | ok | uguale (`01-pannelli.png`) |
| Pannelli, sottocampo | Proprietà a gruppi annidati | gruppi con cornice | annidati (`02-sottocampo.png`) |
| Inverter | totali, tooltip con `describe` | senza tooltip | uguale (`03-inverter.png`) |
| Inverter | scheda: disco con maniglia, nome, 2-3 righe, «⋯» | disco scuro, carattere al posto della maniglia | uguale, maniglia a sei punti |
| Inverter | menu: Rinomina F2, Sposta su, Sposta giù, Scheda tecnica, Stringa, Svuota, Togli | altro ordine, senza tasti né separatori | uguale |
| Inverter | ottimizzatori: frase, «Ottimizzatori…», scelta, «indietro» sulla riga | due controlli senza frase, «indietro» nel menu | uguale |
| Inverter | «Aggiungi un inverter dal catalogo…», «Scegli gli inverter in automatico…» con tooltip del comando | altre parole, senza tooltip | uguale |
| Inverter | rapporto voluto su una riga, scala | sopra, scala con colori diversi | uguale |
| Stringhe | stato, inverter mostrato a metà riga, riassunto a destra | senza stato né riassunto, scelta a tutta riga | uguale (`04-stringhe.png`) |
| Stringhe | schede in due colonne, alte uguali in una riga, un ingresso solo a metà | altezze diverse | uguale |
| Stringhe | testata: nome, segno a colori, «+» con il suo tooltip | segno monocromo, «+» carattere | uguale |
| Stringhe | riga: quadratino, nome, moduli, tooltip con le tensioni, clic, doppio clic, destro | pallino, tooltip diverso | uguale |
| Stringhe | schema unifilare: casella tratteggiata per l'ingresso libero, riquadro in disegno | pulsante «+», niente riquadro | uguale (`05-schema.png`) |
| Stringa scelta | identità con segno, barre, controlli a segni e linee, fonte, Ridisegna, Sposta in…, Elimina | scelta dell'ingresso sempre aperta, altre parole | uguale (`06-stringa-scelta.png`) |
| Condizioni | etichetta a capo e campo accanto, frase | campo sotto, numeri nudi | uguale |
| Sottocampo selezionato | solo con un sottocampo scelto, non con una fila; colonna unica | anche con la fila | uguale |
| Accumulo | frase, «Configura accumulatore…» | «Configura…» | uguale (`07-accumulo.png`) |
| Progetto vuoto, inverter senza stringhe | stesse frasi | | uguale (`08-vuoto.png`) |
| Barra della fase | striscia a destra: riassunto, stringa scelta, stringa in disegno | assente | sostituita dal riepilogo di R419, sotto |

Gesti fatti sui due programmi con messaggi nativi sul desktop separato [V]: clic su una scheda (l'inverter mostrato diventa quello in entrambi), «⋯» (stesse voci, stessa disposizione), clic su una riga di stringa (stessa stringa scelta, sezione Inverter aperta, stessa posizione di scorrimento), passaggio del mouse.

### Differenze rimaste, tutte scritte

- **Pannelli:** nei Widgets le righe «Modulo» e «Azimut» hanno 9 px di margine in più, residuo di un layout Qt senza margini azzerati. Non l'ho riportato: è in `PropertyEditor` per tutte le fasi. [V] Lo stesso in Modellazione.
- **Scheda 1 px più in basso** [V]: il `M.Card` mette il corpo 1 px sotto. Comune a tutte le schede, dentro la tolleranza di `CONTESTO.md`.
- **Vista Tabella nel menu delle stringhe:** c'è in Quick e non nei Widgets. L'ho lasciata, con la scelta A + 2 (R394) già applicata da `r13-fasi`: decide Daniel se la vuole.

## Il controllo dei confini (R406)

**Come era nei Widgets.** [V] Nessuno strumento unico: un widget non disegna fuori dal genitore, e `QFormLayout`, `FitArea` e `QScrollArea` fanno il resto; le prove lo fissano caso per caso (`tests/widget/test_nested_groups.py`, `test_properties.py`, `test_string_list.py`, `test_fades.py`). In Quick nessuno impedisce a un `Text` di stare sopra la barra di stato, quindi serve qualcuno che guardi: lo strumento è la traduzione del principio, non di un codice.

**Lo strumento.** `tests/quick/confini.py`: `audit(window)` cammina l'albero e, applicati i ritagli dei genitori, segnala `fuori-finestra`, `barra-di-stato`, `fuori-contenitore`, `tagliato`, `sforato`, `sovrapposto`, `scheda-grande`, `senza-barra`, `senza-sfumature`, `deformato`, `margini`. Una segnalazione deve esserci ancora un momento dopo: una transizione non conta. `python tests/quick/confini.py` percorre gli stati, un processo per ogni misura e pannelli, in finestre vere su un desktop nascosto; con `--platform offscreen` senza finestre.

**La prova.** `tests/quick/sistema/test_confini.py`: `TheCheck` prova ogni regola su una finestrella che la viola, `TheWindow` cammina la finestra vera (`MERIDIANA_CONFINI=tutto` per tutta la matrice).

**Il difetto di Daniel.** [V] riprodotto sul ramo di partenza: la frase che il backend dell'Impianto dice alla fine di una proposta stava in `PlantSide.qml` sotto le tre sezioni, fuori dal conto dello spazio. A 1100x700 scende sulla barra di stato e sui suoi pulsanti. Foto prima e dopo: `docs/quick/confronto/r14-impianto/12-difetto-daniel-prima-e-dopo.png`. Il controllo la trova sul ramo di partenza come `barra-di-stato`, `fuori-contenitore`, `fuori-finestra` e `sovrapposto`. Ora la frase va sulla barra di stato in una riga, come dice la finestra dei Widgets, e la sezione non ha più niente sotto.

**Casi trovati e chiusi.** Sul ramo di partenza, a 1600x960 e 1000x640, chiaro, testo normale, offscreen: 38 stati su 88 con segnalazioni.

| Caso | Dove | Come si è chiuso |
|---|---|---|
| Testo sulla barra di stato, fuori dalla scheda e dalla finestra | Impianto | frase sulla barra di stato |
| Liste che scorrono senza sfumature: 13, in 45 stati | Impianto, risultati, Relazione, Impostazioni, File, catalogo, accumulo | **comune:** `M.ScrollBar` porta da sola `EdgeFades`, con il fondo che trova sotto la lista; le barre proprie di Impostazioni, File e risultati sostituite |
| Lista senza barra | dettagli del catalogo | barra |
| Testo di un campo sopra il pulsante accanto | ricerca del sito | **comune:** `M.TextField` ritaglia il suo testo |
| Testo di una scelta più largo del campo | Relazione, Impianto | **comune:** `M.ComboBox` con elide. Nei Widgets è tagliato senza puntini: scritto come differenza |
| Comando a capo tagliato | Proprietà ed Economia, pannello stretto | **comune:** altezza dal testo disposto, `wrap_button` |
| Controllo schiacciato, pannello stretto | Proprietà | **comune:** il pannello destro si ferma a 284 px, 237 in Impianto, come i Widgets (`minimumSizeHint`, R341); prima a 120 |
| Orologio tagliato dal bordo della vista | barra del sole, vista 3D stretta | ciò che non ci sta va via intero |

**Risultato.** [V] Finestre vere Direct3D 11 sul desktop separato, progetto di Rho: **1584 stati a scala 1** (chiaro e scuro, testo normale e grande, 1600x960, 1000x640, 800x560, pannelli normali, stretti e larghi; 6 fasi, sottostati di Modellazione e Impianto, tutte le pagine di File e Impostazioni, le finestre di dialogo), **176 a scala 2** (scuro, testo grande, 1600x960 e 800x560, pannelli normali e stretti): **zero segnalazioni**. Ultimi ritocchi dopo la matrice a scala 1: la soglia delle colonne del riepilogo e due regole del controllo, ricoperti dalla matrice a scala 2 e dalle prove.

**Eccezioni, tutte con il motivo in `EXCEPTIONS`:** le etichette di un disegno in pianta si sovrappongono allontanando la vista, come nei Widgets; la parola sulla faccia del cubo è scalata dalla vista.

**Cosa non guarda.** Il controllo legge rettangoli: non vede un colore sbagliato né un elemento coperto da uno opaco. Le finestre di dialogo le apre e misura, ma il «doppio mento» di R403 è un giudizio che resta da fare a occhio. Le proporzioni rispetto ai Widgets le dà il confronto a foto, non il controllo.

## Altre schede destre

Foto `11-altre-schede-a.png` e `-b.png`, Widgets a sinistra.

- **Corretto:** Producibilità, Consumi, Bilancio avevano il posto della barra occupato dal contenuto e il primo gruppo 5 px più in alto; la chevron delle sezioni era un'icona sottile, ora è quella dei gruppi.
- **Producibilità, da fare:** nei Widgets «Inverter» è un riquadro con il pulsante a sinistra, in Quick un titolo in grassetto con il pulsante a tutta riga. Nella barra manca la zona a destra con «Ombre dell'orizzonte lontano» e «Ombre degli ostacoli della scena»: **due opzioni che in Quick non si vedono**.
- **Consumi, da capire:** nella foto Quick dice «un impianto da 0.0 kWp» e «Automatico: Domestico» dove i Widgets dicono 358,6 kWp e «Media tensione». [I] Finché l'anno non è calcolato Quick non usa i moduli posati. Manca anche il suggerimento nel Codice POD; in più c'è un «Calcola» a tutta riga.
- **Bilancio:** Accumulo aperto in Quick, chiuso nei Widgets: [I] è la memoria dei gruppi chiusi, da controllare.
- **Relazione:** capitoli spenti in Quick perché l'anno non era ancora calcolato, non è una differenza. Piccoli spostamenti delle caselle, 2-6 px.

## Riepilogo nella barra (R419)

Daniel: «in quest'area non voglio questa roba. Voglio un gruppo con angoli arrotondati e sfondo leggermente più scuro [...] che contenga in tempo reale quanti moduli ho messo in totale e a quale potenza di picco corrisponde, + dati inverter messi, quale potenza, quale collegata, quale scollegati, ottimizzatori [...]»; «e ovviamente in stessa area si vedono i dati di quelli selezionati». Solo in Quick, non è fedeltà ai Widgets. Foto: `09-riepilogo.png`.

- **Stile:** `Controls/InfoGroup.qml`, riusabile: la superficie e il raggio del riquadro di un inverter (`Radius.CARD` sul colore `field`), colonne di «etichetta valore» nel testo piccolo. Tante righe quante ne stanno; il resto nel tooltip della colonna. La misura viene da fuori, mai da ciò che dice: niente salta.
- **Dati:** `backend/plant_summary.py`. Nessun valore calcolato in QML. I moduli posati si contano dai risultati di posa già in mano, quindi seguono subito; ciò che è collegato viene dall'impianto costruito dal suo lavoro in un altro thread. Una raffica di segnali si legge una volta sola, al giro successivo.
- **Contenuto:** moduli posati, collegati, scollegati con un segno di attenzione se ce ne sono, stringhe; inverter (numero e modello se è uno), potenza AC con DC/AC, ingressi usati e liberi, ottimizzatori se ci sono, altrimenti energia tagliata dopo il calcolo.
- **Selezione, in un posto suo che resta vuoto senza selezione:** stringa in disegno, moduli selezionati, stringa, ingresso, inverter, modulo, fila, sottocampo. Ho aggiunto il clic su una scheda di ingresso, che non esisteva, per poter selezionare un ingresso.
- **Stretta:** sotto 590 px le colonne diventano due e gli inverter lasciano il posto alla selezione finché c'è; se la barra lascia meno di 300 px il riquadro va sopra la pianta, come `place_strip` dei Widgets, con una colonna sola se serve.
- **Selezione a finestra:** il costo era quasi tutto fuori dal riepilogo. [V] Tre cause, tolte: ogni selezione faceva ricostruire tutte le schede del pannello (`plant.changed`), le sovrapposizioni si disegnavano due volte, i moduli accesi andavano e tornavano attraverso QML come migliaia di oggetti. Ora sono percorsi nativi uniti. Misura con 5150 moduli a finestra, input nativo, macchina occupata da altri processi: giro più lungo da 0,66 s a circa 0,3 s. **Non è sotto i 30 ms**: è un colpo solo al rilascio, non durante il gesto. Il resto è il disegno delle stringhe (`wiring_scene`) e i segnali verso QML. Il calcolo del riepilogo per 16 000 moduli selezionati resta sotto 30 ms (prova) e `refresh` 0,5 ms.

## Ottimizzatori sulla pianta (R424)

Foto: `10-ottimizzatori.png`. Con ottimizzatori la linea di stringa va da unità a unità, un quadratino del colore della stringa per unità (anche con 2 moduli per unità), cavi sottili dall'unità ai suoi moduli. Con un modulo solo per unità il quadratino sta fuori centro, così il cavo si vede. `string_paths.optimizer_units` dà la geometria, `plan_wiring` unisce i percorsi per colore una volta sola finché nulla cambia, `optimizerBatch` li disegna: pochi percorsi nativi, nessun elemento per modulo. Da lontano resta la sola linea. Legenda sulla pianta quando ci sono ottimizzatori. [V] Foto viste in chiaro e in scuro.

Limite: la stringa con ottimizzatori non usa le corsie affiancate di `legs_together`: linee di stringhe vicine possono sovrapporsi.

## Tooltip della pianta (R425)

Prima in Quick il tooltip del modulo non c'era proprio. Ora `moduleTip` in `Plan.qml` sta al puntatore e dice il modulo sotto il puntatore: «Modulo 3 di 8», l'ottimizzatore se c'è, la frase della stringa dei Widgets; per un modulo senza stringa la frase dei Widgets. Il testo viene da una tabella che l'impianto riempie quando è costruito, chiesta quando cambia il modulo, mai a ogni passo.

[V] `tests/quick/percorsi/test_native_plant.py`, messaggi nativi sul desktop separato. **Sul solo ramo questa prova si salta da sé**: il piano non riceve l'hover, è la causa comune di `r14-correzioni` (0c3715fa). Provata su un'unione di prova con quel ramo: 5 su 5, testo diverso sui tre moduli e sulla stringa dopo, 80 ms dopo il passaggio; sparisce uscendo; tornando subito ricompare senza attesa.

Vale con lo strumento Seleziona. **3D:** nei Widgets e in Quick nessun tooltip sui moduli, solo il contorno al passaggio, dopo 80 ms di fermo: non ho aggiunto niente.

## Unione con `r14-correzioni`

Provata in una cartella temporanea, quattro conflitti piccoli:

- `Controls/Menu.qml`: tenere `fades: false` e il loro `visible` sulla barra;
- `Controls/ToolTip.qml`: tenere sia `placed` sia il loro `pressed`;
- `Shell/Workbench.qml`: `Math.round(Math.max(root.panelMinimum, Math.min(rightExtent, width*0.34)))`;
- `Plant/PlantInverters.qml`: tenere la mia e portare il loro `pressed: discMouse.pressed` in `PlantInverterCard.qml`.

## Morte a vuoto offscreen

[V] Con `QT_QPA_PLATFORM=offscreen` e il render loop `threaded` il processo muore con `access violation` nei primi secondi: 8 volte su 8 con la finestra di Impianto aperta su un progetto collegato, e 6 su 6 sul ramo di partenza. Con `QSG_RENDER_LOOP=basic`, 8 su 8 vivi. Senza finestra, tre thread nello stesso calcolo: 6 su 6 vivi. Gli stack mostrano i lavori in `load_pvlib` e in scipy, ma il filo che muore non ha il GIL: [I] è il filo di disegno. [V] Su finestre vere Direct3D sul desktop separato non è mai successo in una ventina di avvii. Secondo le parole di `CLAUDE.md` è «tests only», finché non si vede altrove. Le mie prove e `confini.py` offscreen usano `basic`, con il motivo scritto; importate nella suite, valgono per tutto il processo.

## Suite finale

`tests/quick` offscreen con `QSG_RENDER_LOOP=basic` e senza le prove native, per non aprire finestre fuori dal desktop separato:

- **ramo di partenza `r13-unita`:** 625 prove, 5 fallite;
- **questo ramo:** 660 prove, 6 fallite: le stesse 5 (`test_tables` del peso del carattere, due di `test_registry`, `test_pedigree`, `test_shell` con `requestImage`) più `test_report`, un limite di 0,1 s misurato 0,265 con la macchina carica, che da sola passa.

In un'esecuzione precedente, con altri lavori in corso, due prove differenziali hanno dato errore (`test_differential`, `test_properties_differential`): da sole passano e nell'ultima suite non si sono ripetute. [I] Carico o stato condiviso del processo, non ho trovato la causa. La prova nativa `test_native_plant` è girata sull'unione di prova, 5 su 5. `test_native` non l'ho rilanciata.

Resta non in stage `docs/quick/collaudo/run-native.json`: l'ha riscritto la suite, non è un mio cambiamento e non l'ho riportato indietro.

## Semplificazioni proposte

Nessuna toglie qualcosa. Da guardare, con foto:

- **Vista Tabella nel menu delle stringhe** (in più): tenerla o toglierla? `05-schema.png` mostra il menu.
- **`M.ComboBox` con i puntini** invece del testo tagliato: `04-stringhe.png`.
- **Riga «Modulo» dei Pannelli senza i 9 px in più dei Widgets:** `02-sottocampo.png`. Lì erano un margine dimenticato di Qt; lascerei così.
- **Clic su una scheda di ingresso:** nei Widgets non fa niente, qui la seleziona, serve a R419.
