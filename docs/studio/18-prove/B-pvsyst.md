# B3. Meridiana contro PVsyst su casi pubblici

Prova della revisione completa (studio 18, sezione B, parte 3), 23/10/2026, ramo `revisione-completa`.
Script: `docs/studio/18-prove/confronto_pvsyst.py` (risultati in `confronto_pvsyst-risultati.txt`) e
`confronto_pvsyst_ipotesi.py` (risultati in `confronto_pvsyst_ipotesi-risultati.txt`). Lanciati dalla radice del
repository con `PYTHONPATH=src QT_QPA_PLATFORM=offscreen`, Python 3.12.6, pvlib 0.16.1, cache PVGIS in una cartella
temporanea (`--cache`). Rete usata: solo l'API di PVGIS (`re.jrc.ec.europa.eu`, versioni 5.3 e 5.2), il 23/10/2026.

Legenda: **[V]** verificato (come è detto accanto); **[I]** dedotto o ipotizzato.

---

## 0. In breve

1. **Otto casi** con rapporto PVsyst completo (7.2.11 fino a 8.0.21), tutti fissi e monofacciali: tre con il **meteo
   orario identico** a quello di PVsyst (il file `.MET` del progetto, pubblico nei campioni: India, Egitto, Kuwait), uno
   con la **stessa fonte** PVGIS (Grecia; con PVGIS 5.2 i mensili coincidono alla cifra), quattro con PVGIS **scalato
   mese per mese** sulla tabella del rapporto (Montescaglioso con 20 file e orizzonte, NEOM clima caldo, LaFact due
   falde, Pelham file con effetto elettrico). [V: `confronto_pvsyst-risultati.txt`]
2. **A parità di meteo e di modulo, la catena di Meridiana da GlobHor a EArrMPP sta entro ±1,5 % di PVsyst**, e la
   E_Grid entro ±2 % dove l'inverter è a stringa senza sovraccarico per ingresso e senza media tensione: PEAKI
   EArrMPP -0,03 %, India +1,46 %, Egitto +1,41 %, Kuwait -0,68 %; PR entro +1,8/-0,6 punti. [V: tabelle del §2]
3. Passo per passo, con lo stesso meteo: **trasposizione entro 0,05 punti** (Perez, convenzioni dell'ora e del sole
   coincidono), **IAM entro 0,15 punti** (profilo a punti letto come PVsyst), **qualità, LID, mismatch identici**;
   **temperatura: Meridiana è ottimista di 0,2-0,6 punti** nei climi caldi (usa l'efficienza STC nel bilancio termico,
   PVsyst quella al punto di lavoro: con l'85-90 % dell'efficienza STC lo scarto si chiude, prova nel §2.3);
   **cavi DC: ottimista di 0,2-0,3 punti** (scala la perdita col rapporto di potenza invece che con la corrente al
   quadrato: con R·I² i numeri di PVsyst tornano entro 0,07 punti); **livello di irraggiamento: ±1 punto**, che non è
   il modello ma i parametri a un diodo del modulo (lista CEC o adattamento al datasheet invece del file `.PAN`).
   [V: §2.3 e `confronto_pvsyst_ipotesi-risultati.txt`]
4. **Le file** (Montescaglioso, 20 file a 20° passo 7,5 m): ombra lineare 2,13 % contro 2,20 % di PVsyst, quota di
   cielo nascosta 4,28 % contro 0,044 di PVsyst, quota di albedo persa 76,3 % contro 0,769: il modello geometrico
   coincide. Ma Meridiana **applica sempre l'effetto elettrico** delle file (-1,49 %), che PVsyst "ombre lineari" non
   ha e che PVsyst "secondo le stringhe" pesa con una frazione a scelta (Pelham 50 %: -0,42 % contro -1,31 %).
   [V: §3.1 e §3.4]
5. **Il meteo pesa più di ogni dettaglio del modello.** PVGIS 5.3 (SARAH-3) contro il Meteonorm dei rapporti: +8,4 %
   di GHI a Montescaglioso (Meteonorm 8.0), +15 % in Egitto, +18 % in India (dove PVGIS usa ERA5), -5 % nel
   Hertfordshire; sulla E_Grid di Meridiana da -0,6 % a +29 %. Oggi Meridiana legge solo il PVGIS TMY: **un rapporto
   PVsyst italiano fatto con Meteonorm non si riproduce**, e nemmeno uno fatto con PVGIS 5.2 se la base è cambiata.
   [V: §4]
6. **Non modellato** (effetto letto nei rapporti): sovraccarico per ingresso MPPT (-1,94 % a PEAKI, invisibile con la
   potenza DC sommata), curva di efficienza del file `.OND` (±0,5 punti senza taratura), consumo notturno (-0,01/-0,45),
   soglie di tensione (-0,25 LaFact, -1,99 Risicone), trasformatore MT (-1,1/-1,3), linea MT (-0,05/-0,7), ausiliari
   (-0,2/-0,5), degrado (-0,1/-0,3 %/anno), bifacciale (guadagno sul retro +3,8/+11,3 %), inseguitori, limite di
   immissione, spettrale, orizzonte sull'albedo (≤0,1 %). [V: §5]
