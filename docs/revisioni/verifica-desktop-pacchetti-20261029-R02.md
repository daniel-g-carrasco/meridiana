# Verifica desktop e pacchetti, 29 ottobre 2026, R02

Prove effettuate sul checkout `b3c0146` con il seguito in integrazione. I pacchetti R04 provati restano quelli
congelati su `3fc6c84`, senza essere sostituiti. La ricetta Windows corretta è compilata separatamente in un
installer **R05-test**, usando lo stesso bundle R04/R10. Non è il pacchetto finale del nuovo modello 20.
Nessun commit di Meridiana, firma, tag, pubblicazione o aggiornamento di un'installazione reale in questo lotto.

## Popup R209 sul compositore Windows

[V] Piattaforma Qt `windows`, Dell P2415Q al 200%, Python 3.12 e PySide6 6.12. Finestra di prova senza focus né
input del puntatore; lo stato della finestra in primo piano resta invariato. Le prime prove quasi trasparenti
non permettevano di giudicare gli angoli: per la cattura il solo popup di prova è opaco, poi viene chiuso.

[V] Il campo misura 478 px logici; la lista 360 x 110 px e mostra tutte e quattro le scelte. La cattura nativa
dei popup chiaro e scuro, osservata, non riproduce un alone scuro interno agli angoli. DWM restituisce
`DWMWA_WINDOW_CORNER_PREFERENCE=2`, e modalità scura rispettivamente 0 e 1. La lettura dell'attributo colore
bordo restituisce `E_INVALIDARG`: non viene dichiarata come prova positiva di quell'attributo.
Non è necessaria una nuova correzione a `popups.py`.

Fotografie reali dei soli popup, acquisite tramite Computer Use/WGC e conservate senza modifiche:
`foto/desktop-pacchetti-20261029-R02/popup-native-light.png` e `popup-native-dark.png`.
Ricevute in `build/native-popup-20261029-R04-{light,dark}/receipt.json`.
La verifica vale per questo compositore e questa scala; non è una prova nativa su ogni sistema o al 250%.

## 3D e animazioni native

[V] Il sorgente è stato avviato sul Dell con opacità circa 2%, senza attivazione né input. La 3D usa
**Direct3D 11 sulla Intel Iris Xe**: scena senza errori, immagine GPU presente. Una vera orbita cambia i byte
del fotogramma mantenendo 722 x 912 pixel prima e dopo. Fotogramma guardato:
`foto/desktop-pacchetti-20261029-R02/gpu-native-after-orbit.png`.
Ricevuta e misure: `build/native-desktop-20261029-R03/receipt.json`.

[V] Anche il vero binario R04 è stato provato con `MERIDIANA_SELF_TEST_PLATFORM=windows`, avvio nascosto
`STARTUPINFO/SW_HIDE` e cartelle isolate. Primo piano invariato. Self-test: **zero errori in 13,48 s**,
`PASS 3D graphics: D3D11` e `PASS 3D first frame: frame`; 128 moduli, IFC, energia e PDF verificati.
La cattura della finestra da 2800 x 1800 pixel è stata guardata: il modello 3D è visibile e completo.
Log in `build/frozen-native-selftest-20261029-R02/`, foto `foto/desktop-pacchetti-20261029-R02/frozen-native-window.png`.
Questo risultato chiude la precedente limitazione del solo frame GPU offscreen per il bundle R04.

[V] Le sequenze File e cambio fase terminano, senza veli rimasti o crash. La prova rileva però pause superiori
a 30 ms: nel secondo campione, apertura File 57-67 ms di chiamata e massimi intervalli del loop 63-67 ms;
una chiusura arriva a 161 ms, l'ingresso nella prima fase energetica a 225 ms. L'orbita campionata ha un massimo
di 25,9 ms, senza intervalli oltre 30 ms. Il primo campione era concorrente alla compilazione dell'installer
e resta diagnostico. Non si dichiara risolta R120 né si ricavano FPS del compositore da questi numeri.

## Installer Windows: difetti trovati e prova corretta

[V] L'installer R04 originale, SHA256 `42313416fd86599ab88698c7da93128194a4bc45c54956e2c17d14556487effa`,
ha creato un collegamento Start Menu nonostante `/NOICONS`. Il controllo lo ha intercettato, interrompendo prima
di avviare il programma installato; la disinstallazione del solo target isolato è riuscita e ha rimosso il
collegamento. Nessun valore `.mer` o ProgID è cambiato. Restava una chiave vuota
`HKCU/Software/Classes/Applications/Meridiana.exe`, assente al baseline: è stata rimossa soltanto dopo averne
verificato nuovamente l'assenza iniziale e l'attuale totale vuoto. Ricevute e log originali sono conservati in
`build/desktop-package-check-20261029-R02/`, inclusa `empty-key-cleanup-R01.json`.

[V] Due correzioni nella ricetta:

- `AllowNoIcons=yes`, necessario perché `/NOICONS` funzioni anche con la pagina dei gruppi nascosta.
- Registrazione `SupportedTypes` condizionata a `Tasks: associate`, rimozione del solo valore e delle chiavi
  vuote con `uninsdeletevalue`/`uninsdeletekeyifempty`, anche sul contenitore dell'eseguibile.

