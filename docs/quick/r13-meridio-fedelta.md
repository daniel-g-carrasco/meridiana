# Meridio: integrazione e fedeltà, 05/11/2026

[V] Il pulsante Meridio della finestra Quick apre la conversazione collegata alla sessione reale. Il ramo porta anche aiuto, manuale, tour, impostazione del fornitore e allegati. Widgets, nucleo dell'assistente, modello e sessione non sono stati modificati: confronto Git con `4be571b`. R332 resta fermo.

## Cosa è stato portato

| Parte | Comportamento e prova |
|---|---|
| Registro della finestra | `assistant_part.py` installa host, chat, aiuto e comandi. Configurazione condivisa con File/Impostazioni, selezione e progetto della sessione aperta. Proposta applicata solo dal pulsante, annullabile con Undo. |
| Movimento, R369 | Personaggio e fumetto seguono lo stesso gesto QML. Soglia di trascinamento Qt, lato conservato finché c'è spazio, scivolamento al cambio lato. Presa sul personaggio e sul titolo. La prova cattura ogni passo e conta zero nuove richieste Python allo sprite durante il trascinamento. |
| Forma e dimensioni, R371 | Un solo tracciato per corpo e coda, senza linea interna. Raggio 10, coda 12, metà base 11. Presa specchiata, bordo opposto fermo e coda ancorata durante la riduzione. Apertura/chiusura con dissolvenza, meno movimento rispettato. |
| Personaggio | Sprite originale liscio o pixel, raggi separati, respiro, battito di palpebre, sguardo ritardato, piccole pause ed espressioni. Stati riposo, pensiero e risposta. Si ferma quando non visibile o inattivo. Posizione per fase salvata nello stato Quick. |
| Conversazione | HTML dei messaggi condiviso con il renderer Widgets, testo progressivo, tabelle, immagini, domande numerate, invio e stop, menu del fornitore, voce, stato e costi. Rotella verso l'alto conserva il punto di lettura. |
| Allegati, R320 | File, immagini, incolla, trascinamento, anteprima e rimozione. «Mostra ciò che vedo» cattura il centro reale senza Meridio. Schede apribili con il controllo C3 condiviso. Miniatura nella misura originale, pulsanti visibili nel fumetto flottante. |
| Fornitore | Invito nella conversazione, scelta locale/cloud e configurazione con chiave mascherata. Profili e credenziali separati, nessuna richiesta al modello durante il salvataggio. Prove con archivio delle chiavi in memoria. |
| Aiuto, R383 | Il «?» visibile di Proprietà apre l'aiuto corrispondente. In flottante evita il pannello e torna con Esc o chiusura; nella scheda non si sposta. Se disabilitato compare per la visita. Lo spazio del vecchio Aiuto è della shell. |
| Manuale e tour | Contenuti del nucleo, navigazione interna, 13 tappe reali, menu delle tappe, sospensione/ripresa e luce sul bersaglio. Il tour attraversa File e le fasi senza cambiare il progetto. |

## Confronto visivo e gesti

La [galleria](confronto/r13-meridio/index.html) distingue la matrice finale dalle iterazioni che hanno fatto emergere i difetti. Il riferimento è il progetto sintetico `capannone_rho()` di `tests/_fixtures.py`, non un progetto privato. Ogni coppia usa lo stesso progetto e la stessa risposta finta. Finestre vere sulla piattaforma Windows, Direct3D11, sul desktop separato; nessun evento al mouse o alla tastiera del sistema.

- Matrice finale: 1366 × 900, 1600 × 960 e 1920 × 1080, chiaro/scuro, scala 1/2. In più: testo grande nella scheda, allegato, tabella, invito e pagina del fornitore, aiuto e tour. Ogni JSON riporta misure effettive, DPR, renderer, geometria, richieste finte e avvertenze QML. Immagini intere, fumetti e ritagli al 200% restano accanto ai JSON.
- [V] Guardate tutte le 19 coppie di `finale-r02`, inclusi i ritagli al 200%. Il caso con testo grande ha motivato l'ultimo ritocco R197: le domande a capo ora fanno crescere il pulsante, con i margini verticali dei Widgets. Le due catture successive, testo normale flottante e grande nel dock, sono in `ritocco-testo-grande`; conservata la foto precedente per il confronto.
- `percorso-r04`: stessi 13 gesti nei due programmi, con verifica di apertura e aggancio a ogni passo. Ctrl+L, passaggio sul fornitore, campo, scrittura, Invio, suggerimenti chiusi/aperti, aggancio, ridimensionamento, distacco, Esc, riapertura e chiusura. Verificato anche che Quick parta dentro il pannello centrale.
- Prove dedicate: trascinamento di personaggio e titolo, cambio lato, tutti i bordi, ridimensionamento, ritorno dall'aiuto, fuoco del campo, menu, allegati, schede, consenso, proposte e tour. Il testo inserito e le proposte passano dalle funzioni reali; nessun servizio a pagamento è chiamato.

## Difetti trovati guardando le foto

[V] Corretti la linea fra corpo e coda, il titolo non centrato, lo sguardo fermo, l'incolla testo+immagine, la barra di scorrimento sul lato sbagliato, il vuoto aggiunto dal DropArea, il contenuto del dock fuori posto dopo il resize, l'ancora QML non valida per una tupla Python, il primo avvio frameless nell'angolo alto, il saluto vuoto e i pulsanti degli allegati tagliati. Le relative regressioni sono in `test_fidelity`, `test_scene` e `test_integration`.