7. **Giudizio:** il nucleo fisico di Meridiana (sole, trasposizione, orizzonte, file, IAM, modulo, perdite costanti) è
   dello stesso ordine di PVsyst e si può correggere con tre ritocchi piccoli e verificabili (bilancio termico,
   cavi DC, interruttore dell'effetto elettrico); ciò che manca per arrivare a un rapporto confrontabile è altrove:
   **altre fonti meteo**, **i parametri `.PAN` e `.OND`**, **la struttura per MPPT**, **le voci lato AC e MT**. Fino ad
   allora i numeri "da relazione" sono GlobInc, GlobEff, EArrNom, EArrMPP e la E_Grid di impianti a stringa con
   DC/AC vicino a 1, dicendo la fonte meteo; non lo sono bifacciale, inseguitori, impianti MT e inverter in
   sovraccarico. [I, sui numeri del §2 e del §3]

---

## 1. Materiale e metodo

### 1.1 I casi

| Caso | PVsyst | Meteo del rapporto; GHI kWh/m², T °C | Campo | Modulo (PVsyst) e inverter | Uc; perdite (%) | IAM; ombre | Fonte |
|---|---|---|---|---|---|---|---|
| `peaki`, Neochoropoulo (GR), 39,62 N 20,85 E | 7.4.8 | PVGIS api TMY; 1594,6; 12,7 | 735 × 540 W = 396,9 kWp, 49 × 15, fisso 25/0 | Luxor LX-540M/182-144+; 4 × Huawei SUN2000-100KTL-M1 (400 kWac, 40 MPPT al 10 %) | 20; cavi DC 1,5, qualità -0,75, mismatch 2,0 | Fresnel AR a 9 punti; nessuna | casi.json n. 9, `GR_MinSports_PEAKI_fixed_PVsyst-7.4.8.pdf` |
| `kanpur`, IIT Kanpur (IN), 26,51 N 80,23 E | 7.4.0 | Meteonorm 8.1 1996-2015 sintetico, **`.MET` pubblico**; 1591,2; 25,2 | 16 × 315 W = 5,04 kWp, 2 × 8, fisso 24/0 | Generic PM318B01_315 (parametri custom); Huawei SUN2000-4.95KTL-JPL1 | 20; 1,5, -0,75, 2,0 | ASHRAE b0 0,05; nessuna | campione `github-sabya169-PVsyst` (.VC0, `New.VC0-Report.pdf` p. 3-5) |
| `almarj`, Al Marj (EG), 30,16 N 31,33 E | 7.4.6 | Meteonorm 8.1 1991-2010 sintetico, **`.MET` pubblico**; 1889,5; 22,8 | 114 × 540 W = 61,56 kWp, 6 × 19, fisso 28/-3 | Jinko JKM540M-72HL4-TV; 1,5 × Huawei SUN2000-40KTL-M3 (60 kWac) | 20; 1,5, -0,75, 2,0 | Fresnel AR a 9 punti; nessuna | campione `github-youefkh05-PV_plant_model` (.VC0, `Results_Report.pdf` p. 3-5) |
| `kuwait`, Jalib ash Shuyukh (KW), 29,26 N 47,89 E | 8.0.21 | Meteonorm 8.2 1998-2000 sintetico, **`.MET` pubblico**; 1941,4; 27,1 | 168 × 550 W = 92,4 kWp, 12 × 14, fisso 29/0 | LONGi LR5-72HPH-550M; 2 × SMA STP50-40 Core1 (100 kWac) | 20; 1,5, -0,25, 2,0 | profilo utente a 9 punti; nessuna | campione `github-IKH116-export-zip` (.VC0, `PVsyst_Variant1_Simulation_Report.pdf` p. 3-5) |
| `montescaglioso` (MT), 40,52 N 16,66 E | 7.2.11 | Meteonorm 8.0 sintetico; 1501,1; 17,6 | 8550 × 660 W = 5643 kWp, 285 × 30, **20 file** 20/0, passo 7,5 m, larghezza 4,79 m (GCR 63,8 %) | Risen RSM132-8-660BMDG; 28 × Huawei SUN2000-215KTL-H3 (5600 kWac) | 29; cavi DC 1,0, AC 1,0, qualità -0,5, LID 1,6, mismatch 1,0+0,1, sporcamento 2,0; ausiliari 4 W/kW, trafo MT, linea MT | profilo utente; **orizzonte PVGIS stampato**, ombre lineari | casi.json n. 5, `IT_MASE_744498_...pdf` p. 2-10 |
| `neom` (SA), 28,33 N 34,95 E | 7.4.0 | Meteonorm 8.1 1998-2002 sintetico; 2260,6; 26,3 | 10203 × 490 W = 4999 kWp, 537 × 19, fisso 30/0 | Generic LR5-66HPH-490M G2; 5 × Generic PVS800-57-0875kW-B (4375 kWac, DC/AC 1,14) | 20; 1,5, -0,75, 2,0+0,2 | profilo utente; nessuna | casi.json n. 8 |
| `lafact`, Terrassa (ES), 41,58 N 2,01 E | 7.3.4 DEMO | Meteonorm 8.1 1996-2015 sintetico; 1596,3; 15,5 | 1180 × 500 W = 590 kWp: 612 moduli a 10/+86 e 568 a **20/180 (nord)** | JA Solar Deep Blue 3.0 500 W; 6 × Fronius Tauro Eco 100-3-D | 20; 1,5, -0,25, 2,0+0,2 | profilo utente; nessuna | casi.json n. 13 |
| `pelham`, Hertfordshire (UK), 51,94 N 0,12 E | 7.4.5 | Meteonorm 8.0 1986-2005 sintetico; 1076,6; 10,2 | 95664 × 550 W = 52615 kWp, 3986 × 24, **file** 20/-2, passo 8,69 m, larghezza 4,60 m | CSI CS6W-550MS; 214 × Huawei SUN2000-175KTL-H0 (37450 kWac, **DC/AC 1,40**) | 29; 1,5, AC 1,5, -0,5, LID 1,0, mismatch 0,5+0,1, sporcamento 0,8; ausiliari, trafo MT | ASHRAE 0,05; orizzonte stampato, **ombre secondo le stringhe, effetto elettrico 50 %** | casi.json n. 7 |

Tutti con albedo 0,20 e trasposizione Perez [V: pagine dei parametri dei PDF]. Le energie di PVsyst sono quelle del
diagramma delle perdite e della tabella mensile (`casi.json` per i rapporti pubblici; per i tre campioni i mensili
sommati dai record orari del `.VC0` con `meridiana.pvsyst.project.read_variant`, e i passi del diagramma copiati dal
PDF con la pagina nello script) [V: `build_cases()` dello script].

### 1.2 Come è stato ricostruito ogni progetto con il nucleo di Meridiana

Tutto passa dall'API di `energy/simulate.py`: `Meteo`, `Horizon`, `ModuleSpec`, `InverterSpec`, `ArraySpec`, `Losses`,
`simulate()`. Nessuna interfaccia, nessun file `.meridiana`.

- **Modulo.** Il rapporto stampa solo costruttore, modello, potenza, numero, area e il punto di lavoro a 50 °C. Quando
  il modello è nella lista CEC del catalogo (Jinko, LONGi 550, Risen, Canadian) si usa quel record, con i suoi
  parametri a un diodo (SAM); quando non c'è, un record della stessa classe (PEAKI: LR5-72HPH-540M al posto del Luxor
  144 mezze celle da 540 W; NEOM: LR5-66HBD-490M al posto del "Generic LR5-66HPH-490M") oppure valori tipici battuti a
  mano (Kanpur: back-contact da 96 celle, come dicono area 1,63 m² e 48,5 V per modulo a 50 °C; LaFact: 132 mezze celle
  da 500 W). Lo script lo dichiara caso per caso [V: riga "Modulo:" dei risultati].
  Il **coefficiente di temperatura** è quello che il modello di PVsyst mostra, ricavato dal Pmpp stampato a 50 °C:
  γ = (Pmpp50/Pnom - 1)/25 (PEAKI 361/396,9 → -0,362 %/K; Kanpur -0,375; Al Marj -0,348; Kuwait -0,333;
  Montescaglioso -0,338; NEOM -0,335; LaFact -0,327 a 40 °C; Pelham -0,336) [V: pagina 3 dei PDF]. La sensibilità al
  γ della lista CEC è nel §7. L'area del modulo è quella stampata (l'efficienza entra nel bilancio termico).
- **IAM.** PVsyst stampa i 9 punti del profilo (Fresnel AR, o utente): passati a `ModuleSpec.iam_profile`, che
  `profile_iam()` unisce come PVsyst (retta fino al primo punto sotto 1, poi cubica). Per Fresnel AR i punti stampati
  coincidono con `pvlib.iam.physical(n=1.526, n_ar=1.29, K=0)` entro 0,002 [V: prova a mano con pvlib]. Dove PVsyst
  usa ASHRAE (Kanpur, Pelham) si usa `Losses.iam_b0 = 0,05` senza profilo.
