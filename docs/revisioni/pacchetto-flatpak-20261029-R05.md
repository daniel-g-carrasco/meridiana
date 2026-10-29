# Pacchetto Flatpak R05: 29 ottobre 2026

La R05 contiene il congelamento applicativo R14, compresi formato logico 20, gruppi fisici degli ottimizzatori,
assegnazione globale delle stringhe, produzione sulla rete elettrica collegata e controlli dei risultati asincroni.
Il nome interno Linux e `r08`; la revisione consegnata e R05. I tentativi e i pacchetti precedenti restano conservati.
Ricetta e prove storiche sono in `docs/revisioni/pacchetto-flatpak-20261029.md` e nel rapporto R04.

## Artefatto verificato

```text
C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\dist\packages-20261029-R05\meridiana-linux-x86_64-20261029-R05.flatpak
```

- [V] Dimensione: **185.441.592 byte**.
- [V] SHA-256: `5b2377305aaf1352653a6f29f53b48ce3f8dfc644438fdd26e9eb1b2f53cffab`.
- [V] Copia Windows riletta e verificata con lo stesso SHA-256; creazione esclusiva dei nuovi file, senza sostituire
  file esistenti.
- [V] Importazione in un nuovo repository OSTree `bundle-check-repo-r08`: **21.752 oggetti**, nessun errore di `fsck`.
  Commit importato identico all'export:
  `ccd091d302a7c2c60d8adf5d7647e4c1f37077536467b0a849d1c4eee46dadb4`.
- [V] Catalogo italiano riletto anche dal repository importato dal bundle.

## Sorgenti e ambiente

[V] Baseline Git dichiarata: `b3c0146`. Il contenuto applicativo e individuato dal manifest del congelamento
`build/source-manifest-20261029-R14.json`, SHA-256
`a3c59ea8c62c716aa485dfdbe0c6129a8d45a7f028d08c6aec4811153c18e795`.
Il campo `application_commit` della ricevuta resta `null`, da collegare al commit applicativo dopo l'integrazione
della sessione principale. Non sono stati creati commit da questo agente.

[V] Snapshot Linux: **340 file**. Tutti i **339 file comuni** con il manifest principale corrispondono, applicando
la sola normalizzazione CRLF in LF a `bin/meridiana` e
`data/io.github.daniel_g_carrasco.meridiana.desktop` nella copia Linux. I sorgenti Windows non sono stati cambiati.
Il file presente soltanto nel manifest principale e il catalogo compilato `locale/it/LC_MESSAGES/meridiana.mo`;
quello presente soltanto nello snapshot e `tools/compile_po.py`. Il build compila il catalogo dal PO congelato:
le **3.529 voci** dei cataloghi Windows e Linux sono state confrontate con GNUTranslations e sono identiche.
Non si assume identita binaria dei due compilatori gettext. Anche i **318 file installati** di codice, risorse e
manuale corrispondono allo snapshot.

[V] Build in WSL `openSUSE-Tumbleweed`, Flatpak 1.18.4, flatpak-builder 1.4.12, KDE Platform/SDK 6.11,
PySide BaseApp 6.11 e Python 3.13.15 nel pacchetto. Il build usa `--disable-download`, replica i 13 riferimenti
di cache delle sole dipendenze nel nuovo namespace e ricostruisce il modulo applicativo. Le ricette fissate con
hash PyPI, comprese pypdf 6.21.4 e IfcOpenShell 0.9.0.post1, non sono state modificate in questa revisione.
Non sono stati ripetuti download grandi.

## Prove eseguite

[V] Self-test del programma impacchettato con `flatpak-builder --run`, Qt offscreen e cartelle di prova isolate:
**0 errori in 21,85 s**. Catalogo prodotti di 24.262 record; import di pypdf e `ifcopenshell.geom`; finestra 1400 x 900;
posa di 128 moduli; export IFC4 e riapertura di 128 `IfcSolarDevice` (235.551 byte); energia positiva di
23.922 kWh/anno dalla fixture collegata di 57,6 kWp; PDF di 1.602.011 byte.

[V] Sei prove supplementari nel pacchetto:

1. `.mer` ZIP, prima voce MIME non compressa, formato logico **20**, namespace BIM e piano ausiliario salvati e riaperti.
2. Superficie IFC4 virtuale: validazione dello schema senza errori, GUID stabile tra export e importazione esatta,
   ancora senza moduli.
