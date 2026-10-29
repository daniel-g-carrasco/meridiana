# Revisione UX, formato .mer e pacchetti del 29 ottobre 2026

Base del lotto: `209bd9a`. Verifica dei sorgenti conclusa, pacchetti in collaudo finale. R224 corretto e verificato; gli esiti dei pacchetti sono registrati separatamente.
I log grezzi sono conservati in `build/`, le fotografie finali della UI in
`docs/revisioni/foto/ux-ripresa-20261029/light-R04` e `dark-R04`.

## Interfaccia verificata

- Nuovo progetto: il mondo offline appare subito; ricerca locale dei comuni separata dalla query online,
  senza suffisso ISTAT nel nome. Due campi coordinate, incolla coppia/link, virgola decimale italiana.
  Dati facoltativi sempre visibili e disattivati con spunta condivisa; spazio privacy stabile.
- Richieste reali Nominatim riuscite per Carignano, Torino e Piazza San Carlo, Torino, con lo stesso URL e
  User-Agent del programma. Due risultati per ciascuna, log `build/geocoding-live-20261029.json`.
- Sfumature delle schede fino all'ultimo pixel; cifre delle fasi e aiuti centrati sui contorni visibili.
  Popup limitati a 360 px. La correzione della preferenza DWM richiede ancora controllo degli angoli sul
  desktop Windows: la fotografia offscreen non dimostra il risultato del compositore.
- Bussola con perno fisso, freccia piu piccola e N solidale. Se collide con la barra, passa in basso con
  animazione; movimento ridotto rispettato. Prove su rotazione e ridimensionamento.
- Inverter operativo nella prima scheda; tutti i suoi ingressi visibili. Selezionare una stringa passa al
  relativo inverter; cambiare inverter elimina la selezione nascosta. Disegna stringa usa l'inverter operativo.
  Gestione dell'intero impianto esplicita, comandi automatici globali dichiarati.
- Indicatori B a fondo tenue, margine sinistro 6 px e destro 8 px, distanza simbolo/numero 4 px, zero attenuato.
- Pannello Aiuto nell'angolo richiudibile sia dal comando destro sia da quello inferiore, con ripristino del gruppo.
- Meridio: suggerimenti compatti ripiegabili, fase con nome leggibile e invio esplicito. Navigazione verso
  destinazioni enumerate e contorno temporaneo sul controllo esatto, senza cambiare valore o focus.
  La distinzione grafica conversazione/ruoli richiesta dopo la preview resta R221, non completata da questo lotto.

## .mer

ZIP con MIME, manifesto, JSON del progetto e risorse binarie deduplicate per SHA-256. Il formato logico resta18;
la versione del contenitore è1. Il backup precedente viene validato, le versioni future non aprono una vecchia
copia per errore. Limiti e lettura senza estrazione di percorsi arbitrari. I numeri JSON non finiti sono rifiutati
anche quando derivano da un esponente eccessivo: regressione riprodotta con 1e999 e -1e999, corretta e provata.

Daniel ha escluso la retrocompatibilita di prodotto con .meridiana: Meridiana non è ancora usata in produzione.
Resta un adattatore JSON per le fixture storiche. API di salvataggio ancora sincrona; i limiti e le misure sono
nella specifica `docs/superpowers/specs/2026-10-29-formato-mer-pacchetti-design.md`.

## Template Qt

Commit `b98bc3797a926df8a56797c05cfe3ee97a32497f`: sfumature, popup, cifre, indicatori B e spotlight, galleria
ed esempio. Preservate le tre modifiche preesistenti del template. Suite127 prove prima del seguito spotlight,
poi6 mirate per il seguito. Manifest Meridiana `template-sync-qt_R02.json` e tabelle `_R03.json`:15+1 mapping
verificati con hash normalizzati. Questo non equivale a parita di tutti i comportamenti fra le app:
R223 richiede ancora l'audit dell'animazione File e delle differenze con Quotario.

## Prove

La suite generale è stata avviata una volta per gruppi. Dopo difetti o modifiche successive si ripetono i gruppi
coinvolti. Non si presenta un primo passaggio fallito come un passaggio interamente verde.

- Nucleo:869 prove, una sola aspettativa rimasta sul vecchio suffisso; corretta a .mer,7 prove mirate verdi.
- Calcoli:193 verdi prima della correzione R224; rieseguiti dopo, esito dettagliato nel punto R224 sotto.
- Formati:84 verdi; successiva regressione numeri non finiti,15 prove del codec verdi.
- Widget:440 prove, un errore di ownership nella fixture del tema condiviso. Sequenza10prove riproduceva
  l'errore: corretta senza cambiare asserzioni, verde anche dopo smaltimento oggetti Qt e riuso della cache.
- Finestra:165 prove in1452,764s, quattro fallimenti nel passaggio generale. Selftest iniziale della fixture
  senza stringhe risolto dal collegamento esplicito e passato nel lotto108; aspettativa sulla vecchia posizione
  della bussola aggiornata al comportamento richiesto e test mirato verde. Il test temporizzato dello spinner
  passa nella ripetizione isolata. Resta il limite prestazionale del tema:1,966s contro1s nella suite,
  1,032s nella ripetizione. La soglia non è stata modificata e non si dichiara la suite interamente verde.