- **Perdite costanti.** Come stampate, con una correzione: la "Module Quality Loss -0,8 %" della pagina dei parametri è
  il valore -0,75 % arrotondato (i `.VC0` dei campioni hanno `PQualityModP = -0.75`; il diagramma stampa +0,75 %)
  [V: `campioni.txt` della ricognizione, `SubArray.quality=-0.75`]. Lo studio 11 (§5.2) diceva "input -0,8 % stampato
  come +0,75 %, applicato dentro il modello": è una lettura sbagliata, va corretta. LaFact: -0,3 → -0,25. Il mismatch di
  modulo e di stringa è dato come somma (PVsyst li combina in un po' meno: 2,0+0,2 → -2,15 %, non -2,2). `Losses.lid`
  è passato esplicitamente a 0 dove PVsyst non lo ha (altrimenti `None` vale "LID del modulo o 1 %",
  `simulate.py:308`).
- **Termica.** Uc 20 → `thermal="semi"`, Uc 29 → `"open"` (`THERMAL`, `simulate.py:43`).
- **File.** `ArraySpec(rows, pitch, slant, stack=2, upright=True)` dalla pagina "Sheds configuration" (larghezza 4,79 m
  = due moduli da 2,384 m in verticale) [V]. Pelham: 1840 tavole → `rows=1840`.
- **Orizzonte.** Il profilo stampato nel rapporto (PVGIS, azimut da sud + ovest) convertito in azimut da nord:
  `az_nord = (az + 180) mod 360` [V: `build_horizon()`].
- **Inverter.** `InverterSpec(pac=P_AC totale, eta=…)`. Due varianti: `catalogo` (efficienza europea del catalogo per il
  modello o il più vicino: SUN2000-100KTL-M2 98,4 %, SUN2000-5KTL-L1 97,8 %, SUN2000-50KTL-M3 98,0 %, Tauro Eco 98,2 %;
  dove non c'è, un valore di famiglia dichiarato) e `inv.tarato` (η_nom scelto in tre iterazioni perché la perdita
  annua di efficienza di Meridiana sia quella stampata da PVsyst: così si isolano gli altri passi). La taratura dice
  anche quanto vale, per PVsyst, l'inverter: PEAKI 98,44 %, Kanpur 97,23, Al Marj 98,51, Kuwait 97,39, Montescaglioso
  98,97, NEOM 98,19, LaFact 98,74, Pelham 98,83 [V].

### 1.3 Il meteo, in tre modi

1. **`.MET` del progetto** (Kanpur, Al Marj, Kuwait): `read_met()` del pacchetto `meridiana.pvsyst` dà GlobHor, DiffHor,
   T_Amb e vento orari nell'ora solare del sito, etichettati all'inizio dell'ora; il `Meteo` è costruito con
   `time_offset_h = 0,5` (PVsyst mette il sole a metà intervallo, studio 06 §1.1.14.1) e la DNI derivata da globale e
   diffusa a quell'istante (`pvlib.irradiance.dni`, azzerata sotto 2° di altezza, limitata all'extra-atmosferica),
   pressione dalla quota. I mensili di GlobHor, DiffHor e T_Amb coincidono con la tabella del rapporto alla cifra
   [V: tabelle mensili dei tre casi]. Questo isola la **differenza di modello**.
2. **PVGIS TMY** come lo prende l'applicazione (`meteo.typical_year`, 5.3, SARAH-3 2005-2023) e, per PEAKI, anche
   **PVGIS 5.2** (SARAH-2 2005-2020) con `pvlib.iotools.get_pvgis_tmy(url=…/v5_2/)`: i mensili del rapporto coincidono
   con il 5.2 alla cifra (GHI 1594,6, DHI 604,5, T 12,72) e non con il 5.3 (1581,9): il rapporto del 2024 usava la base
   SARAH-2 [V: tabella mensile `5.2 catalogo`].
3. **PVGIS scalato** (Montescaglioso, NEOM, LaFact, Pelham): il TMY 5.3 scalato mese per mese in modo che globale,
   diffusa e temperatura media coincidano con la tabella del rapporto (globale e diffusa per rapporto, la diretta
   normale per il rapporto delle componenti dirette, la temperatura per differenza; quattro passate perché la diffusa
   è limitata alla globale). Le somme mensili tornano entro 0,1 %, **la forma oraria resta quella di PVGIS**: dove un
   mese va gonfiato del 20-30 % (Pelham aprile) le ore di picco superano il cielo sereno e falsano clipping e
   temperatura (§3.4) [V: tabella mensile di Pelham].

### 1.4 Che cosa si confronta

