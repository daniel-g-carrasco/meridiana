# Pacchetto Flatpak R04: 29 ottobre 2026

La R04 e l'anteprima verificata per la consegna locale. Lo snapshot Linux R05 corrisponde al congelamento Windows R10:
formato 19, superfici BIM e ricerca inverter asincrona con controllo della posa corrente. Le revisioni precedenti
restano conservate. Ricetta e prove storiche sono in `docs/revisioni/pacchetto-flatpak-20261029.md`.

[V] Ambiente WSL openSUSE-Tumbleweed: Flatpak 1.18.4, flatpak-builder 1.4.12, KDE Platform/SDK 6.11 e PySide BaseApp 6.11.
Il self-test usa Python 3.13.15. Pypdf 6.21.4 e IfcOpenShell 0.9.0.post1 restano fissati dalla ricetta con hash PyPI;
questa revisione aggiorna i sorgenti applicativi, mantenendo le dipendenze gia costruite.

## Bundle verificato

```text
C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\dist\packages-20261029-R04\meridiana-0.1.0-preview20261029-R04-linux-x86_64.flatpak
```

- [V] Dimensione: **185.410.688 byte**.
- [V] SHA-256: `08b4babd1b5876d2ffb33c68d1927fadae565d475625d804f70330be36ee78c8`.
- [V] Copia Windows riletta e verificata con lo stesso SHA-256. Installer e ZIP Windows della sessione principale
  restano accanto al bundle; nessun file preesistente è stato sostituito.
- [V] Importazione in `bundle-check-repo-r05`, nuovo repository OSTree senza installare l'app.
  `ostree fsck` verifica **21.749 oggetti**, senza errori. Commit importato identico all'export:
  `44f11e801b714ff7b19bb34bb80e792fe03cfe5ec52730bdecf71f0127c890a5`.
- [V] Catalogo italiano riletto anche dal repository importato dal bundle.
- [V] Self-test del programma impacchettato, `flatpak-builder --run` e Qt offscreen:
  **0 errori in 16,70 s**; 128 moduli posati, export IFC4 e riapertura di 128 `IfcSolarDevice`
  (235.551 byte), energia positiva di 23.683 kWh/anno, PDF di 1.634.423 byte, finestra acquisita 1400 x 900.
- [V] Prova aggiuntiva nel pacchetto: `.mer` ZIP con prima voce MIME non compressa, schema logico **19**, namespace
  BIM e `SupportPlane` salvati e riaperti; superficie IFC4 virtuale esportata e importata esattamente, ancora senza
  moduli; GUID stabile al secondo export; validazione dello schema IFC4 senza errori; PDF pypdf scritto e riletto;
  rifiuto di `1e999` e `NaN`; traduzione italiana del nuovo supporto e registrazione MIME. `pip check` non trova
  requisiti mancanti.
- [V] Confrontati tutti i 337 file dello snapshot con l'albero congelato, applicando la sola normalizzazione LF
  descritta sotto: nessuna differenza logica. I 332 file comuni con il manifest principale
  `build/source-manifest-20261029-R10.json` coincidono. Anche i 315 file effettivamente installati di codice,
  risorse e manuale coincidono con lo snapshot.

La revisione consegnata si chiama R04; i sorgenti/build locali si chiamano R05 perché la prima R04 era stata fermata
per la revisione del controllo della posa nell'operazione asincrona. La correzione finale è inclusa in R05.

### Terminazioni di riga e ripresa

[V] Il checkout Windows presenta CRLF. Il primo tentativo `source-r04/build-dir-r04` si è fermato su
`desktop-file-validate`, che richiede LF. Il secondo, `source-r04-lf/build-dir-r04-lf`, ha superato il build e l'export,
ma il congelamento è stato revocato prima del bundle per correggere la ricerca su posa superata. Entrambi i tentativi
rimangono conservati; nessun bundle di quei sorgenti superati è stato creato.

[V] Nella sola copia Linux finale sono stati convertiti CRLF in LF per `bin/meridiana` e
`data/io.github.daniel_g_carrasco.meridiana.desktop`. Il codice logico e i sorgenti Windows restano identici.
La scansione delle prime righe degli script ha individuato anche `tools/compile_po.py`, che il manifest invoca
esplicitamente con `python3`, quindi il suo shebang CRLF non viene usato per l'avvio.

[V] Il build R05 usa `--disable-download` e riutilizza la cache esistente. Il namespace della cache del builder
dipende dal percorso assoluto del manifest: i 13 riferimenti delle sole dipendenze sono stati replicati nel nuovo
namespace `source-r05`, conservando quelli precedenti. Il log mostra cache hit delle dipendenze e ricostruzione
del modulo applicativo. Non sono stati ripetuti download grandi.

[V] Il primo comando del probe supplementare usava direttamente `python3` senza il `PYTHONPATH` impostato dal launcher
e si è fermato prima di importare l'app. Il comando corretto, con `PYTHONPATH=/app/share/meridiana`, ha superato tutte
le prove. Il log iniziale rimane in `smoke-r05/package-probe.log`; il risultato valido è `package-probe-rerun.log`.
Non è stata necessaria alcuna modifica ai sorgenti applicativi dopo il congelamento.

### Rapporti consegnati

Nella stessa directory del bundle:

```text
linux-package-receipt-R04.json
linux-self-test-R04.txt
linux-self-test-runtime-R04.log
linux-package-probe-R04.log
linux-pip-check-R04.txt
linux-bundle-import-R04.log
linux-source-manifest-R05.json
linux-parent-freeze-R10.json
linux-build-R05.log
meridiana-0.1.0-preview20261029-R04-linux-x86_64.flatpak.sha256
```

[V] La scena Qt Quick 3D è `Ready`. La prova offscreen non produce un frame GPU e lo segnala come `INFO`;
non costituisce una prova della resa interattiva 3D. L'app non è stata installata nel profilo utente.
L'associazione al doppio clic da un desktop Linux installato rimane da provare.

Percorsi WSL finali nella directory di lavoro indicata in fondo: `source-r05`, `build-dir-r05`, `repo-r05`,
`smoke-r05`, `bundle-check-repo-r05`. I comandi eseguiti sono conservati nel workspace in
`build/flatpak-r05-driver.sh` e `build/flatpak-r05-finish.sh`; il probe è in `build/flatpak-r04-probe.py`.

## Directory di lavoro conservata

```text
\\wsl.localhost\openSUSE-Tumbleweed\home\daniel\meridiana-flatpak-20261029-172631
```

Il rapporto descrive build e verifiche eseguite; non attesta una pubblicazione remota o un'installazione sul profilo
utente. Il workflow remoto non e stato avviato. Non sono stati creati commit da questo agente.
