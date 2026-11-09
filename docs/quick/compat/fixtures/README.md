# Fixture Rho congelata

[V] `rho.meridiana` è la copia identica del progetto di prova autorizzato
`Prova capannone Rho.meridiana`, acquisita il 04/11/2026. L'originale non viene
modificato. SHA-256:

```
40d342e81e6314ee5462aa181b6947a218372186dbe7b23013a11cd12005ec13
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
