# Verifica finale del pacchetto Windows R05

Prova eseguita il 29 ottobre 2026 sul pacchetto finale, con installazione e disinstallazione reali in una cartella di test nuova. Non modifica i risultati della precedente verifica R02: questa ricevuta riguarda il binario del congelamento R14.

## Identità verificata

- Pacchetto: `dist/packages-20261029-R05/meridiana-setup-v0.1.0-preview20261029-R05-windows-x64.exe`.
- SHA256 del setup: `9dfcd52512c90d7a343a54708e2d961ba80b4dd6a5ee990bcf807c1cd1b87eac`, uguale alla ricevuta R05 e invariato dopo la prova.
- Manifest: `build/source-manifest-20261029-R14.json`, SHA256 `a3c59ea8c62c716aa485dfdbe0c6129a8d45a7f028d08c6aec4811153c18e795`, uguale al congelamento indicato nella ricevuta del pacchetto.
- L'eseguibile installato coincide con `dist/windows-bundle-20261029-R14/Meridiana/Meridiana.exe`: SHA256 `fe97f921e8feda58e0d648cf05a464dd8f8c6271cd03f6be2d23723d4ec165bb`.
- `application_commit` nella ricevuta è ancora `null`: in questa prova l'identità del sorgente è riferita al manifest R14. L'integratore aggiungerà il riferimento al commit conclusivo.

## Installazione e isolamento

Eseguito `tools/check_desktop_windows.py` con ricevuta R05 esplicita, bundle R14, `--platform windows` e directory nuova `build/desktop-package-check-20261029-R05-final`.

L'harness ha verificato assenza di un'installazione registrata e del mutex dell'app prima di procedere. Target unico: la sottocartella `installed-app` della directory di prova. Il processo avvia setup e self-test con `SW_HIDE` e `CREATE_NO_WINDOW`; non invia clic o tasti.

Il setup usa `/CURRENTUSER /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOCLOSEAPPLICATIONS /NORESTARTAPPLICATIONS /NOICONS /TASKS=` e un `/DIR` esplicito. Le directory temporanee e XDG sono isolate. La ricetta contiene `AllowNoIcons=yes` e subordina le registrazioni `Applications/Meridiana.exe` e `SupportedTypes` al task `associate`.

Installazione riuscita, codice 0, 23,469 s. Durante l'installazione nessuna associazione o registrazione dei file controllata è cambiata; collegamenti Desktop e menu Start invariati.

## Self-test nativo del programma installato

Self-test riuscito: codice 0, nessun fallimento, 17,12 s nel registro interno (18,586 s del processo). Piattaforma Qt Windows reale; `MERIDIANA_SELF_TEST_PLATFORM=windows` seleziona la piattaforma nativa anche se l'ambiente esterno dell'harness usa offscreen per precauzione.

Prove positive: finestra in italiano, cartelle isolate, disposizione di 128 moduli, esportazione e rilettura IFC, scena 3D pronta, grafica D3D11, primo frame 3D, calcolo annuale 23.922 kWh da 57,6 kWp, relazione PDF da 1.585.816 byte. Il self-test non riproduce suoni: verifica la disponibilità delle uscite audio e dei motori vocali.

La finestra in primo piano prima e dopo il self-test è la stessa. La cattura del widget Qt nativo da 2800 × 1800 pixel è stata aperta e guardata: mostra il progetto di prova, il tetto con i moduli e la vista 3D renderizzata. Non è una cattura dell'intero desktop e non contiene dati dell'utente.

Immagine: `docs/revisioni/foto/desktop-pacchetti-20261029-R05/windows-installed-native.png`.

## Disinstallazione e ripristino

Disinstallazione riuscita, codice 0, 1,535 s, tramite il solo uninstaller della cartella isolata verificata. Ricevuta finale positiva su tutti i controlli:

- Registro ripristinato esattamente rispetto allo snapshot iniziale, nelle viste HKCU/HKLM a 32 e 64 bit controllate.
- Collegamenti Desktop e menu Start ripristinati, già invariati durante l'installazione.
- Marcatore dei dati utente di prova conservato con lo stesso SHA256.
- Eseguibile installato rimosso e nessun processo della prova rimasto attivo al controllo conclusivo.
- Installer originale invariato.

## Evidenze e limiti

Ricevuta grezza: `build/desktop-package-check-20261029-R05-final/receipt.json`. Nella stessa cartella: log Inno di installazione e disinstallazione, log dei processi, `installed-selftest.txt`, `installed-selftest-runtime.log` e cattura originale.

Nessun sorgente runtime modificato, nessuna associazione `.mer` persistente, nessuna sovrascrittura di un'installazione esistente. Le prove native di popup e animazioni della precedente verifica restano documentate in R02 e non sono state ripetute senza motivo. Questa verifica riguarda Windows; installazione e self-test Linux sul laptop sono verificati separatamente dall'integratore. Nessuna pubblicazione, firma, tag o rilascio eseguito da questa prova.
