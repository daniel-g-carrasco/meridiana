# 14a. Modelli locali semplici per Meridio

25/10/2026. Seguito dello studio 14 (sezione 4, «In locale»). Risponde alla richiesta R105 di Daniel: «Devi individuare delle metodologie semplificate per usare modelli locali se possibile».

Legenda:
- **[V]** verificato: letto il 25/10/2026 in una fonte ufficiale (documentazione, repository, scheda del modello, classifica: gli URL sono nella sezione 10), oppure provato sul PC di Daniel o nei test;
- **[I]** dedotto, oppure preso da una fonte secondaria.

Voti da 1 a 5, dove 5 è il migliore: sono il mio giudizio sui fatti raccolti qui.

## 1. In breve

- **Meridiana ora trova da sé i modelli locali del PC.**
  - Guarda chi risponde su 127.0.0.1 alle porte di serie dei programmi: Ollama, LM Studio, llama.cpp, Jan, Lemonade, Docker Model Runner, KoboldCpp e qualunque server compatibile con OpenAI.
  - Guarda anche che cosa è installato sul disco e non avviato, e dice come avviarlo.
  - Elenca i modelli di ciascuno, legge la memoria del PC, sceglie il modello da usare e dice perché.
  - Un pulsante («Usa questo») riempie i campi; un altro («Prova») fa una domanda di prova che deve tornare come chiamata di uno strumento.
- **Quando sul PC non c'è niente, la guida è di due comandi**: installare Ollama e scaricare il modello adatto alla memoria. Meridiana non installa e non scarica niente da sé.
- **Ollama è la strada consigliata per chi non vuole configurare niente** [I]:
  - un installatore senza permessi di amministratore;
  - un servizio che resta acceso;
  - un comando per il modello.
  - La sua trappola: dalla sua API compatibile con OpenAI il contesto resta a 4.096 token sotto i 24 GiB di memoria video, e le istruzioni di Meridio verrebbero tagliate senza avviso [V].
  - Per questo Meridiana gli parla con la sua API propria, che accetta il contesto (16.384 token) e il ragionamento spento a ogni richiesta.
- **Per il PC di Daniel** (32 GB di RAM, RTX A2000 da 8 GB):
  - modello: **Qwen3.6-35B-A3B**, quello già provato con gli strumenti di Meridio nello studio 14, cioè `ollama pull qwen3.6:35b-a3b` (circa 24 GB);
  - in alternativa, la stessa scelta dello studio 14: llama.cpp con un comando solo, `winget install llama.cpp` e poi `llama-server -hf unsloth/Qwen3.6-35B-A3B-GGUF:UD-IQ4_XS -c 16384`.
- Sul PC di Daniel oggi non c'è nessun programma di modelli locali [V]: la parte «trovati» è provata con server finti, quella della guida anche sulla finestra vera.

## 2. Il PC di Daniel [V]

Letto il 25/10/2026 in sola lettura: `Get-CimInstance`, `nvidia-smi`, `Get-Command`, `Test-Path`, `Get-NetTCPConnection`.

| Parte | Valore |
|---|---|
| CPU | Intel Core i7-12700H, 14 core |
| RAM | 31,6 GB |
| GPU | NVIDIA RTX A2000 8GB Laptop GPU (8.192 MiB, driver 595.95) e Intel Iris Xe |
| Programmi di modelli locali | nessuno: né `ollama`, né `llama-server`, né `lms`, né Jan; nessuna cartella `.ollama`, `.lmstudio`, `Jan` |
| Porte in ascolto | nessuna di 1234, 1337, 5001, 8000, 8080, 9931, 11434, 13305 |

## 3. I programmi che servono i modelli (ottobre 2026)

