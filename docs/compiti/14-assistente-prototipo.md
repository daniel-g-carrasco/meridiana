# Compito per una sessione cloud: Meridio risponde davvero (studio 14, passi 1-3)

Bozza del 23/10/2026, da lanciare **dopo i compiti dello studio 16**. Lo studio è `docs/studio/14-assistente-agente.md`; il guscio di Meridio c'è già (`src/meridiana/assistant.py`, `src/meridiana/ui/assistant.py`). Le regole di lavoro sono quelle di `docs/compiti/fase-2.md` («Come lavorare»):
- ramo `assistente-1` da `lavoro`;
- richiesta di unione in bozza verso `lavoro`;
- un commit per pezzo con i suoi test, spinto subito;
- `docs/richieste.md` aggiornato;
- riassunto in italiano alla fine.

**Deciso da Daniel il 23/10/2026:**
- nome **Meridio**;
- **il modello locale come predefinito**, partendo da Qwen3.6-35B-A3B con `llama-server` (llama.cpp, Vulkan), come provato sul portatile (studio 14, 4.4);
- **Claude con la chiave API di Daniel per le domande difficili**, sempre dopo un consenso esplicito e mai con dati del progetto senza quel consenso.

**Limiti della sessione cloud.** Qui non c'è né il modello locale né la chiave di Daniel: tutto si prova con un server finto (risposte in streaming SSE registrate) e con l'SDK Anthropic simulato. Le prove vere le fa la sessione locale sul portatile e sul PC, e vanno scritte in «Da provare sul PC di Daniel».

## Passo 1: il prototipo minimo (studio 14, sezione 9, passo 1)
1. `assistant/providers.py` nel nucleo: un'interfaccia sola; il primo adattatore è compatibile con OpenAI, verso `llama-server`, con le risposte che arrivano man mano.
2. Tre strumenti in sola lettura: `read_checks`, `project_summary`, `go_to`.
3. Nella chat di Meridio: il testo che arriva man mano, il pulsante Ferma, Ctrl+L. Lo stato «pensa» del personaggio mentre risponde.
4. La chiamata in un thread (`QRunnable`): la finestra non aspetta mai.
5. Test:
   - con un server SSE finto le domande A e D della sezione 4.4 tornano con le chiamate agli strumenti giuste;
   - Ferma interrompe;
   - senza server la chat dice che il modello locale non è avviato e come avviarlo.

## Passo 2: le proposte (studio 14, sezione 9, passo 2)
6. `propose_fix` e `propose_edit` con le schede di conferma; ogni proposta applicata passa da `edit()` e si annulla con Ctrl+Z.
7. `read_selection`, `read_results`, `read_pedigree`, `read_rules`; «Chiedi a Meridio» sulle verifiche.
8. Test: le domande 23-29 della batteria con il server finto; Ctrl+Z annulla ogni proposta.

## Passo 3: Claude con la chiave API (studio 14, sezione 9, passo 3)
9. L'adattatore Anthropic con l'SDK ufficiale.
   - Modelli: Haiku per le domande correnti e Sonnet per le difficili, come nello studio 14 (3.5). Prima di scrivere il codice controlla gli identificativi e i prezzi correnti sulla documentazione ufficiale.
   - La chiave sta nel portachiavi del sistema (`keyring`), mai nei file.
10. Il consenso:
    - la prima volta che una domanda andrebbe al cloud, Meridio chiede il permesso e dice che cosa partirebbe;
    - un progetto si può segnare «riservato» (mai al cloud);
    - nomi e indirizzi sostituiti da segnaposti (studio 14, 6.6);
    - la spia casa o nuvola sul personaggio.
11. I costi: il conteggio dei token e la stima in euro della conversazione, visibili.
12. Senza rete: torna al locale e lo dice.
13. Test: nessun dato parte senza consenso (verificato sul client simulato); un progetto riservato non parte mai; la chiave non finisce in nessun file.

## Fatto (24/10/2026 sera, ramo `voce`, R82)

Il compito è stato fatto da una sessione locale (non cloud), sul ramo `voce` creato da `grafica`, con in più la voce parlata chiesta da Daniel il 24/10 («Puoi dare una voce a Meridio?»).