I **nodi** del diagramma di PVsyst e i valori di `Simulation.chain` di Meridiana: GlobHor (`ghi`), GlobInc (`poa`,
prima dell'orizzonte, come PVsyst), GlobEff (dopo `soiling`), EArrNom (`nominal`), EArrMPP (dopo `dc_wiring`), EOutInv
(dopo `clipping`), E_Grid (dopo `unavailability`), resa e PR (stessa definizione E/(P0·GlobInc), `simulate.py:372`).
I **passi** in % sul valore precedente, con la mappa dello studio 11 §5.2. Le voci di PVsyst senza equivalente
(soglie, consumo notturno, ausiliari, trasformatore, linea MT) sono raccolte in un **fattore** con cui si moltiplica
la E_Grid di Meridiana per un confronto alla pari. Per i casi a file, lo script stima anche la E_Grid di Meridiana
senza l'effetto elettrico delle file (dividendo per il passo), perché PVsyst "lineare" non lo ha.

### 1.5 Limiti del metodo

- Due moduli su otto sono surrogati (PEAKI, NEOM) e due battuti a mano (Kanpur, LaFact): il passo "livello di
  irraggiamento" dipende dai loro parametri a un diodo, non dal modello (§2.3). [V: §7]
- Senza il file `.OND` l'inverter si confronta solo tarato. [V]
- La scalatura mensile vale per le somme, non per le ore (§1.3). [V]
- PVsyst 8 stampa i passi con un decimale (Kuwait): scarti sotto 0,05 punti non sono leggibili. [V]
- Dei rapporti pubblici non si hanno il `.PAN`, il `.OND`, la scena 3D né il Meteonorm (studio 11 §3). [V]

---

## 2. Stesso meteo: la differenza di modello

Variante principale: meteo del rapporto (`.MET`, o PVGIS 5.2 per PEAKI), inverter tarato.

### 2.1 Nodi

| Nodo | PEAKI PVsyst | Meridiana | Kanpur PVsyst | Meridiana | Al Marj PVsyst | Meridiana | Kuwait PVsyst | Meridiana |
|---|---|---|---|---|---|---|---|---|
| GlobHor kWh/m² | 1594,6 | 1594,6 (0,00 %) | 1591,2 | 1591,2 (0,00) | 1889,5 | 1889,5 (0,00) | 1941,4 | 1941,4 (0,00) |
| GlobInc kWh/m² | 1818,5 | 1817,6 (-0,05 %) | 1693,1 | 1693,6 (+0,03) | 2055,6 | 2055,6 (0,00) | 2125,1 | 2125,0 (0,00) |
| GlobEff kWh/m² | 1780,4 | 1779,4 (-0,06 %) | 1649,2 | 1648,0 (-0,07) | 2015,3 | 2014,3 (-0,05) | 2093,8 | 2090,1 (-0,18) |
| EArrNom MWh | 707,0 | 706,2 (-0,11 %) | 8,327 | 8,306 (-0,25) | 124,09 | 124,00 (-0,07) | 193,86 | 193,13 (-0,38) |
| EArrMPP MWh | 640,0 | 639,8 (-0,03 %) | 7,243 | 7,349 (+1,46) | 109,54 | 111,09 (+1,41) | 168,34 | 167,20 (-0,68) |
| EOutInv MWh | 615,0 | 627,8 (+2,09 %) | 6,986 | 7,120 (+1,92) | 107,73 | 109,28 (+1,44) | 163,67 | 162,51 (-0,71) |
| E_Grid MWh | 615,5 | 627,8 (+2,01 %) | 6,986 | 7,120 (+1,92) | 107,73 | 109,28 (+1,44) | 163,67 | 162,51 (-0,71) |
| E_Grid × fattore voci mancanti | | 627,8 (+2,00 %) | | 7,088 (+1,46) | | 109,25 (+1,41) | | (-0,71) |
| Resa kWh/kWp | 1551 | 1582 | 1386 | 1413 | 1750 | 1775 | 1771 | 1759 |
| PR % | 85,28 | 87,03 (+1,75 pt) | 81,87 | 83,41 (+1,54) | 85,13 | 86,36 (+1,23) | 83,35 | 82,76 (-0,59) |

[V: `confronto_pvsyst-risultati.txt`, tabelle "Nodi della catena", colonne `5.2 inv.tarato` e `MET inv.tarato`]

### 2.2 Passi (% sul valore precedente; tra parentesi lo scarto in punti)

| Passo | PEAKI PVsyst / Meridiana | Kanpur | Al Marj | Kuwait |
|---|---|---|---|---|
| trasposizione | +14,00 / +13,98 (-0,02) | +6,40 / +6,44 (+0,04) | +8,80 / +8,79 (-0,01) | +9,5 / +9,46 (-0,04) |
| IAM | -2,10 / -2,10 (0,00) | -2,59 / -2,69 (-0,10) | -1,96 / -2,01 (-0,05) | -1,5 / -1,65 (-0,15) |
| livello di irraggiamento | -0,65 / -0,86 (-0,21) | -0,85 / +0,08 (+0,93) | -0,44 / +0,42 (+0,86) | +0,4 / -0,89 (-1,29) |
| temperatura | -6,76 / -6,60 (+0,16) | -10,26 / -9,79 (+0,47) | -9,20 / -8,85 (+0,35) | -10,9 / -10,33 (+0,57) |
| qualità del modulo | +0,75 / +0,75 | +0,75 / +0,75 | +0,75 / +0,75 | +0,2 / +0,25 (+0,05) |
| mismatch | -2,00 / -2,00 | -2,00 / -2,00 | -2,00 / -2,00 | -2,0 / -2,00 |
| cavi DC (1,5 % a STC) | -1,11 / -0,91 (+0,20) | -0,99 / -0,75 (+0,24) | -1,09 / -0,86 (+0,23) | -1,1 / -0,85 (+0,25) |
| inverter, efficienza (catalogo) | -1,87 / -1,91 (-0,04) | -3,11 / -2,54 (+0,57) | -1,63 / -2,14 (-0,51) | -2,8 / -2,39 (+0,41) |
| inverter, efficienza (tarato) | -1,87 / -1,87 | -3,11 / -3,11 | -1,63 / -1,63 | -2,8 / -2,80 |
| inverter, sopra la nominale | -1,94 / 0,00 (+1,94) | 0 / 0 | 0 / 0 | 0 / 0 |
| voci solo di PVsyst | notturno -0,01 | notturno -0,45 | notturno -0,03 | nessuna |

[V: tabelle "Passi del diagramma delle perdite" dei risultati]

### 2.3 Lettura passo per passo

- **Trasposizione (±0,05 punti).** Con lo stesso orario di irraggiamento, Perez di pvlib e di PVsyst coincidono anche
  nei mensili (Kanpur e Al Marj: GlobInc mensile entro ±0,1 %; Kuwait ±0,1 %). Le convenzioni di tempo (sole a metà
  ora per i `.MET`, `irradiance_time_offset` di PVGIS per il TMY) sono giuste. [V: tabelle mensili]
- **IAM (-0,05/-0,15 punti).** Il profilo a punti è letto come PVsyst; lo scarto residuo viene dalla parte diffusa:
  Meridiana integra il profilo sul cielo e sul suolo (Marion), PVsyst usa un fattore costante calcolato integrando sul
  cielo visto; dove la diffusa è metà del globale (Kuwait 47 %) lo scarto sale a 0,15 punti. [I]
- **Livello di irraggiamento (±1 punto): parametri, non modello.** Con lo stesso meteo PVsyst dà -0,85 (Kanpur),
  -0,44 (Al Marj), +0,4 (Kuwait, un guadagno a bassa luce), Meridiana +0,08, +0,42, -0,89. Il passo dipende da R_shunt,
  R_shunt(0) e R_serie del `.PAN`, che non sono pubblici; Meridiana usa il record CEC (Jinko R_sh 669 Ω: quasi nessuna
  perdita; LONGi 550 R_sh 169 Ω: perdita) o l'adattamento De Soto al datasheet (Kanpur, LaFact). La sensibilità
  (§7) sposta la E_Grid di 0,1-0,8 %. **Per arrivare a PVsyst servono i parametri del `.PAN`** e il suo modello
  (`pvlib.pvsystem.calcparams_pvsyst` c'è in pvlib 0.16.1 [V: `dir(pvlib.pvsystem)`]); `catalog/panond.py:82-133`
  legge dal `.PAN` solo i valori di targa, non `RShunt`, `Rp_0`, `Rp_Exp`, `RSerie`, `Gamma`, `muGamma`. [V]
- **Temperatura (Meridiana ottimista di +0,16/+0,57 punti).** Stesso modello termico (Uc, Uv, α 0,9,
  `pvlib.temperature.pvsyst_cell`, `simulate.py:299`), stesso γ. La differenza è l'efficienza nel bilancio:
  Meridiana passa `a.module.efficiency` (STC, 19-21,5 %), PVsyst itera quella al punto di lavoro (studio 06
  §1.1.13.2). Prova: con `pvsyst_cell` forzato a 0,85-0,92 dell'efficienza STC lo scarto scende da +0,57 a +0,25
  (Kuwait), da +0,35 a +0,02 (Al Marj), da +0,47 a +0,18 (Kanpur), da +0,16 a -0,03 (PEAKI)
  [V: `confronto_pvsyst_ipotesi-risultati.txt`]. Il resto (0,2 punti nei climi più caldi) è la non linearità in
  temperatura del modello a un diodo di PVsyst, che il γ costante di Meridiana non ha [I].
- **Qualità, LID, mismatch: identici.** Fattori costanti in entrambi. La combinazione modulo+stringa di PVsyst vale
  0,05 punti meno del prodotto (NEOM, LaFact). [V]
- **Cavi DC (Meridiana ottimista di +0,20/+0,25 punti su 1,5 % a STC).** `simulate.py:326-327` scala la frazione STC
  con P/P_STC (perdita ∝ P²); PVsyst calcola R·I² con la corrente dell'ora, e la corrente non cala con la temperatura
  come la potenza. Ricalcolo sulle stesse ore con I/I_STC = (G_eff/1000)(1 + α_Isc ΔT): -1,17, -1,11, -1,00, -1,13 %
  contro -1,10, -1,09, -0,99, -1,11 % di PVsyst (entro 0,07 punti); la formula di Meridiana dà -0,85, -0,86, -0,75,
  -0,91. [V: `confronto_pvsyst_ipotesi-risultati.txt`]
- **Inverter.** Con l'efficienza di catalogo lo scarto è ±0,5 punti e dipende dal modello assunto, non da una
  tendenza (a PEAKI la taratura dà 98,44 %, pari all'efficienza europea del M2 di catalogo, 98,4 %). La curva PVWatts
  scalata è un surrogato ragionevole della curva `.OND`; `panond.py:136-172` legge dal `.OND` solo `EfficEuro` e
  `EfficMax`, non il profilo di efficienza. [V]
- **Sovraccarico per ingresso (PEAKI -1,94 %).** 49 stringhe su 40 ingressi MPPT al 10 % (4 × 100 kW): nove ingressi
  portano 16,2 kWp su 10 kWac e PVsyst li taglia; Meridiana somma la potenza DC di tutto l'impianto e con DC/AC 0,99
  non taglia nulla (`simulate.py:357-358`). È l'intero scarto di E_Grid di PEAKI: tolto questo, +0,07 %. [V]
- **Consumo notturno (Kanpur -0,45 %, Al Marj -0,03, PEAKI -0,01).** Non c'è. Su un impianto da 5 kW con
  autoconsumo notturno dell'inverter vale mezzo punto. [V]
- **E_Grid e PR.** Tolte le voci che Meridiana non ha, con lo stesso meteo: PEAKI +2,0 % (tutto MPPT), Kanpur +1,5 %,
  Al Marj +1,4 %, Kuwait -0,7 %. Nei mensili di Kanpur e Al Marj lo scarto è uniforme (+1,1/+2,1 % ogni mese); in
  Kuwait è stagionale (-1,7 % a dicembre, 0 a luglio: il segno della perdita a bassa luce del record CEC). [V]

---

## 3. Meteo scalato: file, orizzonte, due falde, clima caldo

Le somme mensili coincidono col rapporto; la forma oraria è quella di PVGIS 5.3. Gli scarti di trasposizione
(-1,40 punti a Montescaglioso, -3,0 a LaFact, -0,3 a Pelham, +0,1 a NEOM) vanno letti con questo limite: nei tre casi
a meteo identico la trasposizione sta entro 0,05 punti.

### 3.1 Montescaglioso, 20 file a 20°, passo 7,5 m, orizzonte PVGIS (il caso italiano)

| Passo | PVsyst | Meridiana (scalato, inv. tarato) | Nota |
|---|---|---|---|
| trasposizione | +11,40 | +10,00 (-1,40) | forma oraria del meteo scalato [I] |
| orizzonte | -0,55 | -0,45 (+0,10) | cielo visto 98,61 % contro "Diffuse Factor 0,99"; PVsyst riduce anche l'albedo (Albedo Factor 0,86), Meridiana no (`simulate.py:236`): vale circa 0,08 punti [I: 0,14 × albedo 0,2 × (1-cos20)/2] |
| ombre vicine, lineari | -2,20 | -2,13 (+0,07) | cielo nascosto dalla fila davanti 4,28 % contro attenuazione diffusa 0,044; albedo perso 76,3 % contro 0,769 (pagina iso-ombre del rapporto) [V] |
| IAM | -0,22 | -0,23 | profilo utente = 1 fino a 60° |
| sporcamento | -2,00 | -2,00 | |
| livello di irraggiamento | -0,09 | -0,55 (-0,46) | record CEC del Risen; con De Soto +0,29 [V: §7] |
| temperatura | -4,03 | -4,10 (-0,07) | Uc 29; T cella massima 59 °C |
| qualità, LID, mismatch | +0,50, -1,55, -1,10 | +0,50, -1,60, -1,10 | |
| effetto elettrico delle file | nessuno (lineare) | **-1,49** | sempre acceso in Meridiana (`simulate.py:249, 316, 322`) |
| cavi DC (1,0 %) | -0,60 | -0,52 (+0,08) | |
| inverter | -1,42 | -1,42 (tarato 98,97 %) | catalogo 98,4 %: -1,99 |
| cavi AC (1,0 %) | -0,53 | -0,52 | |
| solo PVsyst | ausiliari -0,40, trafo MT -1,13, linea MT -0,24, notturno -0,01 | fattore 0,9823 | |

Nodi: GlobInc 1651,2 contro 1671,6 (-1,22 %), GlobEff 1573,0 contro 1589,9 (-1,06 %), EArrNom -1,14 %, EArrMPP 8114
contro 8373 MWh (-3,09 %), E_Grid 7957 contro 8065 MWh (-1,34 %; × fattore: -3,09 %; senza l'effetto elettrico delle
file: +0,16 %), PR 85,40 contro 85,50. Nei mesi invernali la E_Grid di Meridiana è -11/-18 % (dic -17,9 %): è
l'effetto elettrico delle file, concentrato nelle ore basse, più il -4 % di trasposizione del meteo scalato a
dicembre [V: tabella mensile]. Con il PVGIS 5.3 grezzo (GHI +8,4 %): E_Grid 8811 MWh, +9,25 %.

**Lettura.** Il modello delle file di Meridiana (ombra lineare, cielo, albedo) riproduce PVsyst entro 0,1 punti sul
caso che somiglia di più ai progetti italiani a terra. Due cose lo allontanano: l'effetto elettrico non spegnibile
(-1,5 % che PVsyst "lineare" non ha, e che PVsyst "secondo le stringhe" avrebbe pesato con la sua frazione) e le voci
di media tensione (-1,8 % in tutto). [V]

### 3.2 NEOM, 5 MWp a 30°, clima caldo (T 26 °C, T cella fino a 77 °C)

GlobInc +0,10 %, GlobEff -0,05 %, EArrNom -0,23 %, EArrMPP -0,80 %, E_Grid 10503 contro 10602 MWh (-0,94 %), PR 83,20
contro 84,07. Passi: temperatura -11,27 contro -11,26 (0,0 punti, con Uc 20 e il γ del rapporto; con il γ CEC -0,321:
-10,80), livello di irraggiamento -0,23 contro +0,57 (modulo surrogato), cavi DC -1,02 contro -1,31 (-0,29), IAM
-1,66 contro -1,52, clipping -0,16 contro 0,00 (DC/AC 1,14: PVsyst non taglia, Meridiana poco: picchi del meteo
scalato [I]). [V]

### 3.3 LaFact, due falde 10/+86 e 20/180 (nord)

GlobInc 1423,4 contro 1472,6 (-3,3 %), e lo scarto resta con il PVGIS grezzo (GlobInc/GlobHor 0,895 contro 0,922):
circa -10 % a dicembre e gennaio, -1 % a luglio. Dopo la trasposizione la catena torna in riga: GlobEff/GlobInc -0,19
punti, EArrMPP/EArrNom +0,86 (modulo battuto a mano), PR 87,59 contro 86,85. **Non spiegato**: nei sette casi a
falda singola la trasposizione coincide; qui o la pesatura delle due orientazioni nel GlobInc di PVsyst non è per
potenza, o la falda a nord riceve in PVsyst più diffusa d'inverno. Si scioglie solo con PVsyst (prova sul PC di
Daniel: simulare le due falde una per volta). [I]

### 3.4 Pelham, file a 20° a 51,9° N, ombre "secondo le stringhe" al 50 %, DC/AC 1,40

Passi dell'irraggiamento: trasposizione -0,30, orizzonte -0,24 contro -0,42 (+0,18: albedo factor 0,91 e profilo
basso), ombre lineari -2,45 contro -2,92 (+0,47: la scena di PVsyst ha anche terreno e siepi), IAM -3,33 contro
-3,20, GlobEff +0,27 %. Effetto elettrico: Meridiana -1,31 contro -0,42 (PVsyst al 50 %: al 100 % sarebbe circa
-0,84 [I]); somma ombre + elettrico 3,76 contro 3,34 (Meridiana più pessimista di 0,4 punti). Livello di
irraggiamento -1,14 contro -1,15 (record CEC del Canadian: perfetto). **Artefatti della scalatura**: temperatura
-1,33 contro -0,67 e clipping -5,26 contro -0,61, perché aprile, maggio e giugno sono gonfiati del 20-30 % sulle ore
di PVGIS; col PVGIS grezzo temperatura -0,54 e clipping -1,65 (resta un punto in più: con DC/AC 1,40 conta la curva
oraria e il limite di potenza del `.OND`, 192,5 kVA contro 175 kW nominali [I]). E_Grid -4,8 % è quindi un numero del
metodo, non del modello; EArrMPP/EArrNom -1,51 punti. [V/I come detto]

---

## 4. La differenza meteo

| Caso | Meteo del rapporto: GHI, T | PVGIS 5.3 (base): GHI, scarto | PVGIS 5.2: GHI, scarto | T 5.3 - T rapporto | Effetto sulla E_Grid di Meridiana (5.3 grezzo contro meteo del rapporto) |
|---|---|---|---|---|---|
| PEAKI (GR) | PVGIS 5.2: 1594,6, 12,7 | SARAH-3: 1581,9, -0,8 % | SARAH-2: 1594,6, 0,0 % | +0,7 °C | -0,70 % |
| Kanpur (IN) | Meteonorm 8.1: 1591,2, 25,2 | **ERA5**: 1883,8, +18,4 % | ERA5: 1906,6, +19,8 % | 0,0 | **+28,7 %** |
| Al Marj (EG) | Meteonorm 8.1: 1889,5, 22,8 | SARAH-3: 2173,4, +15,0 % | SARAH-2: 2176,2, +15,2 % | -0,7 | +14,7 % |
| Kuwait | Meteonorm 8.2: 1941,4, 27,1 | SARAH-3: 2110,9, +8,7 % | SARAH-2: 2067,4, +6,5 % | -0,1 | +8,8 % |
| Montescaglioso | Meteonorm 8.0: 1501,1, 17,6 | SARAH-3: 1627,5, **+8,4 %** | SARAH-2: 1620,4, +7,9 % | -1,1 | +10,7 % |
| NEOM (SA) | Meteonorm 8.1: 2260,6, 26,3 | SARAH-3: 2332,6, +3,2 % | SARAH-2: 2344,0, +3,7 % | -0,1 | +2,1 % |
| LaFact (ES) | Meteonorm 8.1: 1596,3, 15,5 | SARAH-3: 1699,8, +6,5 % | SARAH-2: 1660,9, +4,0 % | -0,4 | +5,9 % |
| Pelham (UK) | Meteonorm 8.0: 1076,6, 10,2 | SARAH-3: 1021,6, -5,1 % | SARAH-2: 1033,3, -4,0 % | +0,1 | -0,6 % |

[V: righe "PVGIS 5.3 TMY", "PVGIS 5.2 TMY" e riassunto finale dei risultati; le basi sono nei metadati di PVGIS]

- La **diffusa** di PVGIS è molto più bassa di Meteonorm (India -43 %, Egitto -26 %, Kuwait -17 %, Montescaglioso
  -10 %): anche a parità di GHI i due anni tipici non sono lo stesso clima. [V: tabelle mensili `PVGIS 5.3 catalogo`]
- A 80° E PVGIS esce dal dominio SARAH e passa a **ERA5** senza che l'utente lo veda: +18 % in India, dove ERA5 è noto
  per sovrastimare (aerosol). La sorgente va mostrata e, fuori dal dominio SARAH, segnalata. [V sulla base; I sulla
  causa]
- I rapporti italiani per le autorizzazioni usano Meteonorm 8.0-8.2 (periodi 1986-2005, 1991-2012; studio 11, 19
  casi su 27) oppure il PVGIS TMY di un'altra versione: **con il solo PVGIS 5.3 Meridiana non riprodurrà la E_Grid di
  un rapporto PVsyst italiano**, e lo scarto (+8-10 %) non è un difetto di modello. Servono: lettura di file meteo
  (`.MET` di PVsyst, CSV PVsyst, Meteonorm; pvlib 0.16.1 ha `get_meteonorm_tmy` con chiave e `read_panond`), la scelta
  della versione PVGIS (5.2 e 5.3 rispondono entrambe) e un anno tipico ricostruito da valori mensili. Oggi
  `meteo.py:128-151` e `ui/window.py:169` conoscono solo `typical_year` 5.3 (con il 6 beta di riserva). [V]

---

## 5. Le voci di PVsyst e Meridiana, una per una

| Voce di PVsyst | Meridiana | Effetto visto nei rapporti (27 casi dello studio 11 + questi 8) | Stima per Meridiana |
|---|---|---|---|
| trasposizione Perez | c'è | | coincide (±0,05 pt) [V] |
| orizzonte: diretta e circumsolare, fattore sulla diffusa | c'è | -0,1/-2,5 % | coincide entro 0,1-0,2 pt [V] |
| orizzonte: fattore sull'albedo (0,70-0,91) | **manca** (`simulate.py:236`) | | ≤0,1 % [I] |
| ombre vicine lineari (file) | c'è (`shaded_fraction1d`, Passias, infinite sheds) | -0,8/-5,9 % | coincide entro 0,1 pt sulle file; scena 3D con terreno e siepi: 0,5 pt [V] |
| ombre vicine: albedo attenuato dalle file | c'è (`simulate.py:259-264`) | 0,65-0,83 | coincide (0,763 contro 0,769) [V] |
| ombre di ostacoli 3D con effetto elettrico "secondo le stringhe" e frazione | c'è per gli ostacoli (Martinez-Moreno, senza frazione); per le file sempre acceso, senza opzione lineare | elettrico -0,4/-5,4 % | file: -1,5 % in più dove PVsyst è lineare; Pelham +0,9 pt contro il 50 % [V] |
| "Module layout" (calcolo dettagliato per modulo) | manca | -1,0/-2,7 % (casi 14, 15) | n.d. |
| IAM Fresnel, ASHRAE, profilo utente | c'è (profilo a punti; ASHRAE b0) | -0,1/-4,3 % | entro 0,15 pt [V] |
| sporcamento annuo | c'è | | identico; PVsyst ha anche i mensili [V] |
| livello di irraggiamento (modello a un diodo del `.PAN`) | De Soto/CEC | -1,96/+0,57 % | ±1 pt finché manca il `.PAN` [V] |
| temperatura (Uc, Uv, α) | c'è | -0,3/-11,4 % | ottimista 0,2-0,6 pt nei climi caldi (efficienza STC nel bilancio) [V] |
| correzione spettrale | manca | +0,02/-0,06 % | trascurabile [V] |
| qualità del modulo, LID | c'è | | identici [V] |
| mismatch moduli + stringhe | c'è (una cifra) | | 0,05 pt sulla regola di combinazione [V] |
| mismatch retro bifacciale, di orientamento, di invecchiamento | manca | -0,4/-1,0 %; -0,01 %; con ageing | |
| degrado (anno n) e ageing tool | manca nella catena (`ModuleSpec.yearly_loss` entra solo nel bilancio pluriennale, `ui/window.py:239`) | -0,12/-0,31 % anno 1; 0,25-0,62 %/anno | 0,2-0,3 % all'anno 1; serve per P50/P90 e anni successivi [V] |
| ottimizzatori | manca | 0,0 % (caso 16) | |
| cavi DC R·I² | c'è con P² | -0,25/-1,31 % | ottimista 0,2-0,3 pt su 1,5 % STC [V] |
| inverter: curva `.OND` | PVWatts scalata all'efficienza pesata | -1,4/-3,1 % | ±0,5 pt senza taratura [V] |
| inverter: sovraccarico per MPPT, per inverter come cablato | pool di tutto l'impianto (`simulate.py:357`) | 0/-1,94 % (PEAKI) | invisibile; -1,9 % a PEAKI [V] |
| inverter: corrente massima, sovratensione, soglie di potenza e tensione | manca | 0/-0,25 %, -1,99 % (Risicone) | |
| consumo notturno | manca | -0,01/-0,45 % | 0,0-0,5 % [V] |
| ausiliari (W/kW, notte) | manca | -0,13/-0,5 % | |
| cavi AC "a STC" | c'è, riferito alla P_AC nominale (`simulate.py:359`) | -0,1/-1,52 % | uguale con DC/AC ≈ 1; +0,24 pt con DC/AC 1,4 [V] |
| trasformatore MT (ferro + rame), linee MT e AT | manca | -1,10/-1,32 %; -0,05/-0,68 % | 1,2-2,0 % negli impianti a terra italiani [V] |
| limite di immissione | solo nel bilancio economico, non nella catena | -0,09 % (Rotello), 0 | |
| indisponibilità | c'è, come frazione di energia (`simulate.py:361`) | 2 % di tempo → -1,64 %, 1 % → -0,81, 0,5 % → -0,40 | pessimista di 0,2-0,4 pt (PVsyst estrae periodi anche notturni) [V] |
| bifacciale (vista del terreno, retro, mismatch) | manca (`bifaciality` memorizzato) | guadagno sul retro +3,8/+11,3 % nei 9 casi bifacciali | impossibile oggi [V] |
| inseguitori (N-S, asse inclinato, verticale, backtracking) | manca | trasposizione +21/+40 % contro +11/+15 % fissi | impossibile oggi [V] |
| passo sub-orario e correzione del clipping | manca (orario) | | |
| PR, PR bifacciale, PR corretto in temperatura | PR sì (stessa definizione) | | |
| meteo: Meteonorm, Solcast, Solargis, `.MET`, CSV, PVGIS 5.2 | solo PVGIS 5.3 TMY | | ±8-30 % sulla E_Grid [V: §4] |

---

## 6. Difetti trovati, in ordine di gravità

1. **Solo il PVGIS 5.3 come meteo** (`energy/meteo.py:128-151`, `ui/window.py:169`): nessuna lettura di `.MET`, CSV
   PVsyst, Meteonorm, né scelta della base (5.2/5.3), né anno tipico da mensili; il passaggio a ERA5 fuori dal dominio
   SARAH non è segnalato. È la prima causa di scarto con qualunque rapporto PVsyst (+8/+30 %). Non è un errore di
   calcolo ma un confine del prodotto. [V: §4]
2. **Bilancio termico con l'efficienza STC** (`energy/simulate.py:299-300`, `module_efficiency=a.module.efficiency`):
   temperatura ottimista di +0,16 (PEAKI), +0,35 (Al Marj), +0,47 (Kanpur), +0,57 (Kuwait) punti. Correzione: usare
   l'efficienza al punto di lavoro, iterando con il modello elettrico (due passate bastano a PVsyst) o, in prima
   battuta, 0,88 × η_STC: prova nel file `confronto_pvsyst_ipotesi-risultati.txt`. [V]
3. **Cavi DC scalati con P/P_STC invece che con (I/I_STC)²** (`energy/simulate.py:326-327`): -0,20/-0,25 punti su
   1,5 % a STC, -0,08 su 1,0 %. Correzione: frazione × (I/I_STC)² con I/I_STC = (G_eff/1000)(1 + α_Isc(T_c - 25)),
   o meglio con la corrente al MPP del modello a un diodo (già calcolata in `power_at_25`); riproduce PVsyst entro
   0,07 punti. Lo stesso errore sul lato AC (`simulate.py:359`, scala con P/P_AC,nom: con DC/AC 1,4 +0,24 punti). [V]
4. **Inverter per tutto l'impianto** (`energy/simulate.py:357-358`): nessun taglio per ingresso MPPT o per inverter
   come cablato (`energy/stringing.py` conosce le stringhe per ingresso ma `simulate()` non le usa); nessuna curva
   `.OND` (`catalog/panond.py:136-172` legge `EfficEuro` e `EfficMax` soltanto); nessun consumo notturno né soglie.
   -1,94 % a PEAKI; ±0,5 punti sull'efficienza senza taratura. [V]
5. **Effetto elettrico delle file sempre acceso e senza frazione** (`energy/simulate.py:249, 316, 322`): -1,49 % a
   Montescaglioso dove PVsyst (lineare) ha 0; -1,31 contro -0,42 a Pelham (PVsyst al 50 %). Serve l'interruttore
   lineare/elettrico e, per il modello a stringhe, la frazione come in PVsyst; il modello Martinez-Moreno a 2 moduli
   in verticale è un limite superiore. [V]
6. **Parametri del modulo non dal `.PAN`** (`catalog/panond.py:82-133` non legge `RShunt`, `Rp_0`, `Rp_Exp`,
   `RSerie`, `Gamma`, `muGamma`; `energy/components.py:77-101` usa De Soto/CEC): passo "livello di irraggiamento"
   a ±1 punto (Kuwait -1,29, Kanpur +0,93, Al Marj +0,86, NEOM -0,80, LaFact +0,67) e γ diverso da quello del `.PAN`
   (CEC -0,375 contro -0,333 del rapporto per il LONGi 550: -1,4 % di E_Grid). pvlib ha `calcparams_pvsyst` e
   `fit_pvsyst_sandia`. [V: §2.3 e §7]
7. **`cells_in_series` fidato dal record CEC** (`energy/components.py:70-71`): la lista CEC ha N_s = 24 per il Jinko
   JKM540M-72HL4-TV e 22 per il Risen RSM132-8-660BMDG (celle per sottostringa, non in serie); se i parametri SDM del
   record vengono scartati (`_given_sdm`, tolleranza 2 %, `components.py:170`) l'adattamento De Soto fallisce e il
   modulo diventa **lineare** (riga "SDM De Soto dal datasheet (LINEARE)" di Al Marj): -0,4 % di E_Grid e nessuna
   perdita a bassa luce. L'euristica sul Voc (`components.py:74-75`) darebbe 72 e 66. [V]
8. **Orizzonte senza fattore sull'albedo** (`energy/simulate.py:236`, `ground` non ridotto): PVsyst stampa un
   "Albedo Factor" 0,70-0,91; vale ≤0,1 % di energia, +0,10/+0,18 punti sul passo orizzonte. [V/I]
9. **Indisponibilità come frazione di energia** (`energy/simulate.py:361`): PVsyst estrae periodi di tempo (2 % →
   -1,64 %): Meridiana pessimista di 0,2-0,4 punti a parità di input. [V]
10. **Voci mancanti nella catena**: trasformatore MT, linee, ausiliari, consumo notturno, degrado, limite di immissione
    (è in `economics.py`, non in `simulate`), bifacciale, inseguitori, spettrale (§5). Per gli impianti a terra
    italiani le prime tre valgono 1,5-2 %. [V]
11. **Trasposizione a due falde** (LaFact -3 punti): non spiegata, da verificare con PVsyst sul PC di Daniel; i casi a
    falda singola coincidono. [I]
12. **Studio 11 §5.2, riga "Module quality loss"**: la frase "input -0,8 % prints as +0,75 % (applied inside the
    model)" è sbagliata: l'input è -0,75 % (`PQualityModP` dei `.VC0`), la pagina dei parametri lo arrotonda. Da
    correggere nello studio. [V]