3. Scrittura e rilettura PDF con pypdf.
4. Rifiuto dei numeri non finiti `1e999` e `NaN` nel lettore del progetto.
5. Traduzione italiana del supporto e registrazione MIME Linux.
6. Persistenza dei gruppi fisici espliciti degli ottimizzatori nel formato 20.

[V] `pip check`: nessun requisito mancante. Validazione desktop e metainfo superata nel build. La scena Qt Quick 3D
e `Ready`; il self-test offscreen segnala correttamente che non viene disegnato un frame GPU. La prova non attesta
la resa interattiva 3D o l'associazione al doppio clic in una sessione desktop Linux installata.

L'app non e stata installata nel profilo utente durante queste verifiche. Il workflow remoto non e stato avviato;
non sono stati pubblicati pacchetti o rilasci. L'installazione sul portatile Linux via SSH resta operazione distinta
della sessione principale.

## Tracciabilita e tentativi conservati

[V] `source-r06/build-dir-r06/repo-r06` conserva il congelamento R12 superato; `source-r07/build-dir-r07/repo-r07`
conserva R13. Entrambi hanno superato self-test e probe; il driver e stato fermato prima di produrre un bundle da
consegnare quando la sessione principale ha revocato il relativo congelamento. R14 in `source-r08` include il controllo
che rifiuta un vecchio risultato PlantJob quando un nuovo calcolo impianto e gia accodato.

I percorsi WSL finali sono `source-r08`, `build-dir-r08`, `repo-r08`, `smoke-r08` e `bundle-check-repo-r08`, sotto:

```text
\\wsl.localhost\openSUSE-Tumbleweed\home\daniel\meridiana-flatpak-20261029-172631
```

I comandi sono conservati nel workspace in `build/flatpak-r08-driver.sh`, il confronto sorgenti in
`build/verify-flatpak-r08.py`, il probe in `build/flatpak-r05-probe.py` e la copia esclusiva con verifica hash in
`build/collect-flatpak-r05.py`.

Nella cartella R05 del bundle sono consegnati:

```text
linux-package-receipt-R05.json
linux-self-test-R05.txt
linux-self-test-runtime-R05.log
linux-package-probe-R05.log
linux-pip-check-R05.txt
linux-source-verification-R05.json
linux-bundle-import-R05.log
linux-build-R05.log
linux-bundle-build-R05.log
linux-source-manifest-R05.json
linux-parent-freeze-R05.json
meridiana-linux-x86_64-20261029-R05.flatpak.sha256
```

### Comando per la verifica sul portatile

L'AppID e `io.github.daniel_g_carrasco.meridiana`, branch `stable`. Dopo l'installazione, la sessione principale puo
eseguire il seguente self-test in una nuova cartella host. Questi comandi nativi non sono stati eseguiti da questo
agente; la prova WSL descritta sopra usa il build isolato.

```sh
mkdir "$HOME/meridiana-verifica-R05"
flatpak run --filesystem="$HOME/meridiana-verifica-R05" io.github.daniel_g_carrasco.meridiana --self-test "$HOME/meridiana-verifica-R05/self-test.txt"
```

Il self-test seleziona Qt offscreen e non apre finestre. L'esito atteso termina con `PASS all: 0 failed`.

## Adeguamento delle prove di finestra

[V] Le sole sezioni EnergyPages e PlantPhase di `tests/finestra/test_window.py` sono state adeguate senza modificare
il runtime. Produzione e confronto varianti usano una fixture esplicitamente collegata; il percorso senza hardware
verifica ancora zero produzione e consumo stimato dal contesto. Il catalogo usato dalla prova positiva fornisce
limiti MPPT e di cortocircuito completi. Le azioni attendono posa corrente e risultati dei job prima delle asserzioni.

[V] Tre prove EnergyPages verdi nel log `build/gui-energy-plant-r14.log`. Quel primo run conserva il fallimento del
vecchio PlantPhase, corretto aggiungendo le attese della posa: il successivo run finale PlantPhase e **1/1 verde in
19,561 s**, log `build/gui-plantphase-final-r14-R02.log`. Ruff e `git diff --check` sul file passano.
Nessuna suite completa e stata ripetuta da questo agente, nessun nuovo msgid introdotto.
