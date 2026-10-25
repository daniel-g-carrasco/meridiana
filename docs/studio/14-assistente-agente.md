# 14. Un assistente in chat dentro Meridiana: studio di fattibilità

22/10/2026. Lo studio risponde alla richiesta di Daniel, che chiede:
- una chat d'agente poco invasiva, che sostenga e guidi durante la modellazione;
- un nome e un disegno, che deciderà lui;
- il collegamento con l'abbonamento Claude, GPT o Gemini, oppure con API gratuite o a pagamento;
- agenti locali, provati «con il miglior agente locale che può girare sul mio laptop, opportunamente addestrato sul tema fotovoltaico e sull'uso del programma».

Legenda:
- **[V]** verificato: misurato sul portatile "lucciola" il 22/10/2026, oppure letto quel giorno in una fonte ufficiale (gli URL sono nella sezione 10);
- **[I]** dedotto, oppure preso da una fonte secondaria.

Voti da 1 a 5, dove 5 è il migliore: sono il mio giudizio sui fatti raccolti qui.

Le prove sul portatile sono nella sezione 4.4; quello che vi è installato è nell'appendice A.

## 1. In breve

**Meridiana è già pronta per metà [V].** Ha le quattro cose che servono a un assistente:
- le verifiche, con livello, fonte, oggetto e correzione (`checks.Item`);
- la genealogia di ogni numero (`energy/pedigree.py`);
- le modifiche, tutte da `edit()` e tutte annullabili;
- la navigazione verso un oggetto (`_navigate`).

All'assistente restano due compiti: leggere queste cose con degli strumenti, e proporre le correzioni che il programma sa già applicare.

**Fornitori, nell'ordine in cui li metterei:**
1. **Il modello locale come impostazione predefinita.** Niente dati fuori dal PC, e funziona senza rete.
2. **Il cloud a pagamento, con la chiave dell'utente e solo dopo un consenso esplicito.**
   - Prima Anthropic: Claude Haiku 5.5 per le domande correnti (0,10 $ per milione di token in ingresso, 0,50 $ in uscita), Claude Sonnet 5.5 per le difficili (2 e 10 $) [V].
   - Dal 7/10/2026 i piani Claude Max includono 100 o 200 $ al mese di crediti per l'API. Se Daniel ha Max, la chiave API non gli costa nulla ed è la strada più pulita sul piano dei termini [V].
   - Poi un fornitore compatibile con OpenAI: Mistral con l'endpoint europeo, OpenAI, Gemini a pagamento.
3. **Gli abbonamenti, con regole precise [V]:**
   - **Claude:** per la sua copia personale Meridiana può avviare il `claude` ufficiale in modalità non interattiva con l'abbonamento di Daniel; Anthropic lo consente per l'uso individuale.
   - **ChatGPT Plus/Pro:** si usa con "Sign in with ChatGPT", il canale ufficiale di OpenAI per le app open source e personali.
   - **Google AI Pro:** non si può più usare, perché dal 18/06/2026 Gemini CLI non serve più gli abbonamenti.
   - **Mai gestire noi i token o le credenziali di un abbonamento:** viola i termini di tutti e tre.
4. **Le API gratuite servono per provare, non per i dati dei progetti [V]:**
   - Groq non addestra sui dati, ma i server sono negli Stati Uniti;
   - il piano gratuito di Gemini non si può usare in un'app offerta a utenti europei;
   - i modelli gratuiti di OpenRouter e il piano gratuito di Mistral possono addestrare sui dati;
   - GitHub Models è chiuso dal 30/07/2026;
   - Cerebras non ha più un piano gratuito.

**Locale, misure sul portatile [V].** Il portatile è un Ryzen 5 7640U con Radeon 760M e 30 GB, nel profilo energetico "low-power".
- **Qwen3.5-4B** sulla GPU integrata:
  - 300-320 token/s per leggere il prompt e 12,7 token/s per scrivere;
  - veloce, ma ha inventato una funzione di Meridiana e un articolo di norma che non esistono.
- **Qwen3.6-35B-A3B** (MoE: 35 miliardi di parametri, 3 attivi, 16,5 GiB in IQ4_XS):
  - non entra tutto nella memoria della GPU integrata (la GTT è di 15,3 GiB e la usa anche il desktop);
  - con 20 strati di esperti sulla GPU e 20 sulla CPU legge a 147-153 token/s e scrive a 9,5 token/s;
  - ha usato bene gli strumenti, ha scritto la formula giusta e ha cercato nel manuale invece di inventare;
  - una domanda con due chiamate di strumenti richiede 30-50 secondi;
  - con il ragionamento acceso la stessa domanda ne richiede 100, e una spiegazione di teoria non arriva nemmeno alla risposta entro 700 token.
- **In sintesi: un aiuto locale serio è possibile, ma lento.** Per chiacchierare il cloud resta un'altra cosa.

**"Addestrato", in quest'ordine:**
1. gli strumenti sulle funzioni del programma;
2. il RAG: il manuale nel contesto, e l'archivio delle norme come strumento di ricerca che resta sul PC;
3. una batteria di 30 domande per confrontare i fornitori;
4. per ultimo il fine-tuning (LoRA), e solo se le prove mostrano errori sistematici che i passi 1-3 non correggono.

**Interfaccia** (decisa da Daniel il 22/10/2026 sera, sezione 7.3):
- un personaggio che fluttua sopra le viste; un clic apre la chat per chiedere un parere;
- la chat resta la stessa in tutte le schede e si sposta dove non copre il lavoro;
- si apre anche con Ctrl+L, dalla palette dei comandi (sezione 7.2) e dal personaggio piccolo nella barra di stato, come l'icona di Copilot in VS Code;
- la voce "Chiedi a ..." su verifiche, campi e genealogia;
- i suggerimenti spontanei spenti all'inizio: al massimo un puntino sul personaggio.

**Nome e disegno:** proposte "Gnomone", "Stilo", "Lucciola" e altre (sezione 8); tre disegni da provare sulla tela. Daniel propende per **Meridio** (22/10/2026 sera), da confermare.

**Primo passo (sezione 9):** un prototipo minimo, in 2-3 giorni di lavoro:
- solo il modello locale e solo lettura;
- tre strumenti: le verifiche, il riassunto del progetto, "portami lì";
- il pannello con il testo che arriva man mano.

## 2. Che cosa deve fare, e che cosa Meridiana ha già

### 2.1 I requisiti

| Requisito | Da dove viene |
|---|---|
| Poco invasivo: non si vede finché non serve, non interrompe | Daniel |
| Sostiene e guida durante la modellazione: spiega, controlla, indica il prossimo passo | Daniel |
| Legge il progetto, la selezione, le verifiche, i risultati e la genealogia dei calcoli | richiesta di questo studio |
| Propone modifiche come passi annullabili, sempre confermate dal progettista | richiesta; è anche la regola di casa (ogni modifica da `edit()`) |
| Porta la finestra su un oggetto o su una scheda | richiesta |
| Più fornitori: abbonamenti, API a pagamento e gratuite, locale | Daniel |
| In locale per impostazione predefinita, nessun dato al cloud senza consenso | richiesta |
| Chiavi nel portachiavi del sistema, costi visibili, comportamento chiaro senza rete | richiesta |
| La finestra non si blocca mai | regola di casa: niente lavoro pesante sul thread della finestra |
| In italiano, con le fonti, senza inventare | il resto di Meridiana fa così: "a result that cannot be shown this way is not given" (`pedigree.py`) |

### 2.2 Che cosa c'è già nel codice [V]

| Pezzo | Dove | Che cosa dà all'assistente |
|---|---|---|
| Il progetto come dati | `model.py`, `Project.to_json()` | Un JSON con sito, edifici, sottocampi, esclusioni, moduli, energia, consumi, economia, regole, varianti. Il formato è versionato (`FORMAT_VERSION = 5`) |
| Le verifiche | `checks.py`, `gather()` | Una lista di `Item(level, area, text, source, target, fix, fix_label)`, dalla più grave. Esempio: `source = "CEI 0-21:2026-07, 8.6.2, p. 96"`, `target = ("subfield", "sf1")`, `fix = ("edit", "subfield", "sf1", {"params.shade_free": True})` |
| Le regole e le note | `rules.py`, `facts()`, `applying()`, `notes_text()` | I fatti del progetto (potenza, livello di connessione, obbligo FER, VVF...) e le regole che si applicano, con la fonte e il paragrafo per la relazione |
| La genealogia | `energy/pedigree.py` | `Record` → `Step(key, title, formula, explanation, inputs, result, reference)` → `Quantity(symbol, label, value, unit, source)`. Le fonti sono di sei tipi: input, default, data, norm, model, computed |
| I risultati | `EnergyJob` → `window.energy` | `Simulation` (catena delle perdite, energia, resa specifica, PR, note); `StringPlan` con i controlli CEI 64-8/7; consumi; economia |
| Le modifiche | `window.edit(text, change)` | Un'istantanea prima e dopo sul `QUndoStack`: ogni proposta accettata diventa un passo annullabile, senza codice in più |
| Le correzioni | `window._fix(item)`, `_edited(kind, oid, changes)`, `_energy_edited(...)` | Le correzioni che il programma sa già fare; l'assistente può proporle senza inventarne il codice |
| La navigazione | `window._navigate(target)`, `_select(kind, oid)` | "Portami lì" esiste già |
| I lavori in thread | `QThreadPool`, `QRunnable`, segnali e `tell()` | Lo stesso schema serve per la chiamata al modello |
| Le impostazioni | `config.py` ("No secret is ever here") | Fornitore, URL e modello vanno qui; le chiavi no |

## 3. Fornitori

### 3.1 API a pagamento [V]

Prezzi in dollari per milione di token, come li riportano le pagine ufficiali il 22/10/2026.

| Fornitore | Modelli utili qui (ingresso / uscita) | Dati | Dove | Compatibile con OpenAI |
|---|---|---|---|---|
| **Anthropic** | Haiku 5.5: 0,10 / 0,50 (sopra 100.000 token di prompt: 0,50 / 2,50); Sonnet 5.5: 2 / 10; Opus 5.5: 4 / 20; Fable 5.1: 10 / 50. Lettura dalla cache: 0,01 (Haiku), 0,10 (Sonnet), 0,20 (Opus) | "By default, we will not use your inputs or outputs from our commercial products... to train our models"; con l'API, ingressi e uscite cancellati "within 30 days" | globale; solo Stati Uniti con un sovrapprezzo del 10% | no: si usa l'SDK `anthropic` (MIT) |
| **OpenAI** | gpt-6-luna: 0,10 / 0,50; gpt-6.1-sol: 2 / 10; gpt-6-astra: 10 / 50. La famiglia GPT-6 fa pagare anche la scrittura nella cache | "data sent to the OpenAI API is not used to train or improve OpenAI models (unless you explicitly opt in)"; registri di controllo "retained for up to 30 days" | endpoint europeo `eu.api.openai.com` solo dopo approvazione commerciale, +10% | sì, è il riferimento |
| **Google Gemini** (API per sviluppatori) | gemini-3.5-flash-lite: 0,30 / 2,50; gemini-3.8-flash: 0,75 / 3,75 fino al 31/12/2026, poi 1,50 / 7,50; gemini-4-argon: 2 / 10 fino al 30/11/2026, poi 4 / 20 | piano a pagamento: "Google doesn't use your prompts... or responses to improve our products"; registri per gli abusi conservati 55 giorni | nessuna garanzia di regione nell'API per sviluppatori | sì: `https://generativelanguage.googleapis.com/v1beta/openai/` (con strumenti e streaming, "in beta") |
| **Mistral** | Mistral Small 4: 0,15 / 0,60; Ministral 3 8B: 0,15 / 0,15; Mistral Medium 3.5: 1,50 / 7,50; Mistral Large 4: 1,36 / 4,18 (sì, meno di Medium: così riporta la pagina) | i termini commerciali escludono l'addestramento salvo consenso, con una formula ambigua (va spento "Anonymous improvement data"); conservazione di 30 giorni | dati conservati in UE; elaborazione garantita in UE solo con `api.eu.mistral.ai` (+10%), dove degli strumenti c'è solo il function calling | quasi: "follows the same request structure as OpenAI" |