13. **Combinazione del mismatch** modulo + stringa (0,05 punti) e **diffusa IAM** (0,1-0,15 punti): differenze di
    dettaglio, da documentare, non da correggere per forza. [V]

---

## 7. Sensibilità (stesso meteo della variante principale, inverter tarato; scarto di E_Grid da PVsyst)

| Variante | PEAKI | Al Marj | Kuwait | Montescaglioso | NEOM | LaFact | Pelham |
|---|---|---|---|---|---|---|---|
| principale (γ del rapporto, SDM del catalogo, IAM del rapporto) | +2,01 % | +1,44 % | -0,71 % | -1,34 % | -0,94 % | -2,52 % | -4,83 % |
| γ della lista CEC | +1,75 (γ -0,375) | +2,17 (-0,322) | -2,15 (-0,375) | -1,63 (-0,361) | -0,46 (-0,321) | n.d. | -4,85 (-0,320) |
| SDM De Soto dal datasheet invece del CEC | +2,27 | +1,04 (lineare) | -0,21 | -0,51 | -0,85 | n.d. | -4,59 |
| IAM ASHRAE 0,05 (default) invece del profilo | +1,43 | +0,89 | -1,50 | -3,92 | -1,68 | -4,10 | n.d. |
| perdite predefinite di Meridiana (sporcamento 2, mismatch 1, LID 1, cavi 1,5/1,0) | -1,36 | -1,85 | -3,44 | -1,39 | -4,03 | -4,95 | -6,15 |

