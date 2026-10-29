# Pacchetti Windows R06, 29/10/2026

[V] Creati ZIP portabile e Setup locale dal bundle completato
`dist/windows-bundle-20261029-R16/Meridiana`. PyInstaller: completato in 266,325 s, log
`build/pyinstaller-final-R16.log`. La precedente costruzione R15 è conservata e non è stata usata per questi pacchetti.

[V] Fonte effettiva: working tree congelato R17, 353 file verificati prima e dopo la preparazione.
Manifest `source-manifest-20261029-R17.json`, SHA-256
`c19960fa2b64464a0e9498eed9ff48ec0e420d58a9e4494641a7e7957f8c79a3`.
La ricevuta Windows R02 distingue `source_base_commit` da `source_state=uncommitted frozen R17`:
la base Git bf0767b non viene presentata come commit contenente tutte le modifiche. L'integratore aggiungerà
il commit applicativo soltanto dopo il commit finale e la verifica della corrispondenza col manifest.

## File prodotti

Cartella `dist/packages-20261029-R06`:

| File | Byte | SHA-256 |
| --- | ---: | --- |
| meridiana-portable-20261029-R06-windows-x64.zip | 223051966 | 793cbf0035d1ee882ac2eb3018a60108f088556f377f638d386990ee4f22f600 |
| meridiana-setup-v0.1.0-preview20261029-R06-windows-x64.exe | 155315359 | 4e9c1e459625219cd888ea049a44a11ae52bb86ba525a5868fceaa0b37b7984f |

[V] Inno Setup ha compilato in 118,609 s; log `build/inno-final-R06.log`.
Il nome del programma resta Meridiana. La versione interna resta 0.1.0, mentre Setup identifica la revisione locale
come 0.1.0-preview20261029-R06. I pacchetti sono anteprime locali non firmate: nessun accesso alle chiavi private,
nessun tag e nessuna pubblicazione di release.

## Prove

[V] ZIP: 4327 file, nomi e dimensioni identici al bundle; verifica CRC completa senza errori.
L'eseguibile nell'archivio e nel bundle ha SHA-256
`5c1fd76807b008ea68989c7e87946dddb0a0e3f6b8378d27a93af8301ac92a19`.

[V] Portabile: self-test Windows nativo, finestra avviata nascosta con stato/cache temporanei isolati.
D3D11 e primo frame in 0,56 s; calcolo, IFC e relazione PDF superati. Esito: 0 errori in 32,87 s,
34,40 s inclusa apertura del processo. Finestra in primo piano invariata.
Foto `windows-portable-native-R06.png` ispezionata: scena 3D del progetto di prova presente e leggibile.

[V] Setup provato con `tools/check_desktop_windows.py --platform windows --bundle ...R16/Meridiana`,
cartella nuova `build/desktop-package-check-20261029-R06-final/installed-app`:
- installazione per utente, silenziosa e senza icone o associazioni, exit 0 in 28,246 s;
- eseguibile installato identico al bundle;
- self-test Windows nativo: D3D11, primo frame in 0,63 s, 0 errori in 24,67 s;
- processo self-test exit 0 in 26,323 s e finestra in primo piano invariata;
- disinstallazione exit 0 in 1,730 s; eseguibile di prova rimosso;
- registri e collegamenti ripristinati esattamente alla baseline, che prima era vuota;
- marcatore dati utente nella cartella isolata conservato e pacchetto Setup invariato.

Le prove non hanno usato progetti reali. Non è stato provato un aggiornamento sopra un'istanza reale in esecuzione.
Il checker rifiuta registrazioni preesistenti e un mutex applicativo attivo: nessuna protezione è stata aggirata.

## Ricevute

[V] Nel pacchetto: `windows-package-receipt-R06-R02.json`, `windows-installed-receipt-R06.json`,
`windows-portable-selftest-receipt-R06.json`, `windows-source-verification-R06.json`,
`windows-zip-verification-R06.json`, manifest R17, checksum e log delle due prove.
La prima ricevuta usata dal checker identificava la base Git; è conservata soltanto come evidenza storica in
`build/windows-package-receipt-R06-base-checkonly.json`. La copia consegnata usa i campi base/stato espliciti.
Nessun sorgente applicativo modificato e nessun commit eseguito durante questo lotto di packaging.