[V] Il caso frameless falliva con `avatarX = 0` contro `352` attesi: il centro non aveva ancora la trasformazione definitiva verso l'overlay. Ora si aggiorna dopo il fotogramma. Il «?» nascosto della shell è stato sostituito nella prova dal vero `section-help:site`, raggiunto anche attraverso i figli visuali dei delegate.

[V] Due ulteriori casi riprodotti e corretti: aiuto aggiornato ma invisibile dietro la linguetta Proprietà, e fumetto alto sopra i comandi (`y = 33` contro il limite `124`). L'aiuto seleziona il dock anche quando già aperto; geometria, trascinamento e ridimensionamento rispettano l'area fra comandi e barra di stato. Il ritorno R383 è verificato sia con Esc sia con clic sulla croce.

[V] Domande pronte con testo grande: il pulsante non teneva conto dell'altezza del testo a capo e dei suoi margini. La foto nel dock mostrava la seconda riga tagliata. La regressione R197 verifica testo visibile, più larghezze, presenza di righe a capo e spazio per l'intera etichetta con il margine inferiore. Sul codice precedente fallisce con `44 > 36`; sul codice corretto passa.

## Differenze rimaste e semplificazioni dichiarate

1. Il dock usa le linguette del sistema di pannelli Quick: condivide la zona destra con Proprietà. Nei Widgets le due schede possono stare una sopra l'altra. Il contenuto di Meridio è figlio del dock vero e segue le sue misure; la disposizione appartiene alla shell. Confronto: passi 7 e 8 del percorso.
2. Aiuto e manuale occupano il fumetto durante la visita, conservando la conversazione. È l'applicazione di R383; il riferimento Widgets conserva ancora la scheda Aiuto. Il tour Quick conserva la misura 340 × 560, ridimensionabile, anziché stringersi automaticamente sul testo di ogni tappa. Per questo può avere più spazio vuoto.
3. L'invito a configurare il modello resta una scheda. Il pulsante apre una pagina dedicata nel fumetto, mentre Widgets espande i campi nella scheda. La pagina conserva tutte le operazioni e lascia più spazio ai campi e alle spiegazioni. Si torna alla conversazione al salvataggio o con «Non ora».
4. Le tabelle Markdown con barre verticali sono rese come tabelle HTML nella conversazione Quick. Nel riferimento Widgets la stessa risposta può restare testo. Nessun HTML del modello viene eseguito; le celle passano dall'escape del nucleo.
5. Restano differenze nella spaziatura delle liste, nelle frecce dei suggerimenti, nei pulsanti delle schede e nella rasterizzazione del testo fra QTextDocument Widgets e Qt Quick. La posizione assoluta del fumetto e il lato iniziale possono differire con gli spazi della shell; durante il gesto il lato resta stabile finché c'è spazio. Non è una certificazione di identità pixel per pixel. I ritagli al 200% le rendono visibili.
6. Le animazioni Quick muovono il sottoalbero grafico vivo: non congelano uno screenshot della finestra come l'ottimizzazione Widgets R369/R371. Questo evita ricostruzioni Python durante il gesto. La fluidità percepita sul monitor va ancora confrontata.

## Verifiche e limiti

[V] Suite finale Meridio: 64 prove verdi in 69,9 s, compresa la nuova regressione R197. Prima: 63 prove verdi in 168,8 s e 26 prove mirate dopo i limiti dell'area utile, verdi in 116,3 s. Lint completo `ruff --select F,E9,B` verde. Sistema: 46 prove verdi. Formati: 96 prove verdi. Nessuna soglia allargata per ottenere il verde. Log conservati nella [cartella verifiche](confronto/r13-meridio/verifiche/README.md). Verificati anche i 171 collegamenti della galleria.

[V] Compatibilità generale: 70 prove eseguite, un fallimento, 7 saltate e 2 fallimenti attesi già dichiarati. Il fallimento è `RegistryTest.test_all_requests_and_test_methods_have_exact_inventory_rows`: registro `docs/quick/compat` non aggiornato ai sorgenti integrati, 132 segnalazioni nella prova eseguita. Log conservato in `confronto/r13-meridio/verifiche/compatibilita.txt`. Non è stato nascosto e non sono stati riscritti i registri della parte compatibilità.

Non verificati: chiamate vere ai fornitori, chiavi reali, voce con modelli installati e tempi di presentazione sul monitor Dell al 200%. Il desktop separato verifica grafica e gesti Qt, non il puntatore fisico né la fluidità percepita a 4K con la mappa. Nessun push, tag o rilascio.

Riproduzione: ambiente `PYTHONPATH=tests;src`, `PYTHONUTF8=1`, `QSG_RENDER_LOOP=basic`, `QT_QUICK_CONTROLS_STYLE=Basic`; Python della `.venv` condivisa in sola lettura. Matrice: `python -m quick.meridio.capture_matrix --out <cartella nuova>`; percorso: `python -m quick.meridio.pilot tests/quick/percorsi/meridio.json --project <Rho sintetico> --out <cartella nuova>`.