- Totale passaggio generale:1751 prove. Le correzioni successive sono verificate nei gruppi pertinenti.
- R224:108 prove mirate verdi, gruppo calcoli201 con200 verdi e sola vecchia frase di test aggiornata,
  classe relativa5/5 verde. PDF, record, CSV, UI economica e .mer verificati anche con energia zero.
  Vedere `produzione-moduli-collegati-20261029.md`.
- Selftest finale da sorgente:0 errori in18,16s, export e riapertura IFC4 con128 moduli, energia23683kWh,
  PDF1590540byte. Nuova fixture con38 moduli collegati su128, gli altri90 non producono.
- Ruff src/tests/tools e catalogo GNUmsgfmt verificati; sei traduzioni obsolete duplicate rimosse conservando
  copia del PO in build/it-before-msgfmt-cleanup-20261029.po.

## Pacchetti e limiti

Le anteprime Windows R01-R03 e Flatpak R01 precedono R224 e non sono la consegna definitiva.
Il selftest Windows R03 passa, ma il log non contiene le importazioni IFC/PDF aggiunte durante una build:
la cache PYZ ha conservato il codice precedente. Il pacchetto definitivo deve partire da una directory build
nuova dopo il congelamento dei sorgenti, con controllo del log e confronto delle impronte.
Il bundle Windows R04 ha poi rilevato un difetto reale: ifcopenshell.geom assente. Ricetta corretta con
il modulo geometrico e le famiglie API caricate dinamicamente dall'export; il selftest ora esporta e riapre
un IFC4 completo contando i128 moduli, oltre a verificare le importazioni. R05 interrotto prima di confezionare;
R06 ricostruito da directory nuova: il roundtrip ha rilevato le tabelle JSON IFC mancanti. La ricetta ora raccoglie le risorse dati di IfcOpenShell; R07 ha poi esposto il bootstrap EXPRESS: senza parser fisico e moduli rules, IfcOpenShell avviava sys.executable bootstrap.py, cioe una seconda istanza del programma congelato. La prova diagnostica con parser/regole aggiunti supera il roundtrip IFC e termina con 0 errori in 10,81 s. La ricetta include ora anche tali sorgenti e le regole caricate dinamicamente; R08 ricostruito da zero con questa soluzione: selftest del binario con exit 0 e 0 errori in 28,21 s; IFC4 riaperto con 128 moduli e 195263 byte, energia 23683 kWh, PDF 1590540 byte. La fixture salva .mer e lo apre nella finestra.
La prova Flatpak e le verifiche OSTree sono in `pacchetto-flatpak-20261029.md`.
Nessuna installazione sull'ambiente reale, firma o pubblicazione di release è stata dichiarata eseguita.

## Richieste successive conservate

R215 dimensionamento/stringatura globale, R216 est-ovest, R217 pensiline, R219 icona Allinea, R220 tipografia e
relazioni, R221 conversazione Meridio, R222 rientro gruppi Verifiche, R223 armonizzazione comportamenti.
R224 moduli scollegati è corretto e integrato nel commit 246ec58. La direzione HTML File/Impostazioni è approvata da Daniel;
la ristrutturazione completa resta da attuare. I nuovi messaggi aggiungono requisiti senza cancellare questi esiti.

Richieste aggiunte in seguito: R225-R229 revisione ombre/ottimizzatori/MPPT; R230 BIM; R231 importazione IFC e superfici ausiliarie; R232 hover calendario; R233-R234 tooltip. Restano in coda, non dichiarate implementate.

## Consegna locale verificata R03

Cartella `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\dist\packages-20261029-R03`.
Windows usa il bundle R08; Linux il Flatpak R03. Installer compilato con Inno Setup 6.7.4 in 98,407 s,
ZIP provato con `7z t` (4325 file, 519120192 byte decompressi), Flatpak importato in OSTree e fsck senza errori.
Selftest Windows: exit 0, 0 errori in 28,21 s. Selftest Linux: 0 errori in 21,57 s.
I controlli non sostituiscono installazione/disinstallazione e prova GPU sul desktop, ancora da eseguire.
Nessuna release pubblicata o firma applicata. Rapporti e `SHA256SUMS.txt` accompagnano gli artefatti.

| File | Byte | SHA-256 |
| --- | ---: | --- |
| meridiana-0.1.0-preview20261029-R03-linux-x86_64.flatpak | 185271488 | `fe8719717a27d23e8f31e088a250095f04dfc850fb5c4a9ffe2302f7dc9d761d` |
| meridiana-0.1.0-preview20261029-R03-windows-x64.zip | 218297157 | `ea5631d6374568a96cf80b2874d5344d12deeb183842315042b46b8ba924d89c` |
| meridiana-setup-v0.1.0-preview20261029-R03-windows-x64.exe | 155112597 | `1adbc45123c466f04b519e8f2fb6f6432a1d1667c5d05a9238c65e4e7f6ef294` |
