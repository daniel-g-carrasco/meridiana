# Ingressi e gruppi fisici degli ottimizzatori

Seguito di R227 e R229, dopo il pacchetto R04. Nessun dato mancante viene ricavato dividendo
arbitrariamente una corrente totale per il numero di MPPT.

## Ingressi dell'inverter

Un MPPT regola una tensione di lavoro. Più coppie di connettori possono essere collegate allo stesso
MPPT: le correnti si sommano, il punto di lavoro rimane comune. Il numero di connettori non è quindi
il numero di inseguitori indipendenti. Negli inverter SolarEdge trattati, il controllo MPPT è distribuito
sugli ottimizzatori e l'inverter lavora con una tensione di stringa prefissata; le unità Synergy sono
distinte dai normali MPPT del catalogo.

[V] `InverterSpec` ora espone il limite operativo per MPPT in funzione del numero di stringhe,
i limiti dei singoli ingressi quando documentati, e il limite comune dell'intero inverter.
I dati restano separati. Una configurazione assente da una tabella condizionata non eredita automaticamente
il valore più alto della tabella.

[V] Huawei SUN2000-20K-MB0: 20 A con una stringa e 30 A con due stringhe sul medesimo MPPT;
due MPPT e quattro ingressi fisici. Fonte: scheda Huawei SUN2000-12/15/17/20/25K-MB0,
versione 01-202504, p. 2, archivio locale
`C:\Users\Grasso\Elettrico\reference\catalogs\Huawei\inverters\Huawei - SUN2000-12-25K-MB0 - 01-202504 EN.pdf`.
Verificata anche la copia ufficiale:
https://solar.huawei.com/admin/asset/v1/pro/view/c3ba89c365cb42ce92d9ba3c366253f1.pdf
Il valore Isc 40 A senza portata esplicita non è stato trasformato in un limite per connettore.
I limiti 20/30 A sono strutturati nel record del modello e mostrati accanto all'MPPT in Impianto.

## Ottimizzatori fisici

[V] I valori di tensione minima/massima di ingresso e massima di uscita già presenti nel catalogo
arrivano ora al modello `Optimizer`; restano `None` quando non documentati. Cablaggio in serie
e ingresso parallelo sono distinti. Due moduli sullo stesso ottimizzatore condividono il controllo
elettrico dell'unità: non diventano due MPPT indipendenti.

[V] Dal menu di una stringa si apre «Moduli su ciascun ottimizzatore». È possibile comporre
gruppi singoli e doppi nello stesso ordine della stringa, per esempio 2 + 1 + 2.
Il numero di ottimizzatori è il numero dei gruppi fisici, non il solo arrotondamento del numero di moduli
diviso due. I controlli verificano le occupazioni effettive e impediscono gruppi maggiori della capacità.
Gli abbinamenti possono essere modificati con un solo passaggio di Annulla e viaggiano nel `.mer`.

Il formato logico 20 aggiunge `optimizer_group_sizes` ai collegamenti. I file precedenti conservano
l'interpretazione per ordine di stringa; prima delle modifiche gli abbinamenti impliciti sono resi espliciti
per non accoppiare accidentalmente moduli diversi dopo una rimozione. La fixture del formato 19 è conservata.

## Verifiche

- Test di limiti 20/30 A, separazione corrente totale/MPPT/connettore, campi assenti e malformati.
- Test di conservazione delle tensioni catalogate e conteggio dei gruppi singoli su ottimizzatori doppi.
- Roundtrip `.mer` e rifiuto di partizioni invalide con il percorso del campo nel messaggio.
- Dialogo: gruppo da tre non confermabile; ottimizzatore singolo senza comando di unione.
- Finestra: proposta stringhe in un job annullabile, risposta tardiva scartata dopo cancellazione o modifica.
- Una ricerca conclusa può proporre soltanto una parte dei moduli se gli ingressi non bastano: i collegamenti
  validi sono applicabili e il messaggio indica quanti moduli rimangono scollegati. Una ricerca interrotta
  o senza verifica conclusa non applica risultati; il dimensionamento automatico richiede invece tutti i moduli.
- Revisione indipendente: una proposta senza sostituzione di hardware conserva gli inverter selezionati;
  applicazione e Annulla verificati anche quando la proposta cambia insieme hardware e collegamenti.
- CSV: intestazioni con virgole, punti e virgola, virgolette o ritorni a capo mantengono lo stesso numero
  di colonne dei dati in italiano e inglese. Risultati per inverter in kWh e somma AC coerente con il totale.
- Dialogo fotografato e ispezionato nei due temi: `foto/completamento-20261029/gruppi-R03`.
  La prima riga mantiene lo stesso rientro pur avendo la casella disabilitata; lo stile delle caselle
  nelle tabelle è condiviso con il template Qt.

La ricetta fisica del calcolo annuale e le sue ipotesi sono documentate separatamente nel rapporto
`modello-elettrico-20261029-R02.md`. Un modello numerico verificato non equivale a una campagna
di misure su tutti i moduli e gli ottimizzatori commerciali.
