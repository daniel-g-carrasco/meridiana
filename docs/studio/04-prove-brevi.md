# Programma FV: prove brevi per scegliere l'interfaccia

21/10/2026, sera. Le prove proposte in `01-confronto-approcci.md`, sezione 9, fatte davvero.

**Macchine usate**

| Macchina | Dettagli |
|---|---|
| PC di lavoro | Windows 11, Intel Iris Xe, schermo a scala 200% |
| Portatile "lucciola" | Framework 13 AMD (Radeon 760M), Lucciola 45 (kernel 7.2 CachyOS), Niri 26.04 su Wayland, schermo 2880 × 1920 a 120 Hz con scala 2. Accesso via `ssh fw13` |
| WSL openSUSE sul PC | solo per controlli di funzionamento: la sua grafica non è affidabile (sezione 4) |

Tutto è [V]: provato e misurato, salvo dove scritto [I]. Script, risultati e screenshot sono in `C:\Users\utente\Elettrico\output\programma-fv\prove\`. Il prototipo è in `C:\Users\utente\Elettrico\output\programma-fv\prototipo\`.

## 1. In breve

- **Qt 6 (PySide6) passa tutte le prove, su Windows e su Linux con Niri, anche dentro Flatpak**, sia con il motore web (A4) sia con Qt Quick 3D (A2).
- **GTK su Linux con Niri è ottimo:** composizione con Vulkan, 117 fps su 120 Hz. Su Windows però resta il limite misurato: composizione cairo, 18-29 fps.
- **Proposta: Qt 6 + PySide6 con Qt WebEngine (A4).** Qt Quick 3D (A2) resta l'alternativa valida.
- **Problemi trovati, nessuno bloccante:**
  - il servizio WMS delle ortofoto nazionali è a tratti guasto lato server;
  - WebGL può mancare, e serve un ripiego;
  - i pacchetti sono grandi (611 MB su disco, 226 MB compressi) e vanno snelliti;
  - con Niri le finestre sono spesso a mezza larghezza.

## 2. Il prototipo (A4: Qt + WebEngine)

Una finestra con tre parti: i parametri a sinistra, la mappa al centro, il 3D a destra.
- **Disegno del tetto:** si disegna il contorno sull'ortofoto nazionale (PCN 2012).
- **Posa in Python** (`prototipo\layout.py`, shapely, senza interfaccia):
  - con i vincoli VVF: fascia di 1 m dal bordo, gruppi di al massimo 20 m, corridoi di 2 m;
  - file inclinate, con il passo ricavato dall'altezza del sole di progetto;
  - azimut e inclinazione con la convenzione della CEI 82-25;
  - Po,cc.
- **Risultato** disegnato sulla mappa e in 3D, con l'ortofoto stesa sotto l'edificio; clic su un modulo per selezionarlo.

**Come è fatto**
- **Indirizzo interno `fv://app/`:** pagine e librerie JavaScript (three.js r160, OpenLayers 10.2.1) sono incluse nel pacchetto, senza CDN.
- **Rete solo da Python:** le richieste ai servizi esterni le fa Python, attraverso lo stesso indirizzo interno, con una cache. È così che il programma vero parlerà con PVGIS, che non accetta chiamate dalle pagine web.
- **Python e pagine nello stesso processo:** comunicano con QWebChannel, quindi niente server e niente porte aperte.

**Sul capannone di prova** (Arkema, Rho, impronta OSM di 1.582 m²):

| Caso | Moduli | Po,cc |
|---|---|---|
| Con i vincoli VVF | 290 in 4 gruppi | 130,5 kW |
| Senza vincoli | 352 | 158,4 kW |

- Azimut α = -19°, inclinazione β = 10°, passo tra le file 3,33 m.
- Con i vincoli VVF i moduli sono il 18% in meno.
- Controlli geometrici:
  - distanza minima dei moduli dal bordo: 1,027 m;
  - distanza tra i gruppi: 2,000 m;
  - gruppo più grande: 15,6 × 18,4 m.
- Calcolo della posa in 17-27 ms.

**Come provarlo su questo PC**
1. Creare un ambiente con Python di python.org: `python -m venv venv`.
2. Installare: `venv\Scripts\pip install PySide6==6.12.0 shapely`.
3. Dalla cartella `prototipo`: `venv\Scripts\python fvproto.py`.

## 3. Risultati

| Prova | Windows | Linux, Niri (pip) | Linux, Niri, Flatpak BaseApp PySide 6.11 |
|---|---|---|---|
| Prototipo A4, 3D | 50-59 fps (Iris Xe tramite ANGLE/D3D11) | 60 fps (Radeon tramite ANGLE/GLES) | 60 fps, GPU accelerata anche nella sandbox |
| Prototipo A4, selezione del modulo | sì | sì | sì |
| Prototipo A4, avvio fino alla finestra pronta | 10,5 s il primissimo uso del motore web, poi 3,0 s dai sorgenti | 0,5 s | 0,9 s |
| Prototipo A4, pacchetto PyInstaller | 611 MB, 3.159 file, zip 226 MB; avvio 2,4-2,6 s; 57-60 fps | - | - |
| Qt Quick 3D, 3.600 moduli con ombre | 60 fps (D3D11); pacchetto 420 MB, zip 164 MB | 120 fps (OpenGL) | 120 fps |
| Qt Location con tile OSM | sì | sì | - |
| GTK 4 GtkGLArea | 18-29 fps (cairo; GL e Vulkan non partono) | 117 fps (Vulkan), 103 (GL) | - |

