# Meridiana: correzioni d'uso, formato e pacchetti

**Obiettivo:** risolvere i 15 punti segnalati il 29 ottobre, definire `.mer`, preparare pacchetti verificabili e riportare i componenti riusabili nel template Qt.

**Autorizzazione:** Daniel il 29/10: procedere secondo le indicazioni, valutare Astra/Sol e riportare le deduzioni nel template. Le proposte estetiche restano distinguibili dalle decisioni gia prese.

**Architettura:** conservare Python/PySide6 e le azioni/sessioni esistenti. Sol per difetti delimitati; Astra per formato e disegno complessivo. Nessuna modifica ai dati reali. Prove grafiche offscreen. Nessuna release pubblica implicita nella preparazione dei pacchetti.

## Verifiche

Test mirati e lint durante ogni lotto; foto dei componenti realmente usati, temi chiaro/scuro, testo grande e larghezza stretta. Suite completa alla fine dell'integrazione. Segnalare separatamente difetti funzionali, limiti delle prove e soglie prestazionali preesistenti.

## Lotti e proprietari

- [ ] Punti 1-4: `ui/new_project.py`, localizzazione e mappa. Riprodurre ricerca e mappa nera; etichetta distinta dalla query; dati facoltativi visibili e disattivati; privacy senza salti; coordinate spiegate. Sol `new_project_ux`.
- [ ] Punti 5, 11, 13, 14: sfumature, pannelli sul doppio bordo, centraggio ottico, popup proporzionati. Test su componenti reali. Sol `shared_ux`.
- [ ] Punti 6-7: `ui/plan_overlays.py`: bussola con centro fisso, freccia pulita, N solidale e posizione animata che evita la barra. Verifica resize, rotazione e movimento ridotto.
- [ ] Punti 8-10, 12, 15: proposta visiva coerente per Meridio, inverter attivo, strumenti, pillole, File e Impostazioni. Confronto con lo stato del codice; implementazione dei cambi gia definiti e proposta esplicita delle scelte estetiche.
- [ ] Formato `.mer`: inventario del formato 18 e alternative, migrazioni e compatibilita, limiti e risorse incorporate. Astra `format_packages_design`.
- [ ] Pacchetti: inventario degli strumenti e delle lacune, Windows installer/portatile e Linux Flatpak. Costruzione e self-test dei pacchetti possibili; nessuna dichiarazione di installazione provata senza prova.
- [ ] Integrazione, traduzioni, foto, test complessivi e consegna su Windows.
- [ ] Riporto nel template Qt delle correzioni generiche e aggiornamento dei manifest di allineamento, documenti e lezioni verificate.

## Casi da controllare

- Nuovo progetto senza rete o senza tessere nella cache deve spiegare lo stato e restare utilizzabile.
- Testo grande e privacy attiva non devono cambiare larghezza della pagina o nascondere campi.
- Resize ripetuto e movimento ridotto non devono lasciare animazioni o sovrapposizioni.
- Versioni future, risorse assenti e file danneggiati non devono perdere l'originale. Nessuna compatibilita richiesta con .meridiana.
- Pacchetto congelato deve includere traduzioni, dati geografici, Qt Quick 3D e associazioni corrette.

## Continuita e nuove richieste del 29/10

Daniel chiede esplicitamente che i nuovi messaggi non facciano perdere il lavoro in corso: mantenere decisioni,
motivazioni, prove e attivita aperte. R221-R223 sono aggiunte in coda; R224 (energia dei moduli non collegati)
blocca la consegna dei pacchetti per correttezza dei risultati. Le build gia prodotte restano conservate come
preview superate, senza cancellarle o chiamarle finali. La verifica generale gia avviata continua; dopo il fix
energetico si rieseguono i gruppi coinvolti, senza azzerare le prove indipendenti gia svolte.

Punto di ripresa verificabile:
- template Qt commit b98bc3797a926df8a56797c05cfe3ee97a32497f, tre modifiche preesistenti preservate;
- manifest consumer R02 e tabelle R03 verificati; 19 prove pagina Nuovo/Meridio e 7 inverter operativo verdi;
- suite nucleo869: sola aspettativa .meridiana superata, corretta con 7 prove mirate;
- suite calcoli193 e formati84 verdi prima di R224;
- suite widget440: solo ciclo vita Theme nella fixture, riprodotto e corretto con sequenza10prove;
- suite finestra ancora in esecuzione, log build/final-20261029-finestra.log;
- Windows bundle R03 selftest0errori, prima di R224; il log NON contiene ancora le nuove prove IFC/PDF: cache PyInstaller da ricreare in directory nuova al freeze finale;
- Flatpak R01 selftest e prove .mer/IFC/PDF verdi, prima di R224; nuovo bundle dopo correzione energetica;
- nessun commit Meridiana ne aggiornamento cartella avvio per questo lotto ancora eseguito.
