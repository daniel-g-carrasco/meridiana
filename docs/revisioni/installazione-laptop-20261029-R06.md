# Installazione e verifica nativa Flatpak R06

[V] Installato nel profilo utente di `fw13` (hostname `lucciola`) il bundle R06, dopo il via libera dell'integratore sulla suite finale. La cartella remota è nuova: `~/fvtest/meridiana-consegna-20261029-R06`. La consegna R05 e i log precedenti sono conservati. Nessuna operazione sui dati utente o sulle preferenze del compositor.

## Identità verificata

- Commit applicativo: `36fc0a0ad50733587ea16440a6df23ce6e4a4ec3`, distinto dalla base del lavoro `bf0767b`.
- Freeze sorgenti R17: `c19960fa2b64464a0e9498eed9ff48ec0e420d58a9e4494641a7e7957f8c79a3`.
- SHA-256 bundle locale e remoto: `97363a4ac79f2fc3723c3d3a7dc75fff825bb113c33efbe0ca4c37295cc9480d`.
- Commit OSTree installato: `350ae0a8fc1f9c981ecf6ceb68e43841445b4ae7ed4f33de46989b88708b2dd0`, identico al bundle esportato e reimportato.
- Commit precedente R05: `ccd091d302a7c2c60d8adf5d7647e4c1f37077536467b0a849d1c4eee46dadb4`.
- AppID `io.github.daniel_g_carrasco.meridiana`, architettura x86_64, branch stable, runtime org.kde.Platform 6.11, installazione user.

[V] La desktop entry esportata contiene `--file-forwarding`, `@@ %f @@` e il tipo MIME `application/x-meridiana-project+zip`. Non è stato aperto tramite doppio clic un progetto dell'utente.

## Prove native

[V] Autotest standard sulla sessione Wayland attiva: **zero errori in 13,80 s**. Verificati OpenGL, scena Ready e primo frame 3D (`frame`, 0,03 s), layout di 128 moduli, scambio IFC di 128 moduli, energia 23.922 kWh/anno, PDF 1.585.800 byte e cattura della finestra 1842 x 1642 pixel. La selezione esplicita della vista 3D nel self-test distribuito evita il precedente falso fallimento R05 dovuto al layout stretto.

[V] Prova aggiuntiva `tools/check_native_flatpak_view.py`: **zero errori in 11,18 s**, uscita 0, verifica rotazione di 30 gradi positiva. Finestra assegnata da Wayland 921 x 821 pixel logici; vista 603 x 399, immagine 1206 x 798. L'immagine dopo la rotazione ha hash diverso e la sonda registra `orbit_checks: [true]`.

[V] Le due immagini sono state aperte e ispezionate. Il primo frame mostra edificio, terreno e ombre prima dell'arrivo della posa; l'immagine dopo la rotazione mostra le quattro file di moduli e un orientamento diverso. Nessuna immagine vuota. La differenza include l'arrivo della posa, quindi l'hash da solo non viene usato come prova esclusiva della rotazione: l'orientamento è stato verificato anche visivamente.

Le prove usano cartelle temporanee isolate e non modificano file installati, bundle o preferenze del desktop. Nessun accesso cloud a pagamento.

## Ricevute e immagini

- `dist/packages-20261029-R06/laptop-installation-receipt-R06.json`.
- `dist/packages-20261029-R06/linux-package-receipt-R06-R02.json`: nuova revisione con commit applicativo e installazione nativa; la ricevuta preinstallazione resta conservata.
- Log standard, probe, installazione e desktop entry nella stessa cartella di consegna, prefisso `laptop-`.
- Evidenze integrali e manifest SHA-256 in `build/laptop-install-20261029-R06`.
- Immagini in `docs/revisioni/foto/desktop-pacchetti-20261029-R06/linux-first-frame.png` e `linux-orbit.png`.
