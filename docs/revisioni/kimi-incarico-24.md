# Incarico 24 per Kimi: sfumature, scritte, sezioni con la spunta, salvataggi, meteo, Meridio (R192-R197), 27/10/2026

Usa la skill meridiana, e soprattutto «armonizziamo»: ogni correzione qui va fatta una volta nei moduli condivisi e
vale ovunque. Leggi parola per parola le righe R192-R197 di docs/richieste.md, e R161 e R177 per le sfumature.

## Dove lavori
Nella cartella ~/dev/meridiana-kimi, sul ramo kimi-incarico-24 preso da kimi-incarico-23 (il lanciatore lo crea).

## Punti
1. **R192, le sfumature.** Dopo R177 (sfumatura piena sul bordo e 8 px d'aria, ui/fades.py) Daniel le trova peggiorate:
   nel pannello Inverter scorso la prima voce resta velata in alto. Fotografa nella sessione nascosta tre varianti
   (quella di R161, quella di R177, una via di mezzo che proponi tu) sul pannello Inverter scorso a metà, sul Bilancio e
   su un elenco, chiaro e scuro; raccomandane una e realizzala in ui/fades.py. Il contenuto non deve mai arrivare sulla
   linea della scheda (R177) né restare velato quando è fermo in cima.
2. **R193, le scritte troncate.** «Quota dell'energia immessa che è condivisa» è tagliata sopra e sotto: una riga di
   modulo deve crescere con la sua etichetta a capo. Correggi dove si costruiscono le righe dei moduli, poi fai un
   controllo automatico su tutte le pagine e i pannelli (chiaro e scuro, testo Medio e Grande, finestra larga e stretta)
   che trovi ogni etichetta più alta dello spazio che ha, e correggi quello che trova.
3. **R194, la spunta che apre la sua sezione.** Senza la spunta «L'impianto è in una CER» i campi della sezione sono
   spenti (non compilabili, attenuati, con il suggerimento che dice perché); con la spunta si accendono. Un meccanismo
   unico e riusabile, applicato a tutte le sezioni simili che trovi (elencale nell'esito). I valori restano salvati ma
   non entrano nei calcoli finché la spunta è tolta.
4. **R195, i salvataggi.** Nella barra di stato (le «sezioni apposite di info»): durante un salvataggio un piccolo
   segno di attività, poi «Salvato alle 10:42» (con Ctrl+S) o «Salvato in automatico alle 10:42», discreto, nello stile
   dei messaggi della barra; se il salvataggio fallisce, il messaggio d'errore che c'è già.
5. **R196, il meteo da solo.** Quando il sito ha le coordinate e i dati del clima e dell'orizzonte mancano, Meridiana li
   scarica da sola in sottofondo (se c'è rete) e li salva dentro il progetto, che deve restare autonomo (R150). Non a ogni
   apertura: di nuovo solo se il sito si sposta oltre una distanza che scegli e motivi, se cambia la versione della banca
   dati o se Daniel lo chiede. Senza rete lo dice chiaramente e calcola con quello che ha. Misura e scrivi nell'esito
   quanto pesano i dati per sito.
6. **R197, il fumetto di Meridio.** Il nome più distante dalla maniglia di ridimensionamento; le opzioni di risposta
   solo quando servono, come pulsanti del programma (stesso stile, hover compreso); Meridio non chiede «ti faccio la
   proposta?»: la fa subito e apre la finestrella della proposta, che Daniel guarda e applica o no. Cambia il comportamento
   del modello (istruzioni e strumenti) e provalo con il provider finto, ripetendo una conversazione in cui oggi chiede
   il permesso.
7. **Chiusura.** Registro, CHANGELOG, po/it.po, esito in docs/revisioni/kimi-incarico-24-esito.md con le foto e i moduli
   condivisi cambiati (Claude li porta nel modello grafico), tutti i gruppi di prove, ruff, msgfmt.
