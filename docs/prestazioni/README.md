# Prestazioni: fluidità della finestra

Riferimento per riconoscere un rallentamento o un miglioramento. Daniel, 25/10/2026: «salva tutti questi risultati per
riferimento futuro in vista di possibili rallentamenti o miglioramenti»; il metro è un programma «rapido» come VS Code
(R120: «Io voglio che Meridiana sia bello agile»).

## Come si misura

```
python tools/fluidity.py --out docs/prestazioni/AAAA-MM-GG/<nome>.json [--on-screen] [--no-3d] [--sequence all]
```

- Finestra vera sulla piattaforma Windows (mai `offscreen`, che disegna in un altro modo), cartelle temporanee, il
  progetto di prova `%USERPROFILE%\dev\meridiana-prove\Prova capannone Rho.meridiana`, finestra 1600×960.
- Una sequenza fissa di gesti, ognuno misurato fino a quando la finestra torna quieta. Trascinamenti, rotelle e
  passaggi del mouse vanno a un passo ogni 16 ms, cioè a 60 Hz. Il tempo di un gesto da 40 passi è quindi almeno
  640 ms: conta quanto lo supera, e soprattutto i blocchi.
- **Blocco**: ogni volta che la finestra non risponde per più di 30 ms. A 60 fotogrammi al secondo un fotogramma
  dura 16 ms, quindi un blocco è almeno un fotogramma perso: è lo «scatto» che si sente.
- `--on-screen` apre la finestra sullo schermo principale: misura anche quanto costa a Windows mostrarla. Si usa
  solo con il via di Daniel, perché per un minuto la finestra copre il suo lavoro. Senza, la finestra sta fuori da
  ogni schermo e si misura il solo lavoro del programma.
- `--no-3d` mette un riquadro vuoto al posto della vista 3D (la `QQuickWidget`): è la prova A/B del suo peso.
- Ogni misura scrive un file JSON con data, commit, schermo, macchina e versione di Qt. I file stanno in una
  cartella per giorno, accanto a questa pagina.

**Obiettivo** (R120): nessun blocco durante trascinamenti, rotelle e ridimensionamenti; al massimo un blocco sotto i
50 ms per un cambio di fase o di pagina; il programma aperto con il progetto in meno di 3 s.

**Macchina di riferimento**: il PC di Daniel. Intel i7-12700H, Iris Xe con NVIDIA RTX A2000 Laptop, 32 GB, Windows 11
26100, schermo DELL P2415Q 3840×2160 al 200 %, Qt 6.12.0.

## Misure del 25/10/2026 (prima delle correzioni)

Commit 242e097, cartella `2026-10-25`. Cinque misure: la sequenza base fuori schermo, poi sul Dell con e senza
vista 3D, e la sequenza dei grafici sul Dell con e senza vista 3D. Sul Dell la prima misura con il 3D si è fermata
dopo il bordo destro, perché il processo di prova è caduto: è da indagare.

### Sequenza base

| Gesto | Fuori schermo | Sul Dell | Sul Dell senza 3D |
|---|---|---|---|
| apertura con il progetto (vedi la nota sotto) | - | primo disegno 3,8-4,3 s, anno 4,5-5,0 s | - |
| fase Impianto, la prima volta: blocchi (peggiore) | 2 (102 ms) | 3 (103 ms) | 4 (93 ms) |
| fase Consumi: blocchi (peggiore) | 1 (42 ms) | 1 (87 ms) | 1 (64 ms) |
| pagina File aperta: blocchi (peggiore) | 0 | 2 (59 ms) | 2 (41 ms) |
| bordo del pannello sinistro, 40 passi: blocchi (tempo bloccato) | 0 | **32 (1125 ms)** | **0** |
| bordo del pannello destro, 40 passi: blocchi (tempo bloccato) | 0 | **44 (1825 ms)** | 16 (570 ms) |
| rotella su Verifiche, albero, pianta, 3D | 0 | 0 | 0 |
| pianta e 3D trascinati, 40 passi | 0 | 0 | 0 |
| finestra ridimensionata, 15 passi: blocchi (tempo bloccato) | 0 | non misurato | 14 (624 ms) |

Nota sull'apertura: nei file JSON di questa notte `opened_ms` (7,5-8,5 s) comprende un'attesa fissa di 6 s dello
strumento, quindi non è il tempo di apertura (lo era stato detto a Daniel per errore, poi corretto). Il tempo vero è
stato misurato a parte, dall'avvio del processo, sul Dell: primo disegno della finestra a 3,8-4,3 s, anno calcolato a
4,5-5,0 s. Dal 25/10 notte lo strumento misura `opened` come costruzione della finestra, primo disegno e anno
calcolato, contati dalla costruzione della finestra; fuori schermo Windows disegna tardi, quindi il primo disegno vale
solo con `--on-screen`.