[V: tabelle "Sensibilita'" dei risultati; Kanpur ha solo la riga delle perdite predefinite: -1,34 %]

Letture: il γ del modulo vale fino a 1,4 % (Kuwait); i parametri a un diodo fino a 0,8 % (Montescaglioso); il
profilo IAM del modulo fino a 2,5 % quando il profilo utente è generoso (Montescaglioso: 1,000 fino a 60°); le perdite
predefinite di Meridiana (sporcamento 2 %, LID 1 %) sono più prudenti di quelle dei rapporti e spostano la E_Grid di
-1,3/-6 %: non sono un errore, ma vanno dichiarate come scelte.

---

## 8. Giudizio

**Quanto vicino.** Con lo stesso meteo e lo stesso modulo Meridiana riproduce PVsyst: GlobInc e GlobEff entro 0,2 %,
EArrNom entro 0,4 %, EArrMPP entro ±1,5 %, E_Grid entro ±2 % (inverter a stringa, DC/AC ≈ 1, niente MT), PR entro
+1,8/-0,6 punti, e la geometria delle file (ombra, cielo, albedo) entro 0,1 punti. Gli scarti hanno cause note e
piccole: efficienza STC nel bilancio termico (0,2-0,6 pt), cavi DC in P² (0,2-0,3 pt), parametri del modulo (±1 pt),
effetto elettrico delle file senza interruttore (1,5 pt). [V]