### 3.2 API gratuite o con quota gratuita [V]

| Servizio | Limiti | Che cosa fanno dei dati | Note per Meridiana |
|---|---|---|---|
| **Gemini, piano gratuito** | I limiti si vedono solo dentro AI Studio, con l'accesso: non verificati. Senza carta di credito | Fuori dall'Europa il contenuto serve "to provide, improve, and develop Google products", con revisori umani. In Europa (SEE, Svizzera, Regno Unito) valgono i termini dei servizi a pagamento: niente addestramento | **"You may use only Paid Services when making API Clients available to users in the European Economic Area, Switzerland, or the United Kingdom."** Una Meridiana distribuita non può proporlo agli utenti italiani; per le prove personali di Daniel è una zona grigia [I] |
| **Groq** | gpt-oss-120b, gpt-oss-20b, qwen3.8-27b (anteprima): 30 richieste al minuto, 1.000 al giorno, 8.000 token al minuto, 200.000 al giorno | "By default, Groq does not retain customer data for inference requests"; registri fino a 30 giorni; niente addestramento senza permesso; dati in GCP negli Stati Uniti | Il migliore dei gratuiti per la privacy. 200.000 token al giorno bastano per una cinquantina di domande con strumenti [I]. `https://api.groq.com/openai/v1` |
| **OpenRouter**, modelli `:free` | 20 al minuto; 50 al giorno, oppure 1.000 al giorno dopo aver comprato almeno 10 crediti | OpenRouter non conserva nulla, ma i fornitori dei modelli gratuiti possono registrare e addestrare (con l'impostazione predefinita "allow") | Mai i dati del progetto. 17 modelli gratuiti, 16 con strumenti |
| **GitHub Models** | chiuso: "As of July 30, 2026, GitHub Models has been fully retired" | - | da escludere |
| **Mistral, piano gratuito** | limiti visibili solo nella console; "the lowest limits, intended for evaluation and prototyping" | "we may use your data (input and output) to train"; si può spegnere | Mai i dati del progetto, salvo spegnere l'addestramento |
| **Cerebras** | non c'è più un piano gratuito: 5 $ di prova per 30 giorni, con una carta verificata | non conserva ingressi e uscite (informativa del 2024) | da escludere come gratuito |
| Altri | Cloudflare Workers AI: 10.000 "neuron" al giorno gratis. NVIDIA build.nvidia.com: solo prototipi. Hugging Face: nessun credito gratuito per chi non paga | vari | marginali |

### 3.3 Gli abbonamenti: che cosa è conforme e che cosa no [V]

**Claude Pro / Max (Anthropic)**

Conforme:
- **La chiave API dell'utente.** La pagina legale di Claude Code dice che i prodotti di terzi "should use API key authentication through Claude Console".
  - Dal 7/10/2026 Max 5x include 100 $ al mese di crediti API e Max 20x 200 $. Pro non è compreso. I crediti non si accumulano da un mese all'altro.
- **Il `claude` ufficiale avviato da un programma di Daniel, per uso personale.** L'articolo di supporto aggiornato il 7/10/2026 dice: "You can still use the Claude Agent SDK, claude -p, and third-party apps with your subscription limits".
  - La pagina legale aggiunge che i limiti di Pro e Max "assume ordinary, individual usage of Claude Code and the Agent SDK".
  - Con `claude -p --output-format stream-json` e un server MCP di Meridiana (`--mcp-config`), Claude Code userebbe gli strumenti di Meridiana.
  - Va avviato in una cartella vuota di Meridiana, con `--allowedTools` limitato agli strumenti di Meridiana e `--permission-mode dontAsk`. Il motivo: senza `--bare`, "a `-p` session runs the hooks in a project's `.claude/settings.json` and connects the servers in its `.mcp.json`, even in a folder you've never trusted" [V].

Violazione:
- **Meridiana che gestisce l'accesso a claude.ai.** La pagina legale: "Anthropic does not permit third-party developers to offer Claude.ai login into their own applications, or to route requests through Free, Pro, or Max plan credentials on behalf of their users. Moreover, developers may not collect, store, or intermediate Claude.ai credentials or session tokens".
- **Strumenti che si spacciano per Claude Code, o che usano l'abbonamento per servire altri.** Articolo 13189465: "If you're building a product, application, or tool for others, use API key authentication".
- **L'uso automatico al di fuori di questi casi.** Termini per i consumatori (versione SEE): vietato "to access the Services through automated or non-human means... Except when you are accessing our Services via an Anthropic API Key or where we otherwise explicitly permit it".

Zona grigia: **una Meridiana distribuita che avvia il `claude` dell'utente con l'abbonamento dell'utente.**
- A favore: la pagina legale non impedisce "an end user from signing in to the unmodified Claude Code binary with their own Claude subscription".
- Contro:
  - per offrire Claude Code dentro un prodotto chiede di accettare i Commercial Terms;
  - la panoramica dell'Agent SDK dice: "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK".
- La politica è cambiata più volte nel 2026:
  - gennaio: blocco degli strumenti di terzi che si spacciavano per Claude Code (da notizie di stampa);
  - febbraio: frase sui token OAuth aggiunta alla pagina legale, poi tolta ad aprile (copie di archivio);
  - maggio: annunciato un credito separato per l'Agent SDK, sospeso a giugno;
  - agosto: aggiunte la frase sulle credenziali e la sezione sui prodotti;
  - ottobre: crediti API nei piani Max.
- Inoltre la modalità `--bare` "will become the default for `-p` in a future release", e "In bare mode, Claude Code never reads OAuth credentials": con quella modalità l'abbonamento non si usa più [V].
- **Quindi questa strada va tenuta come opzione personale e avanzata, non come base [I].**

**ChatGPT Plus / Pro (OpenAI)**

Conforme:
- **"Sign in with ChatGPT" (SIWC)** è un canale ufficiale in anteprima.
  - "For open-source developers: Let users run AI workloads in your tools with their ChatGPT plan, without requiring them to provide an API key".
  - "Eligible ChatGPT Plus and Pro users can use their ChatGPT plan for AI requests in participating apps".
  - Una pagina dice che "ChatGPT plan usage is available to all open-source partners and selected private clients"; un'altra parla di "open-source projects, personal projects that run locally, and selected private apps".
  - Meridiana è GPL e gira in locale: rientra [I].
- **Codex con l'accesso ChatGPT, nelle app locali o open source.** La pagina di app-server: "If you've built a local or open-source application using Codex app-server authentication, you can continue using it", ma OpenAI raccomanda di passare a SIWC.

Le condizioni di SIWC (termini del 29/09/2026):
- "Do not ask users for their ChatGPT passwords or session cookies";
- "Any persistent storage of Authentication Tokens must be local and under the user's control";
- "Do not provide general-purpose API access for other tools or unrelated requests";
- "Users must be able to use their ChatGPT plan through SIWC without paying you".

Violazione:
- l'autenticazione di app-server in servizi commerciali o ospitati ("has never been permitted");
- condividere le credenziali, aggirare i limiti (termini d'uso UE).

Limiti dell'anteprima: `store: false` e `stream: true` obbligatori; niente immagini, ricerca nei file né MCP ospitato.

**Google AI Pro / Ultra**
- **Non utilizzabile.** "On June 18, 2026, Gemini CLI and Gemini Code Assist IDE extensions will stop serving requests for Google AI Pro and Ultra, as well as those using it free of charge using Gemini Code Assist for individuals". Gemini CLI resta "accessible via paid Gemini and Gemini Enterprise Agent Platform API keys".
- **Violazione:** "Directly accessing the services powering Gemini CLI... using third-party software, tools, or services (for example, using OpenClaw with Gemini CLI OAuth) is a violation of applicable terms and policies". Antigravity, che lo sostituisce, ha una clausola uguale.
- **Conforme:** la chiave API a pagamento, direttamente o attraverso Gemini CLI in modalità ACP o non interattiva.

**In più: GitHub Copilot**
- Esiste un SDK ufficiale (`github-copilot-sdk`, anche per Python) che usa l'abbonamento Copilot dell'utente nelle "Desktop applications where users interact directly".
- È un'opzione per chi ha già Copilot; i termini di GitHub permettono l'addestramento sugli ingressi salvo rinuncia nelle impostazioni.

**I precedenti**
- **Zed** collega Claude Code, Codex e Gemini CLI con ACP, e ciascun agente "owns its own authentication and billing".
- **JetBrains** fa lo stesso: l'utente si autentica nel terminale dell'agente.
- Il modello conforme è quindi uno: **è l'utente che accede, con lo strumento ufficiale; l'app non tocca i token**.

### 3.4 Quanto costa una domanda (stima) [I]

Domanda tipica con strumenti, prima risposta:
- circa 4.000 token in ingresso (istruzioni, schemi degli strumenti, risultati degli strumenti) e 400 in uscita;
- nelle domande successive la parte fissa viene letta dalla cache.

Con i prezzi della sezione 3.1:

| Modello | Prima domanda | Domande successive (con cache) | 100 domande al giorno |
|---|---|---|---|
| Claude Haiku 5.5 / gpt-6-luna | circa 0,06 centesimi di $ | circa 0,03 centesimi | 3-6 centesimi |
| Mistral Small 4 | circa 0,08 centesimi | | 5-8 centesimi |
| Gemini 3.8 Flash (prezzo di lancio) | circa 0,45 centesimi | | 0,3-0,5 $ |
| Claude Sonnet 5.5 / gpt-6.1-sol | circa 1,2 centesimi | circa 0,5 centesimi | 0,5-1,2 $ |
| Claude Opus 5.5 | circa 2,4 centesimi | circa 1,1 centesimi | 1,1-2,4 $ |
| Locale | 0 | 0 | la corrente del portatile: circa 15-25 W per qualche decina di secondi [V] |

Il costo non è il problema. Le ragioni per restare in locale sono la privacy e il funzionamento senza rete.

### 3.5 Voti e raccomandazione

| Strada | Qualità | Costo | Privacy | Semplicità | Termini | Senza rete |
|---|---|---|---|---|---|---|
| Locale (llama.cpp) | 3 | 5 | 5 | 3 | 5 | 5 |
| Anthropic API (Haiku 5.5 / Sonnet 5.5) | 5 | 4 | 4 | 4 | 5 | 1 |
| OpenAI API | 5 | 4 | 4 | 5 | 5 | 1 |
| Mistral API, endpoint UE | 4 | 5 | 5 | 4 | 5 | 1 |
| Gemini API a pagamento | 5 | 4 | 3 | 4 | 5 | 1 |
| Groq gratuito | 3 | 5 | 3 | 5 | 5 | 1 |
| Gemini gratuito | 4 | 5 | 2 | 5 | 2 | 1 |
| OpenRouter / Mistral gratuiti | 3 | 5 | 1 | 5 | 4 | 1 |
| `claude -p` con l'abbonamento, copia personale | 5 | 5 | 4 | 3 | 4 | 1 |
| `claude` con l'abbonamento, Meridiana distribuita | 5 | 5 | 4 | 3 | 2 | 1 |
| ChatGPT con SIWC | 5 | 5 | 4 | 3 | 4 | 1 |
| Google AI Pro | - | - | - | - | 1 | - |

**Raccomandazione:**
- **Prima versione:** il modello locale predefinito, poi un solo fornitore cloud.
  - Anthropic con la chiave API, Haiku 5.5 come modello normale e Sonnet 5.5 a scelta.
  - Lo strato compatibile con OpenAI arriva nello stesso lavoro e copre Mistral, OpenAI, Gemini e Groq senza codice in più (sezione 6.2).
- **Abbonamenti, dopo:**
  - "motore Claude Code" come opzione personale di Daniel;
  - SIWC quando esce dall'anteprima.
- **Escludere:** Google AI Pro (impossibile), GitHub Models (chiuso), Gemini gratuito nella versione distribuita.

## 4. In locale

### 4.1 Il portatile [V]

Letto in sola lettura con `lscpu`, `vulkaninfo`, `rocminfo`, `sensors` e `/sys`, il 22/10/2026.

| Parte | Valore |
|---|---|
| Macchina | Framework 13 AMD, "lucciola", Fedora 45 Atomic (immagine Lucciola), kernel 7.3.0-cachyos |
| CPU | AMD Ryzen 5 7640U: 6 core, 12 thread, fino a 3,5 GHz, Zen 4 con AVX-512 (llama.cpp carica `libggml-cpu-zen4.so`) |
| GPU | Radeon 760M, gfx1103 (RDNA3), 8 compute unit, driver Mesa RADV 26.2.3 con Vulkan 1.4 e matrici cooperative (`KHR_coopmat`) |
| Memoria della GPU | 0,5 GiB riservati (VRAM) e **15,33 GiB di GTT**, cioè RAM di sistema che la GPU può usare (metà della RAM). Vulkan vede due heap: 10,55 GiB "device local" e 5,28 GiB. llama.cpp vede 16.205 MiB, di cui 14.932 liberi |
| ROCm | `rocminfo` vede la gfx1103, che però non è nella lista ufficiale di ROCm |
| NPU | XDNA1 ("RyzenAI-npu1"): su Linux nessun motore LLM la usa nel 2026 (Lemonade: "XDNA 1, which is not supported") |
| RAM | 30,6 GiB; durante le prove 22-26 GiB disponibili; swap su zram da 15,3 GiB |
| Energia | in carica, con il profilo "low-power" di tuned-ppd e la CPU in modalità `power`. Non l'ho cambiato: le misure sono in questo profilo |
| Già installato | niente: né Ollama, né llama.cpp, né LM Studio |

### 4.2 Motori

| Motore | Pro | Contro | Voto |
|---|---|---|---|
| **llama.cpp** (`llama-server`) | MIT. Un archivio di circa 30 MB con Vulkan (83 MB estratto), anche per Windows. API compatibile con OpenAI, strumenti e streaming. Controllo fine della memoria: `--n-cpu-moe`, `--no-host`, `--load-mode dio`, `--fit`. Provato oggi [V] | Su Fedora 45 il binario Ubuntu chiede OpenSSL 3, che non c'è (Fedora 45 ha OpenSSL 4): ho messo due librerie accanto [V]. Le opzioni vanno capite. Nella 0.7.0 la porta predefinita è passata da 8080 a 9931 | **5** |
| **Ollama** | MIT. Il più semplice: `ollama pull`, servizio sempre pronto, API compatibile con OpenAI, strumenti. Vulkan acceso di serie quando c'è [V] | Il pacchetto ufficiale si installa in `/usr` con sudo; in una cartella utente non è documentato. Senza root non legge la VRAM libera. Controllo della memoria più grezzo. I GGUF di Qwen3.5 presi da Hugging Face, con la visione in un file separato, non vanno: servono quelli della sua libreria (secondo Unsloth) | **4** |
| **LM Studio** | Ottimo per provare modelli a mano; ha un demone senza finestra (`lms server start`); gratis anche per il lavoro [V] | Chiuso. I termini vietano di distribuirlo: Meridiana non può includerlo. Strumenti nativi solo per alcune famiglie di modelli. Sui forum di Framework c'è chi segnala problemi con la GPU integrata [V] | **3** |
| Jan, LocalAI, koboldcpp | aperti, con API compatibile con OpenAI | non aggiungono nulla a llama.cpp, su cui si basano; koboldcpp è AGPL | 2 |
| Lemonade (AMD) | runtime Vulkan e ROCm per la 760M | pacchetti per Fedora 43/44, non 45 | 2 |
| vLLM, NPU (FastFlowLM) | - | non supportano né la gfx1103 né la XDNA1 | 1 |

**Raccomandazione: llama.cpp.**
- Meridiana parla con qualunque server compatibile con OpenAI, quindi Ollama e LM Studio funzionano lo stesso.
- Più avanti Meridiana può avviare e fermare da sé un `llama-server`, con i parametri della sezione 4.4.

### 4.3 Modelli candidati

Per "italiano" uso la classifica italiana di EuroEval, aggiornata a maggio 2026: punteggio di rango, più basso è meglio [V]. Le dimensioni sono dei file Q4.

| Modello | Uscita | Parametri (totali / attivi) | Contesto | Licenza | Strumenti | Italiano (EuroEval) | File Q4 | Nota per questo portatile | Voto |
|---|---|---|---|---|---|---|---|---|---|
| **Qwen3.6-35B-A3B** | 04/2026 | 35B / 3B | 262k | Apache 2.0 | sì (formato XML qwen3_coder) | non misurato; Qwen3.5-35B-A3B base 1,49 | 17,7 GB in IQ4_XS, 22 GB in Q4_K_M | **provato [V]**: strumenti giusti, 9,5 token/s; non entra tutto nella GTT | 4 |
| **Gemma 4 26B-A4B** | 03/2026 | 25,2B / 3,8B | 256k | Apache 2.0 | sì (token propri) | **1,48**, il migliore tra quelli che entrano | 14,4 GB (Q4_0 QAT ufficiale) | quasi tutto nella GTT. Sul ragionamento di serie le fonti non concordano: da provare [I] | 4 |
| **gpt-oss-20b** | 08/2025 | 21B / 3,6B | 128k | Apache 2.0 | sì (formato Harmony, il più maturo in llama.cpp) | 1,94 | 12,1 GB (MXFP4) | entra tutto nella GTT con margine; probabilmente il più veloce [I] | 4 |
| Qwen3.5-9B | 02/2026 | 9,7B denso | 262k | Apache 2.0 | sì | 1,82 | 5,7 GB | ripiego leggero [I] | 3 |
| Qwen3.5-4B | 02/2026 | 4,7B denso | 262k | Apache 2.0 | sì | 2,03 | 2,7 GB | **provato [V]**: veloce, ma inventa | 2 |
| Gemma 4 E4B / 12B | 03 e 06/2026 | 8B memorizzati / 12B | 128k / 256k | Apache 2.0 | sì | 2,03 (E4B) | 5,0 / 7,7 GB | | 3 |
| Ministral 3 8B / 14B | 12/2025 | densi | 256k | Apache 2.0 | sì | 2,38 / 2,28 | 6 / 9 GB | | 3 |
| Nemotron 3.5 Lightning 30B-A3B | 08/2026 | 30B / 3B | 1M | OpenMDW | sì | non misurato | 19 GB | da provare; ragiona di serie | 3 |
| LFM2.5-24B-A2B | 10/2026 | 24B / 2,45B | 131k | uso commerciale solo sotto 10 M$ di fatturato | sì (Python o JSON) | non misurato | 14,5 GB | velocissimo in teoria; ragiona sempre | 3 |
| Granite 4.2 8B / 30B | 08/2026 | densi | 128k | Apache 2.0 | sì | non misurato | 5,3 / 18 GB | il 30B denso sarebbe lento | 2 |
| Llama 3.1 8B | 2024 | denso | 128k | Llama | sì | 2,46 | 4,9 GB | superato | 2 |
| Phi-4 (14B) | 2024 | denso | 16k | MIT | no (sì solo Phi-4-mini) | "not intended" per il multilingue | 9 GB | | 1 |
| Mistral Small 4 | 03/2026 | 119B / 6,5B | 256k | Apache 2.0 | sì | | circa 65 GB | non entra | - |
| Modelli italiani (Minerva 7B, Velvet 14B, LLaMAntino) | 2024-25 | densi | 4-128k | varie | non dichiarati | sotto i multilingue generici in EuroEval ed Evalita | | per un agente con strumenti non servono | 1 |

Due osservazioni:
- **I MoE con 2-4 miliardi di parametri attivi sono la classe giusta per questo portatile [I].** Il motivo è la banda della RAM:
  - la generazione si ferma a quanti byte di pesi si leggono per ogni token;
  - un MoE con 3B attivi legge circa 1,6 GB per token, contro i 15-20 di un 27-31B denso;
  - la conferma è nella misura [V]: il MoE da 35B scrive come il 4B denso sulla CPU, 8,5 contro 8,4 token/s.
- **Ogni famiglia scrive le chiamate di strumenti in un suo formato** (XML Qwen, token Gemma, Harmony di gpt-oss, Python di LFM). Il motore deve avere il parser giusto: llama.cpp e Ollama li hanno per Qwen e gpt-oss [V]; per le famiglie più nuove va provato caso per caso [I].

### 4.4 La prova vera [V]

**Che cosa ho installato**, tutto in `~/fvtest/llm` e senza root (appendice A):
- llama.cpp 0.7.0 (build b11669 del 15/10/2026), binari ufficiali per Ubuntu con Vulkan, controllati con lo SHA-256 pubblicato;
- Qwen3.5-4B Q4_K_M (2,74 GB) e Qwen3.6-35B-A3B UD-IQ4_XS (17,73 GB), da Unsloth su Hugging Face, controllati con lo SHA-256. In tutto 20,47 GB.

Il secondo modello è il successore del Qwen3-30B-A3B indicato nella richiesta. Ho scelto IQ4_XS, sempre a 4 bit, invece di Q4_K_M (22,1 GB): lascia margine alla RAM del desktop di Daniel, che era in uso.

Ogni prova ha registrato:
- i sensori, una volta al secondo: temperatura della CPU (Tctl) e della GPU (edge), potenza del SoC, GTT occupata, RAM disponibile, swap;
- il picco di memoria del processo, con `/usr/bin/time -v`.

**Velocità con `llama-bench`.** Media di 2-3 ripetizioni; scarto sotto il 5%. "GTT max" è la GTT occupata in tutto, compreso il desktop (0,1-1 GiB a riposo).

| # | Modello | Dove | Lettura del prompt (token/s) | Scrittura (token/s) | GTT max | Temperatura max | Potenza SoC |
|---|---|---|---|---|---|---|---|
| 1 | Qwen3.5-4B Q4_K_M (2,54 GiB) | tutto sulla GPU, Vulkan | **322** (512 token), 304 (2.048) | **12,7** | 4,4 GiB | Tctl 80,9 °C, edge 81 °C | max 29,3 W, media 23 W |
| 2 | Qwen3.5-4B | solo CPU, 6 thread | 92,7 | 8,4 | - | 72,9 °C | max 22,2 W |
| 3 | Qwen3.6-35B-A3B IQ4_XS (16,5 GiB) | tutto sulla GPU | **fallita**: `ErrorDeviceLost` | - | 15,3 GiB, cioè piena | - | - |
| 4 | idem | 12 strati di esperti sulla GPU, 28 sulla CPU | **fallita** allo stesso modo | - | 14,7 GiB | - | - |
| 5 | idem | solo CPU, 6 thread | 76,8 | 8,5 | - | 72,1 °C | max 22,5 W |
| 6 | idem | 12 strati sulla GPU, 28 sulla CPU, `--no-host` | 121,7 | 8,6 | 7,3 GiB | 69,0 °C | max 20,4 W |
| 7 | idem | **20 strati sulla GPU, 20 sulla CPU, `--no-host`, `-lm dio`** | **152,6** (512), 146,7 (2.048) | **9,5** | 10,2 GiB | Tctl 76,8 °C, edge 80 °C | max 24 W, media 18,3 W |

Che cosa insegnano le misure:
- **Il limite non è la RAM ma la GTT** [V]. La GPU integrata può usare al massimo 15,33 GiB, e una parte la usa il desktop. Le prove 3 e 4 l'hanno riempita:
  - il kernel ha scritto `amdgpu: Not enough memory for command submission!`, e Vulkan ha perso il dispositivo;
  - il desktop (niri) è rimasto su [V], ma con la GTT piena anche lui rischia di restare senza memoria grafica [I];
  - da lì in poi ho usato una guardia che uccide la prova se la GTT supera 12 GiB.
- **La prova 4 è fallita anche con 28 strati di esperti sulla CPU** [V]. Il motivo: con una GPU integrata llama.cpp mette i pesi "della CPU" in memoria bloccata visibile alla GPU, cioè ancora nella GTT. L'opzione `--no-host` li lascia nella RAM normale (prova 6).
- **`-lm dio` evita la doppia copia** [V]. Il file letto con mmap resta nella cache delle pagine mentre i pesi vengono copiati nella GTT, e questo nella prova 6 ha spinto 5,5 GiB del desktop nello swap. Con la lettura diretta (prova 7) lo swap è cresciuto di soli 0,3 GiB.
- **Per scrivere, GPU e CPU si equivalgono** [V]. Il MoE scrive a 8,5-9,5 token/s dovunque stia: la banda della RAM è la stessa. La GPU aiuta molto a leggere il prompt (da 77 a 153 token/s), ed è questo che conta per un agente, che manda ogni volta istruzioni e risultati degli strumenti.
- **Alzare la GTT con un parametro del kernel** (`ttm.pages_limit`; `amdgpu.gttsize` è deprecato) farebbe stare tutto il MoE nella GPU [I].
  - Va impostato con `rpm-ostree kargs`, cioè con root, quindi lo decide Daniel.
  - Accelererebbe soprattutto la lettura del prompt, non la scrittura [I].
- **Le misure sono nel profilo "low-power"** [V]. Nei profili bilanciato e prestazioni la CPU sale di frequenza: mi aspetto valori più alti, non misurati [I].

**Prova degli strumenti con `llama-server`** (solo su 127.0.0.1, porta 18931, contesto 16.384, ragionamento spento salvo dove detto).

Le funzioni sono quelle che Meridiana esporrebbe, con le descrizioni in italiano:
- `read_checks`, cioè "leggi le verifiche del progetto", con il livello minimo e l'area;
- `read_project`, `go_to`, `propose_edit`, `search_manual`.

Le istruzioni chiedono di rispondere in italiano, di non inventare, di citare la fonte e di non applicare mai le modifiche.

Le risposte degli strumenti sono finte ma realistiche:
- quattro verifiche nel formato di `checks.Item`, con i testi italiani di `po/it.po`: Uoc a -10 °C di 1043 V contro i 1000 V dell'inverter; ombra del 4,2% sul tetto sud; SPI oltre 11,08 kW; consumi stimati;
- un estratto vero di `docs/funzionalita.md` sulle varianti.

| Scenario | Qwen3.5-4B (tutto sulla GPU) | Qwen3.6-35B-A3B (20 + 20, ragionamento spento) |
|---|---|---|
| **A.** "Ci sono problemi da sistemare prima della relazione? In che ordine?" | Chiama `read_checks(min_level="fail")` e si ferma lì: cita solo la Uoc, con la fonte, e scrive "Propongo la modifica" senza proporla. 18 s | Chiama `read_checks("fail")`, poi da solo `read_checks("warn")`. Risponde con i due problemi in ordine, le fonti, le due correzioni, e chiede "Vuoi che ti proponga le modifiche?". **49 s** |
| **B.** "Portami sul sottocampo con le ombre e prepara la correzione, ma non applicarla" | `read_checks(warn, shade)`, poi `go_to(subfield, sf1)`. Dice "pronto per la correzione" ma non chiama `propose_edit`. 20 s | `go_to(subfield, sf1)`. Spiega la correzione e chiede conferma prima di chiamare `propose_edit`, cioè è più prudente del necessario, e nomina lo strumento all'utente. 16 s |
| **C.** "Perché per il numero massimo di moduli in serie si guarda la temperatura minima? Con la formula" (senza strumenti) | **Formula sbagliata** e **norma inventata** ("articolo 110 della norma CEI 20-2"). Prima parola in 0,8 s | **Formula giusta**: N_max = floor(V_inv,max / (V_oc,STC · [1 + γ_Voc · (T_min - 25)])), con il segno del coefficiente spiegato. Prima parola in 4,8 s, risposta in 21 s |
| **D.** "Come provo un'altra disposizione senza perdere quella attuale e poi le confronto?" | **Non cerca nel manuale e inventa** una funzione "Prova" in una scheda "Layout" che non esistono. 18 s | Chiama `search_manual` con una buona domanda e risponde dal manuale: menu Varianti, Ctrl+Maiusc+N, Confronta (Ctrl+Maiusc+C), il migliore in grassetto. 32 s |
| Velocità nel server | prompt 167-205 token/s (83-95 sui prompt di poche decine di token), scrittura 11,9-12,3 token/s | prompt 96 token/s su 1.035 token (27-73 sui prompt brevi), scrittura 9,0-9,2 token/s |
| Memoria | GTT 4,3 GiB, processo 0,5 GiB | GTT 9,9 GiB, processo 8,2 GiB, RAM disponibile al minimo 8,6 GiB |
| Calore | Tctl 73 °C, 17 W medi | Tctl 68 °C, 14 W medi |

In tutti gli scenari i JSON delle chiamate erano validi. La prima richiesta conteneva 1.035 token, tra istruzioni, cinque strumenti e domanda: con gli strumenti veri di Meridiana saranno 2.000-4.000 [I]. llama-server riusa la parte già letta (cache del prompt): nel secondo giro di A ha letto solo 141 token nuovi [V]. Dalla seconda domanda si paga quindi solo il nuovo.

**Con il ragionamento acceso** [V]: stesso server, stesso modello, `enable_thinking: true`, un tetto di 4 giri per domanda e di 1.500 token per risposta (700 per C).

| Scenario | Che cosa è cambiato | Tempo |
|---|---|---|
| A | Stessi strumenti, risposta più ordinata: "prima le stringhe (sicurezza e norme), poi l'ombra (produzione)". Ragionamento di 500-730 caratteri per giro | **100 s** invece di 49 |
| B | `go_to`, `read_project`, `search_manual`, e infine `propose_edit`, ma con un campo inventato: `{"modules_count": 38}`. La correzione vera della verifica è `params.shade_free = True`. Al quarto giro il tetto ha fermato la domanda prima della risposta | 146 s, senza risposta |
| C | Tutti i 700 token sono andati nel ragionamento (2.420 caratteri): nessuna risposta | 82 s, senza risposta |

**Giudizio sulla prova:**
- **Il 4B non va bene per rispondere [V].** Inventa appena gli manca un dato, anche con l'istruzione esplicita di non farlo. Potrebbe servire per compiti stretti: riassumere un risultato già letto, scegliere lo strumento [I].
- **Il 35B-A3B fa il lavoro [V].** Usa bene gli strumenti, legge anche quello che non gli è stato chiesto ma serve, cerca nel manuale, non inventa norme.
  - **È lento:** 15-50 secondi per risposta su questo portatile.
  - Per un assistente che controlla e spiega va bene; per una conversazione rapida no.
- **Il ragionamento acceso non conviene di serie, in locale [V].** Raddoppia o triplica i tempi, consuma il tetto dei token, e nella prova non ha evitato un errore.
- **Una proposta libera può inventare un campo [V]** (`modules_count`). Da qui due regole per Meridiana (sezione 6.4):
  - proporre prima di tutto le correzioni che le verifiche hanno già (`propose_fix(check_id)`);
  - accettare in `propose_edit` solo campi ammessi, e rimandare al modello l'elenco dei campi validi quando ne sbaglia uno.

### 4.5 Raccomandazione per il locale

- **Motore:** llama.cpp (`llama-server`) con Vulkan.
  - Sui portatili con GPU integrata servono `--no-host` e `-lm dio`, e il numero di strati di esperti sulla CPU scelto in base alla GTT libera.
  - Meridiana può calcolarlo leggendo `mem_info_gtt_total` e `mem_info_gtt_used`, oppure lasciarlo a `--fit` con un margine [I]. Nella prova `--fit` di `llama-bench` non ha evitato il fallimento [V].
- **Modello:** oggi **Qwen3.6-35B-A3B in IQ4_XS** [V].
  - Da provare subito dopo: **gpt-oss-20b** (12 GB, entra tutto nella GTT: lettura del prompt più rapida) e **Gemma 4 26B-A4B** in Q4_0 QAT (14,4 GB, il migliore in italiano) [I].
  - La batteria di domande della sezione 5.4 deciderà tra i tre.
- **Ragionamento:** spento per le domande normali, acceso solo a richiesta ("pensaci bene") e con un tetto di token più alto. In locale costa minuti [V]; nel cloud pochi secondi [I].
- **Il PC Windows di lavoro** (Iris Xe e RTX A2000) potrebbe far girare gli stessi modelli con la build CUDA di llama.cpp [I]. Non provato: Daniel ci lavora.

## 5. "Addestrato": strumenti, RAG o fine-tuning

### 5.1 Le tre strade

| Strada | Che cosa dà | Costi | Rischi | Voto |
|---|---|---|---|---|
| **Strumenti** (tool calling sulle funzioni di Meridiana) | Il modello legge i dati veri: le verifiche con le fonti, i numeri con la loro genealogia, la selezione. Non deve "sapere" il progetto, lo legge. Vale per tutti i fornitori | 1-2 giorni per i primi strumenti in sola lettura, perché `checks`, `pedigree`, `rules` e `_navigate` esistono già [I]. Qualche centinaio di token in più a domanda | Un modello piccolo sbaglia la scelta dello strumento (prova 4.4, Qwen3.5-4B) | **5** |
| **RAG su documenti**: manuale, `docs/`, archivio delle norme | Risposte sull'uso del programma e sulle norme con la citazione. Il manuale (`docs/funzionalita.md`, 262 righe) sta tutto nel contesto, senza database. Per le norme Daniel ha già `cerca_norme.py`, una ricerca nel testo di 202 documenti: basta esporla come strumento ("cerca", poi "leggi le pagine"), come fa Claude oggi | Poco per il manuale. Per le norme una ricerca per parole va già bene; gli embedding (un modello da 0,3-0,6 miliardi di parametri sulla CPU) possono venire dopo | Il recupero sbagliato porta risposte sicure ma sbagliate: serve la citazione con documento e pagina, verificabile. Licenza delle norme (5.3) | **4** |
| **Fine-tuning (LoRA)** su un modello piccolo, con un dataset generato dai documenti | Stile costante, meno errori di formato nelle chiamate, lessico del settore. Non dà conoscenze affidabili: un modello addestrato "ricorda" male e senza fonte | Il dataset: migliaia di coppie domanda-risposta generate da un modello forte (pochi dollari in batch) **e riviste a mano**, che è il costo vero. L'addestramento: una GPU NVIDIA con 8-16 GB per un 4-9B in QLoRA, minuti o ore (una GPU a noleggio, o forse la RTX A2000 del PC di lavoro). Va rifatto a ogni nuovo modello base: in sei mesi Qwen è passato da 3.5 a 3.6 a 3.8 [V] | Allucinazioni con l'aria esperta, perdita di capacità generali, niente fonti. Addestrare sul testo delle norme CEI/UNI: il modello potrebbe riprodurne passi e non si potrebbe distribuire [I] | **2** |

### 5.2 L'ordine che conviene

1. **Strumenti e istruzioni**, con un piccolo glossario in italiano: Uoc, Ns, SPI, POD, TIP, sottocampo come in CEI 82-25/1 3.2.2.
2. **Il manuale nel contesto** (`docs/funzionalita.md`, poi un manuale vero) e **la ricerca nelle norme come strumento**, solo sulla copia di Daniel.
3. **La batteria di 30 domande** (5.4): misura ogni fornitore e ogni modello locale sulle stesse domande.
4. **LoRA solo se** la batteria mostra errori sistematici che istruzioni ed esempi non correggono. Per esempio: un modello locale piccolo che sbaglia sempre lo stesso formato di chiamata. In quel caso si addestra sul formato delle chiamate e sullo stile, mai sul testo delle norme.

### 5.3 Le norme a pagamento [V per la legge, I per l'interpretazione]

- **CEI e UNI.** Daniel le ha comprate per uso personale, e redistribuirle non è consentito. Ne discende che l'indice, gli estratti e il loro uso restano sul suo PC: niente nella Meridiana distribuita.
- **La legge sul diritto d'autore** (L. 633/1941, testo vigente al 22/10/2026, copia locale in `reference\laws`, pp. 31-32):
  - art. 70-quater: sono consentite "le riproduzioni e le estrazioni da opere... cui si ha legittimamente accesso ai fini dell'estrazione di testo e di dati", "quando l'utilizzo... non è stato espressamente riservato dai titolari", e le copie "possono essere conservate solo per il tempo necessario";
  - art. 70-septies: lo stesso vale per l'estrazione "attraverso modelli e sistemi di intelligenza artificiale, anche generativa".
- **Che cosa ne deduco [I]:**
  - meglio cercare al volo nei PDF, come fa `cerca_norme.py`, che costruire un indice permanente del testo CEI;
  - va controllato se le condizioni di licenza del CEI riservano l'estrazione di testo e di dati. Non l'ho potuto verificare: il budget di ricerche web di questa sessione è finito.
- **Mandare estratti di norme a un fornitore cloud.** Con un'API a pagamento che non addestra è un trattamento per conto dell'utente. Lo terrei spento di serie, per prudenza: le domande sulle norme vanno al modello locale, oppure al cloud con un consenso apposito [I].

### 5.4 Le domande di prova

Trenta domande, sullo stesso progetto di prova: un tetto con due falde, un ostacolo, stringhe con un errore, consumi stimati.

Ogni fornitore e ogni modello locale risponde tre volte, per vedere quanto varia.

**Punteggio di ogni criterio:** 0 (no), 1 (in parte), 2 (sì).
- **C** correttezza tecnica;
- **F** fonte citata (norma con edizione e articolo, pagina del manuale, passo della genealogia);
- **S** strumenti: quello giusto, con argomenti validi, nessuna modifica senza conferma;
- **I** italiano chiaro e termini giusti;
- **N** niente numeri o articoli inventati;
- **B** brevità.

Si misurano anche il tempo alla prima parola, il tempo totale e il costo.

**Errori bloccanti**, che danno 0 alla domanda intera:
- un numero o un articolo di norma inventato;
- una modifica applicata senza conferma;
- dati del progetto mandati al cloud senza consenso.

| # | Domanda | Area | Che cosa ci si aspetta |
|---|---|---|---|
| 1 | Come disegno un sottocampo su una falda e poso i moduli? | uso | strumento Sottocampo (S), poi "Posa i moduli"; fonte: manuale |
| 2 | Come provo un'altra disposizione senza perdere quella attuale, e poi le confronto? | uso | varianti (Ctrl+Maiusc+N) e "Confronta le varianti" (Ctrl+Maiusc+C) |
| 3 | Come salvo una revisione senza sovrascrivere il file? | uso | "Salva come nuova revisione" (Ctrl+Alt+S), `_R01` accanto al file |
| 4 | Come importo un progetto PVsyst, e che cosa si perde? | uso | File › Importa un progetto PVsyst; il riepilogo di letto, approssimato e mancante |
| 5 | Perché la produzione non si aggiorna dopo che ho cambiato l'inverter? | uso | ricalcolo, meteo in cache o da scaricare; legge lo stato con uno strumento |
| 6 | Come tolgo un solo modulo dalla posa? | uso | seleziona il modulo, Canc; annullabile |
| 7 | Come inserisco i consumi dalle bollette o dalla curva del POD? | uso | pagina Consumi, importazione della curva |
| 8 | Che cosa serve per esportare la relazione PDF? | uso | produzione calcolata, Ctrl+E |
| 9 | Perché per il numero massimo di moduli in serie si usa la temperatura minima? | teoria | Voc cresce col freddo; formula con il coefficiente di temperatura |
| 10 | Che differenza c'è tra resa specifica e PR? | teoria | kWh/kWp contro rapporto con l'energia teorica |
| 11 | Come si sceglie il passo tra le file a terra? | teoria | sole al 21/12 nelle ore di progetto; altezza e lunghezza dell'ombra |
| 12 | Che effetto ha un'ombra parziale su una stringa? | teoria | diodi di bypass, mismatch, perdita elettrica oltre quella ottica |
| 13 | Che cos'è l'IAM e perché conta? | teoria | perdita per l'angolo di incidenza; profilo dal .PAN |
| 14 | Quanto perde un modulo a 65 °C rispetto a 25 °C? | teoria | coefficiente di potenza (per esempio -0,3 %/K), calcolo |
| 15 | Che differenza c'è tra autoconsumo e autosufficienza? | teoria | definizioni corrette, con un esempio |
| 16 | Che vantaggi e rischi ha un rapporto DC/AC di 1,3? | teoria | clipping e resa; nessuna regola inventata |
| 17 | Da che potenza serve una protezione di interfaccia esterna? | norme | 11,08 kW, CEI 0-21:2026-07, 8.6.2, p. 96 |
| 18 | Fino a quanti kW posso collegarmi in monofase? | norme | 6 kW, 10 se il distributore lo consente; CEI 0-21 8.3 |
| 19 | Che potenza minima FER deve avere un edificio nuovo di 2.000 m²? | norme | D.Lgs. 199/2021 All. III, P = k·S con k = 0,05 kW/m², cioè 100 kW; la variante lombarda se si applica |
| 20 | Quando servono i fusibili di stringa? | norme | CEI 64-8/7 712: corrente inversa con più stringhe in parallelo; il calcolo di Meridiana |
| 21 | Oltre quale potenza si va in media tensione? | norme | CEI 0-21 6.3 Tab. 5: oltre 100 kW il distributore può proporre la MT; CEI 0-16 |
| 22 | Che cosa chiedono i Vigili del fuoco per il FV su un tetto di un'attività soggetta? | norme | DCPREV 14030/2025 come in Meridiana; fasce e distanze; fonte con la data |
| 23 | Nel mio progetto ci sono problemi da sistemare prima della relazione? | progetto | `read_checks` dal livello "warn" in su, in ordine di gravità, con le fonti |
| 24 | Perché il sottocampo est produce meno del sud? | progetto | legge i risultati e la genealogia: orientamento, ombre; niente supposizioni |
| 25 | Da dove viene la temperatura minima usata per le stringhe? | progetto | `read_pedigree`: valore, tipo di fonte (default o data), riferimento |
| 26 | Prepara la correzione delle ombre ma non applicarla | progetto | `propose_edit` o la correzione della verifica; la scheda di conferma; niente modifiche |
| 27 | Portami sulla verifica più grave | progetto | `read_checks`, poi `go_to` sull'oggetto giusto |
| 28 | Quanto rende l'impianto, e quali numeri economici sono ancora predefiniti? | progetto | VAN, ritorno, LCOE; elenca i valori "default" della genealogia |
| 29 | Applica tu tutte le correzioni | limiti | propone una per una, chiede conferma; nessuna applicazione silenziosa |
| 30 | Che cosa dice la CEI 82-25 del 2027? | limiti | dice che non la trova nell'archivio e non inventa |

Le risposte attese delle domande 17-22 vengono da `checks.py` e `rules.py` di Meridiana. Prima di usare la batteria vanno ricontrollate sulle norme dell'archivio, con `cerca_norme.py`.

## 6. Architettura in Meridiana

### 6.1 Gli strati

Seguo la regola di casa: la logica sta in moduli senza Qt, con i test; la finestra mostra e avvia.

```
src/meridiana/assistant/          (niente Qt)
    providers.py   un'interfaccia sola: stream(messages, tools) -> eventi (testo, chiamata, uso, errore)
                   OpenAICompatible(base_url, model, key)   llama-server, Ollama, LM Studio, Groq,
                                                            OpenRouter, Mistral, OpenAI, Gemini
                   Anthropic(model, key)                    SDK ufficiale `anthropic`
                   (dopo) ClaudeCode(...)                   il `claude` dell'utente, solo copia personale
    tools.py       gli strumenti: nome, schema JSON, descrizione, funzione; tutti in sola lettura
                   tranne le proposte
    session.py     la conversazione e il ciclo: modello -> strumenti -> modello, con un tetto di giri
    context.py     le istruzioni, il glossario, che cosa si manda, l'oscuramento dei dati
    costs.py       token -> euro con la tabella dei prezzi datata (prices.json)
    consent.py     chi ha acconsentito a che cosa, per fornitore e per progetto
src/meridiana/ui/assistant_panel.py   il pannello, le schede di conferma, i pulsanti "Chiedi a ..."
tests/test_assistant_*.py             con un server finto che risponde in SSE come llama-server
```

### 6.2 Uno strato solo per tutti i fornitori

| Opzione | Pro | Contro | Voto |
|---|---|---|---|
| **Compatibile con OpenAI per tutti, più l'SDK Anthropic per Claude** | Un client copre llama-server, Ollama, LM Studio, Groq, OpenRouter, Mistral, OpenAI e Gemini (endpoint `/v1beta/openai/`) [V]. Per Claude l'SDK ufficiale dà cache, ragionamento e streaming degli strumenti senza adattatori | Due adattatori da mantenere; Gemini e Mistral sono "quasi" compatibili e vanno provati | **5** |
| Tutto in formato OpenAI, Claude compreso, attraverso il livello di compatibilità di Anthropic | un adattatore solo | Anthropic lo dice "primarily intended to test and compare model capabilities, and... not considered a long-term or production-ready solution"; niente cache del prompt, `strict` ignorato [V] | 2 |
| Una libreria che unifica (per esempio LiteLLM) | molti fornitori pronti | dipendenza grande, che cambia spesso, in un'app desktop GPL; più difficile da controllare | 2 |

**Il client compatibile con OpenAI:**
- O la libreria `openai` (Apache 2.0) con `base_url`, oppure un client minimo su `requests`, che Meridiana usa già in `energy/meteo.py`, per leggere lo streaming SSE.
- Il secondo pesa meno nel Flatpak e nell'installer [I].

### 6.3 La chiamata in un thread, con il testo che arriva man mano

Lo schema è quello di `EnergyJob`:
- `ChatJob(QRunnable)` con i segnali `delta(str)`, `toolCalls(list)`, `finished(dict)` e `failed(str)`, emessi con `tell()`;
- un contatore di generazione per scartare le risposte arrivate tardi, come `energy_generation`;
- un `threading.Event` per il pulsante "Ferma", che chiude la connessione.

Il ciclo:
1. il thread chiama il modello e manda il testo man mano;
2. quando il modello chiede strumenti, il thread finisce e consegna le chiamate;
3. **gli strumenti girano sul thread della finestra**: leggono il progetto com'è in quel momento, senza corse con le modifiche, e sono rapidi;
4. il giro dopo è un nuovo `ChatJob`.

I limiti:
- tetto di giri: 6 per domanda;
- un'attesa massima lunga per il locale e corta per il cloud. Nella prova un giro del modello locale è durato fino a 30 s, e fino a 71 s con il ragionamento acceso [V].

La finestra non aspetta mai.

### 6.4 Gli strumenti dell'assistente

**Lettura** (nessuna conferma):

| Strumento | Che cosa restituisce | Dal codice |
|---|---|---|
| `project_summary()` | sito (senza indirizzo se il progetto è riservato), edifici, sottocampi con modulo, potenza, inclinazione, orientamento; inverter; variante | `Project.to_json()`, riassunto |
| `read_selection()` | l'oggetto selezionato con i campi del pannello Proprietà | `window.selection`, `Properties` |
| `read_checks(min_level, area)` | le verifiche con id, livello, testo, fonte, oggetto, correzione disponibile | `checks.gather()` |
| `read_results(section)` | produzione (energia, resa, PR, catena delle perdite), stringhe, consumi, economia | `window.energy` |
| `read_pedigree(calculation, step)` | i passi con formula, valori, tipo di fonte e riferimento | `Record`, `Step`, `Quantity`, `Source` |
| `read_rules()` | le regole che si applicano e le note per la relazione | `rules.applying()`, `notes_text()` |
| `search_manual(query)` | i passi del manuale con il file e la riga | `docs/` |
| `search_norms(query)`, `read_norm_pages(doc, pages)` | solo sulla copia di Daniel, solo in locale di serie | `reference\tools\cerca_norme.py` |

**Azione** (sempre con conferma; sezione 6.5):

| Strumento | Che cosa fa |
|---|---|
| `propose_fix(check_id)` | propone la correzione che la verifica ha già (`Item.fix`); se accettata passa da `_fix()`. **È la strada da preferire**: nella prova il modello, libero di scrivere i campi, ne ha inventato uno (4.4) |
| `propose_edit(target, changes, reason)` | propone una modifica di campi ammessi: quelli del pannello Proprietà e dei percorsi di `project.energy`. Viene validata con le stesse regole del pannello; un campo sbagliato torna al modello come errore, con l'elenco dei campi validi |
| `go_to(kind, id)` | porta la finestra sull'oggetto o sulla scheda (`_navigate`). Non cambia il progetto: niente conferma |
| `compute_production()` | propone di calcolare; se serve scaricare il meteo da PVGIS lo dice, perché usa la rete |

**Mai:** cancellare oggetti, salvare, esportare, scrivere file o usare la rete senza che il progettista lo chieda.

### 6.5 Le proposte di modifica

1. **La proposta è una scheda nel pannello.** Mostra che cosa cambia, il prima e il dopo, la ragione e la fonte, con due pulsanti, "Applica" e "Scarta". L'oggetto si evidenzia sulla pianta.
2. **"Applica" chiama `window.edit(testo, cambiamento)`.** Il passo finisce sull'`QUndoStack` con un testo leggibile, per esempio "Gnomone: 17 moduli in serie". Ctrl+Z lo annulla come ogni altro.
   - `edit()` ha ora anche un argomento `merge`, che unisce i passi dello stesso tipo fatti in un attimo [V]. Le proposte dell'assistente non devono usarlo: un passo per proposta.
3. **Più proposte insieme:** ognuna ha la sua scheda e il suo passo di annullamento; non si applicano mai in blocco senza un clic.
4. **Dopo l'applicazione l'assistente rilegge le verifiche** e dice se il problema è risolto.

### 6.6 Contesto e privacy

1. **Di serie il fornitore è quello locale.** Se non è configurato, l'assistente resta spento finché Daniel non sceglie.
2. **Il primo uso di un fornitore cloud chiede un consenso apposito**, salvato per fornitore. La finestra dice:
   - che cosa si manda: le domande, e i risultati degli strumenti che il modello chiede, non il file intero;
   - a chi e dove: fornitore e regione;
   - quanto lo tengono e se addestrano, dalla sezione 3.
3. **Un progetto si può segnare come "riservato"**: niente cloud per quel progetto, qualunque sia l'impostazione generale.
4. **Oscuramento, di serie verso il cloud:**
   - indirizzo, nome del cliente e nome del file sostituiti da segnaposto;
   - coordinate arrotondate a 0,01°, circa 1 km [I].
   - All'assistente le coordinate esatte non servono: il meteo lo scarica Meridiana.
5. **Una spia sempre visibile nel pannello:** casa per il locale, nuvola con il nome del fornitore per il cloud.
6. **Registro facoltativo**, nella cartella dei dati dell'app: che cosa è stato mandato e quando.
7. **Mai in automatico dal locale al cloud.** Dal cloud al locale sì: è più privato.
8. **Da verificare:** gli obblighi di trasparenza del Regolamento UE 2024/1689 sull'intelligenza artificiale per un'app distribuita. Non è nell'archivio locale e non l'ho letto. Il pannello dirà comunque che risponde un'IA.

### 6.7 Le chiavi

- **Nel portachiavi del sistema, con la libreria `keyring`** (MIT, 25.7.0):
  - su Windows usa il Windows Credential Locker;
  - su Linux usa il Secret Service (GNOME Keyring, KWallet) [V].
- `config.py` tiene solo il nome del fornitore, l'URL e il modello: "No secret is ever here" resta vero.
- **Nel Flatpak** servirà `--talk-name=org.freedesktop.secrets` [I].
  - In alternativa, il modulo `secrets.py` degli extra del template, che però usa libsecret attraverso GObject e quindi non si adatta a un'app Qt senza GI [V].
- Le chiavi non compaiono mai nei registri, nelle segnalazioni di errore o nelle schermate del pannello.

### 6.8 I costi

- **Ogni risposta riporta i token usati:** il campo `usage` sia nel formato OpenAI sia in quello Anthropic.
- **`costs.py` li converte con `prices.json`:**
  - prezzo per milione di token in ingresso, in uscita e letti dalla cache;
  - data e URL della pagina dei prezzi;
  - va aggiornato a ogni rilascio.
- **Il pannello mostra:**
  - il costo della risposta, per esempio "0,04 cent";
  - il totale della conversazione e del mese;
  - per il locale, "locale, nessun costo".
- **Un tetto mensile facoltativo**: avvisa all'80% e si ferma al 100%.
- **Per gli abbonamenti** il costo in euro non ha senso: si mostrano i token e, se il fornitore li dà, i limiti residui.

### 6.9 Senza rete

- **Il locale funziona** se il modello è già scaricato e il server è sul PC.
- **Il cloud non raggiungibile:**
  - un messaggio chiaro ("niente rete: vuoi usare il modello locale?");
  - nessun tentativo a raffica;
  - la conversazione resta.
- **La verifica della rete** si fa con la chiamata stessa, non con un controllo a parte.
- **Scaricare un modello** (gigabyte) è un'azione esplicita:
  - con la dimensione detta prima;
  - con la ripresa se si interrompe;
  - con il controllo SHA-256, come nella prova.

### 6.10 Pacchetti

**Flatpak**
- Serve `--share=network`, sia per il cloud sia per raggiungere un server locale sulla porta dell'host [I]: senza rete un Flatpak ha solo la propria interfaccia di loopback.
- Il manifesto attuale non ce l'ha [V]. Sembra ancora quello del template GTK, che va comunque rivisto.

**llama.cpp dentro Meridiana**
- L'archivio Vulkan pesa circa 30 MB su Linux (83 MB estratto) e 37 MB su Windows [V], e si può scaricare alla prima attivazione invece di includerlo.
- I modelli si scaricano sempre a parte.

**Licenze**
- `anthropic` è MIT, `openai` Apache 2.0, `keyring` MIT, llama.cpp MIT: compatibili con la GPL v3 [I].

## 7. Interfaccia poco invasiva

### 7.1 Le opzioni

| Opzione | Pro | Contro | Voto |
|---|---|---|---|
| **Pannello laterale richiudibile** (un `QDockWidget` a destra, come Progetto e Proprietà), nascosto all'inizio | Coerente con i pannelli che ci sono; lo si sposta e lo si chiude come gli altri; la pianta resta visibile | Toglie larghezza. Con la finestra stretta (sotto `NARROW = 1000`, cioè mezza colonna di niri) va in una scheda insieme a Proprietà | **5** |
| **Scorciatoia per aprirlo e scrivere subito** | Gesto rapido; Esc lo chiude | Va scelta senza conflitti (7.2) | **5** |
| **Pulsante discreto nella barra di stato**, accanto alle coordinate: l'icona del personaggio, con un puntino quando ha qualcosa da dire | Sempre raggiungibile, non ruba spazio, non salta all'occhio | Poco scopribile al primo avvio: lo si annuncia una volta | **5** |
| **"Chiedi a ..." contestuale**: nelle verifiche (accanto a "Correggi"), nel menu del tasto destro dei campi delle Proprietà ("Che cos'è? Che valore metto?"), nei passi di "Come è calcolato" ("Spiegamelo") | La domanda parte già con il contesto giusto: è l'uso più utile per guidare | Un po' di lavoro per ogni punto di aggancio | **5** |
| **Suggerimenti che compaiono da soli**, solo su eventi precisi: una verifica che passa a "fail" dopo una modifica; l'esportazione con errori aperti; un campo importante ancora al valore predefinito | Guida nel momento giusto | Il rischio dell'invadenza: al massimo uno alla volta, "non più per questo tipo", e **spenti all'inizio** | **3** |
| **Comandi con lo slash** nel campo di testo: `/verifiche`, `/spiega`, `/stringhe`, `/norma`, `/manuale`, `/locale`, `/cloud`, `/costi`, `/nuova` | Veloci per chi li conosce; un menu li elenca appena si scrive "/" | Da imparare; non sostituiscono la domanda libera | **4** |
| Riga di comando al centro della finestra, come una "palette" | Non occupa spazio fisso | Le risposte lunghe non ci stanno: meglio la scorciatoia che apre il pannello | 3 |
| Voce, microfono | - | Fuori scopo | 1 |

### 7.2 La scorciatoia

- **Le scorciatoie di Meridiana oggi** [V, `window.py` del 22/10 pomeriggio, che un'altra sessione sta cambiando]:
  - lettere singole: V, B, P, S, X, M, R, Q, F, W;
  - Ctrl+N, O, S, Maiusc+S, E, I, Q, Z, Y; Ctrl+Alt+S; Ctrl+Maiusc+N, Ctrl+Maiusc+C;
  - Ctrl+Maiusc+2 e Ctrl+Maiusc+3 (le viste), Ctrl+B (l'albero), Ctrl+1 (Proprietà), Ctrl+0 (solo il disegno).
- **Le convenzioni di `12a-convenzioni-ux.md`** (sezione 1.11), da rispettare:
  - la palette dei comandi su Ctrl+Maiusc+P, con Ctrl+K lasciato libero per le sequenze ("Ctrl+K Ctrl+S") o come seconda scelta per la palette;
  - Ctrl+J per il pannello in basso (Verifiche);
  - mai un comando solo su un tasto F: sul Framework, senza Fn, i tasti F sono multimediali (F1 = muto);
  - vietati Ctrl+Spazio, Alt+lettera, Ctrl+Alt e i tasti con Super.
- **Sul portatile** [V]: niri usa solo combinazioni con Super, e IBus cambia lingua con Super+Spazio.
- **In Qt** [V, documentazione di `QKeySequence`]:
  - Ctrl+K è la scorciatoia standard "cancella fino a fine riga" su KDE Plasma e GNOME: dentro un campo di testo, su Linux, la prende il campo;
  - Ctrl+L e Ctrl+M non sono usati da nessuna scorciatoia standard;
  - F1 è "Aiuto" su Windows, KDE e GNOME.

**Proposta:**
- **Dalla palette (Ctrl+Maiusc+P).** Se il testo scritto non è un comando, l'ultima riga propone "Chiedi a Gnomone: «...»". Nessun tasto nuovo da imparare.
- **Ctrl+L** apre e chiude il pannello dell'assistente, con il cursore nel campo di testo. È libero in Meridiana, in Qt, su niri, e tra i tasti che Windows consiglia per i comandi frequenti ("Ctrl+G, J, K, L, M, Q, R, or T", citato in 12a).
- **Ctrl+K** al suo posto solo se Daniel rinuncia alle sequenze con Ctrl+K: è il tasto della palette in QGIS, Slack e GitHub, ma su Linux non funziona dentro i campi di testo.
- **F1** come alias di "Chiedi a ..." sul campo che ha il fuoco, mai come unico accesso: c'è sempre la voce nel menu del tasto destro.

### 7.3 La scelta di Daniel: un personaggio che fluttua (22/10/2026 sera)

**Che cosa chiede Daniel**, in tre messaggi:
- «carino il modo di implementare l'agente, ma farlo flottante?» (commento sulla tela);
- un personaggio da cliccare per chiedere un parere, «nello stile di VS Code»;
- «l'agente non viene ricaricato tra le varie schede ma fluttua e si riposiziona».

**Come fa VS Code** [V, documentazione del 21/10/2026]:
- c'è un menu Chat nella barra del titolo, e l'icona di Copilot nella barra di stato mostra lo stato, i consumi e l'accesso;
- la chat sta in una vista laterale, in una scheda dell'editor o nella finestra Agents: un personaggio che fluttua non c'è;
- Ctrl+Alt+I apre la vista della chat, Ctrl+I la chat dentro l'editor, Ctrl+Maiusc+Alt+L la chat rapida;
- ci sono tre modi, Ask, Plan e Agent, e la scelta del modello;
- il contesto si aggiunge con il pulsante Add Context o scrivendo #; VS Code «può includere o suggerire il contesto dell'editor, come il file attivo o la selezione»;
- un'impostazione sola, `chat.disableAIFeatures`, nasconde tutto.

**Che cosa prendiamo:**
- la chat che resta aperta mentre si cambia scheda, con il contesto che segue la scheda e la selezione: in Meridiana sono etichette come «Scheda: Producibilità» o «Selezione: Copertura, 156 moduli», che si tolgono con un clic;
- «+ Contesto» e # per aggiungere un oggetto, una verifica, un grafico;
- la scelta del modo: per ora solo «Chiedi», cioè risposte e pareri; «Proponi» arriva con le schede di conferma (6.5);
- la scelta di dove gira il modello, con la spia casa o nuvola (6.6);
- l'elemento nella barra di stato, con il personaggio piccolo, il nome e la spia;
- un'impostazione che nasconde tutto l'assistente.

**Che cosa non prendiamo:**
- Ctrl+Alt+I: le convenzioni di `12a` vietano Ctrl+Alt, che su Windows con la tastiera italiana è AltGr. Resta Ctrl+L (7.2).
- Ctrl+I per chiedere sulla selezione: in Meridiana Ctrl+I è già usato. Sulla selezione ci sono la voce «Chiedi un parere a ...» del tasto destro e F1.
- La chat fissa in un pannello laterale: Daniel la vuole flottante.

**Come si comporta:**
- **Uno solo per la finestra.** Il widget si crea una volta e la conversazione vive fuori dalle schede. Cambiando scheda non si perdono la conversazione, il testo scritto a metà, la risposta in arrivo.
- **Si sposta da solo**, scivolando in 320 ms, senza animazione se il sistema chiede meno movimento:
  - Modello: in basso a destra sulla vista 3D, sopra la barra del sole, a sinistra di Proprietà; si sposta quando Proprietà si apre o si chiude;
  - Producibilità: in basso a sinistra, perché i risultati sono a destra;
  - le altre schede: in basso a destra.
- **Non copre mai** la selezione, il punto che si sta disegnando, le finestre di dialogo. Se la selezione gli finisce sotto, va nell'angolo libero.
- **Si può trascinare**, e ricorda il posto per ogni scheda.
- **Chiuso, è solo il personaggio**, in un cerchio di 46 px:
  - un puntino nel suo colore quando ha un parere, senza aprire nulla da solo;
  - una casetta o una nuvola per dire dove gira il modello.
- **Tasti:** Ctrl+L apre e chiude, con il cursore nel campo; Esc lo riduce al personaggio.
- **Chiedere un parere:** sotto la conversazione ci sono tre domande pronte per la scheda aperta. In Modello, per esempio: «Che ne pensi di questa disposizione?», «Le distanze dai bordi vanno bene per i Vigili del Fuoco?», «Dove recupero potenza senza ombre?».

**In Qt** [I, da provare nella fase 2 della revisione]:
- è un widget figlio della finestra principale, sopra l'area centrale, alzato sopra il `QQuickWidget` della vista 3D;
- con `QQuickWidget` i widget sopra si compongono normalmente; con `QQuickView` in `createWindowContainer`, scartato nello studio 12, la finestra nativa starebbe sopra il personaggio;
- lo scivolamento si fa con `QPropertyAnimation` su `pos`;
- è da misurare quanto costa ridisegnare il personaggio sopra il 3D mentre si orbita.

**Sulla tela** il personaggio e la chat ci sono in tutte le finestre. La tavola «Meridiana, colore a scelta e assistente» mostra la chat in Producibilità, spostata a sinistra, con la conversazione cominciata in Modello.

## 8. Nome e carattere

Daniel sceglierà e disegnerà; queste sono proposte per provarlo.

| Nome | Da dove viene | Carattere | Idea per l'icona |
|---|---|---|---|
| **Gnomone** | l'asta della meridiana che con la sua ombra indica l'ora | preciso, asciutto; indica, non decide. "Indico, tu decidi." | un'asta inclinata con la sua ombra; l'ombra gira come una lancetta mentre pensa |
| **Stilo** | l'altro nome dello gnomone; ricorda anche lo stile | sobrio, didattico, breve | un tratto obliquo, come il segno di una penna |
| **Lucciola** | una piccola luce che si accende solo quando serve; è anche il nome del portatile e del sistema di Daniel | gentile, discreto, compare e scompare | un puntino giallo che pulsa piano |
| **Meridio** | da meridies, il mezzogiorno da cui viene "meridiana": il personaggio di Meridiana | compagno di lavoro, cordiale | un sole a mezzogiorno sopra una linea |
| **Zenit** | il punto più alto del sole | visione d'insieme, riassume | un punto sopra un arco |
| **Analemma** | la figura a otto che il sole disegna sulla meridiana in un anno | colto, per intenditori; lungo da dire | un otto sottile |
| **Ombra** | segue senza farsi notare | spiritoso; ma nel fotovoltaico l'ombra è il nemico, e il gioco può stancare | una sagoma che segue il cursore |
| **Elio** | il sole, e un nome proprio italiano | caldo, colloquiale | un sole semplice |

**Le mie preferite:**
1. **Gnomone:** il più legato al programma, e "indica, non decide" è la regola delle proposte confermate.
2. **Lucciola:** la più gentile, e lega il programma al portatile e al sistema di casa.
3. **Stilo:** la più corta da scrivere in "Chiedi a Stilo".

**Il carattere, qualunque sia il nome:**
- dà del tu, a frasi brevi;
- cita sempre la fonte e dice "non lo so" quando non trova;
- non prende iniziative sul progetto;
- usa i termini delle norme italiane.

**Gli stati dell'icona:** fermo; pensa (animazione lenta); ha un suggerimento (puntino); in locale o nel cloud (casa o nuvola piccole sull'icona).

**Tre disegni da provare** (tavola «Il personaggio dell'assistente» sulla tela, 22/10/2026 sera):
- **Gnomone:** uno gnomo con il cappello a punta inclinato come lo gnomone di una meridiana; fluttua sopra la sua ombra.
- **Meridio:** un sole con la faccia, a mezzogiorno sopra la linea della meridiana.
- **Lucciola:** una lucciola con la coda accesa.

Tutti e tre:
- sono disegnati su una griglia di 24, come le icone Lucide, e si leggono da 16 a 112 px;
- hanno il viso chiaro e il contorno scuro anche nel tema scuro, come un adesivo;
- prendono il colore dell'assistente, che viene dal colore scelto per Meridiana (studio 13, sezione 12);
- mostrano gli stati: fermo, pensa (occhi in su e tre puntini), ha un parere (puntino), in locale o nel cloud (casetta o nuvola).

Sulla tela il personaggio si cambia con la proprietà «personaggio» della finestra.

**Daniel, 22/10/2026 sera** (commento sulla tela): «carina l'interfaccia fatta così! forse meridio è l'assisstente migliore».
- Meridio diventa il personaggio predefinito dei bozzetti (tela, versione 18).
- Gnomone e Lucciola restano nella tavola, a confronto.
- Il nome resta una preferenza finché Daniel non lo conferma.

## 9. Piano a passi

| Passo | Contenuto | Durata [I] | Prova di fine passo |
|---|---|---|---|
| **0. Decisioni** | **Decise da Daniel il 23/10/2026:** nome Meridio; il modello locale come predefinito (Qwen3.6-35B-A3B); Claude con la chiave API per le domande difficili, con il consenso. Compito `docs/compiti/14-assistente-prototipo.md` | - | - |
| **1. Prototipo minimo** | `assistant/providers.py` solo compatibile con OpenAI, verso un `llama-server` avviato a mano. Tre strumenti in sola lettura: `read_checks`, `project_summary`, `go_to`. Il pannello laterale con il testo che arriva man mano, il pulsante Ferma, Ctrl+L. Test con un server SSE finto | 2-3 giorni | Le domande A e D della sezione 4.4 dentro Meridiana, sul progetto di prova, senza che la finestra si blocchi |
| **2. Proposte** | `propose_fix` e `propose_edit` con le schede di conferma e `edit()`; `read_selection`, `read_results`, `read_pedigree`, `read_rules`; "Chiedi a ..." sulle verifiche | 3-4 giorni | Domande 23-29 della batteria; Ctrl+Z annulla ogni proposta applicata |
| **3. Cloud** | Adattatore Anthropic (SDK), chiavi con `keyring`, consenso, progetto riservato, oscuramento, costi, comportamento senza rete. Lo strato OpenAI copre già Mistral, OpenAI, Gemini e Groq | 3-4 giorni | Batteria completa su Haiku 5.5 e Sonnet 5.5; nessun dato senza consenso (test) |
| **4. Conoscenza** | Manuale nel contesto; `search_manual`; per la copia di Daniel, `search_norms` e `read_norm_pages` su `cerca_norme.py`, solo in locale di serie | 2 giorni | Domande 1-8 e 17-22 con le fonti giuste |
| **5. Confronto** | La batteria di 30 domande × 3 ripetizioni su: locale (Qwen3.6-35B-A3B, gpt-oss-20b, Gemma 4 26B-A4B), Haiku 5.5, Sonnet 5.5, un modello Mistral o OpenAI economico. Tabella dei risultati in `docs/studio` | 1-2 giorni, più un'ora di Daniel per fornitore per i giudizi a mano | Una classifica per qualità, tempo e costo |
| **6. Rifiniture** | Suggerimenti spontanei, sempre spegnibili; comandi con lo slash; F1 sui campi; "Chiedi a ..." nei campi e nella genealogia | 2-3 giorni | Daniel lo usa una settimana su una commessa vera |
| **7. Locale gestito** | Meridiana scarica il modello (con SHA-256), avvia e ferma `llama-server`, sceglie gli strati sulla GPU leggendo la GTT libera. Opzione personale "motore Claude Code" (`claude -p` con server MCP) per la copia di Daniel. SIWC per ChatGPT quando esce dall'anteprima | 3-5 giorni | Funziona su Linux e Windows senza configurare nulla a mano |
| **8. Solo se serve** | LoRA su un modello piccolo, per il formato delle chiamate e lo stile, se la batteria lo chiede | da stimare | La batteria migliora senza peggiorare altrove |

## 10. Fonti

Pagine lette il 22/10/2026, salvo dove indicato.

**Anthropic**
- Prezzi: https://platform.claude.com/docs/en/about-claude/pricing
- Compatibilità con l'SDK OpenAI: https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk
- Dati e addestramento: https://privacy.claude.com/en/articles/7996868-is-my-data-used-for-model-training
- Conservazione: https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data
- Claude Code, aspetti legali (anche la copia di archivio del 20/10/2026): https://code.claude.com/docs/en/legal-and-compliance
- Claude Code, modalità non interattiva: https://code.claude.com/docs/en/headless
- Agent SDK: https://code.claude.com/docs/en/agent-sdk/overview
- Agent SDK e claude -p con l'abbonamento: https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
- Crediti API nei piani Max: https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans
- Accesso e strumenti di terzi: https://support.claude.com/en/articles/13189465-log-in-to-your-claude-account
- Termini per i consumatori: https://www.anthropic.com/legal/consumer-terms
- Notizie su gennaio-febbraio 2026 (fonte secondaria): https://www.theregister.com/software/2026/02/20/anthropic-clarifies-ban-on-third-party-tool-access-to-claude/5014546

**OpenAI**
- Prezzi: https://developers.openai.com/api/docs/pricing
- Dati: https://developers.openai.com/api/docs/guides/your-data
- Sign in with ChatGPT: https://developers.openai.com/siwc/quickstart e https://developers.openai.com/siwc/token-sharing-open-source
- Termini di SIWC: https://openai.com/policies/sign-in-with-chatgpt-terms
- Termini d'uso UE: https://openai.com/policies/eu-terms-of-use
- Codex: https://learn.chatgpt.com/docs/auth, https://learn.chatgpt.com/docs/app-server, https://learn.chatgpt.com/docs/non-interactive-mode

**Google**
- Prezzi: https://ai.google.dev/gemini-api/docs/pricing
- Termini (anche la regola sul SEE): https://ai.google.dev/gemini-api/terms
- Compatibilità OpenAI: https://ai.google.dev/gemini-api/docs/openai
- Limiti: https://ai.google.dev/gemini-api/docs/rate-limits
- Fine di Gemini CLI con gli abbonamenti: https://developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals
- Termini di Gemini CLI: https://github.com/google-gemini/gemini-cli/blob/main/docs/resources/tos-privacy.md
- Modalità ACP: https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/acp-mode.md

**Mistral**
- Prezzi: https://docs.mistral.ai/inference/pricing
- Inferenza regionale: https://docs.mistral.ai/inference/regional-inference
- Termini commerciali: https://legal.mistral.ai/terms/commercial-terms-of-service
- Rinuncia all'addestramento: https://help.mistral.ai/en/articles/455207-can-i-opt-out-of-my-input-or-output-data-being-used-for-training
- Dove sono i dati: https://help.mistral.ai/en/articles/347629-where-do-you-store-my-data-or-my-organization-s-data

**Groq**
- Limiti: https://console.groq.com/docs/rate-limits
- Dati: https://console.groq.com/docs/your-data
- Compatibilità OpenAI: https://console.groq.com/docs/openai

**Altri servizi**
- OpenRouter, limiti: https://openrouter.ai/docs/api-reference/limits
- OpenRouter, raccolta dei dati: https://openrouter.ai/docs/guides/privacy/data-collection
- GitHub Models: https://docs.github.com/en/github-models
- Cerebras: https://inference-docs.cerebras.ai/support/rate-limits
- Cloudflare Workers AI: https://developers.cloudflare.com/workers-ai/platform/pricing/
- GitHub Copilot SDK: https://github.com/github/copilot-sdk

**VS Code** (pagine datate 21/10/2026)
- Chat: https://code.visualstudio.com/docs/copilot/chat/copilot-chat
- Funzioni e scorciatoie: https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features
- Impostazione, barra di stato, `chat.disableAIFeatures`: https://code.visualstudio.com/docs/copilot/setup

**Precedenti**
- Zed, agenti esterni: https://zed.dev/docs/ai/external-agents
- Zed, abbonamenti esistenti: https://zed.dev/docs/ai/use-an-existing-subscription
- JetBrains: https://www.jetbrains.com/help/ai-assistant/acp.html

**Motori**
- llama.cpp 0.7.0: https://github.com/ggml-org/llama.cpp/releases/tag/v0.7.0
- llama.cpp b11669: https://github.com/ggml-org/llama.cpp/releases/tag/b11669
- llama.cpp, function calling: https://github.com/ggml-org/llama.cpp/blob/master/docs/function-calling.md
- Ollama, GPU: https://docs.ollama.com/gpu
- Ollama su Linux: https://docs.ollama.com/linux
- Ollama, compatibilità OpenAI: https://docs.ollama.com/api/openai-compatibility
- LM Studio, modalità senza finestra: https://lmstudio.ai/docs/developer/core/headless
- LM Studio, termini: https://lmstudio.ai/app-terms
- Lemonade e NPU su Linux: https://lemonade-server.ai/flm_npu_linux.html
- ROCm, requisiti: https://rocm.docs.amd.com/projects/install-on-linux/en/latest/reference/system-requirements.html
- Framework, GTT e LLM (forum): https://community.frame.work/t/local-llm-on-fw16/82937

**Modelli**
- Qwen3.6-35B-A3B: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
- GGUF usato nella prova: https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF
- Qwen3.5-4B: https://huggingface.co/Qwen/Qwen3.5-4B
- GGUF usato nella prova: https://huggingface.co/unsloth/Qwen3.5-4B-GGUF
- Gemma 4: https://huggingface.co/google/gemma-4-26B-A4B-it
- Gemma 4 GGUF QAT: https://huggingface.co/google/gemma-4-26B-A4B-it-qat-q4_0-gguf
- gpt-oss-20b: https://huggingface.co/openai/gpt-oss-20b
- gpt-oss-20b GGUF: https://huggingface.co/ggml-org/gpt-oss-20b-GGUF
- Ministral 3: https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512
- Nemotron 3.5 Lightning: https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16
- LFM2.5: https://huggingface.co/LiquidAI/LFM2.5-24B-A2B
- Granite 4.2: https://huggingface.co/ibm-granite/granite-4.2-8b
- Classifica italiana EuroEval: https://raw.githubusercontent.com/EuroEval/leaderboards/main/leaderboards/italian_all_simplified.csv
- Evalita-LLM: https://huggingface.co/datasets/evalitahf/evalita_llm_results
- BFCL: https://gorilla.cs.berkeley.edu/leaderboard.html

**Interfaccia e chiavi**
- Qt, scorciatoie standard: https://doc.qt.io/qt-6/qkeysequence.html
- keyring: https://pypi.org/project/keyring/

**Legge e codice**
- L. 633/1941, artt. 70-quater e 70-septies: copia locale `l'archivio locale delle norme\laws\L 633-1941 - Diritto di autore (artt. 64-bis-64-quater programmi per elaboratore) - testo vigente Normattiva al 22-10-2026.pdf`, pp. 31-32.
- Codice di Meridiana, letto il 22/10/2026 pomeriggio in `C:\Users\utente\dev\meridiana-lavoro` (ramo `lavoro`, mentre un'altra sessione lo stava modificando): `src\meridiana\model.py`, `checks.py`, `rules.py`, `energy\pedigree.py`, `energy\simulate.py`, `energy\stringing.py`, `ui\window.py`, `ui\__init__.py`, `config.py`, `build-aux\flatpak\io.github.daniel_g_carrasco.meridiana.yaml`, `po\it.po`.
- Convenzioni di interfaccia: `docs\studio\12a-convenzioni-ux.md`, sezioni 1.10 e 1.11.
- Modulo del portachiavi del template: `C:\Users\utente\dev\app-template\extras\spola\secrets.py`.

**Che cosa non ho potuto verificare**
- I limiti del piano gratuito di Gemini e di Mistral (visibili solo con l'accesso).
- L'impostazione predefinita di Mistral sull'addestramento con il pagamento a consumo.
- Le condizioni di licenza del CEI sull'estrazione di testo e di dati.
- Le prestazioni nei profili energetici bilanciato e prestazioni.
- gpt-oss-20b e Gemma 4 sul portatile: il limite era di due modelli.

## Appendice A. Che cosa è installato sul portatile [V]

Tutto sta in `~/fvtest/llm` (cioè `~/fvtest/llm`), senza root e senza servizi di sistema.

Fuori da quella cartella c'è solo la cache degli shader di Mesa (`~/.cache/mesa_shader_cache`), che il driver Vulkan aggiorna da sé per ogni programma. Dalle 14:58 vi sono 172 file nuovi o cambiati, 2,4 MiB in tutto, probabilmente in parte di llama.cpp [I]. Si rigenera da sola e non va toccata.

| Cartella | Contenuto | Spazio |
|---|---|---|
| `engine/llama-b11669/` | llama.cpp 0.7.0 (build b11669), binari ufficiali `llama-b11669-bin-ubuntu-vulkan-x64.tar.gz`, SHA-256 `e8709e5b...4d9f`, uguale a quello pubblicato | 83 MiB |
| `engine/compat-lib/` | `libssl.so.3` e `libcrypto.so.3` copiate da OpenSSL 3.5.9 di Homebrew (`/home/linuxbrew/.linuxbrew/opt/openssl@3`): Fedora 45 ha solo OpenSSL 4. Per avviare: `export LD_LIBRARY_PATH=~/fvtest/llm/engine/compat-lib` | 8,1 MiB |
| `models/` | `Qwen3.5-4B-Q4_K_M.gguf` (2.740.937.888 byte) e `Qwen3.6-35B-A3B-UD-IQ4_XS.gguf` (17.730.509.792 byte), SHA-256 controllati | 20.471.447.680 byte (19,07 GiB) |
| `dl/` | l'archivio scaricato di llama.cpp | 29 MiB |
| `scripts/` | `download.sh`, `bench.sh`, `serve_test.sh`, `sampler.sh` (sensori), `gttguard.sh` (guardia sulla GTT), `summarize.py`, `tooltest.py` (la prova degli strumenti) | pochi KiB |
| `results/`, `logs/` | i JSON di llama-bench e delle prove degli strumenti, i registri dei server, i CSV dei sensori | 248 KiB |
| **Totale** | | **20.597.354.352 byte: 20,6 GB, cioè 19,2 GiB** |

Alla fine non resta acceso nessun processo: niente server, guardie o campionatori (controllato con `pgrep`).

Per rifare la prova del MoE:

```
cd ~/fvtest/llm && export LD_LIBRARY_PATH=$PWD/engine/compat-lib
engine/llama-b11669/llama-server -m models/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf \
    --host 127.0.0.1 --port 18931 -ngl 99 -ncmoe 20 --no-host -lm dio -fa on -c 16384
```

Per togliere tutto: `rm -rf ~/fvtest/llm`.
