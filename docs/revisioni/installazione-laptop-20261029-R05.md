# Installazione e verifica del Flatpak R05 sul portatile Linux

Il Flatpak R05 e installato nel profilo utente del portatile `fw13`. La verifica nativa conferma OpenGL, scena 3D,
primo frame e successiva rotazione, senza modificare il bundle o le impostazioni del desktop. Il self-test standard
conserva un fallimento riprodotto e spiegato: su una finestra stretta il layout nasconde il 3D, ma il test ne attende
comunque il primo frame.

## Ricevuta dell'installazione

| Dato verificato | Valore |
| --- | --- |
| AppID | `io.github.daniel_g_carrasco.meridiana` |
| Versione / architettura / branch | `0.1.0` / `x86_64` / `stable` |
| Installazione | `user`, verificata con `flatpak info --user` |
| Runtime | `org.kde.Platform/x86_64/6.11` |
| Commit sorgenti applicativi | `10da2fc39094736e7a60b324e059b9db58a35513` |
| Commit OSTree installato | `ccd091d302a7c2c60d8adf5d7647e4c1f37077536467b0a849d1c4eee46dadb4` |
| Bundle | `meridiana-linux-x86_64-20261029-R05.flatpak` |
| SHA-256 del bundle sul portatile | `5b2377305aaf1352653a6f29f53b48ce3f8dfc644438fdd26e9eb1b2f53cffab` |

[V] Il commit installato coincide con quello esportato e importato nella verifica del pacchetto. Il checksum del
bundle sul portatile coincide con la consegna Windows. La desktop entry esportata contiene `--file-forwarding`,
gli argomenti `@@ %f @@` e `MimeType=application/x-meridiana-project+zip;`. Questo verifica la registrazione del
formato `.mer`; non e stato provato un doppio clic su un file dell'utente.

## Fallimento iniziale e diagnosi

[V] Il self-test standard nativo Wayland termina con **un solo errore**, `3D first frame: time`, dopo il timeout di
3.000 ms dello skeleton. Sono verdi OpenGL, scena `Ready`, posa di 128 moduli, IFC4 con 128 elementi, energia positiva
di 23.922 kWh/anno e PDF. Il test completo iniziale dura 12,14 s. Il suo fallimento non viene cancellato o riclassificato.

[V] La sessione grafica risulta attiva e sbloccata. La sonda diagnostica R02, senza cambiare il comportamento della
vista, rileva una finestra esposta di **921 x 821 pixel logici**. `MainWindow._adapt` ha soglia `NARROW = 1000`:
quando il compositor assegna una larghezza inferiore, seleziona la sola pianta. Lo splitter vale `[603, 0]`, il
contenitore 3D e nascosto e la vista e larga zero. Le due chiamate a `QuickImage._render` terminano subito per
`isVisible() == False`, senza produrre immagini o segnali `afterRendering`.

La causa e quindi la condizione della prova: `selftest.window` attende il primo frame dopo `win.show()`, senza
assicurarsi che la vista 3D sia ancora visibile dopo il ridimensionamento del compositor. La finestra richiesta di
1400 x 900 non e una garanzia della geometria effettivamente assegnata da Wayland. In questo stato aspettare piu
di tre secondi non rende visibile la vista.

## Controprova con vista esplicitamente selezionata

[V] La sonda R03 usa lo stesso Flatpak e la stessa sessione. Nella sola finestra temporanea del self-test richiama
il metodo gia esistente `_view_mode('3d')`, senza modificare monitor, compositor, finestre altrui o preferenze utente.
La vista diventa **603 x 399 pixel logici**, con un'immagine renderizzata di **1206 x 798 pixel**.

- Primo render effettivo: **158,8 ms**, segnale `afterRendering` ricevuto e immagine non vuota.
- Lo skeleton termina con motivo **`frame`**, prima del timeout.
- Rotazione della camera di **30 gradi**: nove segnali `afterRendering`, dieci chiamate di render complessive e
  checksum dell'immagine diverso.
