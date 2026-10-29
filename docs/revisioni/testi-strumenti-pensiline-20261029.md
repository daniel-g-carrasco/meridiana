# Testi, strumenti e pensiline

Seguito delle richieste R203, R205, R210, R216-R217, R219-R221. Base af17add; implementazione nel ramo
integra-kimi-9-10. Questo documento si aggiunge al registro, senza sostituire le richieste tecniche sulle ombre.

## Interfaccia

File riunisce Salva, Salva con nome e Salva una revisione nella stessa pagina. Le Impostazioni hanno un livello
dedicato con categorie e Torna a File; le opzioni hanno larghezza massima leggibile e i comandi di annullamento
e ripristino stanno sotto. La conferma di ripristino viene annullata cambiando categoria: la revisione
indipendente aveva riprodotto il ripristino di Navigazione dopo una conferma riferita ad Aspetto.

Meridio separa la conversazione dal pannello e distingue i ruoli tramite nome, rientro e fondo. Lo streaming
conserva la posizione quando si leggono messaggi precedenti. La navigazione guidata e lo spotlight del lotto
precedente rimangono attivi. Non vengono inserite nuove connessioni verso servizi esterni nelle prove.

Gli strumenti Modello seguono: selezione/modifica, costruzione, posa, precisione. Est-ovest è raggiungibile
direttamente sul sottocampo selezionato. La conversione protegge file manuali e superfici inclinate; le file
opposte conservano i propri orientamenti effettivi. Le regole elettriche globali sono trattate nell'audit
ombre-stringatura, non soltanto nella funzione est-ovest.

Pensilina per parcheggio crea una o due falde contrapposte con numero di posti, larghezza, profondità,
quota minima, inclinazione e rotazione modificabili. Un clic posa le superfici e i moduli; un solo Annulla
ritira l'operazione. I valori iniziali sono esempi editabili, non dimensioni normative. Pilastri, travi,
verifiche strutturali e sagome dei veicoli restano fuori da questo modello di posa e sono dichiarati nel dialogo.
Le falde usano i piani ausiliari persistenti dello schema 19, mantenendo le informazioni nell'esportazione IFC.

L'icona Allinea a un lato mostra lato inclinato, riferimento orizzontale e rotazione. Il precedente SVG resta
nel confronto fotografico. MPPT e connettori sono denominati separatamente; le unità Synergy e il bus a tensione
fissa non vengono descritti come MPPT indipendenti dell'inverter.

## Testo tecnico e relazione

Prima del web è stato consultato l'indice locale MCM in
`C:\Users\Grasso\Elettrico\reference\templates\06. Identità grafica\README.md`.
La struttura documentale usa gerarchia, numeri e unità leggibili, font e identità di Meridiana, senza copiare
cartigli o dati personali MCM.

Fonti primarie:
- [Qt, Supported HTML Subset](https://doc.qt.io/qt-6/richtext-html-subset.html): CSS effettivamente supportati, unità e `thead` ripetuto.
- [GOV.UK, Table](https://design-system.service.gov.uk/components/table/): confronto e scansione dei dati, intestazioni e allineamento numerico.
- [GOV.UK, Spacing](https://design-system.service.gov.uk/styles/spacing/): spaziatura coerente e gerarchia.

La spiegazione precede la formula. Gli ingressi hanno colonne Simbolo, Grandezza, Valore e unità, Fonte;
il risultato è distinto. Le tabelle ripetono l'intestazione sulle pagine successive. Su carta corpo 10,5 pt,
titoli gerarchici, margini esistenti di 20 mm, intestazione e numerazione pagina/totale. Il tema scuro non
entra nei PDF. Il costo unitario con produzione nulla appare come Nessuna produzione anziché infinito.

Ai profili Completa e Compatta si aggiungono Presentazione al cliente, Revisione del progetto elettrico,
Energia e ipotesi di calcolo; tutti e tre conservano il capitolo delle verifiche. I capitoli restano selezionabili.
Il modello comune è portato in qt-app-template, con note per conversazioni e testi tecnici.

## Verifiche

Prove mirate di geometria, quote, orientamenti, persistenza, undo, dialogo e comandi: 7 verdi nel primo lotto
integrato con File. Test PDF/relazione: 24 verdi prima del controllo visivo e delle correzioni di revisione.
Le immagini `foto/seguito-20261029/light-R02` e `dark-R02` mostrano File e Impostazioni effettivi.
`relazione-R01` è una prova diagnostica senza font caricati, non una consegna; `relazione-R02` usa i font reali.
I rendering offscreen non producono la scena 3D RHI: il relativo riquadro viene omesso come previsto,
senza presentare questa prova come verifica della GPU nativa.

Gli esiti finali del lotto, eventuali ulteriori correzioni, commit e pacchetti sono nel rapporto di integrazione.