| Programma | Porta di serie | Come Meridiana lo riconosce | Strumenti dichiarati | Contesto | Ragionamento | Installazione su Windows | Licenza | Voto per «semplice» |
|---|---|---|---|---|---|---|---|---|
| **Ollama** 0.40.11 (24/10) | 11434 | `/api/version`; modelli da `/api/tags`, capacità da `/api/show` | sì, `capabilities` contiene `tools` (dalla 0.6.4) [V] | 4.096 token sotto 24 GiB di VRAM; si cambia per richiesta solo con l'API propria (`options.num_ctx`) [V] | `think` per richiesta: `false`, oppure `low`/`medium`/`high` per gpt-oss [V] | `OllamaSetup.exe` 1,66 GB senza amministratore, oppure `winget install Ollama.Ollama` [V] | MIT [I] | **5** |
| **llama.cpp** `llama-server` 0.7.0 (15/10) | **9931** (8080 prima della 0.7.0 e nelle immagini Docker) [V] | `/props` (`build_info`), modelli da `/v1/models` o `/models` (più modelli) | `/props` → `chat_template_caps.supports_tools` [V] | fissato all'avvio (`-c`); `--fit on` di serie lo riduce per stare in memoria [V] | per richiesta `chat_template_kwargs.enable_thinking: false` o `reasoning_effort: "none"` [V] | `winget install llama.cpp` [V]; poi un comando con `-hf` che scarica il modello | MIT | 4 |
| **LM Studio** 0.4.26 | 1234 | `/api/v1/models` con `type` e `key`; il vecchio `/api/v0/models` | `capabilities.trained_for_tool_use` [V] | fissato al caricamento (`lms load --context-length`) [V]; Meridiana avvisa se è sotto 12.288 | `reasoning_effort` dalla 0.4.8 [V] | installatore; `lms server start` per il server [V] | chiusa: niente ridistribuzione [V] | 3 |
| **Jan** 0.8.7 (20/10) | 1337 | `/v1/models` sulla sua porta | non dichiarati | per modello | - | installatore di 560 MB; il server va acceso a mano [V] | AGPL [I] | 3 |
| **Lemonade** (AMD) | 13305 | `/api/v1/models` con `labels` | `labels` contiene `tool-calling` [V] | - | - | msi di 11 MB [V] | Apache 2.0 [I] | 3 |
| **Docker Model Runner** | 12434 | `/engines/v1/models` [V] | non dichiarati | - | - | Docker Desktop | - | 2 |
| **Foundry Local** (Microsoft, anteprima) | cambia a ogni avvio [V] | non si trova da solo: Meridiana ne trova il programma e dice di leggere l'indirizzo con `foundry server status` | - | - | - | `winget install Microsoft.FoundryLocal` [V] | - | 2 |
| KoboldCpp, LocalAI, vLLM, text-generation-webui | 5001, 8080, 8000, 5000 [V/I] | come server compatibili con OpenAI | - | - | - | - | varie | 1-2 |
| GPT4All | 4891 [I] | - | - | - | - | ultima versione febbraio 2025 [V]: fermo | MIT | 1 |

Che cosa conta per Meridio:
- **Diversi programmi rispondono anche all'API di Ollama** (Lemonade, Docker Model Runner, LocalAI, KoboldCpp) [V]. Meridiana li riconosce da quello che ha solo ciascuno (tabella sopra), non da `/api/tags`.
- **Il contesto di serie di Ollama** taglia le richieste lunghe dall'inizio: tiene solo metà del contesto, e lo scrive soltanto nel suo registro (ollama#17427, chiuso come comportamento voluto; openclaw#4028: 10.573 token ridotti a 4.096) [V]. Le istruzioni di Meridio e i dieci strumenti sono 3-4.000 token, più i risultati: con 4.096 andrebbero perse proprio le istruzioni.
  - Da qui la scelta: **con Ollama Meridiana usa `/api/chat`**, con `num_ctx` 16.384, il ragionamento spento (`think: false`, oppure `low` per gpt-oss, letto da `/api/show`) e il modello tenuto in memoria per mezz'ora.
  - Il contesto è lo stesso a ogni richiesta: cambiarlo ricarica il modello [I].
- **llama-server ha cambiato porta** con la 0.7.0: la porta di serie di Meridio (9931) è già quella giusta [V].
- **LM Studio non si può includere** in Meridiana: i termini del 23/08/2026 vietano ridistribuzione e modifiche [V]. Meridiana lo trova e lo usa se c'è.

## 4. I modelli piccoli con strumenti (ottobre 2026)

I punteggi degli strumenti (BFCL, Tau2, Tau3) sono quasi tutti **dichiarati da chi ha fatto il modello**, e quelli di aziende diverse non sono confrontabili. La classifica ufficiale BFCL v4 (pagina del 12/04/2026) non ha nessuno dei modelli piccoli del 2026 [V]. La classifica italiana di EuroEval non si legge (è disegnata in JavaScript e il vecchio repository è stato archiviato il 20/05/2026) [V]: il giudizio sull'italiano dello studio 14 (Gemma 4 26B il migliore) non è riverificato; lo sostiene MMMLU, che è multilingue e non solo italiano.

