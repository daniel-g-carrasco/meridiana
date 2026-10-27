ESITO: verde

# Incarico 12: integrazione degli incarichi 5, 6 e 7

27/10/2026, ramo `kimi-integra`, base `c207d1b`. [V] Sono stati uniti soltanto i tre rami richiesti e poi è stato
ripreso soltanto `9ae75e9` dall'incarico 11. Nessun rebase, reset, force o push. I registri dei tre rami mostrano
tutti i loro punti completati: sei per R170, quattro per le mappe più la verifica, tre per R133, R172 e R2 più la
documentazione. Non restano quindi punti dichiarati non fatti. R178 e R180 non sono stati modificati.

## Punto 1: incarico 5, Meridio

Commit di unione `cbebc74`, «Merge Meridio conversation fixes (integration, point 1)».

Conflitti e risoluzione:

- `CHANGELOG.md`: conservate le voci già presenti per R133, R134, R142, R169, R174 e R181 e aggiunte entrambe le
  voci di R170, senza perdere le correzioni della base.
- `docs/progetto.md`: conservate le righe degli incarichi 3 e 4 e aggiunta la riga dell'incarico 5.
- `docs/richieste.md`: mantenuta la descrizione completa della conversazione di Daniel e portato R170 allo stato
  più recente, «fatto nel codice», con il rinvio al rapporto dell'incarico 5.
- `po/it.po`: riunite le voci e le traduzioni delle due parti, poi rigenerato il catalogo.

File toccati dalla risoluzione: `CHANGELOG.md`, `docs/progetto.md`, `docs/richieste.md`, `po/it.po`.

Per Claude: la conversazione completa usa un provider finto. [V] I dati consegnati al modello e le card sono coperti
dalle prove, ma la qualità del ragionamento di Haiku o Sonnet sul progetto reale resta da giudicare come già scritto
in `docs/revisioni/kimi-incarico-5-lavori.md`.

## Punto 2: incarico 6, mappe e mondo

Commit di unione `06e7841`, «Merge reliable maps and world view (integration, point 2)».

Conflitti e risoluzione:

- `CHANGELOG.md`: mantenuta la nuova voce sulle mappe insieme a tutte le voci già unite, comprese quelle di R133 e
  R170.
- `docs/richieste.md`: conservato R170 completato e portati R131, R149 e R173 agli stati finali dell'incarico 6.
- `po/it.po`: riunite le voci delle mappe con quelle precedenti, senza perdere traduzioni.

File toccati dalla risoluzione: `CHANGELOG.md`, `docs/richieste.md`, `po/it.po`.

Per Claude: [V] i ripieghi e il passaggio automatico fra stradale e ortofoto sono provati con server locale e
immagini generate, non contro i server cartografici pubblici. Controllare con cura il dato Natural Earth incluso nei
pacchetti Flatpak e Windows e, sullo schermo, il viaggio tetto-continenti-tetto con una fonte che fallisce davvero.

## Punto 3: incarico 7, Impostazioni, passo delle file e Proprietà

Commit di unione `cabbe45`, «Merge integrated settings and reusable properties (integration, point 3)».

Conflitti e risoluzione:

- `CHANGELOG.md`: unite le voci R2, R133 e R172 con quelle delle mappe e di Meridio; la voce R133 ora descrive le
  Impostazioni dentro File e conserva il comportamento immediato della dimensione del testo.
- `docs/progetto.md`: aggiunte le tre righe dell'incarico 7 dopo quella dell'incarico 5.
- `docs/richieste.md`: mantenuti gli stati più recenti di R2, R131, R133, R170, R172 e R173.
- `po/it.po`: riunite tutte le voci e rigenerato il catalogo.
- `src/meridiana/assistant/tools.py`: mantenuti `params_display` di R170 e `window_from_project` di R172 nella stessa
  risposta di `read_selection`.
- `src/meridiana/checks.py`: mantenute aggregazione pesata delle ombre, base dell'irraggiamento, costo della
  correzione e ore nel formato `11:00`, usando la finestra effettiva del sottocampo invece di quella globale.
- `src/meridiana/fields.py`: aggiunto il nome leggibile di `params.window` alle tabelle condivise.
- `src/meridiana/ui/assistant_chat.py`, `src/meridiana/ui/properties.py`, `src/meridiana/ui/window.py`: conservati
  insieme le card di Meridio, il riuso delle pagine delle Proprietà e le Impostazioni dentro File con applicazione
  immediata.
