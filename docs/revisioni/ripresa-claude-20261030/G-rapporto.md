# Rapporto G (R238, audit del catalogo), ripresa R07, 30/10/2026

Il rapporto completo è `docs/revisioni/catalogo-audit-R07.md`; qui il riassunto nella forma chiesta da
`REGOLE-AGENTI.md`. Nessun dato del catalogo modificato; nessun commit.

## 1. Che cosa ho rivisto

- `tools/audit_catalog_sources.py` (nuovo, 150 righe): letto per intero; `inverter_records` riproduce l'import
  degli inverter con le stesse regole di arrotondamento; `audit` rifiuta un CSV con hash diverso.
- `tests/nucleo/test_catalog_sources.py`: le 4 prove di F, rieseguite; aggiunte 3 prove (classe `BundledData`).
- `src/meridiana/catalog/audit.py` (letto), `src/meridiana/ui/catalog_dialog.py` righe 560-617 (letto, provato
  offscreen), `tools/update_cec.py` (letto), `src/meridiana/catalog/personal.py` riga 49 (letto).
- `build/overnight-r07/f-brief.md`, `f-cec-audit-R01.json`, `f-fetch-sources.py`; il manifesto e i 160 file
  dell'archivio `reference\catalogs\Meridiana-audit-20261029-R01`; i CSV in `reference\catalogs\CEC-SAM`.

## 2. Difetti trovati nel codice

Nessuno nei file del compito. Lo strumento e le prove di F fanno quello che dichiarano.

## 3. Incoerenze nei dati (non corrette, elencate con la fonte)

- 4 moduli CEC con Imp 12,46 A > Isc 12,27 A, già nella fonte (CEC Modules.csv righe 8701, 8702, 15866, 15867):
  LENERGY LP-505-144M-B/-W, Sonali SS-505-144M-B/-W. Restano nel file, la finestra li rifiuta.
- SolaX X3-PRO-20K-G2 e ZCS Azzurro 3PH 11KTL-V3: `cei_0_21 = true` non sostenuto dalla scheda citata (SolaX
  elenca altre norme, ZCS rimanda al sito).
- `datasheet_revision` vuota in Growatt MOD 10KTL3-X, Solis S5-GR3P10K, ZCS 3PH 11KTL-V3, Huawei SUN2000-100KTL-M2.
- Nessuna differenza numerica nei 34 campi Huawei e nelle 33 voci del campione (circa 620 confronti).

## 4. Modifiche richieste a file non miei

Nessuna necessaria. Proposta (facoltativa, per Claude): una prova in `tests/widget/` che apre
`CatalogDialog("modules")` offscreen, attende `rows.rowCount() > 0`, seleziona la riga LP-505-144M-B, chiama
`accept()` e verifica `result() == 0` e `hint.text() == "Product not selected: inconsistent data. imp > isc"`.
Lo script che lo fa oggi è nella cartella di lavoro temporanea della sessione, non nel repository.

## 5. msgid nuovi

Nessuno.

## 6. Prove eseguite

```
python -m unittest tests.nucleo.test_catalog_sources -v   -> 7 prove, OK (5,5 s)
python -m ruff check --select F,E9,B tools/audit_catalog_sources.py tests/nucleo/test_catalog_sources.py -> All checks passed
python tools/audit_catalog_sources.py --reference ".../CEC-SAM/audit-20261029-R01" --output build/overnight-r07/g-cec-audit-R01.json -> {"modules": true, "inverters": true}, exit 0, JSON identico a f-cec-audit-R01.json
script offscreen sul CatalogDialog -> hint "Product not selected: inconsistent data. imp > isc", result 0
verifica SHA-256 dei 160 file d'archivio -> 160 ok, 0 diversi, 0 mancanti
```

File nuovi: `build/overnight-r07/g-cec-audit-R01.json`, `build/overnight-r07/g-verifica-campione-R01.json`,
`docs/revisioni/catalogo-audit-R07.md`, questo rapporto.

## 7. Limiti e cose non verificate

- 239 record curati su 279 senza confronto di campo con la scheda; le 24.262 schede non sono state rilette.
- 17 record (Hoymiles, Tongwei, LONGi, Huasun, Deye, DMEGC) senza PDF in archivio (URL 403/404 il 29/10); 3
  APsystems con sola pagina HTML. Nessuna rete usata oggi.
- Il blocco delle incoerenze sta nella finestra: la scelta automatica dell'inverter (R267) non è stata
  controllata per questo.
- Confronto a occhio su testo estratto: possibile errore di lettura mio sulle tabelle larghe (Solis e JA Solar
  lette sull'immagine).
- `docs/richieste.md` riga R238 non toccata (file non mio): il testo attuale resta corretto; si può aggiungere
  «campione di 33 voci confrontato con il PDF, 2 `cei_0_21` non sostenuti, rapporto catalogo-audit-R07».
