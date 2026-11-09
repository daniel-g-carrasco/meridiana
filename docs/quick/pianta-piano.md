# Pianta Quick: piano di esecuzione

Data: 04/11/2026. Specifica: incarico r12-pianta e `CONTESTO.md`.

Architettura: macchine a stati Python senza Qt per gli strumenti, sessione comune per ogni modifica,
adattatore QObject e scena QML. Le trasformazioni della vista restano in QML. Widgets invariati.
Il disegno confronta Shapes, Canvas e geometria QSG su Direct3D 11.

- [ ] Censire strumenti, passi e prove esistenti; conservare un registro per prova.
- [ ] `plan_tools.py`: disegno, numeri, rettangoli, falde, colmi, file, misure, oggetti, agganci.
- [ ] `plan_edit.py`: selezione, gerarchia, selezioni estese, spostamenti, rotazioni, cancellazioni, stringhe.
- [ ] `plan_maps.py`: fonti, attribuzione, tessere, planisfero e sfondi.
- [ ] `plan.py`, `plan_scene.py`, `Plan/`: adattatore sessione, scena, gesti Qt reali, fascia e menu.
- [ ] Confronto render a 778, 5.000 e 20.000 moduli, scale 1 e 2.
- [ ] Parità con Widgets, convergenza con r12-compat, tema da r12-sistema.
- [ ] Foto dei passi, controllo visivo, lint, formati; esito e limiti verificati.

Contratti fra componenti:

`DrawingMachine`: `set_tool(tool)`, `click(point, modifiers=set())`, `key(key, text='', modifiers=set())`,
`move(point, modifiers=set())`; restituiscono liste di comandi dizionario con `type` e parametri.
Stato pubblico: `tool`, `points`, `pointer`, `typed`, `hint`, `preview`, `state`.
Coordinate in metri Est/Nord; i nomi tasti sono `Enter`, `Escape`, `Backspace`, `Tab`, ecc.; modificatori
`ctrl`, `shift`, `alt`. I metodi senza esito restituiscono `[]`.

`PlanEditor(session)`: selezioni e modifiche tramite `session.edit`, `set_results(results)`,
`click(point, modifiers=set())`, `key(key, text='', modifiers=set())`, `set_tool(tool)`,
`apply_command(command)`; stato `selection`, `hint`, `preview`. Le differenze necessarie al contratto
sono documentate prima dell'integrazione.

Le prove devono distinguere gesti del backend, eventi Qt, foto vere, parità dei progetti salvati e
prestazioni. Una categoria verde non dimostra le altre. R388 e R389 restano aperte fino a verifica completa.