**Dove no.** (a) Il meteo: con il solo PVGIS 5.3 lo scarto da un rapporto è +8/+30 %, e non si può chiudere dentro il
modello. (b) L'inverter oltre la curva media: sovraccarico per ingresso, soglie, consumo notturno, curva `.OND`.
(c) Tutto il lato AC/MT: trasformatore, linee, ausiliari (1,5-2 % a terra). (d) Bifacciale, inseguitori, degrado:
impossibili oggi, e servono in 16 dei 17 casi italiani dello studio 11. (e) La trasposizione a due falde: un caso aperto.
[V/I]

**Che cosa manca per arrivarci, nell'ordine in cui rende.**
1. Lettura di altri meteo (`.MET` PVsyst, CSV PVsyst/Meteonorm, scelta PVGIS 5.2/5.3, anno tipico da mensili) e la
   fonte in chiaro nella relazione; la segnalazione ERA5.
2. Tre ritocchi a `simulate.py` con prova numerica già scritta: efficienza al punto di lavoro, R·I², interruttore
   lineare/elettrico con frazione.
3. Parametri `.PAN` (modello PVsyst via `calcparams_pvsyst`) e curva `.OND` (profilo di efficienza) letti da
   `panond.py`; N_s robusto.
4. Inverter per ingresso MPPT dalla stringatura (`stringing.py` già la conosce), con soglie e consumo notturno.
5. Voci AC/MT come costanti dichiarate: trasformatore (ferro + rame), linea, ausiliari; indisponibilità a periodi;
   degrado all'anno n.