- Self-test completo: **0 errori in 9,18 s**; energia, IFC e PDF restano verdi.

[V] Le due immagini sono state aperte e ispezionate: entrambe mostrano il capannone con le quattro file di moduli,
terreno e ombre; la seconda conferma il diverso orientamento della camera. Non sono immagini vuote o solo sfondi.

Una seconda esecuzione con lo strumento riutilizzabile `tools/check_native_flatpak_view.py` conferma
**0 errori in 9,09 s** e verifica della rotazione positiva. Il processo termina con codice **0**. Non emerge un
avvio grafico freddo superiore a tre secondi: il rendering funziona appena la vista viene resa visibile.

## Strumento riproducibile

```text
C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\tools\check_native_flatpak_view.py
```

Lo script non contiene percorsi personali. Si esegue dentro il Flatpak installato e richiede una nuova directory
di output; rifiuta di riutilizzarne una esistente. Avvia il self-test con configurazione e cache temporanee, seleziona
la vista 3D della sola finestra di prova, acquisisce primo frame e immagine dopo la rotazione. La strumentazione
sostituisce temporaneamente alcuni metodi Python soltanto nel proprio processo: non modifica file installati,
runtime, bundle o impostazioni persistenti.

Esempio da una directory che contiene una copia dello script, in una sessione Wayland attiva. Il suffisso R02 evita
di riutilizzare i risultati R01 gia acquisiti:

```sh
test ! -e native-view-check-R02.log &&
flatpak run --command=python3 --env=PYTHONPATH=/app/share/meridiana \
  --env=MERIDIANA_SELF_TEST_PLATFORM=wayland --filesystem="$PWD" \
  io.github.daniel_g_carrasco.meridiana "$PWD/check_native_flatpak_view.py" \
  --output-dir "$PWD/native-view-check-R02" > native-view-check-R02.log 2>&1
```

La prova si appoggia a metodi interni dell'applicazione e va ricontrollata se questi cambiano. Rimane distinta dal
self-test standard: non nasconde l'errore iniziale e non modifica il suo criterio nel programma distribuito.
Ruff passa sullo strumento. Nessuna ricompilazione o sostituzione del pacchetto e stata necessaria.

## Allegati conservati

```text
C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\build\laptop-install-20261029-R05
```

La cartella nuova contiene, con i nomi originali:

- `install.log`, `installed-commit.txt`, `installed-app-metadata-R01.txt`, `install-verification-R01.txt`;
- `installation-receipt-R01.json` e `diagnostic-sha256-R01.json`;
- `self-test-native.log` e `.txt`, con il fallimento iniziale;
- `firstframe-probe-R02.py`, `.log`, `.txt`, con la vista nascosta e il timeout riprodotto;
- `firstframe-probe-R03.py`, `.log`, `.txt`, `.png` e `orbit-probe-R03.png`, con la controprova positiva;
- `check_native_flatpak_view.py`, `native-view-check-R01.log` e la sottocartella `native-view-check-R01/`,
  contenente `self-test.txt`, `first-frame.png` e `orbit.png` della prova finale riutilizzabile.

I dati del rapporto e della ricevuta riguardano l'applicazione. Non sono stati cambiati configurazione o stato della
sessione utente; non sono state manipolate altre finestre. Il tentativo preliminare R01 della strumentazione aveva
una collisione del nome del wrapper con `QWidget.render`: non e usato come prova del rendering e resta soltanto
nella cartella diagnostica remota. Le conclusioni si basano sulle sonde corrette R02/R03 e sulla prova finale.

Il limite residuo e nel self-test standard su layout stretto: il controllo del primo frame dovrebbe selezionare
esplicitamente la vista 3D prima dell'attesa. Questo rapporto non introduce correzioni al codice distribuito.

Catture finali conservate anche nel repository: `foto/desktop-pacchetti-20261029-R05/linux-first-frame.png`
e `linux-after-orbit.png`, ispezionate dal coordinatore oltre che dall’esecutore.
