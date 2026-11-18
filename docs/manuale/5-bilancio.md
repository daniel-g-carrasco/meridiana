# 5. Bilancio ed economia

Produzione e consumi si incontrano ora per ora sull'anno tipo: ciò che si usa sul posto fa risparmiare in bolletta, il resto va in rete e si vende. I flussi di cassa negli anni dell'analisi danno poi il valore attuale netto, il tasso interno di rendimento e il tempo di ritorno. «Come è calcolato» mostra ogni passo con le sue fonti.

## Autoconsumo

La produzione usata sul posto nella stessa ora, sul totale prodotto; il resto va in rete. Si calcola ora per ora, non sui totali mensili, che lo sopravvaluterebbero. Una batteria accumula parte dell'eccedenza del giorno per la sera e lo alza.

## Autosufficienza

I consumi coperti dall'impianto, direttamente o dalla batteria, sul totale dei consumi. Con l'accumulo sale; senza, l'energia della notte viene sempre dalla rete. Autoconsumo alto e autosufficienza bassa dicono un impianto piccolo per i consumi; il contrario, un impianto grande che vende molto.

## Il primo anno

- **Risparmio**: l'energia autoconsumata in ogni fascia per il suo prezzo.
- **Vendita e incentivi**: l'energia immessa per il suo valore (ritiro dedicato), più l'incentivo della comunità energetica se l'impianto ne fa parte.
- **Bolletta**: la parte energia della bolletta, mese per mese, senza l'impianto e con l'impianto.

## Valore attuale netto

I flussi di cassa di ogni anno dell'analisi, scontati al tasso scelto, meno l'investimento. Positivo, l'impianto rende più di quanto costa a quel tasso. I predefiniti sono 25 anni e un tasso del 4 %, con i prezzi dell'energia che crescono del 2 % l'anno (valori predefiniti di Meridiana, `energy/economics.py`, `Settings`). Il grafico «Taglia» mostra come cambia con la potenza dell'impianto.

## Il rendimento

- **Investimento**: il costo per kWp chiavi in mano (1.300 €/kWp per impostazione) o il totale dell'offerta, che quando c'è vince.
- **Tasso interno di rendimento**: il tasso che porta a zero il valore attuale netto.
- **Tempo di ritorno**: l'anno in cui il flusso di cassa cumulato diventa positivo.
- **Costo livellato dell'energia**: quanto costa ogni kWh prodotto negli anni dell'analisi.

I costi di esercizio (20 €/kWp l'anno) e la sostituzione dell'inverter (al 12° anno, 150 €/kW) sono predefiniti di Meridiana (`energy/economics.py`, `Settings`).

## Prezzi

I prezzi dell'energia comprata e venduta e i costi partono da valori indicativi: 0,25 €/kWh per ogni fascia, 0,10 €/kWh per l'energia immessa (valori predefiniti di Meridiana, `energy/economics.py`, `Settings`). Sono segnati come predefiniti in «Come è calcolato» e nelle Verifiche, e la relazione li elenca in fondo. Sostituiscili con quelli della bolletta (tutti i costi variabili, imposte comprese) e dell'offerta dell'installatore: sono le cifre che più spostano il risultato.
