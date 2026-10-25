# Revisione Kimi 2: durata degli oggetti, thread e segnali

Data: 25/10/2026. Ramo: `kimi-revisione`.

## Metodo e limiti

Ho esaminato i `QRunnable`, i `QProcess`, i timer e le connessioni con lambda in `ui/window.py`, `ui/tileloader.py`,
`ui/quick_image.py`, `ui/theme.py`, `ui/properties.py`, `ui/assistant_chat.py`, `ui/assistant_local.py`,
`ui/update_dialog.py`, `ui/variants.py`, `ui/catalog_dialog.py`, `ui/voice.py`, `ui/ifc_import.py`,
`ui/report_3d.py` e nei loro chiamanti. Ho letto le prove di questi componenti.

Le riproduzioni sono state fatte con Python 3.14 e PySide6 6.12, `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH=src`
della copia `meridiana-kimi` e cartelle XDG temporanee. Nessuna finestra è comparsa sullo schermo. Le eccezioni
sono state raccolte con `sys.excepthook`; `deleteLater()` è stato seguito dall'invio esplicito di `DeferredDelete`.

**Limite**: offscreen Qt Quick non disegna la scena 3D. Posso verificare stati Python, chiamate e rilasci, non la
correttezza delle risorse RHI su una GPU reale. Le prove sulle immagini 3D della relazione usano un processo a sé
(`tests/widget/test_report_3d.py:18-66`), ma non sostituiscono una chiusura ripetuta sulla finestra reale.

## Osservazioni, dalla più grave

### 1. Le lambda dei job globali possono richiamare la finestra dopo la sua distruzione

- **File e righe**: `src/meridiana/ui/window.py:4256-4262` per IFC, `:4516-4524` per gli aggiornamenti;
  `src/meridiana/ui/update_dialog.py:27-40` per `CheckJob`. Per contrasto, i collegamenti bound sono a
  `window.py:2611`, `:2939-2940` e `:3503`.
- **Che cosa succede**: `CheckJob` e `ExportIfcJob` vivono nel pool globale, non come figli della finestra. Le loro
  lambda catturano `self`. Quando la finestra viene distrutta, il job può ancora emettere: la lambda non ha il
  ricevitore Qt della finestra come contesto e prova a usarla. `_cancel_ifc()` interrompe il lavoro, ma un job già
  all'ultimo passo può ancora emettere `step` e `done`.
- **Scenario concreto A**: si chiede «Aiuto > Cerca aggiornamenti», la risposta di rete è lenta e la finestra viene
  chiusa prima che arrivi. Alla risposta, `_update_answer` chiama `tell` sul wrapper C++ di `MainWindow` già
  distrutto.
- **Scenario concreto B**: si esporta un IFC e si chiude la finestra quando il job sta per finire. Il segnale `step`
  raggiunge la barra di avanzamento già distrutta; `done` raggiunge poi il timer della stessa barra.
- **Gravità**: alta. È un uso dopo distruzione riprodotto, con possibile eccezione nella chiusura del programma o
  di una finestra mentre un'altra continua a elaborare eventi.
- **Prova A**: [V] sonda con `updates.latest_release` bloccata su due `threading.Event`, finestra chiusa ed eliminata,
  poi risposta rilasciata. Esito: `RuntimeError: libshiboken: Internal C++ object (MainWindow) already deleted.`
- **Prova B**: [V] sonda con un `ExportIfcJob` finto, ma con segnali e avvio reali, già all'ultimo passo. Dopo la
  distruzione della finestra: `QProgressBar already deleted` e `QTimer already deleted`.
- **Controllo di contrasto**: [V] lo stesso scenario con `LayoutJob`, il cui `done` è collegato al metodo bound
  `_layout_done`, non ha prodotto eccezioni. Quindi non tutti i job hanno questo difetto.