### Sequenza dei grafici (sul Dell)

| Gesto | Con la vista 3D | Senza |
|---|---|---|
| Producibilità aperta: blocchi (peggiore) | 3 (80 ms) | 3 (128 ms) |
| linguette dei grafici di Producibilità e Bilancio | nessun blocco | nessun blocco |
| linguette dei grafici dei Consumi | blocchi da 37-77 ms; la linguetta 5: **239 ms** | 31-62 ms; la 5: 249 ms |
| mouse sopra un grafico, rotella su un grafico | nessun blocco | nessun blocco |
| bordo destro, Producibilità: blocchi (tempo bloccato) | 27 (1001 ms) | 18 (599 ms) |
| bordo destro, Consumi | **63 (2211 ms)** | 15 (479 ms) |
| bordo destro, Bilancio | 38 (1278 ms) | 5 (175 ms) |
| finestra ridimensionata, Producibilità | 14 (804 ms), peggiore 83 ms | 14 (584 ms) |

### Cosa dicono

1. **La vista 3D come `QQuickWidget` pesa su tutta la finestra**, anche quando non si vede. Obbliga Qt a ricomporre
   la finestra attraverso la scheda grafica a ogni fotogramma: sul 4K sono circa 30 ms per fotogramma. Il bordo del
   pannello sinistro passa da 32 blocchi a nessuno togliendola. La correzione è montarla come finestra nativa
   (`QWidget.createWindowContainer`), come fanno i programmi CAD fatti con Qt.
2. **Il pannello destro e i grafici rifanno l'impaginazione a ogni passo** di un ridimensionamento. Dal profilo
   (`profilo-bordo-destro.txt`): `cards.arena` cerca tutti i figli della finestra a ogni movimento, 507 volte in 40
   passi; `sizeHint` delle righe delle Verifiche e dei titoli delle schede viene chiesto migliaia di volte.
3. **Il primo arrivo in una fase** costa da 40 a 130 ms, per la costruzione e l'impaginazione delle pagine.
4. **Una linguetta dei Consumi** blocca da sola per circa 240 ms.
5. Il lavoro del programma, fuori schermo, è piccolo: da 1 a 5 ms per passo di trascinamento. Il costo sta nel
   mostrare la finestra.

## Correzioni del 25/10/2026 notte (ramo `fluidita`)

Ognuna trovata con il profilo sul Dell e verificata misurando di nuovo. I tempi assoluti di questa notte sono un po'
rumorosi: sullo stesso PC lavoravano tre agenti con le loro prove.

| Correzione | Effetto misurato |
|---|---|
| vista 3D disegnata in un'immagine (`ui/quick_image.py`), non più `QQuickWidget` | la finestra torna alla composizione semplice; nelle fasi senza 3D i blocchi del bordo sinistro scendono da 8-19 a 0-5 |
| durante un ridimensionamento la scena 3D resta l'ultima immagine e si ridisegna da ferma | bordo sinistro in Modello: da 32-40 blocchi a 0 |
| cubo di navigazione conservato come immagine finché la vista non ruota | 8 ms in meno a ogni fotogramma del 3D |
| sguardo di Meridio letto al passo della sua animazione, non con un filtro su tutti gli eventi | ~5 ms in meno a ogni passo di trascinamento |
| barre e schede della finestra cercate solo tra i figli diretti; misura dei titoli conservata; righe delle Verifiche reimpaginate da ferme | bordo destro: da 44-50 blocchi a 12-14 |
| un solo filtro di eventi per l'applicazione (`ui/app_events.py`) al posto di tre | ogni evento attraversa Python una volta, non tre |
| riga delle fasi conservata come immagine; scorrimento della linguetta 180 ms (R97) | cambio di fase senza blocchi in Producibilità, Relazione, Modello |
| elenco dei caratteri di matplotlib ridotto ai suoi e ai nostri (da ~1800 a 40), al primo uso | prime formule di «Come è calcolato» da 608 a 43 ms; linguetta da 240-950 a 60-75 ms |
| barra dei colori delle mappe disegnata semplice al posto di `ColorBarItem` | linguette «Giorno tipo» e «Anno» dei Consumi da ~70 a ~25 ms |
| stringatura sul filo della finestra solo con pvlib caricato per intero | all'apertura del progetto la finestra non si ferma più 1,5 s; primo disegno da 3,8-4,3 s a 2,6-2,8 s, anno da 4,5-5,0 a 2,8-3,0 s |