| Modello | Uscita | Parametri (totali / attivi) | Licenza | Strumenti (chi ha misurato) | Italiano | File Q4 (GGUF) | Ollama | Voto per Meridio |
|---|---|---|---|---|---|---|---|---|
| **Qwen3.6-35B-A3B** | 15/04 | 35B / 3B | Apache 2.0 | MCP-Atlas 62,8 e TAU3 67,2 (Qwen); BFCL v4 65,0 (Liquid) [V]; **provato con Meridio** (studio 14, 4.4) | buono [I] | UD-IQ4_XS 17,7 GB; UD-Q4_K_M 22,1 GB [V] | `qwen3.6:35b-a3b`, 24 GB; strumenti, ragionamento, visione [V] | **5** |
| **Gemma 4 26B-A4B** | 31/03 | 25,2B / 3,8B | Apache 2.0 | Tau2 68,2 (Google); BFCL v4 57,1 (Liquid) [V] | il migliore che entra: MMMLU 86,3 [V] | UD-IQ4_XS 13,6 GB [V] | `gemma4:26b-a4b-it-qat`, 16 GB [V] | 4 |
| gpt-oss-20b | 08/2025 | 21B / 3,6B | Apache 2.0 | τ²-Bench 47,7 (Z.ai) [V]; formato Harmony maturo [I] | più debole [I] | MXFP4 12,1 GB [V] | `gpt-oss:20b`, 14 GB; il ragionamento non si spegne [V] | 4 |
| **Qwen3.5-9B** | 02-03/2026 | 9B denso | Apache 2.0 | BFCL v4 66,1, TAU2 79,1 (Qwen) [V] | MMMLU 81,2 [V] | Q4_K_M 5,7 GB [V] | `qwen3.5:9b`, 6,6 GB [V] | 4 |
| Gemma 4 12B | 03/06 | 12B | Apache 2.0 | Tau2 69,0 (Google) [V] | MMMLU 83,4 [V] | Q4_K_M 7,1 GB [V] | `gemma4:12b`, 7,7 GB [V] | 3 |
| Qwen3.8-27B | 05/08 | 27B denso | Apache 2.0 | solo prove d'agente (OSWorld-V 84,3) [V] | - | circa 17 GB [I] | `qwen3.8:27b`, 18 GB [V] | 3 (denso: lento senza una scheda grande) |
| Gemma 4 31B | 31/03 | 31B denso | Apache 2.0 | Tau2 76,9 [V] | MMMLU 88,4 [V] | - | `gemma4:31b`, 19-20 GB [V] | 3 (idem) |
| LFM2.5-24B-A2B | 10/2026 | 24B / 2,45B | lfm1.0 | BFCL v4 65,0 (Liquid) [V] | tra le lingue [V] | Q4_K_M 14,5 GB [V] | `lfm2.5:24b`, 15 GB; ragiona sempre [V] | 3 |
| Nemotron 3.5 Bolt E4B | 23/10 | 8B / 4B effettivi | OpenMDW-1.1 | BFCL v3 68,5, tau2 55,1 (NVIDIA) [V] | tra le lingue [V] | Q4_K_M 6,2 GB [V] | `nemotron-3.5-bolt:e4b`, 7,2 GB [V] | 3 (uscito da due giorni) |
| Nemotron 3.5 Lightning | 11/08 | 30B / 3B | OpenMDW-1.1 | BFCL v4 53,8 (Liquid) [V] | tra le lingue [V] | Q4_0 18,9 GB [V] | `nemotron-3.5-lightning:30b`, 19-25 GB [V] | 3 |
| Ministral 3 8B / 14B | 12/2025 | densi | Apache 2.0 | nessuna misura pubblicata [V] | tra le lingue [V] | 14B Q4_K_M 8,2 GB [V] | `ministral-3:14b`, 9,1 GB; non ragiona [V] | 3 |
| Qwen3.5-4B | 02-03/2026 | 4B | Apache 2.0 | BFCL v4 50,3 (Qwen) [V] | MMMLU 76,1 [V] | 2,7 GB | `qwen3.5:4b`, 3,3 GB [V] | 2: **nello studio 14 inventava** [V] |
| Granite 4.2 8B | 25/08 | 8B denso | Apache 2.0 | BFCL v4 52,4 (IBM) [V] | tra le lingue [V] | 5,4 GB [V] | `granite4.2:8b`: **senza il segno «tools»** [V] | 1 |

