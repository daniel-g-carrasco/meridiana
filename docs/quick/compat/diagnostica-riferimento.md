# Diagnostica del banco di acquisizione, 04/11/2026

Queste osservazioni riguardano il processo di acquisizione. Non sono diagnosi
di difetti introdotti nel programma Quick.

## Calcolo Rho e limite di attesa

[V] Il primo limite di 240 s è stato superato durante la rete elettrica.
Una prova separata della pipeline originale, senza ridurre moduli, stringhe,
ombre o perdite, è terminata in 214,865 s. La rete elettrica ha richiesto
193,753 s. Risultato: 425.352,8506294732 kWh, 8.760 ore.

Evidenza locale: `build/rho-core-probe/result.json` e
`build/rho-core-probe.log`. Il banco attende ora fino a 1.200 s, riusando
il medesimo risultato mentre cambia tema e misura della finestra.

## Arresti durante la diagnostica periodica

[V] Alcune esecuzioni sono terminate con codice -1, senza traceback e in
punti diversi: durante il calcolo, dopo una matrice vuota, dopo quattro
catture Rho. I casi parziali non sono stati dichiarati completi né sovrascritti.
Le loro prove sono conservate in `build/quick-parity/diagnostic-canonical/`.

[V] Una riproduzione con monitor della memoria ha registrato il codice Windows
3221225477, access violation, a 122,456 s. Nel log del dump periodico compare:

```
Timeout (0:01:00)!
Thread ... numpy/_core/fromnumeric.py
Windows fatal exception: access violation
Thread ... numpy/_core/numeric.py, line 2414 in <genexpr>
```

Il thread GUI era in `quick_rif.wait_for`; il thread di calcolo nella rete
elettrica. Il working set era circa 640-690 MB, con picco di circa 714 MB;
la memoria privata circa 1,96 GB. Non si osserva un aumento improvviso prima
dell'arresto. Evidenze: `build/quick-parity/reference-probe.log`,
`reference-memory.jsonl`, `reference-probe-finished.json` e
`build/riferimento/rho-probe-v1/rho-light-s1-1366x900/trace.log`.

[I] L'arresto coincide con `faulthandler.dump_traceback_later(60, repeat=True)`
mentre NumPy e il worker Qt sono attivi. Per verificare questa ipotesi è stato
rimosso soltanto il dump periodico dal banco. Resta `faulthandler.enable()`
per registrare errori fatali. Nessun cambiamento al calcolo o ai sorgenti
applicativi. I nuovi log sono `reference-probe2.log`, `reference-memory2.jsonl`
e `reference-probe2-finished.json`. Il nesso causale resta un'inferenza, non
una diagnosi certa di CPython, NumPy o Qt.

## Chiusura e misura al 200%

[V] Una prima acquisizione vuota aveva scritto tutte le 210 immagini e i sei
manifest, ma il processo restava nella distruzione finale dei wrapper Qt.
Come nel runner già presente `tools/run_tests.py`, il processo dedicato ora
chiude la finestra, aspetta il pool, scarica stdout/stderr e termina con
`os._exit(0)`. Gli errori precedenti non vengono convertiti in successo.

[V] A scala 2 Windows limitava una finestra ridimensionata alla superficie
del desktop, ottenendo 1502×951 invece della misura richiesta. Il controllo
delle dimensioni ha rifiutato la cattura. `setFixedSize` consente la dimensione
logica richiesta; il readback copre l'intero contenuto, anche fuori dal monitor
virtuale. La verifica finale confronta anche dimensioni fisiche e DPR dei PNG.
