# Correzione dopo revisione indipendente, R237, R02

29/10/2026. Integra il rapporto R01; non lo sostituisce.

[V] Riprodotto il difetto segnalato: una coppia inverter/batteria con fonte ma senza limiti completi consentiva il calcolo. I test nuovi sono falliti prima della correzione (sei fallimenti iniziali), compreso il caso quantità 100 senza massimo documentato.

[V] Separati `status` di compatibilità del modello e `missing_limits`. Il calcolo esplicito DC ora richiede intervalli operativi di tensione, massimo di corrente inverter, potenze massime inverter distinte di carica e scarica e quantità ammesse intere e documentate per il modello. Assenza, zero, NaN o limiti frazionari non autorizzano il calcolo. Il campo storico `battery_power_max_w` non chiarisce la direzione: non sostituisce i due limiti direzionali.

[V] In AC un singolo sistema con convertitore proprio conserva i rating dichiarati. Per più sistemi in parallelo serve un massimo documentato, senza presumere scalabilità illimitata. Il widget continua a mostrare i dati mancanti e disabilita Applica quando il calcolo non è possibile. Nessun dato di catalogo è stato inventato o cambiato nella correzione.

[V] Passati 14 test nucleo accumulo, due test widget e Ruff. Restano validi i limiti di modellazione del rapporto R01. Le coppie Huawei verificate hanno tutti i nuovi campi necessari; il relativo bilancio annuale e lo sweep sono stati riprovati dopo la correzione.

## Revisione indipendente del lotto B

Rilevati e trasmessi all'integratore tre difetti, senza modifica diretta dei file di B:

- Alto: il consenso allegati per turno controllava soltanto i nuovi allegati; quelli presenti nella cronologia venivano reinviati al cloud nel messaggio successivo senza conferma specifica. Riproduzione locale di `Chat.ask` senza provider reale: una chiamata start e nessuna richiesta di consenso.
- Medio: il validatore personale rifiutava strutture valide mantenute dall'editor JSON. Riprodotti SUN2000-20K-MB0, errore `dc_current_max_per_mppt_a`, e LUNA2000-7-S1, errore `voltage_range_by_phases_v`.
- Medio: metadati `field_sources.verified` proposti o ereditati rimanevano accreditati anche dopo modifica di un valore. Riprodotto un record personale con provenienza dichiarata dal modello che l'audit classificava `verified_field`. Le fonti vanno conservate come dichiarazioni e la verifica distinta dalla semplice conferma del salvataggio.

[V] L'editor conserva extras e fonte attraverso JSON e validazione, salvo il rifiuto delle strutture sopra. Nessun salvataggio automatico: la scrittura segue il pulsante Salva. I risultati tardivi dei job vengono scartati dopo rimozione/cambio conversazione; i tool sono soppressi nelle conversazioni con documenti. Il verdetto sul lotto B prima delle correzioni è richiesta di modifiche, non conformità completa.
