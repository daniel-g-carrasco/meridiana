# Confronto con PVsyst su report pubblici

Prova del 22/10/2026. Il motore di producibilità di Meridiana (`src/meridiana/energy/simulate.py`) è stato messo accanto a report PVsyst veri, pubblicati da portali VIA, enti pubblici e università. Lo strumento è `tools/compare_pvsyst.py`; i casi sono descritti in `docs/studio/11-pvsyst-casi-di-confronto.md`. I PDF e i dati estratti restano fuori dal repository, in `C:\Users\utente\dev\meridiana-prove\pvsyst-report-pubblici\`.

## Come si confronta

- **Meteo.** Il report non contiene l'anno orario (Meteonorm, Solargis e Solcast non sono pubblici). Meridiana parte dall'anno tipo PVGIS del sito e ne riscala ogni mese: irradiazione globale e diffusa orizzontale e temperatura media diventano quelle del report. Dentro il mese le ore restano quelle di PVGIS, quindi trasposizione e ritagli dell'inverter non possono coincidere al decimo.
- **Componenti.**
  - Il modulo è quello del catalogo quando il modello c'è (lista CEC); altrimenti è il modulo «tipico» di Meridiana alla stessa potenza, e lo strumento lo dice.
  - Lo stesso vale per l'inverter: si usa il suo rendimento pesato. In mancanza si prende la perdita «in funzionamento» del report.
- **Perdite e geometria come nel report:**
  - caso termico dall'Uc;
  - profilo IAM o ASHRAE;
  - sporcamento, qualità (PVsyst stampa la qualità negativa come guadagno), LID, mismatch di moduli e stringhe;
  - cavi in continua a STC, cavi in alternata riportati alla potenza dell'inverter;
  - orizzonte stampato e file con passo e larghezza; i moduli in altezza nella tavola sono ricavati dalla sua larghezza.
- **Cosa manca in Meridiana:** ausiliari, trasformatore MT e linee. Il confronto è pieno fino all'uscita dell'inverter. Le stesse voci mancano nella riga «E_Grid».
- **Casi saltati:** inseguitori e bifacciali (Meridiana non li calcola ancora), report senza coordinate, inverter senza numero o potenza.

## Il risultato

Energia all'uscita dell'inverter e PR, dopo la correzione del modello delle file (sotto):

| Caso | Tipo | Modulo | Uscita inverter | PR (punti) | Nota |
|---|---|---|---|---|---|
| sa-neom-fixed | 5 MWp, 30°, deserto | tipico | +0,2% | +0,68 | Nessuna ombra: il caso più pulito. Temperatura −9,9% contro −11,3% (modulo tipico TOPCon, γ più basso). |
| it-rotello-fixed-tables | 52 MWp su collina | CEC Trina | −0,6% | +0,44 | La collina non è modellata; restano le file. |
| uk-pelham-fixed | 52,6 MWp, 52°N, file | tipico | −1,7% | −0,04 | Ritaglio −2,1% contro −0,6% a DC/AC 1,40: dipende dalle ore di picco del meteo. |
| it-montescaglioso-fixed | 5,6 MWp, file 2 in verticale | CEC Risen | −3,6% | −1,83 | PVsyst usa le ombre «lineari»; Meridiana aggiunge l'effetto elettrico delle file (−3,2%). |
| gr-peaki-fixed-commercial | 397 kWp | tipico | +3,9% | +3,38 | 49 stringhe su 40 ingressi: PVsyst perde −1,9% per sovraccarico sui singoli MPPT, Meridiana somma la potenza. |
| it-altamura-sheds-cigs | 1,6 MWp, film sottile CIGS | tipico | +2,5% | +3,11 | Il CIGS non è in catalogo: il modulo tipico perde meno per irraggiamento (−0,2% contro −2,0%). |
| es-lafact-two-orientations-roof | 590 kWp, ovest e nord | tipico | −2,4% | +0,37 | Trasposizione −2,8% su due falde insolite: forma oraria del meteo. |
| uk-camden-wildcourt-roof-v6 | 5,9 kWp tetto, PVsyst 6 | tipico | −0,8% | −0,36 | Scena 3D non ricostruita. |
| uk-camden-bloo-optimizers-v6 | 8,8 kWp tetto, PVsyst 6 | tipico | +18,7% | +14,6 | Scena 3D con ombre −9,6% e −5,4% non ricostruita: escluso dalla sintesi. |

Fino all'energia nominale del campo (trasposizione, orizzonte, ombre lineari, IAM, sporcamento) Meridiana resta entro l'1% nei casi senza scena 3D; la trasposizione è entro lo 0,6%, tranne LaFact. Le differenze più grandi vengono da cose che Meridiana non modella ancora:
- il sovraccarico dei singoli MPPT;
- i moduli a film sottile;
- l'effetto elettrico, che PVsyst lineare non conta.

## L'errore trovato e corretto

Il confronto ha mostrato che Meridiana perdeva meno di PVsyst per le ombre tra le file (−0,81% contro −2,20% a Montescaglioso). I fattori stampati nel report spiegano la differenza: PVsyst nasconde il 4,4% della diffusa e il 76,9% della luce riflessa dal suolo.

1. **Diffusa del cielo.** Meridiana usava la formula di Passias (`pvlib.shading.sky_diffuse_passias`), che dà (1 − cos ψ)/2 con l'angolo ψ misurato dall'orizzontale. Per un modulo inclinato di β la parte di cielo nascosta è invece (cos β − cos(β+ψ))/(1 + cos β). A Montescaglioso la formula di Passias dava 0,86%. Il fattore di vista delle file infinite integrato sull'altezza (`pvlib.bifacial.utils.vf_row_sky_2d_integ`) dà 4,50%, e la scena di PVsyst 4,4%; a Pelham 3,08% contro 3,6%. Ora Meridiana usa il fattore di vista.
2. **Luce riflessa dal suolo.** Meridiana non la toglieva. Ora le file dietro la prima ricevono quella che il modello delle file infinite di pvlib calcola (Mikofski et al. 2019): il suolo davanti è in parte nascosto dalla fila, in parte nella sua ombra, e vede meno cielo.

Dopo la correzione le ombre tra le file valgono −2,07% contro −2,20% a Montescaglioso e −2,30% contro −2,92% a Pelham. Pelham ha anche siepi e terreno nella scena.

## Cosa viene dopo

- Il sovraccarico per MPPT, cioè le stringhe sugli ingressi con il ritaglio per ingresso.
- Il film sottile, con i suoi coefficienti.
- Inseguitori e bifacciali, per i 15 casi saltati.
- Ausiliari, trasformatore MT e linee, per confrontare anche E_Grid.
- Con la prova di PVsyst 8 si potranno usare gli stessi file meteo (MET) e gli stessi moduli (PAN), e il confronto diventerà ora per ora.