**Passo 1** [V test]
- `src/meridiana/assistant/` diventa un pacchetto: in `__init__.py` il personaggio di prima (spostato, uguale); accanto:
  - `providers.py`: un'interfaccia sola (`stream` dà testo, chiamate, uso, fine); `OpenAICompatible` su `requests` con gli eventi SSE (verso `llama-server`, con `enable_thinking: false` come nella prova dello studio, 4.5); errori in parole (`offline`, `auth`, `limit`, `model`, `server`, `bad`);
  - `tools.py`, `conversation.py` (il ciclo con un tetto di 6 giri), `context.py` (le istruzioni, uguali a ogni giro per la cache; fase e selezione vanno con la domanda), `text.py` (il Markdown del modello in HTML e in frasi).
- Strumenti del passo 1: `read_checks`, `project_summary` (coordinate arrotondate a 0,01°), `go_to`; in più `search_manual` (il manuale e i comandi con i loro tasti), anticipato dal passo 4: senza, la domanda D non ha una risposta vera.
- Nella finestra (`ui/assistant_chat.py`): la chiamata in un `ChatJob` sul pool (la finestra non aspetta), il testo che arriva nel fumetto (ridisegnato al più 20 volte al secondo), la faccia che pensa mentre aspetta e gli strumenti girano, Ferma che chiude il turno subito e spegne la connessione, Ctrl+L come prima; senza server: «Il modello locale non è avviato all'indirizzo … Avvialo su questo PC, per esempio llama-server -m modello.gguf --port 9931».
- La porta predefinita è 9931, quella di `llama-server` dalla 0.7.0 (studio 14, 4.2); si cambia in Preferenze > Assistente.

**Passo 2** [V test]
- `read_selection`, `read_results`, `read_pedigree`, `read_rules`; `propose_fix` (la correzione che la verifica ha già) e `propose_edit` (solo i campi delle Proprietà e delle impostazioni dell'energia, controllati con le regole del file: un campo inventato torna al modello con l'elenco giusto).
- Ogni proposta è una scheda nel fumetto («Scarta», «Applica»): «Applica» passa da `edit()` con il testo «Meridio: …» e si annulla con Ctrl+Z; il modello sa alla domanda dopo che cosa il progettista ha scelto.
- «Chiedi a Meridio» accanto a «Correggi» nelle Verifiche: apre il fumetto con la domanda scritta, come il riquadro d'aiuto.

