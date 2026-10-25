# Confronto della producibilità con PVGIS

Prova del 21/10/2026, motore di producibilità di Meridiana (`src/meridiana/energy/simulate.py`) contro il calcolo PVcalc di PVGIS 5.3 per lo stesso impianto.

## Le condizioni

- **Impianto:** 22 moduli da 450 W (9,9 kWp), su file libere. Inverter da 9 kW con rendimento pesato del 97%.
- **Meteo di Meridiana:** l'anno tipo PVGIS 5.3 (SARAH-3 + ERA5, anni 2005-2023), con l'orizzonte PVGIS applicato da Meridiana.
- **Perdite di Meridiana:** quelle predefinite:
  - sporcamento 2%;
  - LID 1%;
  - mismatch 1%;
  - cavi in continua 1,5% a STC;
  - cavi in alternata 1%.
- **PVGIS:** perdite di sistema all'8%, l'equivalente delle stesse voci. PVGIS calcola da sé riflessione, temperatura, spettro e orizzonte.

Il modulo è quello «tipico» di Meridiana: TOPCon, γ = −0,30 %/K.

## Il risultato

| Sito | Inclinazione | Azimut | Meridiana (kWh) | kWh/kWp | PR | PVGIS (kWh) | Differenza |
|---|---|---|---|---|---|---|---|
| Rho (MI) | 30° | 0° | 14 942 | 1 509 | 85,9% | 14 359 | +4,1% |
| Rho (MI) | 10° | 0° | 13 475 | 1 361 | 85,5% | 13 056 | +3,2% |
| Rho (MI) | 20° | −90° | 11 758 | 1 188 | 85,2% | 11 497 | +2,3% |
| Roma | 30° | 0° | 16 539 | 1 671 | 85,0% | 15 837 | +4,4% |
| Roma | 10° | 0° | 15 242 | 1 540 | 84,9% | 14 588 | +4,5% |
| Roma | 20° | −90° | 13 568 | 1 371 | 84,8% | 13 110 | +3,5% |
| Palermo | 30° | 0° | 16 393 | 1 656 | 84,8% | 16 210 | +1,1% |
| Palermo | 10° | 0° | 15 538 | 1 569 | 84,9% | 15 261 | +1,8% |
| Palermo | 20° | −90° | 14 162 | 1 430 | 84,9% | 13 806 | +2,6% |
| Bolzano | 30° | 0° | 14 872 | 1 502 | 81,8% | 14 171 | +4,9% |
| Bolzano | 10° | 0° | 13 496 | 1 363 | 83,2% | 12 858 | +5,0% |
| Bolzano | 20° | −90° | 11 600 | 1 172 | 80,8% | 11 214 | +3,4% |

## Da dove viene la differenza

A Rho, voce per voce:
- **Radiazione sul piano:** coincide. Meridiana ha 1 757 kWh/m² sull'anno tipo, PVGIS 1 747 sulla media pluriennale.
- **Riflessione sul vetro:** coincide, −2,61% contro −2,74%.
- **Temperatura e basso irraggiamento:** qui sta quasi tutta la differenza. Meridiana perde il 3,4%, PVGIS l'8,3% (con +1,1% per lo spettro). PVGIS usa un modello empirico per il silicio cristallino tarato su moduli di qualche anno fa, con un coefficiente di temperatura più alto. Meridiana usa il coefficiente γ della scheda del modulo scelto.

Con un modulo PERC (γ ≈ −0,35 %/K) la differenza si riduce di circa un punto.

Bolzano ha le montagne fino a 20° sull'orizzonte. Nella prima prova Meridiana toglieva solo la luce diretta e superava PVGIS del 5,6-6,8%. Ora toglie anche la parte di cielo diffuso nascosta dalle montagne, calcolata sulla volta celeste vista dal piano dei moduli. Così rientra nello stesso scarto degli altri siti.

Lo scarto residuo, tra +1% e +5%, è lo scarto tra i due modelli di modulo. Nel programma il confronto con PVGIS resta visibile accanto al risultato di Meridiana, con questa spiegazione.

## Come ripeterlo

Gli script `crosscheck.py` e `crosscheck2.py` (nella cartella temporanea della sessione) chiamano:
- `meridiana.energy.meteo.typical_year`;
- `meridiana.energy.meteo.horizon`;
- `meridiana.energy.simulate.simulate`;
- `meridiana.energy.pvgis.pvcalc`.

Le risposte di PVGIS restano nella cache di Meridiana.
