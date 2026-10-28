# Manuale di Meridiana

Il manuale accompagna il programma: si apre da Aiuto > Manuale e dai collegamenti «Manuale ›» del riquadro d'aiuto, che portano al paragrafo giusto. C'è un capitolo per fase, nell'ordine della riga delle fasi; le Verifiche hanno un capitolo a sé perché valgono in tutte le fasi.

Bozza del 24/10/2026 (compito 17d), scritta dai calcoli e dalle regole del programma: la sostanza tecnica e le fonti sono da rileggere con Daniel.

## Come chiedere aiuto

- **Il riquadro d'aiuto**, in fondo al pannello di destra, in ogni fase: spiega il campo del pannello che ha il fuoco, o il riquadro di risultato sotto il puntatore. Tre righe di testo, la fonte e tre collegamenti: «Manuale ›» (questo manuale, al paragrafo giusto), «Come è calcolato ›» (la pagina dei calcoli, al passo giusto), «Chiedi a Meridio ›» (l'assistente, con la domanda già scritta). Un clic sul titolo lo piega e lo riapre; resta come lo lasci. Se il pannello è più basso di 480 px il riquadro sparisce da solo e i «?» aprono lo stesso testo in un riquadro a comparsa.
- **Il «?»** accanto al titolo di un gruppo delle Proprietà o di un riquadro di risultato apre il riquadro d'aiuto su quel punto.
- **F1** spiega il campo che ha la tastiera, in tutta la finestra.
- **Maiusc+F1** («Che cos'è?») trasforma il puntatore in un punto di domanda: il clic successivo spiega ciò che tocca.
- **Ctrl+?** apre l'elenco delle scorciatoie da tastiera.

I tre comandi stanno anche nel menu Aiuto: un tasto F non è mai l'unica via (sui portatili i tasti F sono spesso tasti multimediali).

## Impostazioni

**File > Impostazioni** riunisce Aspetto, Navigazione, Tastiera, Assistente, Relazione, Mappe e Riservatezza nella finestra principale. Ogni modifica vale e si salva subito. **Annulla l'ultima modifica** torna indietro; **Ripristina i valori predefiniti di questa sezione** chiede conferma nella pagina, senza finestre modali. Il comando si apre anche con Ctrl+,.

## Clienti e commesse

**File > Clienti e commesse** mostra tre colonne: clienti, commesse e dettaglio con progetti e cartelle collegati. **Nuovo cliente** e **Nuova commessa** li aggiungono senza finestre separate. Il codice commessa è di cinque cifre e resta testo, quindi conserva gli zeri iniziali. Il registro è un database SQLite sul PC, con transazioni e una copia `.bak` aggiornata dopo ogni scrittura. Se il database non si apre, Meridiana avvisa senza sovrascriverlo e usa un registro temporaneo, così i progetti restano utilizzabili.

In **File > Nuovo**, nei dati facoltativi, scegli cliente e commessa. Il nome del cliente va nella relazione; una commessa riservata ferma ricerca online e tessere già quando la scegli. Al salvataggio Meridiana collega il file alla commessa e scrive nel progetto gli id della serie, nel formato 18: salvare R02 e riaprire R01 conserva lo stesso collegamento.

Nella pagina del registro, **Collega cartella** aggiunge una cartella esistente alla commessa senza spostare file. Ogni cartella ha la sua casella: solo quando la attivi Meridiana scrive e aggiorna `.meridiana-commessa.json`. Disattivarla rimuove il manifesto e la sua copia. Una commessa riservata non ha mai un manifesto. Se una cartella non è raggiungibile, l'errore viene mostrato e l'operazione viene ritentata alla scrittura successiva, senza fermare le altre cartelle.

**Esporta registro** crea un JSON completo. Se contiene commesse riservate, Meridiana avvisa che il file non è cifrato prima di scriverlo. I consensi delle cartelle non viaggiano nel file: restano locali e una cartella importata parte sempre senza manifesto. Cambiando percorso o commessa serve un nuovo consenso. **Importa registro** mostra prima nuovi, aggiornati, invariati e conflitti. **Applica importazione** unisce per id e conserva i record che non sono nel file; codici, percorsi o campi non validi bloccano tutto, senza doppioni silenziosi o scritture parziali.

## Meridio, l'assistente

- **Ctrl+L**, o un clic sul personaggio, apre la conversazione. Meridio legge il progetto (verifiche, risultati, regole, il manuale) e risponde con le fonti; se una cifra viene da un valore di serie o da una stima lo dice; non cambia niente da solo: propone, e la proposta si applica con un clic e si annulla con Ctrl+Z.
- **Le domande pronte** sotto la conversazione seguono quello che vi siete appena detti e lo stato del progetto: se Meridio chiude con «Vuoi che te lo proponga?» la prima è «Sì, proponimelo»; se l'anno non è calcolato, «Che cosa manca per calcolare l'anno?». Si mandano con un clic o con 1, 2, 3 nel campo vuoto.
- **Dove pensa**: con il modello locale del PC (di serie: niente esce dal PC) o con Claude, se lo scegli, con la tua chiave e il tuo consenso; un progetto segnato riservato resta sempre sul PC.

### Un modello locale in pochi passi

File > Impostazioni > Assistente > **Modelli locali su questo PC** cerca da sola i programmi che servono modelli (Ollama, LM Studio, llama.cpp, Jan, Lemonade, Docker Model Runner, ogni server compatibile con OpenAI), dice quali sono avviati e quali solo installati, elenca i modelli e consiglia quello che usa meglio gli strumenti e sta nella memoria del PC.
- **Usa questo** mette server, modello e tipo di server nei campi; la scelta vale e si salva subito.
- **Prova** fa una domanda breve: deve tornare come chiamata di uno strumento, come quelle di Meridio. La prima volta il modello si carica dal disco: può volerci un minuto.
- **Se non c'è niente**, la pagina dà i passi con i comandi da copiare: installare Ollama (da ollama.com/download, oppure `winget install Ollama.Ollama`) e scaricare il modello adatto al PC, per esempio `ollama pull qwen3.6:35b-a3b` su un PC con 32 GB di RAM e una scheda da 8 GB. Con Ollama non serve impostare altro: Meridiana gli chiede da sé il contesto e il ragionamento spento.
- Chi preferisce llama.cpp: `winget install llama.cpp`, poi `llama-server -hf unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS -c 16384` (la porta 9931 è quella di serie di Meridio).
- Se il modello locale non risponde mentre gli fai una domanda, Meridio cerca da sé un altro modello sul PC e te lo propone con un clic.

## I capitoli

1. [Modello](1-modello.md): il sito, gli edifici, i sottocampi, le esclusioni, la posa dei moduli.
2. [Impianto](2-impianto.md): gli inverter e le stringhe.
3. [Producibilità](3-producibilita.md): l'anno ora per ora, i risultati, le perdite.
4. [Consumi](4-consumi.md): da dove vengono i consumi e che forma hanno.
5. [Bilancio ed economia](5-bilancio.md): autoconsumo, bolletta, flussi di cassa.
6. [Relazione](6-relazione.md): gli elaborati.
7. [Verifiche](verifiche.md): i livelli, le fonti, «Correggi».

## Installare e aggiornare

- **Windows**: l'installer `meridiana-setup-vX.Y.Z-windows-x64.exe` delle versioni pubblicate su GitHub installa il programma solo per te, senza diritti di amministratore, e apre i file `.meridiana` con Meridiana; lo zip portabile è lo stesso programma in una cartella. Le impostazioni restano in `%APPDATA%\Meridiana`, le copie di ripristino e le cache in `%LOCALAPPDATA%\Meridiana`: la disinstallazione non le tocca.
- **Aggiornamenti**: una volta al giorno, un minuto dopo l'avvio, il programma per Windows chiede a GitHub se è uscita una versione più recente (non invia niente di te né dei tuoi progetti); Aiuto > Cerca aggiornamenti chiede subito. Se c'è, una finestra dice che cosa porta: il programma installato scarica l'installer, lo confronta con il checksum che GitHub pubblica e con la firma del progetto (minisign) e, dopo averti chiesto di salvare il progetto, lo avvia; Meridiana si chiude e si riapre aggiornata. Lo zip portabile apre la pagina della versione. Il controllo si spegne in File > Impostazioni > Riservatezza, «Aggiornamenti».
- **Linux**: il Flatpak, costruito dal manifest dei sorgenti finché un repository non lo pubblica; i suoi aggiornamenti arriveranno dal centro software del desktop.
- **Che cosa esce dal PC**: niente di te e mai i file dei progetti. L'indirizzo cercato va a Nominatim di OpenStreetMap, le coordinate del sito a PVGIS, l'area in vista ai server delle mappe, la domanda sulle versioni a GitHub: ognuno con il suo interruttore in File > Impostazioni > Riservatezza. Meridio manda le domande ad Anthropic solo se scegli Claude, dai la tua chiave e acconsenti. In un progetto riservato nomi e indirizzi non escono mai e Meridio resta locale; mappe e PVGIS ricevono le coordinate soltanto dopo il consenso specifico dato a quel progetto.

## Come leggere i numeri

Ogni numero dice da dove viene, con uno di sei tipi di fonte: un valore scritto da te; un valore predefinito di Meridiana, detto come tale; un dato (PVGIS, una scheda tecnica, un catalogo); una norma con edizione, articolo e pagina; un modello pubblicato (Perez 1990, il modello termico di PVsyst); il risultato di un passo precedente. «Come è calcolato», in ogni pagina dei risultati, mostra i passi con le formule; la relazione PDF li riporta e in fondo elenca i valori ancora predefiniti.

In questo manuale i valori predefiniti sono indicati con il file del programma che li fissa, le norme con la regola di `rules.py` o la verifica di `checks.py` che le cita. I numeri dati come «ordine di grandezza» non sono valori di norma: servono a riconoscere un risultato strano.