Esclusi: Llama 4 Scout (109B), Mistral Small 4 (119B), GLM-5.3-Flash (320B), troppo grandi; non c'è un Phi-5; nessun modello italiano del 2026 con gli strumenti (Velvet, Minerva, Italia) [V/I].

Questa tabella è la stessa di Meridiana (`assistant/local.py`, `CANDIDATES`): i voti «strumenti» e «italiano» lì sono quelli che danno l'ordine.

## 5. Quale modello per quale PC

**Come Meridiana conta la memoria** [I, una stima da confermare con le prove]:
- la memoria per un modello è quella della scheda NVIDIA più la RAM meno quello che tengono Windows e i programmi aperti: un quarto della RAM, almeno 6 GB. Sui Mac con chip Apple, il 70 % della memoria unica;
- un modello occupa il suo file più un decimo (i buffer di calcolo) e un gigabyte per 16.384 token di contesto (i modelli ibridi di oggi hanno una cache piccola).

| PC | Memoria per un modello | Modello consigliato con Ollama | Perché |
|---|---|---|---|
| 32 GB e una scheda da 8 GB (**Daniel**) | circa 32 GB | `qwen3.6:35b-a3b` (24 GB, ne serve circa 27) | provato con Meridio; a esperti, quindi veloce anche con una parte in RAM |
| 32 GB senza scheda dedicata (il portatile «lucciola» con Ollama) | circa 24 GB | `gemma4:26b-a4b-it-qat` (16 GB) | Qwen3.6 da 24 GB non entra; con llama.cpp invece entra la versione IQ4_XS da 17,7 GB, quella dello studio 14 |
| 16 GB | circa 10 GB | `qwen3.5:9b` (6,6 GB) | il più forte con gli strumenti a questa taglia, da provare con Meridio |
| 8 GB | circa 2 GB | `qwen3.5:4b` (3,3 GB), con l'avviso | inventa: meglio Claude per le domande vere |
| 64 GB e oltre | circa 50 GB | `qwen3.6:35b-a3b` in una quantizzazione più alta (Q6_K, Q8_0) [I] | lo stesso modello, più preciso |

Sul PC di Daniel Ollama metterebbe circa 7 GB del modello sulla scheda e il resto in RAM [I]. La velocità non è misurata: il modello è a esperti con 3 miliardi di parametri attivi, e il portatile dello studio 14 scriveva 9,5 token al secondo; qui con la scheda NVIDIA mi aspetto di più, da provare [I].

## 6. Le strade semplici, confrontate

| Strada | Pro | Contro | Voto |
|---|---|---|---|
| **A. Ollama, con la guida di Meridiana** (fatta) | installatore senza amministratore; resta acceso; un comando per il modello; Meridiana sistema contesto e ragionamento da sé | file più grandi di quelli scelti a mano (24 contro 17,7 GB); meno controllo della memoria sui portatili con la GPU integrata (studio 14, 4.2); un difetto aperto con le chiamate di Qwen3.6 (sezione 8) | **5** |
| **B. llama.cpp con un comando** (la scelta dello studio 14, sempre possibile) | il motore provato; la porta 9931 è già quella di Meridiana; `-hf` scarica il modello da solo; controllo fine della memoria | va avviato a ogni sessione, con un comando da ricordare | 4 |
| **C. LM Studio** | finestra comoda per provare modelli a mano | chiuso, non si può includere; il contesto va impostato al caricamento | 3 |
| **D. Meridiana che scarica e avvia da sé llama-server** (non fatta) | zero configurazione: un pulsante «Scarica il modello» come per la voce Kokoro | 30-80 MB di motore per sistema e scheda (CUDA, Vulkan, CPU) da tenere aggiornati; 18-24 GB di modello; Meridiana deve gestire un processo pesante | 4 |
| E. Docker Model Runner, Foundry Local | ci sono su alcuni PC | di nicchia; Foundry cambia porta a ogni avvio | 2 |
| F. Solo Claude | niente da installare | costa, e il progetto esce dal PC (con il consenso) | 3 |

**Raccomandazione**: A adesso (è fatta), con B per chi preferisce llama.cpp. D è il passo successivo se Daniel vuole che Meridio funzioni senza aprire un terminale: lo decide lui (sezione 9).