- **Correzione proposta**: eliminare queste lambda, non aggiungere soltanto controlli sparsi. Portare `manual` nel
  `CheckJob` ed emetterlo con il risultato, così `done` può collegarsi direttamente a `_update_answer`. Per IFC,
  sfruttare il vincolo «un solo lavoro alla volta»: conservare percorso e chiave del lavoro corrente e collegare un
  metodo bound `_ifc_export_done(out)` che chiama `_ifc_exported`. I metodi bound vengono scollegati con il
  ricevitore. Aggiungere le due prove di chiusura descritte sopra.
- **Rischio della correzione**: basso per i collegamenti, medio per i dati aggiunti ai segnali. Mantenere un valore
  predefinito per eventuali altri usi di `CheckJob` e non cambiare il formato del risultato IFC.

### 2. La chiusura non cancella PDF e anteprima in corso

- **File e righe**: `src/meridiana/ui/window.py:3430-3437` espone `_cancel_report`, ma `closeEvent` a `:4644-4652`
  non lo chiama e non chiude `preview_run`; i generatori sono creati a `:1326-1348` e `:3338-3373`. La pulizia del
  file temporaneo è nel `finally` di `src/meridiana/ui/report.py:596-601`.
- **Che cosa succede**: i timer hanno correttamente la finestra come contesto, quindi non continueranno dopo la sua
  distruzione. Però `closeEvent` accetta senza chiamare `generator.close()`: `report_run` e `preview_run` restano
  valorizzati finché il Python non li raccoglie. Il `finally` che chiude il painter e toglie `.part` non è quindi
  garantito nel momento della chiusura.
- **Scenario concreto**: durante «Esporta la relazione», si chiude la finestra dopo la prima pagina. Finché un
  riferimento mantiene viva la finestra, il file `relazione.pdf.part` resta sul disco e il generatore resta aperto.
  Lo stesso vale per un allegato aperto dall'anteprima.
- **Gravità**: media. Lascia risorse e file temporanei oltre la chiusura; l'esito visibile dipende dalla raccolta
  degli oggetti Python, non da una cancellazione esplicita e deterministica.
- **Prova**: [V] sonda con generatori reali sospesi su uno `yield`, uno con un file `.part` nel suo `finally` e uno
  per l'anteprima. Dopo `win.close()`: entrambi gli attributi erano ancora presenti, il file esisteva e il
  `finally` dell'anteprima non era stato eseguito. I generatori sono poi stati chiusi dalla sonda per pulire.
  [V] `report.py` conferma che la rimozione di `.part` avviene soltanto entrando nel `finally`.
- **Correzione proposta**: in `closeEvent`, prima di accettare, fermare `preview_soon`, chiudere e annullare
  `preview_run`, e richiamare la stessa cancellazione dell'esportazione usata dal pulsante. Separare una funzione
  interna silenziosa dal messaggio «Report stopped», così la chiusura non scrive messaggi superflui. Provare che
  `.part` sparisce, il vecchio PDF resta intatto e nessun passo successivo viene eseguito.
- **Rischio della correzione**: basso, ma `generator.close()` deve avvenire sul filo principale, dove painter e PDF
  sono stati creati. Verificare anche il registro dei calcoli: se un CSV è già stato scritto, il significato di
  «nothing written» va mantenuto coerente senza cancellare file preesistenti.

### 3. Il nuovo tentativo di una tessera usa il caricatore dopo la distruzione

- **File e righe**: `src/meridiana/ui/tileloader.py:132-154`, soprattutto `QTimer.singleShot` a `:149`;
  `QNetworkAccessManager` è figlio del caricatore a `:59`.
- **Che cosa succede**: dopo una risposta che non è un'immagine valida, un timer senza contesto cattura il
  `TileLoader`. Se il caricatore viene distrutto durante il secondo di attesa, il callback ricostruisce la coda e
  chiama `_pump`, che usa `self.net` già distrutto.
- **Scenario concreto**: una tessera del server nazionale risponde con un documento d'errore; prima del nuovo
  tentativo si chiude il progetto o la finestra. Al timer, il programma prova una nuova richiesta sul manager morto.
