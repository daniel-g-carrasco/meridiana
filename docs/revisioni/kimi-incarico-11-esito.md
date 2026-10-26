# Incarico 11: esito

## 1. La sessione nascosta e la base

[V] `tools/real_session.sh` crea un display Wayland privato, attende il suo socket, assegna quattro cartelle XDG nuove sotto `/tmp`, esegue il comando e chiude il compositore anche quando il comando fallisce. La prova con `false` ha restituito 1 e non ha lasciato processi. `REAL_SESSION_SIZE` cambia il monitor, `REAL_SESSION_COMPOSITOR` sceglie il compositore, `REAL_SESSION_DBUS=1` conserva il bus privato quando serve provarlo.

[V] GNOME Shell 51.0 apriva il socket ma non completava la sincronizzazione Wayland nemmeno con una `QApplication` vuota. Il registro del protocollo si fermava dopo `wl_display.sync`. Con il bus dei portali il blocco comprendeva anche questi errori esatti: `Error calling StartServiceByName for org.freedesktop.impl.portal.desktop.gtk: Timeout was reached` e `Not providing Settings portal: No working backend`. L'alternativa `--display-server` ha risposto esattamente: `Failed to configure: Can't run in display server mode headlessly`.

[V] Il sistema ha già `mutter` 51.0. Con lo stesso `--headless --wayland --virtual-monitor`, la finestra Qt minima si apre e si chiude subito. Il lanciatore usa quindi `mutter` quando è disponibile, altrimenti `gnome-shell`; si può forzare la scelta con `REAL_SESSION_COMPOSITOR=gnome-shell`. Non è stato installato nulla e non si è usato `offscreen` per il giro reale. Il programma usa Wayland, Qt 6.12.0 e la GPU AMD attraverso `/dev/dri/renderD128`.

[V] `tools/real_tour.py` apre `capannone()`, guida le sei fasi con clic di QTest, apre tutte le sezioni di File e lo chiude con Esc. Le 14 fotografie `docs/revisioni/foto/kimi11-giro-*.png` sono state aperte e guardate. Tempi e avvisi sono in `docs/revisioni/kimi11-giro.txt`.

Risultato del giro:

- [V] Il 3D mostra edificio, copertura e moduli in chiaro e in scuro, non è vuoto (`kimi11-giro-01-model-*.png`). Lo scheletro è sparito prima delle fotografie.
- [V] Tutte le fasi arrivano al clic; File si apre, le cinque sezioni cambiano e Esc torna al progetto. La foto a metà dell'apertura precedente è `kimi11-giro-file-meta.png`.
- [V] Grafici, pannelli e comandi restano leggibili nei due temi. Non si vedono sovrapposizioni o salti di disposizione nelle fotografie ferme.
- [V, bassa] Alcuni testi dei pannelli laterali sono abbreviati: per esempio «Riservato: mai inviato a un modello r...» in Modello e il titolo «Campi (i moduli posati, per orien...» in Producibilità. Sono visibili nelle foto del giro a 1600 px; non riguardano i nuovi strumenti.
- [V] Qt ripete `QWaylandTextInputv3::disableSurface ... Trying to disable ... but 0x0 is focused` ai cambi di fase e scrive una volta `QGraphicsGridLayout::removeAt: invalid index -1` entrando in Consumi. Non ho osservato un effetto associato nelle fotografie o nei comandi guidati; restano registrati, senza una diagnosi non riprodotta.
- [V] Alla fine non restano `gnome-shell`, `mutter`, `real_tour.py` o `dbus-run-session` del giro.

### Prove automatiche sulla base c207d1b

[V] Catalogo compilato prima delle prove e `meridiana.__file__` verificato dentro questo worktree. Ogni gruppo è stato eseguito in un processo proprio, offscreen:

| Gruppo | Esito |
|---|---:|
| nucleo | 790 prove, OK, 4 saltate |
| calcoli | 175 prove, OK |
| formati | 59 prove, OK |
| esterni | 6 prove, OK, 6 saltate perché gli ingressi esterni non sono richiesti |
| widget | 310 prove, OK, 1 saltata |
| finestra | 132 prove, OK |

[V] Non ci sono fallimenti della base da correggere e nessun commit di correzione separato è necessario. `ruff` sui due nuovi strumenti, `bash -n tools/real_session.sh` e `git diff --check` sono puliti.