Restano: ridimensionare la finestra (circa 40 ms per passo: Qt rialloca e ridipinge da capo l'intera finestra 4K, 32
MB), il bordo destro nelle fasi con grafici (impaginazione dei grafici), un blocco di circa 50 ms entrando in Consumi e
Bilancio (disegno dei grafici), la pagina File (35-40 ms). Ridipingere tutta la finestra costa 18-22 ms sul Dell: è il
pavimento finché il disegno non si alleggerisce.

## Linux (portatile di Daniel), 25/10/2026 notte

Framework 13, AMD Phoenix, schermo 2880×1920 a 120 Hz al 200 % (1440×960 logici), Fedora con Niri (Wayland),
Python 3.14, PySide6 6.12. La finestra massimizzata (`--maximized`, come Super+M: in una colonna di Niri, larga metà
schermo, la finestra mostra la sola pianta). Stessa sequenza, la versione di base (242e097) e quella con le correzioni
(d399355): `linux-laptop-base.json` e `linux-laptop-fluidita.json`.

| Gesto | Base | Con le correzioni |
|---|---|---|
| avvio: finestra costruita, primo disegno, anno | 1,1 s, 1,5 s, 2,0 s | 0,6 s, 0,7 s, 1,2 s |
| bordo destro, Modello: blocchi | 10 | 0 |
| bordo destro, Consumi: blocchi | 37 | 0 |
| linguette dei grafici dei Consumi | blocchi da 33-59 ms, «Come è calcolato» 85 ms | nessuno, «Come è calcolato» 55 ms |
| pagina File aperta | 2 blocchi | 0 |
| cambio di fase | un blocco da 47-76 ms | un blocco da 30-50 ms |

La prima prova su Linux ha trovato un difetto della vista 3D nuova: su Wayland Qt manda `showEvent` quando la vista
non è ancora visibile, il fotogramma chiesto allora la trovava nascosta e la vista restava vuota. Corretto (il
fotogramma si chiede al giro dopo) e verificato con una foto: la scena esce dritta e con i colori giusti con OpenGL.

Linux contro Windows: il portatile è più fluido del PC di Daniel (nessun blocco nei bordi contro 12-14), ma l'hardware
è diverso e il suo schermo ha 5,5 milioni di pixel contro gli 8,3 del Dell 4K; il confronto pulito tra i due sistemi
andrebbe fatto sulla stessa macchina.

Prova A/B dello stile delle barre di scorrimento (`ui/scrollbars.ScrollStyle`, uno stile in Python che sostituisce misure e disegno dei controlli complessi): con lo stile Fusion semplice i blocchi del bordo destro sono gli stessi (Modello 14 contro 10-12, Consumi 35-36 contro 35-36), quindi non pesa (`bordi-schermo-senza-scrollstyle.json`). Il punto debole che resta è il bordo destro nelle fasi con i grafici (Consumi, Bilancio: 35-38 blocchi), da affrontare congelando i grafici durante il trascinamento come la vista 3D.

## Storico

Una riga per ogni misura nuova: data, commit, cosa era cambiato, i numeri che contano. Se un numero peggiora,
la riga lo dice.

| Data | Commit | Cosa | Bordo sinistro, Modello (blocchi) | Bordo destro, Modello (blocchi) | Primo disegno / anno |
|---|---|---|---|---|---|
| 25/10/2026 | 242e097 | riferimento, prima delle correzioni | 32 | 44 | 3,8-4,3 s / 4,5-5,0 s |
| 25/10/2026 | 05a1399 | 3D in immagine, cubo, sguardo, ricerche dirette, Verifiche | 0 | 14-21 | |
| 25/10/2026 | d312585 | riga delle fasi, un filtro solo, scorrimento 180 ms | 0 | 12-14 | |
| 25/10/2026 | b5c0aeb | avvio: pvlib e matplotlib fuori dal filo della finestra | | | 2,6-2,8 s / 2,8-3,0 s |
| 25/10/2026 | ebddea1 (primo commit pubblico 3b1d8c8) | codice finale con grafica, stringatura e Meridio uniti, PC fermo (`tutto-schermo-finale.json`, `bordi-schermo-finale.json`) | 0 | 10-12 | finestra costruita 1,1 s, primo disegno 1,2-1,4 s dalla costruzione, anno 1,8-2,0 s |