**Passo 3** [V test con l'SDK simulato; nessuna chiamata vera]
- `providers.Anthropic` con l'SDK ufficiale `anthropic` 2.3.0 (licenza Apache-2.0, non MIT come scritto nello studio), importato solo quando serve; istruzioni e strumenti nella cache; Haiku con `effort` basso, Sonnet medio con il ripiego lato server sui rifiuti (beta `server-side-fallback-2026-07-01`, come chiede la skill claude-api).
- Modelli e prezzi dalla skill claude-api (tabella del 06/10/2026) e dalla pagina ufficiale dei prezzi letta il 24/10/2026: `claude-haiku-5-5` 0,10 $ in ingresso, 0,50 $ in uscita, 0,01 $ dalla cache, 0,125 $ in scrittura per milione di token (sopra 100.000 token di prompt 0,50 / 2,50 / 0,05 / 0,625); `claude-sonnet-5-5` 2 / 10 / 0,10 / 2,50. La skill dava 0,20 $ per la lettura dalla cache di Sonnet 5.5; la pagina ufficiale dice 0,10 $, come lo studio: vale la pagina. Il cambio è quello della BCE del 23/10/2026 (1 € = 1,1193 $).
- La chiave nel portachiavi del sistema (`assistant/keys.py`, servizio `meridiana-assistant`), impostata e tolta in Preferenze > Assistente; mai nei file.
- Il consenso: la prima domanda per Claude mostra nel fumetto che cosa partirebbe e una scheda («Modello locale», «Non ora», «Consenti e invia»); niente parte prima del clic; il consenso resta nelle impostazioni (versione 17) e si ritira dalle Preferenze.
- Il progetto «riservato»: formato di progetto 12 (`reserved`, migrazione dalla 11, `progetto-v12.meridiana`); si segna dalle Proprietà del sito o dal menu di Meridio, come passo annullabile; le sue domande vanno sempre al locale.
- Nomi e indirizzi sostituiti da `[PROJECT]`, `[ADDRESS]`, `[FILE]` verso il cloud e rimessi nella risposta mostrata.
- La casetta o la nuvola sul personaggio e nel menu in testa al fumetto (Locale, Claude Haiku 5.5, Claude Sonnet 5.5, progetto riservato, nuova conversazione, impostazioni); la riga dei token e del costo stimato in cima alla conversazione, dalla prima risposta.
- Senza rete: la domanda passa al modello locale, e il fumetto lo dice.

**La voce** [V test con il motore finto di Qt]
- `ui/voice.py` con QtTextToSpeech: lo stesso codice usa WinRT o SAPI su Windows e speech-dispatcher su Linux; l'altoparlante in testa al fumetto, spento di serie, ricordato nelle impostazioni; legge nella lingua del programma.
- Frase per frase mentre la risposta arriva, non alla fine: il modello locale scrive circa 9 token al secondo, una voce ne legge circa 3, quindi la prima frase si sente mentre il resto si scrive e la coda non resta vuota; aspettare la fine lascerebbe mezzo minuto di silenzio.
- Si ferma con Ferma, con Esc (il fumetto che si chiude) e con una domanda nuova; senza motore, o senza una voce della lingua, l'altoparlante è grigio e il suggerimento dice perché.
- Su questo Windows 11 [V]: motori `winrt` (voci italiane Microsoft Cosimo e Microsoft Elsa) e `sapi` (Microsoft Elsa Desktop); Meridiana prende `winrt` e la voce maschile, Cosimo.

**La prova vera sul portatile** [V, 24/10/2026 sera]
- `llama-server` 0.7.0 con Qwen3.6-35B-A3B UD-IQ4_XS (`-ngl 99 -ncmoe 20 --no-host -lm dio -fa on -c 16384`, solo su 127.0.0.1, guardia sulla GTT a 12 GiB), porta inoltrata con SSH; pronto in 29 s; GTT 11,5 GiB con il desktop di Daniel aperto, RAM disponibile 5 GiB durante la prova; spento alla fine (nessun `llama` rimasto).
- Progetto di prova «Capannone Rho» dei test con le due verifiche della prova dello studio; nessun progetto di Daniel.
- A: `read_checks(warn)`, la tensione prima dell'ombra, le fonti; 33 s (prima parola a 13 s). D: `search_manual`, menu Varianti con Ctrl+Maiusc+N e «Confronta le varianti» con Ctrl+Maiusc+C; 31 s (12 s). B: `go_to(subfield s1)` e `propose_fix(c2)`, «non è ancora applicata»; 41 s. 27: `read_checks(fail)` e `go_to(phase plant)`; 21-34 s.
- Le prime prove hanno insegnato tre righe delle istruzioni: proporre invece di descrivere, i livelli con i nomi del programma, chiamare `go_to` quando si chiede «portami» (in una prova aveva detto di aver portato senza farlo); e niente LaTeX né nomi degli strumenti.
- Le risposte registrate sono in `tests/data/assistant/` e i test le ripetono.

## Che cosa resta
- Il passo 4 (il manuale come contesto, le norme dell'archivio come strumento), il passo 5 (la batteria di 30 domande × 3 ripetizioni sui fornitori) e i seguenti dello studio 14, sezione 9.
- `compute_production` come strumento: la correzione «Calcola» di una verifica si può già proporre e applicare (lo dice la scheda, perché può scaricare il meteo da PVGIS).
- Dopo «Applica» Meridio non rilegge da solo le verifiche (studio 14, 6.5, punto 4): lo fa alla domanda dopo.
- Un tetto mensile della spesa e il totale del mese (studio 14, 6.8): oggi si vede il costo della conversazione.
- Il registro facoltativo di che cosa è partito verso il cloud (6.6, punto 6).
- Nel Flatpak servirà `--share=network` e `--talk-name=org.freedesktop.secrets` (6.7, 6.10).
- Unione (24/10 sera): `grafica` aveva preso per la relazione le impostazioni 16 e il formato di progetto 11; questo ramo è diventato impostazioni 17 e formato 12.

## Da provare sul PC di Daniel
- Sul PC: la chiave API di Daniel in Preferenze > Assistente > «Imposta la chiave…», una domanda vera a Haiku e una a Sonnet, il consenso la prima volta, il costo mostrato in cima alla conversazione (confrontarlo con la console di Anthropic), Ferma mentre Claude scrive (lo stream di Claude si ferma al pezzo successivo).
- La voce a orecchio: l'altoparlante in testa al fumetto, Cosimo in italiano, la lettura mentre la risposta arriva, Ferma ed Esc che la zittiscono; se la voce di Elsa piace di più, dirlo.
- Il modello locale avviato sul PC Windows (build CUDA o Vulkan di llama.cpp) invece che sul portatile: non provato.
- Sul portatile, la stessa prova dentro Meridiana con la finestra vera (qui il ciclo e gli strumenti di Meridiana sono stati provati senza finestra, la finestra con le risposte registrate).