- **Gravità**: media. È lo stesso tipo di corsa già corretto in `SystemAccent`, qui con eccezione confermata.
- **Prova**: [V] sonda con una risposta finta non immagine e `RETRIES` reale di un secondo. Dopo `deleteLater()` del
  caricatore e l'elaborazione del timer: `RuntimeError: ... QNetworkAccessManager already deleted.` La coda non
  mostra la richiesta perché `_pump` si interrompe prima di completarla.
- **Correzione proposta**: passare `self` come contesto a `QTimer.singleShot`, mantenendo la lambda con il tile.
  In alternativa, un `QTimer` figlio, singolo e riutilizzato. Aggiungere una prova «errore, elimina prima del
  tentativo, nessuna chiamata a `sys.excepthook`» accanto a `tests/widget/test_tile_loader.py`.
- **Rischio della correzione**: basso. Con il caricatore vivo il tentativo resta identico; con quello distrutto il
  nuovo tentativo non deve avvenire.

### 4. Il ripristino del focus può chiamare `Properties` dopo la distruzione

- **File e righe**: `src/meridiana/ui/properties.py:290-358`, con il timer senza contesto a `:357`;
  `_refocus` a `:387-393`.
- **Che cosa succede**: il callback conserva `self` e la nuova pagina. Se il pannello viene eliminato prima del giro
  degli eventi, `_refocus` inizia chiamando `self.widget()` sul C++ già distrutto. Il controllo «la pagina è ancora
  quella corrente» arriva troppo tardi per proteggere il pannello stesso.
- **Scenario concreto**: una modifica di selezione ricostruisce Proprietà e subito dopo la finestra viene chiusa o
  il pannello eliminato. Al giro successivo scatta il ripristino del focus.
- **Gravità**: media. Eccezione riprodotta sul wrapper, anche se la finestra temporale è breve.
- **Prova**: [V] sonda con `_pending_focus = 0`, costruzione della pagina, `deleteLater()` e `DeferredDelete` prima
  del giro. Esito: `RuntimeError: ... Properties already deleted.`
- **Correzione proposta**: dare `self` come contesto al timer. Il contesto `page` è un'alternativa valida, perché la
  pagina è figlia del pannello, ma `self` esprime meglio chi possiede `_refocus`. Le prove attuali sul focus vanno
  mantenute e va aggiunto il caso di distruzione prima del giro.
- **Rischio della correzione**: minimo. Nessuna variazione quando pannello e pagina restano vivi.

### 5. `QuickImage` lascia alias a oggetti rilasciati e li riusa in un ridimensionamento

- **File e righe**: alias creati in `src/meridiana/ui/quick_image.py:67-70`; rilascio in `_Held.release` a `:48-56`
  e in `QuickImage.release` a `:314-319`; uso di `self.quick` in `_fit` a `:134-140` e nel `resizeEvent` a
  `:142-154`.
- **Che cosa succede**: `_Held.release` annulla i riferimenti dentro `held`, ma non gli alias `self.quick`,
  `self.control` e `self.engine`. Dopo `release()`, `self.quick` non è valido, tuttavia `_fit` chiama
  `self.quick.resize`. Anche `settle` non viene fermato da `QuickImage.release`.
- **Scenario concreto**: si rilascia la scena e poi arriva un ridimensionamento mentre il widget è ancora vivo.
  Il ramo che va a `_fit` usa la `QQuickWindow` già distrutta. Non ho dimostrato che Qt consegni questo evento dopo
  `aboutToQuit`: quello è un possibile contesto, non un fatto verificato.
- **Gravità**: bassa, perché serve una chiamata successiva al rilascio; il difetto è però reale nell'API pubblica
  `release()` e va chiuso mentre si lavora sull'ordine di distruzione.
- **Prova**: [V] dopo `image.release()`, `shiboken6.isValid(image.quick)` è falso; `image._fit()` solleva
  `QQuickWindow already deleted`; una finestra mostrata offscreen e poi ridimensionata produce lo stesso errore
  dentro `resizeEvent`. [V] la doppia `release()` e un `settle` attivo, senza ridimensionamento, non hanno invece
  dato errori.
