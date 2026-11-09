# Risultati Quick: contratto di integrazione

04/11/2026. Modulo pronto nel ramo `r12-grafici`; avvio e shell restano del ramo `r12-sistema`.

## Installazione Python

In `QuickWindow.__init__`, dopo la creazione di `engine`, `bridge` e `shell`, prima di caricare QML:

```python
from meridiana.quick.backend.charts_controller import install_results

self.results = install_results(self.engine, bridge=self.bridge)
self.results.actionRequested.connect(self.shell.trigger)
```

`install_results` registra `Meridiana.ChartBackend`, aggiunge il percorso dei moduli QML e pubblica il controller come proprietà di contesto `results`. Il motore possiede e mantiene vivo il controller. Ripetere l'installazione sullo stesso motore restituisce lo stesso oggetto. La distruzione del motore scollega il controller; si può chiamare anche `self.results.close()` durante la chiusura, prima di `engine.deleteLater()`.

L'installazione non modifica la sessione, non calcola l'energia, non interroga PVGIS e non registra un nuovo comando `compute`: usa quello già collegato a `bridge.recompute` dalla shell.

## Pagine caricabili per URL

| Pagina | File relativo a `qml/Meridiana/Shell/` | Dati |
|---|---|---|
| Produzione | `../Charts/ProductionPage.qml` | `results.production` |
| Consumi | `../Charts/ConsumptionPage.qml` | `results.consumption` |
| Economia | `../Charts/EconomicsPage.qml` | `results.economics` |
| Riepilogo accumulo | `../Charts/StoragePage.qml` | `results.storage` |

I quattro componenti sono registrati anche in `Meridiana.Charts 1.0`. Sono wrapper di sei righe sul medesimo `ResultsPage`: legano `pageData` e inoltrano `actionRequested`. Non duplicano la UI. Ogni istanza mantiene autonomamente linguetta, scorrimento e grafici già preparati.

[V] Nel `Workbench.qml` di `r12-sistema` letto il 04/11 ci sono solo `planSource` e `view3dSource`, non URL per i risultati. Il centro mostra ancora `Prototype.YearChart` in Produzione e il segnaposto nelle altre fasi. App e shell non sono stati modificati da questo ramo per rispettare l'ownership. L'installazione Python e il caricamento delle pagine centrali sono i due collegamenti da applicare nel ramo sistema dopo il merge.

Esempio di sostituzione del grafico prototipo e dei segnaposto nel contenitore centrale; mantiene ogni pagina dopo la prima visita:

```qml
Repeater {
    id: resultPages
    model: [
        { phase: "production", source: Qt.resolvedUrl("../Charts/ProductionPage.qml") },
        { phase: "consumption", source: Qt.resolvedUrl("../Charts/ConsumptionPage.qml") },
        { phase: "economics", source: Qt.resolvedUrl("../Charts/EconomicsPage.qml") }
    ]
    delegate: Loader {
        required property var modelData
        anchors.fill: parent
        anchors.margins: Theme.layout.PAD
        visible: root.phase === modelData.phase
        active: visible || item !== null
        source: modelData.source
    }
}
```

La shell deve aggiornare anche il riferimento diagnostico `chartItem`, che oggi punta all'id del `YearChart` rimosso. Ad esempio può esporre `resultPages.itemAt(0).item` dopo la creazione del primo Loader. Non sostituire i contenuti di Modellazione, Impianto o Relazione. Accumulo appartiene alla sezione Impianto: il suo wrapper è un riepilogo, gli editor restano separati.

Se il ramo sistema introduce proprietà URL configurabili, gli stessi quattro file sono già caricabili senza modifiche; non è necessario un altro host dei risultati.

## API e stati

`ResultsController` espone quattro proprietà `QVariantMap`: `production`, `consumption`, `economics`, `storage`, ciascuna con il proprio segnale. La forma delle mappe è quella di `charts_data`: tessere, schede, grafici, tabelle, record, formule, riferimenti, limiti e stati vuoti.

Proprietà aggiuntive:

