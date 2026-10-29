# Meridiana: correzioni d'uso, formato e pacchetti

**Obiettivo:** risolvere i 15 punti segnalati il 29 ottobre, definire `.mer`, preparare pacchetti verificabili e riportare i componenti riusabili nel template Qt.

**Autorizzazione:** Daniel il 29/10: procedere secondo le indicazioni, valutare Astra/Sol e riportare le deduzioni nel template. Le proposte estetiche restano distinguibili dalle decisioni gia prese.

**Architettura:** conservare Python/PySide6 e le azioni/sessioni esistenti. Sol per difetti delimitati; Astra per formato e disegno complessivo. Nessuna modifica ai dati reali. Prove grafiche offscreen. Nessuna release pubblica implicita nella preparazione dei pacchetti.

## Verifiche

Test mirati e lint durante ogni lotto; foto dei componenti realmente usati, temi chiaro/scuro, testo grande e larghezza stretta. Suite completa alla fine dell'integrazione. Segnalare separatamente difetti funzionali, limiti delle prove e soglie prestazionali preesistenti.

## Lotti e proprietari

- [x] Punti 1-4: `ui/new_project.py`, localizzazione e mappa. Riprodurre ricerca e mappa nera; etichetta distinta dalla query; dati facoltativi visibili e disattivati; privacy senza salti; coordinate spiegate. Sol `new_project_ux`.
- [ ] Punti 5, 11, 13, 14: sfumature, pannelli sul doppio bordo, centraggio ottico, popup proporzionati. Test su componenti reali. Sol `shared_ux`.
- [x] Punti 6-7: `ui/plan_overlays.py`: bussola con centro fisso, freccia pulita, N solidale e posizione animata che evita la barra. Verifica resize, rotazione e movimento ridotto.
- [ ] Punti 8-10, 12, 15: proposta visiva coerente per Meridio, inverter attivo, strumenti, pillole, File e Impostazioni. Confronto con lo stato del codice; implementazione dei cambi gia definiti e proposta esplicita delle scelte estetiche.
- [x] Formato `.mer`: inventario del formato 18 e alternative, migrazioni e compatibilita, limiti e risorse incorporate. Astra `format_packages_design`.
- [x] Pacchetti: inventario degli strumenti e delle lacune, Windows installer/portatile e Linux Flatpak. Costruzione e self-test dei pacchetti possibili; nessuna dichiarazione di installazione provata senza prova.
- [ ] Integrazione, traduzioni, foto, test complessivi e consegna su Windows.
- [x] Riporto nel template Qt delle correzioni generiche e aggiornamento dei manifest di allineamento, documenti e lezioni verificate.

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

Snapshot intermedio, superato dal punto di ripresa finale sotto:
- template Qt commit b98bc3797a926df8a56797c05cfe3ee97a32497f, tre modifiche preesistenti preservate;
- manifest consumer R02 e tabelle R03 verificati; 19 prove pagina Nuovo/Meridio e 7 inverter operativo verdi;
- suite nucleo869: sola aspettativa .meridiana superata, corretta con 7 prove mirate;
- suite calcoli193 e formati84 verdi prima di R224;
- suite widget440: solo ciclo vita Theme nella fixture, riprodotto e corretto con sequenza10prove;
- suite finestra ancora in esecuzione, log build/final-20261029-finestra.log;
- Windows bundle R03 selftest0errori, prima di R224; il log NON contiene ancora le nuove prove IFC/PDF: cache PyInstaller da ricreare in directory nuova al freeze finale;
- Flatpak R01 selftest e prove .mer/IFC/PDF verdi, prima di R224; nuovo bundle dopo correzione energetica;
- nessun commit Meridiana ne aggiornamento cartella avvio per questo lotto ancora eseguito.

## Punto di ripresa dopo integrazione Windows

- Commit Meridiana `246ec58`, integrato con fast-forward nella cartella di avvio `C:\Users\Grasso\dev\meridiana`.
- Anche `meridiana-lavoro` allineata allo stesso commit. Un file manuale aperto impediva l'unlink di Git:
  conservata copia del contenuto precedente in `build/manuale-readme-before-integration-20261029.md`,
  aggiornato il file senza unlink e confrontati tutti i 105 file modificati con il commit. Solo dopo corrispondenza
  completa sono stati allineati HEAD e indice, senza cancellare file o modificare gli altri contenuti di lavoro.
- Template `b98bc3797a926df8a56797c05cfe3ee97a32497f` pubblicato sul repository privato; preservate modifiche preesistenti.
- Suite generale conclusa: 1751 prove, correzioni successive verificate nei gruppi interessati.
  Resta il test prestazionale del cambio tema: 1,032 s nella ripetizione contro soglia 1 s, invariata.
- R224 corretto e provato: i moduli non collegati non producono. Relazione dedicata in
  `docs/revisioni/produzione-moduli-collegati-20261029.md`.
- Formato `.mer` implementato e provato, senza requisito di apertura dei vecchi `.meridiana`.
- File/Impostazioni: proposta approvata, ristrutturazione completa ancora aperta. Anche R215-R223 e R225-R234
  restano distinti dagli interventi gia implementati; R233-R234 registrano stabilita, animazione e palette tooltip.
- Windows R06 ha individuato risorse IFC mancanti; ricetta corretta, nuovo bundle R08 dopo aggiunta delle risorse e delle regole/parser EXPRESS. Prova diagnostica R07 corretta: 0 errori e roundtrip IFC completo.
  Le versioni precedenti restano conservate e non sono la consegna. I risultati finali dei pacchetti
  sono registrati in `docs/revisioni/ux-formato-pacchetti-20261029.md`.

Consegna locale R03 conclusa: EXE Windows, ZIP Windows e Flatpak Linux; selftest entrambi senza errori. Hash e limiti nella relazione finale. Le richieste aperte non sono marcate completate da questa consegna.
