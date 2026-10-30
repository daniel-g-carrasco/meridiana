# Rapporto R: registro delle richieste aggiornato (Fable R, 30/10/2026)

Unico file toccato: `docs/richieste.md`. Solo la colonna Stato delle righe elencate sotto; le parole di Daniel
(colonna Richiesta), le date e la colonna Dove sono rimaste identiche (confronto riga per riga con `git show HEAD`,
a-capo normalizzati: 0 righe con altre colonne cambiate, 0 righe sparite). Nessun commit, nessuna altra operazione git.

## Fonti lette

Tutti i rapporti in `build/claude-r07/` (A, B, C, D, E, F, G, H, I, M, S, T), `decisioni-daniel.md`,
`docs/revisioni/catalogo-audit-R07.md`, `docs/studio/21-arm-tablet/README.md`. Fatti citati negli stati e controllati
sul disco prima di scriverli: i tre test di finestra passati da `QInputDialog.getItem` a `NameDialog.ask` (grep in
`tests/finestra`, 0 residui); la guardia `underMouse` in `src/meridiana/ui/brand_picker.py` riga 94; Equal Earth in
`ui/world_map.py`; `single_instance.py`, `tests/finestra/test_second_start.py`, `tests/formati/test_recovery.py`
presenti; le note dei record SolaX X3-PRO-20K-G2 e ZCS 3PH 11KTL-V3 in `inverters_curated.json`, che citano il
certificato CEI 0-21 con l'URL (correzione del coordinatore su R238, applicata: nessuna domanda a Daniel su questo).

## Righe cambiate (43 stati) e righe aggiunte (2)

Tranche R07, stato riscritto con implementazione, prove, non verificato e rinvii:
- R242 «fatto, da verificare sullo schermo» (sospetto Windows touchpad = rotella, serve il registro reale).
- R243, R244, R245, R246, R247, R248, R249 «fatto e verificato offscreen».
- R250 «fatto e verificato offscreen», con due scelte per Daniel (Meridio sopra File a fine visita; prima visita
  interrotta riparte da Apri).
- R251 «fatto e verificato offscreen», con la domanda H2 (recupero con file esplicito).
- R252, R253, R254, R255, R256, R257, R258 «fatto e verificato offscreen».
- R259 «parziale» (portatile Linux non raggiungibile; nota H8 su `~/fvtest/kokoro-venv` da dire a Daniel).
- R260, R261, R262 «fatto e verificato offscreen» (R260: nessuna chiamata reale ai fornitori).
- R263 «da decidere con Daniel» (quale campo è «l'angolo»: anno del calendario, gizmo, barra del sole).
- R264, R265 «fatto e verificato offscreen».
- R266 «fatto, da verificare sullo schermo» + «da decidere con Daniel» (accelerazione compilata per le ombre).
- R267 «fatto e verificato offscreen» con la decisione S1400 del 30/10 («per l'ottimizzatore va bene così»).
- R268 «fatto e verificato offscreen» + «da decidere con Daniel» (unire le due voci SolarEdge).
- R238 «parziale» (audit G; `cei_0_21` sostenuto dai certificati citati nelle note, nessun dato da cambiare).
- R87 «studio fatto» + «da decidere con Daniel» (quale strada; i circa 3,9 GB nella WSL).
- R144 «fatto, da verificare sullo schermo (collegata a R266)», testo precedente conservato dopo «Precedente:».

Righe vecchie, stato preceduto da «chiusa: ragione», resto della cella invariato: R20, R45, R69, R81, R107, R148,
R171, R191, R236. R38 e R80: «assorbita dalle richieste puntuali successive (R152-R164, R201-R234, R248-R257)» davanti
al testo precedente. R90: «parziale» con il punto per punto (repo pubblico, IFC, manuale, voce, Kokoro = R259,
FreeCAD in attesa, `app-template-test` da cancellare con `delete_repo`). R120: in coda «resta aperta: da misurare
sullo schermo vero».

Aggiunte in fondo all'ultima tabella (3 colonne, come R266-R268):
- R269 «Oggetti 3D di contorno (alberi, ostacoli, persone, auto) in stile minimal»: in corso (30/10), affidato a Kimi
  su richiesta esplicita di Daniel, integrazione di Claude dopo la revisione.
- R270 «Istanza unica e recupero sicuro con più finestre (trovato in revisione D/H)»: fatto e verificato offscreen,
  dal rapporto H (prove, non verificato Linux e pacchetti, domanda H2, port nel modello Qt da fare).

Nessuna riga dice «consegnato» per il lavoro di oggi.

## Controlli finali

- Tabella valida: ogni riga dati ha lo stesso numero di colonne della sua intestazione (5 colonne nelle «Richieste
  aperte», 3 nelle tabelle dal 29/10 in poi). Le righe R221-R234 (sezione «Da decidere») stanno in una tabella senza
  riga di intestazione già in git: non toccate.
- Nessun trattino lungo (U+2014) nel file; a-capo CRLF conservati (366 righe); UTF-8.
- Script usato (fuori dal repository):
  `C:\Users\Grasso\AppData\Local\Temp\claude\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55\scratchpad\aggiorna_richieste.py`.

## Limiti

- Gli stati riportano quello che i rapporti dichiarano verificato; non ho rieseguito le prove.
- La riga R148 è chiusa su un fatto verificabile (la pagina Nuovo dal posto è in `ui/new_project.py`) e sulla
  consegna R06; il passaggio «da rivedere da Claude prima dell'unione» è dato per compiuto dall'integrazione.
- Non ho toccato la colonna Dove di R87 e R90 (restano «-»): il percorso dello studio 21 è dentro lo stato.