- `busy`: preparazione dei dati Quick in corso oppure lavoro segnalato dal Bridge.
- `error`: errore dell'adattatore o errore generico del Bridge. Un errore delle verifiche non invalida l'anno valido e rimane visibile dopo la sua pubblicazione.
- `stale`: confronto degli input con la chiave dell'ultimo anno mostrato, con le stesse chiavi di layout attese di `ProjectSession.energy_outdated()`. La chiave viene conservata anche se il Bridge registra un risultato vuoto dopo un errore. Un errore da solo non implica che gli input siano cambiati; senza sessione il controller non inventa lo stato di obsolescenza. Le tre pagine ripetono questo valore nel campo `stale`.
- `revision`: numero delle pubblicazioni complete dell'adattatore, utile per le prove. Non è la revisione del file di progetto.

Metodi per altri host, da chiamare sul thread GUI:

```python
controller = install_results(engine, session=session)
# Oppure, senza una sessione collegata:
controller = install_results(engine)
controller.update_results(energy_result)  # EnergyResult o EnergyResult.as_dict()
controller.update_settings(project.economics)
controller.update_error("errore del calcolo")
controller.update_error("")              # ripristina le note originali delle pagine
```

`update_results` accetta i risultati del nucleo già disponibili. Converte produzione, consumi ed economia in un `QRunnable` sul pool globale. Pubblica le tre mappe insieme sul thread GUI, prima di emettere i segnali. Le generazioni superate vengono ignorate. I DataFrame ricevuti devono rimanere in sola lettura dopo la pubblicazione, come quelli di `ProjectSession`; non sono copiati sul thread GUI.

`update_settings` aggiorna solo il riepilogo accumulo. `update_error` riguarda un errore dell'anno/adattatore, conserva i dati precedenti e ripristina le note quando l'errore viene cancellato. Gli errori generici del Bridge, comprese le verifiche, seguono un canale separato: non usare `update_error` per inoltrarli manualmente.

Il Bridge reale pubblica anche un risultato vuoto quando il calcolo fallisce. Il controller riconosce questo caso dalla notifica `energy`, dall'errore del Bridge già impostato e dall'assenza di simulazione, consumi ed economia: mantiene l'ultimo anno leggibile. Un errore delle verifiche con risultati presenti non passa per questo percorso.

Con `attach_session`, il controller segue `energy`, `file`, i temi di input energetici e i layout. Selezione e rinomina non ricreano le pagine. Un nuovo file azzera immediatamente i dati del precedente e rende innocue le risposte ancora in viaggio. `attach_bridge` collega inoltre `stateChanged` per stato occupato ed errori. Il controller non usa `bridge.year`, che contiene soltanto il riepilogo giornaliero del prototipo: legge `bridge.session.energy`, l'intero risultato.

I getter restituiscono solo dati già preparati. Zoom, scorrimento, cambio della linguetta e ridimensionamento non richiamano il nucleo né l'adattatore. I chiamanti Python non devono modificare direttamente i dizionari restituiti.

## Comandi

I wrapper chiamano `results.requestAction(action)`. Il controller emette `actionRequested` e traduce l'id locale `choose_battery` nel comando reale `battery_catalog`; `compute` rimane invariato. La connessione Python alla shell mostrata sopra completa il percorso. Il gestore del catalogo batterie deve essere registrato dal componente Impianto; se manca, vale il comportamento «non disponibile» già previsto da `ShellController.trigger`.

## Verifiche

[V] `test_controller.py` usa il vero anno della fixture PVGIS registrata. Controlla proprietà Qt e binding QML vivi, tessera reale in `ProductionPage`, inoltro del comando, pubblicazione atomica, errore del worker, reset file con risposta tardiva, temi della sessione, assenza di conversioni nei getter e import senza Widgets.

[V] Regressione sul Bridge reale: una risposta di `_checks_finished` con `Recorded check failure` mentre l'anno viene adattato non lascia le pagine vuote; l'anno viene pubblicato e l'errore resta visibile. La prova era rossa prima della separazione dei canali.

[V] Seconda regressione sul Bridge reale: `_finished` con dizionario risultati vuoto e `Recorded compute failure` mantiene le tessere dell'anno precedente. Il controller conserva anche la sua chiave input: una modifica dei prezzi successiva all'errore rende correttamente obsoleti quei valori.

Le prove del controller creano `QApplication` tramite gli strumenti condivisi, così possono convivere nello stesso processo con il differenziale Widgets. Screenshot e misure del renderer sono documentati dal coordinatore; questo contratto non dichiara il collegamento già applicato all'avvio ufficiale.

[V] Ultima esecuzione congiunta: 25 test in 20,923 s, OK; lint dei nuovi file Python verde. Controllati i sorgenti nuovi: nessun U+2014.
