# Pacchetto Windows del seguito, R04

Sorgenti applicativi: `3fc6c841d8307bec0ceeb71d9d47f09852be3bd1`. Preview locale
`0.1.0-preview20261029-R04`, versione interna applicativa 0.1.0; nessun tag o pubblicazione.

Il bundle finale è `dist/windows-bundle-20261029-R10/Meridiana`; R10 distingue il tentativo
di build, R04 identifica la consegna. Il precedente bundle R09 resta diagnostico perché precede
la correzione del dimensionamento durante il ricalcolo della posa.

## Prove del binario

PyInstaller terminato correttamente. Confronto SHA256 dei 333 file congelati in
`build/source-manifest-20261029-R10.json`: nessuna modifica dopo il freeze.

Self-test del vero `Meridiana.exe`, avviato nascosto con Qt offscreen, exit code 0:

- Tutte le dipendenze richieste importate, comprese pvlib, IFC e provider Meridio.
- Finestra e progetto `.mer` aperti; posa di 128 moduli.
- IFC esportato e reimportato: 128 moduli, 238.965 byte.
- Produzione del caso di controllo: 23.683 kWh/anno da 57,6 kWp.
- Relazione PDF: 1.617.621 byte; finestra acquisita a 1400 x 900.
- Zero errori, 19,13 secondi. Nessun frame GPU disegnato con offscreen.

Log: `build/windows-selftest-20261029-R10.txt`. La copia sorgente nella cartella di avvio
`C:\Users\Grasso\dev\meridiana` ha superato separatamente lo stesso self-test (22,65 s).

## Confezionamento

ZIP del bundle con 7-Zip; verifica dell'intero archivio con `7z t`: exit code 0,
4.327 file, 519.180.394 byte non compressi e 218.348.724 byte compressi.
Ricetta installer Inno Setup `build-aux/windows/meridiana.iss`, con BundleDir impostata
sul bundle finale R10. Artefatti e somme SHA256 nella cartella `dist/packages-20261029-R04`.

Inno Setup ha concluso correttamente (exit code 0, 104,094 s). Installer finale:
`meridiana-setup-v0.1.0-preview20261029-R04-windows-x64.exe`, 155.171.474 byte,
SHA256 `42313416fd86599ab88698c7da93128194a4bc45c54956e2c17d14556487effa`.
ZIP: SHA256 `bd2b78e5746fd47a63ecfb0a8d5bbd720fdeb84fcc32efe3099f17928ec05c95`.

Queste prove non equivalgono all'installazione/disinstallazione interattiva, alla firma del codice,
alla prova del rendering GPU o alla verifica degli angoli dei popup nel compositore Windows.
I pacchetti sono anteprime locali. Gli artefatti delle revisioni precedenti sono conservati.