6. Bifacciale e inseguitori (studio 11 §5.3), che sono un modulo nuovo, non un ritocco.

**Che cosa si può mettere in relazione oggi** (con la fonte meteo scritta e le perdite dichiarate): GlobInc, GlobEff,
EArrNom, EArrMPP e la E_Grid di impianti fissi monofacciali con inverter a stringa a DC/AC vicino a 1 e consegna in
BT, con un'incertezza di modello di ±2 % oltre a quella del meteo. Non: impianti con sovraccarico per ingresso o
DC/AC > 1,2, impianti MT, bifacciali, inseguitori, anni oltre il primo. [I, sui numeri sopra]

---

## 9. Fonti e file

- Rapporti PVsyst pubblici: `C:\Users\utente\dev\meridiana-prove\pvsyst-report-pubblici\casi.json` e `pdf\` (URL e
  SHA-256 nel suo README; studio 11); campioni con `.MET` e `.VC0`:
  `C:\Users\utente\dev\meridiana-prove\pvsyst-campioni\github-sabya169-PVsyst\`, `...\github-youefkh05-PV_plant_model\`,
  `...\github-IKH116-export-zip\extracted\` (README del 22/10/2026 con licenze e hash).
- PVGIS: `https://re.jrc.ec.europa.eu/api/v5_3/tmy` e `/v5_2/tmy`, interrogati il 23/10/2026 (`usehorizon=0`).
- Studi: `docs/studio/11-pvsyst-casi-di-confronto.md` (casi e mappa dei passi), `06-pvsyst-aurora-pvlib.md` §1.1.13 e
  §1.1.14 (ordine e definizioni delle perdite, bilancio termico, PR), `10-pvsyst-formati-file.md` (lettura di `.VC0`
  e `.MET`).
- Codice letto: `src/meridiana/energy/simulate.py`, `meteo.py`, `components.py`, `system.py`, `pvgis.py`,
  `nearshade.py` (file e effetto elettrico), `catalog/__init__.py`, `catalog/panond.py`, `pvsyst/project.py`.
- Script e risultati: `docs/studio/18-prove/confronto_pvsyst.py` → `confronto_pvsyst-risultati.txt` (836 righe, 8
  casi, 4-6 varianti ciascuno, tempo di calcolo circa 25 s); `confronto_pvsyst_ipotesi.py` →
  `confronto_pvsyst_ipotesi-risultati.txt`. Comandi:

```
PYTHONPATH=src QT_QPA_PLATFORM=offscreen python docs/studio/18-prove/confronto_pvsyst.py --cache <cartella temporanea>
PYTHONPATH=src QT_QPA_PLATFORM=offscreen python docs/studio/18-prove/confronto_pvsyst_ipotesi.py --cache <cartella temporanea>
```
