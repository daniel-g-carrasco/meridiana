# Fixture Rho congelata

`rho.meridiana` è un progetto dimostrativo. SHA-256:

```
f41e1fadf1259286a57d4d86259353736bdb0cab2624d8169d80a3b4b6a22cdb
```

Quattro edifici, due sottocampi posati, sette inverter, 57 stringhe registrate.
Il meteo è quello registrato in `tests/calcoli/riferimenti/`: anno tipico e
orizzonte PVGIS 5.3 di Rho. Nessuna richiesta di rete. Le perdite e la rete
elettrica restano quelle del progetto. Il riferimento non disattiva le ombre
o la simulazione elettrica per accelerare le foto.

La copia rende gli scenari ripetibili anche nei checkout che non hanno la
cartella personale delle prove. I nuovi file `.mer` e le cache del banco sono
creati soltanto in `build/`. Questa fixture è congelata: una revisione futura
riceve un nome nuovo e un nuovo hash.
