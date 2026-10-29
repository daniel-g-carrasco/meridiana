# Flatpak finale R06: build e verifica

[V] Pacchetto generato dalla sorgente congelata R17, revisione interna Linux r10. Il precedente tentativo r09, fermato prima della consegna, resta conservato. Nessun file R05 cancellato o sovrascritto.

## Identità

- Bundle: `dist/packages-20261029-R06/meridiana-linux-x86_64-20261029-R06.flatpak`.
- Dimensione: 185.485.168 byte.
- SHA-256: `97363a4ac79f2fc3723c3d3a7dc75fff825bb113c33efbe0ca4c37295cc9480d`.
- Commit OSTree esportato e reimportato: `350ae0a8fc1f9c981ecf6ceb68e43841445b4ae7ed4f33de46989b88708b2dd0`.
- Freeze: `source-manifest-20261029-R17.json`, SHA-256 `c19960fa2b64464a0e9498eed9ff48ec0e420d58a9e4494641a7e7957f8c79a3`.

[V] Confrontati tutti i 353 file del freeze con lo snapshot Linux; nessun file aggiunto o mancante. Normalizzati soltanto CRLF/LF del launcher Unix e della desktop entry. Confrontati 330 file installati byte per byte; cataloghi italiani Linux/Windows semanticamente identici, 3.707 voci. Il commit Git applicativo viene registrato dall'integratore dopo il commit finale; il freeze identifica già esattamente la sorgente costruita.

## Prove sul pacchetto

[V] Autotest standard offscreen: zero errori. Finestra, posa di 128 moduli, scambio IFC4, energia 23.922 kWh/anno, relazione PDF e cattura finestra verificati. `pip check`: nessuna dipendenza incoerente.

[V] Undici prove aggiuntive superate: codec ZIP/schema20/MIME, IFC delle superfici virtuali con GUID stabile, pypdf, rifiuto valori non finiti, traduzioni/MIME Linux, codec gruppi ottimizzatori, import nuovi servizi/config22/policy Flatpak/comandi locali/redazione diagnostica, accumulo DC e rifiuto limiti assenti/codec accumulo/allegati/catalogo personale, audit di 24.262 record con quattro incoerenze e 34 campi riverificati, traduzioni delle funzioni R06, regressione `SuggestionsBox` (minimo verticale zero nel dock, naturale quando flottante).

[V] Reimportato il bundle in un repository OSTree separato; `fsck` superato, commit identico all'esportazione, catalogo italiano riletto direttamente dal repository reimportato. Checksum ricontrollato dopo la copia in Windows. Sidecar checksum usa il nome finale del bundle consegnato.

Ricevuta e log nella cartella di consegna: `linux-package-receipt-R06.json`, `linux-source-verification-R06.json`, `linux-parent-freeze-R06.json`, `linux-source-manifest-R06.json`, `linux-self-test-R06.txt`, `linux-package-probe-R06.log`, `linux-pip-check-R06.txt`, `linux-bundle-import-R06.log`, log build/runtime.

Limiti: prova in WSL/Qt offscreen, quindi nessuna verifica del rendering GPU interattivo. Il portale desktop WSL segnala `Settings.ReadAll` non disponibile: i controlli completano con successo e il warning resta nel log. Installazione e verifica nativa sul portatile non sono ancora state eseguite con questa ricevuta: attendono il via libera della suite finale.
