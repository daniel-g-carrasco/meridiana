# Compatibilità: che cosa resta

Fino al 10/11/2026 questa cartella teneva il registro di parità fra la finestra Qt Widgets e la Quick (R389:
`parita.json`, `prove.csv`, `richieste.csv`, gli scenari, le differenze approvate) e la matrice fotografica di
riferimento della finestra Widgets (`riferimento/`). La finestra Widgets è stata tolta (ramo `r30-struttura`,
fase B dello studio 43) e con lei il registro, la matrice e gli strumenti che li scrivevano (`tests/quick/parity`,
`tools/quick_rif*.py`): sono nella storia di git, all'ultimo commit che li ha (`db90a85b`).

Le risposte che i Widgets davano nelle prove di confronto sono rimaste come registrazioni accanto alle prove della
Quick (`tests/quick/<gruppo>/riferimenti/`, scritte da `tests/quick/aiuti/riferimenti.py`).

Restano:

- `fixtures/rho.meridiana`: il progetto d'esempio di `package_check` (CI, `build.ps1`, Flatpak) e di alcune prove;
- `prove-native.md`: come si leggono i fotogrammi nativi (`tests/quick/aiuti/realwindow.py`).