Due note:
- Nel motore web il 3D si ferma a 60 fps anche sullo schermo a 120 Hz, mentre Qt Quick 3D arriva a 120 [V]. Per un modello tecnico basta.
- Per confronto, il pacchetto GTK del template pesa 130-140 MB.

## 4. Cosa si è scoperto

1. **La BaseApp Flatpak di PySide 6.11 contiene Quick 3D, WebEngine, WebChannel e Location.** Il README che li dava per esclusi è superato.
   - Lanciando Python dentro la BaseApp va indicato `QTWEBENGINEPROCESS_PATH=/app/lib/libexec/QtWebEngineProcess`.
   - La GPU funziona dentro la sandbox con la Radeon.
2. **Il WMS delle ortofoto nazionali (PCN) è solo HTTP e a tratti guasto lato server.** Il 21/10 sera, dal portatile, rispondeva "Unable to access file ... \\192.168.65.12\nas1_vol1\..." per le richieste con i due fusi; un'ora prima dal PC andava. Per il programma vero:
   - ritentativi;
   - cache su disco;
   - una seconda fonte (Esri con la chiave dell'utente);
   - mappa e posa che funzionano anche senza sfondo, come è successo nella prova.
3. **WebGL può mancare** (sandbox senza GPU, macchine virtuali, desktop remoto): Chromium lo blocca se trova solo la grafica software. La vista 3D deve accorgersene e dirlo, e la pianta 2D deve continuare a funzionare. `--ignore-gpu-blocklist` resta come ultima risorsa, lenta.
4. **La WSL non serve per provare la grafica:** il motore web perde le texture (errori dma_buf), e in Flatpak va in software. Va bene solo per controllare che le cose partano.
5. **Niri:**
   - i programmi devono essere Wayland nativi (le app solo X11 passano da xwayland-satellite); Qt e GTK lo sono;
   - la disposizione a colonne dà finestre strette: l'interfaccia vera deve funzionare a mezza larghezza, per esempio con mappa e 3D in schede invece che affiancati e il pannello laterale richiudibile;
   - in Flatpak Qt segue da solo il tema scuro;
   - da verificare a occhio: le decorazioni della finestra Qt (Niri non ha `prefer-no-csd` nella configurazione) e i dialoghi dei file tramite portale (xdg-desktop-portal-gnome è installato) [I].
6. **Pacchetti grandi.** PyInstaller raccoglie molti moduli Qt inutili (Qt3D, Charts, DataVisualization, Graphs...). Con le esclusioni giuste si dovrebbe scendere sensibilmente [I]. Su Linux la Flatpak non porta Qt dentro, perché sta nella BaseApp e nel runtime KDE.
7. **Toolchain su Windows più semplice che con GTK:** Python di python.org con le wheel di pip, senza MSYS2. PyInstaller 6.22 gestisce PySide6 6.12, compresa la wheel separata di WebEngine.
8. **Python 3.15 sul portatile:** PySide6 6.12 e shapely 2.2 si installano da wheel.

## 5. Proposta

**Interfaccia: Qt 6 + PySide6, con mappa e 3D in Qt WebEngine (A4).**
- È provata su Windows e su Linux con Niri, da sorgenti, congelata e in Flatpak.
- Ha le librerie migliori per mappe e 3D e un'app Python vera intorno.

GTK resta la scelta di casa per le app senza 3D. Qt Quick 3D (A2) è l'alternativa se si preferisce evitare JavaScript, al prezzo di una mappa meno capace.

**Conseguenze sul metodo di casa.** Il template attuale è GTK, quindi questa sarebbe la prima app Qt. Proposta: costruire lo scheletro Qt dentro l'app FV (finestra, impostazioni, traduzioni, pacchetto PyInstaller, installer, Flatpak con la BaseApp, CI, aggiornamenti firmati con minisign, che si riprendono dal template) e solo dopo ricavarne un template Qt.

**Prossimi passi**, nell'ordine:
1. la decisione di Daniel sull'interfaccia;
2. il nome e il repository;
3. il nucleo 0.1 (`03-architettura-e-prima-fase.md`).

Restano da provare:
- la costruzione vera della Flatpak con flatpak-builder (manifest con la BaseApp e le wheel di shapely e numpy);
- l'installer Inno Setup e il pacchetto snellito;
- decorazioni e dialoghi su Niri;
- la scala frazionaria (1,25 e 1,5);
- l'ortofoto Esri con una chiave.

## 6. Cosa resta installato dalle prove

**Portatile** (Daniel decide se toglierlo o tenerlo per i passi successivi):
- `~/fvtest`, 851 MB: ambiente Python, prototipo, risultati;
- la Flatpak utente `io.qt.PySide.BaseApp//6.11`, 980 MB, con le sue dipendenze.

Per togliere tutto: `rm -rf ~/fvtest` e `flatpak uninstall --user io.qt.PySide.BaseApp//6.11`, poi `flatpak uninstall --user --unused`.

**PC di lavoro:**
- le cache del motore web in `%APPDATA%\python\QtWebEngine`, `%APPDATA%\fvproto`, `%LOCALAPPDATA%\fvproto` e `%LOCALAPPDATA%\qt_probe`, pochi MB;
- l'ambiente di prova nello scratchpad della sessione, temporaneo.

**WSL openSUSE:** pacchetti di sistema, ambiente PySide6, Flathub e BaseApp. Daniel ha detto che si può usare liberamente.