## 7. Che cosa fa Meridiana (25/10/2026) [V nei test]

- `assistant/local.py`:
  - `running`: le porte provate tutte insieme con una connessione di 0,3 s (su Windows una porta chiusa impiega 2 s a rifiutare); poi chi risponde è riconosciuto;
  - `installed`: i programmi e i modelli sul disco (le cartelle di Ollama, LM Studio, i GGUF della cache di Hugging Face per llama.cpp, Jan);
  - `machine`, `choose`, `suggested`, `guide`, `check`.
- `assistant/providers.py`, `Ollama`: l'API propria di Ollama, con il contesto e il ragionamento a ogni richiesta; un errore 500 prima della prima parola è richiesto una volta (ollama#16383); «il modello non sa usare gli strumenti» detto in parole.
- **Preferenze > Assistente > Modelli locali su questo PC** (`ui/assistant_local.py`): che cosa gira e che cosa è solo installato, i modelli con il consigliato e il perché, «Usa questo», «Cerca di nuovo», «Prova»; senza niente, i passi con i comandi da copiare e il pulsante per la pagina di Ollama. La ricerca gira sul pool: la finestra delle Preferenze si apre subito.
- **Nella chat**: se il modello locale non risponde, Meridio lo dice e cerca da sé; se trova un altro modello, una scheda lo propone («Usalo e rifai la domanda»); se trova un programma installato e spento, dice come avviarlo; se non trova niente, una scheda porta alla guida.
- Impostazioni versione 20: `assistant_local_runtime` («» per i server compatibili con OpenAI, «ollama»).

## 8. Rischi e trappole

- **Qwen3.6 su Ollama**: ollama#16383 (aperto dal 01/06, visto fino alla 0.40.7) [V]: quando il modello scrive male l'XML di una chiamata, Ollama risponde 500. Meridiana richiede una volta; se ricapita, l'errore è detto.
- **Qwen3.6 su llama.cpp**: llama.cpp#30118 (aperto il 07/10) [V]: nella build b11382 il 9 % delle chiamate finisce nel testo invece che come chiamata. La prova «Prova» lo scoprirebbe solo se capita in quel momento.
- **Ollama, chiamate tagliate**: ollama#17562 (aperto) [V]: una chiamata tagliata dal limite di token torna come intera; una chiamata di Gemma 4 senza la graffa finale si perde. Meridiana controlla gli argomenti prima di eseguire qualsiasi strumento (`tools.py`): una chiamata guasta torna al modello come errore.
- **gpt-oss**: il ragionamento non si spegne; Meridiana lo tiene a «low» [V].
- **I punteggi** della sezione 4 vengono da chi ha fatto il modello: la batteria di 30 domande dello studio 14 (sezione 5.4) deciderà davvero, sul PC di Daniel.

## 9. Domande per Daniel

1. **Ollama come strada consigliata** al posto di llama.cpp per chi non vuole terminale, tenendo llama.cpp come alternativa? Raccomandazione: sì.
2. **Il passo D** (Meridiana che scarica llama-server e il modello e li avvia da sé, come la voce Kokoro)? Raccomandazione: sì, ma dopo la prova vera di Qwen3.6 su questo PC, per sapere quale build (CUDA o Vulkan) e quali parametri servono.
3. **La prova vera sul tuo PC**: installare Ollama e `qwen3.6:35b-a3b` (24 GB sul disco) lo fai tu quando vuoi; io non installo niente sul tuo PC. Poi la batteria di domande dello studio 14.

## 10. Fonti