[V] Inno Setup 6.7.4 ha compilato il nuovo installer di sola prova in 84,516 s:
`build/desktop-installer-R05-test/meridiana-setup-v0.1.0-preview20261029-R05-test-windows-x64.exe`,
SHA256 `18d1d330b8601a66943af84e933e6ccf651034f5ca32cb1819c656b4bde8b08c`.
Il bundle e l'installer R04 restano intatti.

[V] Installazione controllata in una directory nuova, verificata sotto `build/desktop-package-check-20261029-R05-test`:
`/CURRENTUSER /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOCLOSEAPPLICATIONS /NORESTARTAPPLICATIONS /NOICONS /TASKS=`
e `/DIR` esplicita. Prima della prova erano assenti installazioni e registrazioni dell'app; il mutex di un'app
reale in esecuzione viene rifiutato dal controllo, per evitare il riavvio previsto dalla ricetta dell'aggiornamento.

[V] Installer exit 0; vero eseguibile installato, self-test offscreen senza errori in **13,66 s**;
uninstaller exit 0. Nessuna icona creata durante la prova corretta. Dopo: eseguibile rimosso, registro e
collegamenti identici al baseline, marker dei dati conservato e hash del pacchetto invariato.
Non è provato il percorso interattivo con associazioni abilitate, che avrebbe modificato il profilo reale.

## Installazione e rimozione Flatpak

[V] Bundle R04 SHA256 `08b4babd1b5876d2ffb33c68d1927fadae565d475625d804f70330be36ee78c8` installato
realmente in un nuovo profilo Flatpak/XDG privato, con directory home privata per i soli processi della prova.
Il runtime KDE 6.11, commit `fe192771c0992ad873e6a9ccc6e4f087c76314ce5ced165650cc7ea045a6bbaa`,
è stato trasferito dalla cache OSTree già presente a un repository locale nuovo. Nessun download di dipendenze.

[V] La voce desktop è esportata nel solo profilo isolato; il programma installato supera il self-test offscreen
con **zero errori in 10,96 s**. La rete e i socket grafici/audio sono disabilitati, il filesystem concesso è
quello di prova. La rimozione con `flatpak uninstall --user --noninteractive` riesce: app ed export desktop
rimossi, marker dei dati conservato, bundle intatto e riferimenti dell'installazione originale identici al prima.

Ambiente conservato: `/home/daniel/meridiana-installed-check-20261029-R02-27pwnafj` in WSL openSUSE;
log e ricevuta copiati in `build/desktop-flatpak-check-20261029-R02/`.
Non è una prova di doppio clic su un desktop Linux o della GPU del portatile Linux.

## Spunte degli alberi e riporto nei template

[V] Il dialogo dei gruppi usava spunte native degli item view da 14 px, fuori dal mixin condiviso.
Ora `CheckboxStyle` tratta `PE_IndicatorItemViewItemCheck` per `QAbstractItemView`, con la stessa allocazione
da 22 px e lo stesso segno dei `QCheckBox`; `PE_FrameFocusRect` dell'albero rimane delegato a Qt.
Le immagini del dialogo nei due temi sono state guardate: righe da 26 px, nessuna sovrapposizione.
Spazio cambia lo stato e il focus rimane all'albero. Nessuna modifica alla logica dei gruppi.

[V] Regressione prima rossa (14 contro 22), poi verde. Source: 7 prove checkbox e 8 prove app/ricetta;
template Qt: 21 prove checkbox/tabelle/intestazioni, Ruff completo pulito. Raster del nuovo indicatore
confrontati con quelli del controllo normale ai fattori 1, 2 e 2,5 nei due temi, inclusi parziale e focus.
Le foto sono `foto/desktop-pacchetti-20261029-R02/checkbox-item-view-{light,dark}.png`.

[V] La stessa ricetta senza `AllowNoIcons` era nel programma campione del gemello GTK `app-template`;
corretta e provata anche con una nuova app generata: 48 prove per copia senza errori, con 3 e 7 skip dovuti
alle dipendenze/casi condizionati. Il template GTK non contiene la registrazione di estensioni.
Nel template Qt sono riportati mixin e regressione; i tre file preesistenti modificati da Daniel conservano
gli SHA256 iniziali e restano esclusi dai commit. I relativi hash dei commit sono forniti al coordinatore
per il manifest del consumatore. Nessuna implementazione delle richieste R235-R240 in coda.

[V] Commit pubblicati soltanto nei due repository privati, autore e committer Daniel Grasso:

- `qt-app-template`: `0b5d9654b3ec9cd79aa25cc8df73f384112b7c7b`, mixin `checkboxes`, regressione e nota desktop.
- `app-template`: `8a3691f29561826cb2dfbbab50032b02075792a7`, ricetta `AllowNoIcons`, regressione e nota installer.

I riferimenti remoti `main` coincidono con gli hash. Il file preesistente modificato della skill nel gemello GTK
resta escluso dal commit, come i tre file preesistenti del modello Qt. Nessun commit o push di Meridiana.

Harness riproducibili in `tools/check_desktop_windows.py`, `check_desktop_flatpak.py`,
`check_native_desktop.py`, `check_native_popups.py`. Le ricevute distinguono prove positive, fallimento
intercettato e limiti; nessuna installazione di prova viene presentata come rilascio pubblico.
