# Compito per una sessione cloud: i calcoli, più vicini a PVsyst (revisione 18)

Bozza del 23/10/2026 dalla revisione completa (`docs/studio/18-revisione-completa.md`, sezione 2.B; i rapporti `docs/studio/18-prove/B-calcoli.md` sezioni 6 e 7 e `B-pvsyst.md` sezioni 6 e 8, con gli script `confronto_pvlib.py`, `confronto_pvgis.py`, `confronto_pvsyst.py` e `confronto_pvsyst_ipotesi.py` da rilanciare dopo ogni passo come prova numerica). Regole di `docs/compiti/fase-2.md`: ramo `calcoli` da `lavoro`, un commit per passo, ogni cambio di formula con la fonte nella pedigree e nel test, niente dipendenze nuove (pvlib ha già `calcparams_pvsyst` e `fit_pvsyst_sandia`).

## Passo 1: il modello del modulo
1. `components.py:70-75`: `cells_in_series` non fidato dal record CEC quando contraddice il Voc (il Jinko 540 con N_s 24 diventa lineare); l'euristica sul Voc per prima; un test con un record incoerente.
2. `components.py:176-201`: la bassa irradianza non più un artefatto dell'adattamento al solo punto STC: con il `.PAN` i parametri PVsyst (`RShunt`, `Rp_0`, `Rp_Exp`, `RSerie`, `Gamma`, `muGamma`, letti da `catalog/panond.py:82-133`) con `calcparams_pvsyst`; senza `.PAN`, l'adattamento vincolato anche a bassa irradianza (la resa relativa a 200 W/m² da scheda, se c'è, altrimenti un valore convenzionale dichiarato); il passo «livello di irradianza» della pedigree che dice da dove viene.
3. Il ripiego lineare con un test (D §6.19).

## Passo 2: tre ritocchi provati su PVsyst (B3 §6.2, §6.3, §6.5)
4. `simulate.py:299-300`: il bilancio termico con l'efficienza al punto di lavoro (due passate) invece dell'efficienza STC: chiude +0,16/+0,57 punti.
5. `simulate.py:326-327` e `:359`: cavi DC in (I/I_STC)² con la corrente al MPP del modello, cavi AC con (P/P_nom)² solo dove la perdita è resistiva: chiude 0,2-0,3 punti.
6. `simulate.py:249, 316, 322`: l'effetto elettrico delle file con l'interruttore lineare/elettrico e la frazione, come PVsyst; il predefinito e la sua spiegazione nelle Proprietà (studio 16 e design §2.4).

## Passo 3: l'inverter
7. L'inverter per ingresso MPPT dalla stringatura (`energy/stringing.py` conosce le stringhe per ingresso, `simulate.py:357-358` no): taglio per ingresso e per inverter, soglie di avvio, consumo notturno, curva `.OND` letta da `panond.py:136-172` (profilo di efficienza, non solo `EfficEuro`). Dipende dal compito 16d per gli oggetti inverter e ingresso: finché non c'è, il taglio per inverter con la quota di stringhe assegnata.
8. L'indisponibilità come periodi di tempo (`simulate.py:361`), non come frazione di energia.

## Passo 4: PVGIS e i limiti dichiarati
9. Il secondo parere PVGIS già corretto dal 18a (`crystSi2025`, base di anni detta); l'orizzonte con un fattore sull'albedo (`simulate.py:236`).
10. La relazione e «Come è calcolato» con una sezione «Che cosa il modello non include»: bifacciale (`bifaciality` letto e non usato), spettro, degrado nell'anno e P50/P90 (PVGIS dà `SD_y`), neve, sporcamento mensile, trasformatore e ausiliari, cavi con lunghezze, inseguitori; il passo «livello di irradianza» e l'effetto elettrico delle ombre marcati come stime.
11. `economics.irr` oltre il 100 % (`economics.py:182-189`) e i profili di consumo con la fonte scritta (`consumption.py:42-102`).

## Passo 5: altre fonti meteo (da decidere: domanda 4 dello studio 18)
12. La lettura dei `.MET` e dei CSV di PVsyst e Meteonorm (`pvsyst/project.py` legge già i `.MET`), la scelta PVGIS 5.2/5.3, l'anno tipo da medie mensili, la fonte meteo scritta nella relazione; la segnalazione quando PVGIS passa a ERA5 fuori dal dominio SARAH.

## Da provare sul PC di Daniel
- Il caso LaFact a due falde (B3 §6.11) con PVsyst.
- I sei casi PVsyst di `confronto_pvsyst.py` dopo i passi 1-3: gli scarti attesi entro ±1 punto sui nodi del modulo e della temperatura.