- **Correzione proposta**: rendere esplicito lo stato rilasciato: fermare `frame` e `settle`, annullare anche gli
  alias, e fare in modo che `_fit` e `resizeEvent` non facciano nulla dopo il rilascio. Valutare nello stesso passo
  i piccoli accessor (`status`, `errors`, `rootObject`, `quickWindow`) perché restituiscano uno stato vuoto invece
  di un wrapper morto. Non cambiare l'ordine già documentato di distruzione delle risorse RHI.
- **Rischio della correzione**: medio, perché `View3D` usa questi accessor durante la costruzione. Le guardie devono
  operare solo dopo `release`; i test esistenti sulla scena restano obbligatori. La sequenza con GPU reale va fatta
  verificare da Claude, non offscreen.

### 6. Il cambio di schema di `Theme` ha un timer senza contesto

- **File e righe**: `src/meridiana/ui/theme.py:523-559`, in particolare `:559`.
- **Che cosa succede**: `_scheme_changed` rimanda `self.apply` senza un ricevitore nel timer. Se il `Theme` viene
  eliminato prima del giro e l'applicazione non può uscire presto per la scorciatoia `key == self.applied`, alla
  fine arriva `self.changed.emit()` su un segnale il cui oggetto è già distrutto.
- **Scenario concreto**: cambia lo schema del sistema e subito dopo viene eliminata la finestra proprietaria del
  tema. Nella riproduzione ho cambiato anche l'accento per percorrere l'intera applicazione invece del ritorno
  anticipato; il cambio reale di schema altera invece `dark`.
- **Gravità**: bassa. La corsa dura un solo giro degli eventi e richiede una sequenza precisa, ma l'eccezione è
  confermata.
- **Prova**: [V] sonda con `Theme`, `_scheme_changed`, eliminazione prima del giro e applicazione completa. Esito:
  `RuntimeError: Signal source has been deleted`.
- **Correzione proposta**: `QTimer.singleShot(0, self, self.apply)`, come già fatto in altri punti del progetto.
  Aggiungere la prova di eliminazione prima del timer, senza dipendere dal portale o dallo schema reale.
- **Rischio della correzione**: minimo. Nessuna variazione di tempi o palette con il tema vivo.

### 7. La guardia di `SystemAccent` non impedisce l'avviso dei processi `gdbus` ancora attivi

- **File e righe**: `src/meridiana/ui/theme.py:390-397` avvia due letture; processi creati a `:420-428`; guardia
  a `:430-448`.
- **Che cosa succede**: la guardia evita correttamente la lettura di un processo non valido. Però non ferma i due
  `QProcess` prima che il proprietario venga distrutto. Qt stampa un avviso per ciascun processo ancora in corsa.
- **Scenario concreto**: su Linux si apre e si chiude subito il programma mentre `gdbus` non ha ancora risposto per
  accento e movimento ridotto. I due processi vengono distrutti ancora attivi.
- **Gravità**: bassa. Non ho riprodotto un uso dopo distruzione dentro `_answered`, già protetto; restano l'avviso
  e una terminazione dei processi non gestita esplicitamente.
- **Prova**: [V] sonda con un `gdbus` finto che dorme due secondi. Alla distruzione del `SystemAccent`, due volte:
  `QProcess: Destroyed while process ("gdbus") is still running.` Lo stesso avviso è comparso in altre sonde che
  chiudevano l'applicazione durante le letture.
- **Correzione proposta**: un metodo `stop()` del singleton che scollega i segnali, svuota `_processes`, termina i
  processi validi e attende solo il necessario nella chiusura. Collegarlo ad `aboutToQuit`, non alla chiusura di
  ogni `MainWindow`, perché `SystemAccent` è condiviso dall'applicazione. Usare un `gdbus` lento nella prova e
  controllare sia l'assenza di avvisi sia l'assenza di segnali tardivi.
- **Rischio della correzione**: basso, ma l'attesa non deve bloccare di nuovo l'avvio o la chiusura per secondi.
  La chiusura è il momento giusto per terminare una lettura che non serve più.

### 8. Anche il ritardo della schermata diagnostica cattura la finestra senza contesto