Lette il 25/10/2026 (tra parentesi la data della pagina, dove c'è). Raccolte da una ricerca sul web fatta per questo studio.

**Ollama**
- Versioni: https://github.com/ollama/ollama/releases (v0.40.11, 24/10/2026); `capabilities` dalla v0.6.4: https://github.com/ollama/ollama/releases/tag/v0.6.4
- Contesto: https://docs.ollama.com/context-length ; FAQ: https://docs.ollama.com/faq.md
- API compatibile con OpenAI: https://docs.ollama.com/api/openai-compatibility
- API propria: https://docs.ollama.com/api/chat.md , https://docs.ollama.com/api-reference/show-model-details.md , https://docs.ollama.com/api/tags.md , https://docs.ollama.com/api/ps.md
- Ragionamento e strumenti: https://docs.ollama.com/capabilities/thinking , https://docs.ollama.com/capabilities/tool-calling.md
- Windows e Linux: https://docs.ollama.com/windows.md , https://docs.ollama.com/linux.md , https://docs.ollama.com/gpu.md , https://ollama.com/download/windows
- winget: https://github.com/microsoft/winget-pkgs/tree/master/manifests/o/Ollama/Ollama
- Libreria dei modelli: https://ollama.com/library/qwen3.6/tags , https://ollama.com/library/qwen3.5/tags , https://ollama.com/library/qwen3.8/tags , https://ollama.com/library/gemma4/tags , https://ollama.com/library/gpt-oss/tags , https://ollama.com/library/ministral-3/tags , https://ollama.com/library/nemotron-3.5-lightning , https://ollama.com/library/nemotron-3.5-bolt , https://ollama.com/library/lfm2.5/tags , https://ollama.com/library/granite4.2
- Difetti: https://github.com/ollama/ollama/issues/16383 , https://github.com/ollama/ollama/issues/17562 , https://github.com/ollama/ollama/issues/17427 , https://github.com/openclaw/openclaw/issues/4028

**llama.cpp**
- Server: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md ; capacità del modello: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/common/jinja/caps.h
- Versione 0.7.0 (15/10/2026), porta 9931: https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0
- Installazione: https://raw.githubusercontent.com/ggml-org/llama.cpp/master/docs/install.md ; winget: https://github.com/microsoft/winget-pkgs/tree/master/manifests/g/ggml/llamacpp
- Difetti: https://github.com/ggml-org/llama.cpp/issues/24807 , https://github.com/ggml-org/llama.cpp/issues/30118
- Cartella dei download di `-hf` (fonte secondaria, 17/04/2026): https://knightli.com/2026/04/17/llama-cli-hf-download-default-cache-path/

**LM Studio**
- https://lmstudio.ai/docs/developer/rest , https://lmstudio.ai/docs/developer/rest/list , https://lmstudio.ai/docs/developer/rest/chat , https://lmstudio.ai/docs/developer/core/authentication , https://lmstudio.ai/docs/cli , https://lmstudio.ai/changelog/lmstudio-v0.4.8
- Termini (23/08/2026): https://lmstudio.ai/app-terms

**Altri programmi**
- Jan: https://docs.jan.ai/desktop/api-server , https://docs.jan.ai/desktop/data-folder , https://api.github.com/repos/janhq/jan/releases/latest (20/10/2026)
- Docker Model Runner: https://docs.docker.com/ai/model-runner/api-reference/
- Foundry Local (19/10/2026): https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-local/reference/reference-cli
- Lemonade: https://lemonade-server.ai/docs/guide/configuration/ , https://lemonade-server.ai/docs/api/openai/ , https://lemonade-server.ai/docs/api/ollama/
- LocalAI: https://api.github.com/repos/mudler/LocalAI/releases/latest (23/10/2026); KoboldCpp: https://github.com/LostRuins/koboldcpp ; GPT4All: https://api.github.com/repos/nomic-ai/gpt4all/releases/latest (25/02/2025)

**Modelli**
- https://huggingface.co/Qwen/Qwen3.6-35B-A3B , https://huggingface.co/Qwen/Qwen3.5-9B , https://huggingface.co/Qwen/Qwen3.8-27B , https://huggingface.co/openai/gpt-oss-20b , https://ai.google.dev/gemma/docs/core/model_card_4 (30/07/2026) , https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512 , https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16 , https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-BF16 , https://huggingface.co/LiquidAI/LFM2.5-24B-A2B , https://huggingface.co/ibm-granite/granite-4.2-8b
- File GGUF: https://huggingface.co/api/models/unsloth/Qwen3.6-35B-A3B-GGUF/tree/main , https://huggingface.co/api/models/unsloth/gemma-4-26B-A4B-it-GGUF/tree/main , https://huggingface.co/api/models/unsloth/Qwen3.5-9B-GGUF/tree/main , https://huggingface.co/api/models/ggml-org/gpt-oss-20b-GGUF/tree/main
- Classifiche: https://gorilla.cs.berkeley.edu/leaderboard.html (12/04/2026) ; https://euroeval.com/leaderboards/Monolingual/italian (non leggibile) ; https://github.com/EuroEval/leaderboards (archiviato il 20/05/2026)
