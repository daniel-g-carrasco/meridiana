# Completamento della lista: piano di implementazione

> Per gli esecutori: applicare executing-plans o subagent-driven-development per compiti verificabili.

**Obiettivo:** completare i residui della lista R198-R234 dopo la consegna R04, senza confondere
un'implementazione con una validazione sperimentale non disponibile.

**Architettura:** conservare il nucleo puro Python, i job cancellabili e il formato `.mer`.
Modello elettrico a curve I/V e conversione per inverter; assegnazione con vincoli globali;
dati di catalogo tracciabili e accoppiamento esplicito degli ottimizzatori. UI e template restano allineati.

**Tecnologie:** Python 3.12, NumPy/SciPy/pvlib, PySide6, Inno Setup e Flatpak.

**Specifica:** richieste R198-R234 in `docs/richieste.md`, audit
`docs/revisioni/ombre-stringatura-audit-20261029.md`, autorizzazione Daniel: «Vai pure avanti, termina la lista».
Le scelte visive e il contenitore `.mer` sono già approvati; non viene riaperta la progettazione.

## Vincoli

- Nessun modulo scollegato contribuisce alla produzione; nessun numero stimato passa per dato di targa.
- Norme e schede: prima archivio locale, poi fonti primarie; registrare ipotesi e campi mancanti.
- Niente cancellazione di progetti o pacchetti precedenti, niente pubblicazione/tag o dati utente nelle prove.
- Test mirati prima dei cambi, suite del lotto prima dell'integrazione; UI sempre responsiva.
- Le misure di campo non disponibili restano un limite di validazione, non una funzione da simulare come provata.

## Attenzione in revisione

1. Ombra che attraversa più sottostringhe rispetto alla stessa area su una sola.
2. Due moduli su un ottimizzatore: stessa unità MPPT, cablaggio serie/parallelo e orientamenti distinti.
3. Inverter diversi o sbilanciati: niente compensazione fittizia del clipping fra unità.
4. Più connettori su un MPPT, limite condiviso e limite condizionato dal numero di ingressi usati.
5. Ricerca annullata o troncata: non dichiarare impossibile/ottima una soluzione non dimostrata.

## Lotti

- [x] A. Curve elettriche e ombre: regressioni fisiche, implementazione e integrazione in nearshade/simulate/pipeline;
  confronto indipendente, tempi annuali, risultati e ipotesi visibili. Proprietario Astra.
- [x] B. Assegnazione globale: regressioni di soluzioni perse, risolutore vincolato in plant/stringing/sizing,
  vincoli comuni, cancellazione e completezza dichiarata. Proprietario Sol.
- [x] C. Catalogo e ottimizzatori: topologia ingressi, limiti condizionati, accoppiamento esplicito e controlli
  di coerenza in components/optimizers/catalog/model/UI; test di calcolo e roundtrip. Proprietario root.
- [ ] D. Desktop e installazione: popup/GPU con piattaforma nativa, installazione isolata e disinstallazione,
  prove senza alterare impostazioni/progetti/associazioni utente. Eventuali fix comuni anche nel template. Sol.
- [ ] E. Revisione incrociata e integrazione: suite del lotto, traduzioni, foto, manuale e registro aggiornati;
  nuovo freeze, nuovi pacchetti verificati e allineamento della cartella di avvio Windows.

Ogni lotto produce un rapporto distinto con verifiche, fonti e limiti. Il registro generale è aggiornato
solo dall'integratore. La chiusura di una riga richiede la prova del comportamento richiesto, non il solo rapporto.

## Aggiunte durante l'esecuzione

Daniel ha aggiunto in fondo R235-R239: aggiornamenti, allegati Meridio/cataloghi personali, accumulo e
compatibilità CC/CA, audit cataloghi, segnalazioni bug dalla GUI/chat. Sono conservate in `docs/richieste.md`;
non interrompono né sostituiscono i lotti A-E in corso. Il loro piano seguirà la ricognizione dei componenti
esistenti (anche template GTK), senza ripartire da zero o dichiararli completati per la sola registrazione.

Ulteriore aggiunta R240: visita guidata Meridio al primo accesso e richiamabile manualmente o dalla chat,
riutilizzando navigazione e spotlight R218. Conservata in coda alle precedenti.

Consegna aggiuntiva autorizzata da Daniel: al termine dei lotti A-E installare via SSH sul laptop Linux
l'ultimo Flatpak verificato di questa tranche; confrontare checksum e versione installata, verificare
l'avvio e conservare la ricevuta. Non sostituire il pacchetto con una build precedente solo perché già disponibile.