- **File e righe**: `src/meridiana/app.py:91-98`.
- **Che cosa succede**: con `MERIDIANA_SCREENSHOT`, la funzione `take` cattura `win` e viene schedulata senza
  contesto. Se la finestra viene chiusa prima del ritardo ma l'event loop resta attivo, `win.grab()` usa il wrapper
  morto e `app.quit()` non viene raggiunto.
- **Scenario concreto**: una schermata diagnostica è programmata fra qualche secondo; la finestra viene chiusa da
  un altro percorso mentre un dialogo o un'altra finestra mantiene attivo il ciclo.
- **Gravità**: bassa. Riguarda un percorso diagnostico, non l'uso normale, e non l'ho riprodotto end-to-end.
- **Prova**: [I] dedotta dalla closure e dagli stessi meccanismi confermati sopra.
- **Correzione proposta**: usare `win` come contesto del timer e prevedere comunque l'uscita dell'applicazione se
  la finestra sparisce prima. Non vale la pena di trattare questo caso prima dei precedenti.
- **Rischio della correzione**: basso; va provato il percorso con il nome dell'immagine e il ritardo finti, senza
  aprire la finestra sullo schermo.

## Controlli che non hanno mostrato un difetto

- **Worker e widget**: [V] una scansione AST dei metodi `run()` dei `QRunnable` non trova chiamate a widget.
  I metodi lavorano su snapshot, file, rete o `QImage` e restituiscono segnali. `CompareJob` riceve una funzione
  dalla finestra, ma `_variant_figures` usa soltanto `ProjectSession.variant_figures`, senza Qt
  (`window.py:2001-2004`, `session.py:376-385`). `Work` riceve funzioni arbitrarie, ma gli usi trovati sono ricerche
  e controlli locali puri.
- **Job bound**: [V] `LayoutJob` completato dopo la distruzione della finestra non ha chiamato `sys.excepthook`.
  Non estendo questo risultato a ogni possibile percorso: le due lambda dei punti 1 e 8 vanno corrette a parte.
- **Catalogo, download e conversazione**: `CatalogDialog`, `UpdateDialog` e `Chat` collegano i risultati a metodi
  del ricevitore. `UpdateDialog.done` imposta anche la cancellazione (`update_dialog.py:168-171`); `Chat._gone`
  cancella il fornitore e chiude la voce (`assistant_chat.py:664-668`). Non ho trovato un accesso a widget nel
  thread.
- **Processi IFC e voce**: `IfcReading.cancel` scollega `finished`, termina e attende il processo
  (`ifc_import.py:102-120`), e `MainWindow.closeEvent` la chiama tramite `_cancel_ifc`. `Kokoro.close` termina il
  worker (`voice.py:116-121`), mentre `_fail` rimanda la notifica con un timer che ha contesto.
- **Grafici**: la coda `_draw_next` verifica `shiboken6.isValid(chart)` prima di toccare un grafico
  (`charts.py:121-133`) e `set_theme` fa lo stesso (`:102-106`). I timer senza contesto qui non producono il
  difetto dei punti precedenti.
- **`QuickImage` e `report_3d`**: la doppia `release()` di `QuickImage` non ha dato errori nella sonda; le risorse
  sono scollegate e cancellate nell'ordine documentato. Resta il problema degli alias del punto 5. La prova della
  relazione esegue il renderer in un processo separato, ma non misura la distruzione sulla finestra reale.

## Ordine consigliato delle correzioni

1. Lambda di aggiornamenti e IFC, con le due prove di chiusura.
2. Cancellazione di relazione e anteprima in `closeEvent`.
3. Timer di `TileLoader` e `Properties`.
4. Stato rilasciato di `QuickImage`, poi timer di `Theme` e arresto di `SystemAccent`.
5. Percorso diagnostico della schermata.

Ogni correzione può essere un commit a sé. Per ciascuna: prova rossa prima della modifica, prova verde dopo,
`ruff check src tests tools` e suite completa. Le condizioni GPU e l'assenza di avvisi alla chiusura sulla finestra
reale restano da verificare sullo schermo da Claude; non sono state misurate fluidità o resa 3D.

Nessun file di codice è stato modificato per questo rapporto.