- `tests/nucleo/test_assistant_answers.py`, `tests/nucleo/test_checks.py`: conservate sia le nuove prove di R170 sia
  quelle della finestra propria del sottocampo; l'attesa sulle ore usa il formato con i due punti.

File toccati dalla risoluzione: `CHANGELOG.md`, `docs/progetto.md`, `docs/richieste.md`, `po/it.po`,
`src/meridiana/assistant/tools.py`, `src/meridiana/checks.py`, `src/meridiana/fields.py`,
`src/meridiana/ui/assistant_chat.py`, `src/meridiana/ui/properties.py`, `src/meridiana/ui/window.py`,
`tests/nucleo/test_assistant_answers.py`, `tests/nucleo/test_checks.py`.

Per Claude: rivedere soprattutto i due incroci semantici, Meridio che legge insieme nomi dei campi e finestra
effettiva, e la correzione delle ombre che combina il costo su tutti gli array con giorno e ore del singolo
sottocampo. [V] Entrambi hanno prove dedicate verdi dopo l'unione.

## Punto 4: strumenti, prove e giro reale

[V] `9ae75e9` è stato ripreso come `9857d9c`. Sono arrivati `tools/real_session.sh`, `tools/real_tour.py`, le 14 foto
`kimi11-giro-*.png` e `docs/revisioni/kimi-incarico-11-esito.md`, conservati come richiesto. Il giro dell'incarico 12
usa nomi `kimi12-*` e aggiunge lo zoom ai continenti, le Impostazioni in chiaro e scuro, il cambio immediato della
dimensione del testo e il suo annullamento.

[V] Interprete `/var/home/daniel/fvtest/venv314/bin/python`; `meridiana.__file__` punta a questo checkout.
`tools/compile_po.py --update` è stato eseguito dopo le unioni. `msgfmt --check --statistics po/it.po` riporta 3.127
messaggi tradotti e nessun fuzzy o non tradotto. Ruff su `src tests tools`, `bash -n tools/real_session.sh` e
`git diff --check` sono puliti.

Prove automatiche offscreen, un gruppo per processo:

| Gruppo | Esito |
|---|---:|
| nucleo | 803 prove, OK, 4 saltate |
| calcoli | 176 prove, OK |
| formati | 59 prove, OK |
| esterni | 6 prove, OK, 6 saltate perché gli ingressi esterni non sono abilitati |
| widget | 322 prove, OK, 1 saltata |
| finestra | 133 prove, OK |
| totale | 1.499 prove, nessun fallimento, 11 saltate |

[V] Non è caduta alcuna prova e non sono state necessarie correzioni dopo le unioni.

### Prova vera e fotografie

[V] `tools/real_session.sh` e `tools/real_tour.py` hanno completato il giro in 53,099 secondi su Wayland, Qt 6.12.0,
monitor nascosto 1600 x 1000. Il registro è `docs/revisioni/kimi12-giro.txt`. Sono state aperte e guardate tutte le
18 foto `docs/revisioni/foto/kimi12-*.png`.

- Le sei fasi cambiano col clic; grafici, pannelli e comandi sono leggibili nei due temi.
- Il 3D mostra edificio, tetto e moduli, non è vuoto; lo scheletro è sparito prima degli scatti.
- Il mondo Natural Earth è visibile in chiaro e scuro e il ritorno al progetto riesce.
- File si apre, le Impostazioni compaiono dentro la pagina, il testo passa da Medio a Grande e torna a Medio con
  Annulla; le altre sezioni si aprono ed Esc chiude File.
- Non si vedono nuove sovrapposizioni o testi tagliati. Restano le abbreviazioni nei pannelli laterali già annotate
  dall'incarico 11. La foto a metà apertura di File è voluta; R178 resta affidato a Claude.
- Qt ripete gli avvisi `QWaylandTextInputv3::disableSurface` e una volta
  `QGraphicsGridLayout::removeAt: invalid index -1`, già presenti nella base. Non ho osservato un effetto associato
  nelle foto o nei gesti guidati e non attribuisco loro una causa non riprodotta.

[V] Non sono rimasti processi del programma, del compositore o del giro. Non è stata installata alcuna dipendenza e
non è stata aperta una finestra sullo schermo di Daniel.
