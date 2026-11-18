# Risposte registrate di Meridio

Le risposte in streaming (server-sent events) di `llama-server` con Qwen3.6-35B-A3B UD-IQ4_XS sul portatile
"lucciola", registrate il 24/10/2026 sera con i fornitori, gli strumenti e il ciclo di Meridiana (compito 14),
così come sono arrivate: un file per giro del modello (`<domanda>-<giro>.sse`). Il percorso del modello sul
portatile è stato tolto dal campo `model`; il resto è com'era.

Server: llama.cpp 0.7.0 (b11669), Vulkan, `-ngl 99 -ncmoe 20 --no-host -lm dio -fa on -c 16384 -np 1`, solo su
127.0.0.1 (studio 14, appendice A); ragionamento spento (`chat_template_kwargs.enable_thinking = false`).

Progetto: «Capannone Rho» dei test (`_fixtures.capannone_rho`, sottocampo posato) con le due verifiche della prova
dello studio 14, 4.4 (`_fakes.with_problems`): Uoc oltre l'inverter (da correggere) e ombra sul sottocampo Sud (da
controllare). Nessun dato dei progetti di Daniel.

| Domanda | File | Strumenti chiamati | Tempo totale | Prima parola |
|---|---|---|---|---|
| A. «Ci sono problemi da sistemare prima della relazione? In che ordine?» | `A-1`, `A-2` | `read_checks(warn)` | 33,3 s | 12,8 s |
| D. «Come provo un'altra disposizione senza perdere quella attuale e poi le confronto?» | `D-1`, `D-2` | `search_manual` | 31,3 s | 11,9 s |
| B. «Portami sul sottocampo con le ombre e prepara la correzione, ma non applicarla» | `B-1` ... `B-5` | `read_checks` due volte, `go_to(subfield s1)`, `propose_fix(c2)` | 40,6 s | 22,2 s |
| 27. «Portami sulla verifica più grave» | `Q27-1` ... `Q27-3` | `read_checks(fail)`, `go_to(phase plant)` | 28,8 s | 13,1 s |

I test (`tests/nucleo/test_assistant_answers.py`) le fanno ripetere da un server finto (`_fakes.FakeServer`) e
controllano le chiamate agli strumenti e il ciclo.
