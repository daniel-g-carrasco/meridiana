# Verifiche

Le Verifiche raccolgono ciò che chiede attenzione, da ogni parte del progetto: le note della posa, le ombre degli ostacoli, le verifiche delle stringhe, ciò che chiede la connessione, le note della producibilità, le stime ancora al posto dei dati, le regole che si applicano. Il pannello sta in basso in tutte le fasi (Ctrl+J); Ctrl+Maiusc+M ci porta la tastiera e le frecce scorrono le voci, con le viste che seguono.

Ogni voce è una frase breve con il suo segno e la sua fonte; la freccia apre il dettaglio (perché, e che cosa fare). Un clic mostra nelle viste l'oggetto di cui parla, con il resto attenuato; un doppio clic porta all'oggetto o alla pagina. Per livello è la vista predefinita; dal menu nella testa si raggruppano per oggetto, per area o «Pronto per la consegna». I filtri «Questa fase» e «Questo oggetto» tengono solo le voci della fase aperta o dell'oggetto selezionato.

## Da correggere

Qualcosa che la norma o la posa non ammette: il progetto non va consegnato così. Esempi: una posa che non si calcola, una stringa oltre la tensione massima dell'inverter, una connessione monofase sopra 6 kW. «Correggi» fa la modifica proposta (Ctrl+. sulla voce in mano), e Annulla la toglie.

## Da controllare

Una perdita o un rischio, non un divieto: decidi tu. Esempi: gli ostacoli che tolgono più del 3 % dell'irraggiamento di un campo, moduli rimasti fuori dalle stringhe, la zavorra da sola su un solaio. Leggi il dettaglio sotto la riga, poi correggi o lascia com'è.

## Da sapere

Un fatto che la relazione citerà: una soglia superata (per esempio, sopra 11,08 kW la protezione di interfaccia è un relè dedicato: CEI 0-21:2026-07, 8.6.2, regola N05), una regola che si applica, un valore ancora predefinito. Niente da correggere. File > Copia le note per la relazione copia i paragrafi delle regole con le loro fonti.

## Superate

Le verifiche passate, ognuna con la sua fonte: ciò che Meridiana ha controllato e trovato a posto. La sezione è chiusa per impostazione, perché venga prima ciò che chiede attenzione.

## Fonte

Ogni voce dice da dove viene: una norma con edizione, articolo e pagina; una legge; il modello di calcolo; oppure «Meridiana» quando è una lettura del programma e non una regola (per esempio la soglia del 3 % delle ombre). Le regole vengono dalla libreria «Utilità Fotovoltaico R02» di Daniel (21/10/2026), i cui testi sono stati controllati sui documenti dell'archivio (`rules.py`).
