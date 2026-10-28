# Incarico 23 per Kimi: la navigazione con il touchpad e con lo spazio, e la mappa da lontano (R189, R190, R191), 27/10/2026

Usa la skill meridiana. Leggi parola per parola R189, R190 e R191 di docs/richieste.md, e R140, R146, R166, R173 che
li hanno preceduti. Daniel lavora **su Windows** (portatile Dell, touchpad di precisione, schermo a 200 %): i suoi eventi
non sono quelli del laptop Linux. Su Windows un touchpad di precisione manda di solito eventi della rotella (angleDelta
verticale e orizzontale, spesso senza fase) e il pizzico come rotella con Ctrl; su Wayland arrivano pixelDelta con le
fasi e i gesti nativi. Il codice deve andare bene per tutti e due, e le prove devono simulare tutti e due.

## Dove lavori
Nella cartella ~/dev/meridiana-kimi, sul ramo kimi-incarico-23 preso da kimi-incarico-22 (il lanciatore lo crea).

## Punti
1. **Il registro degli eventi.** Una variabile d'ambiente (per esempio MERIDIANA_INPUT_LOG=<file>) fa scrivere a
   Meridiana, per pianta e 3D, ogni evento di rotella, gesto, tasto e mouse con tipo, angleDelta, pixelDelta, fase,
   modificatori, sorgente, posizione e ora. Spiega in docs/ come lanciarlo su Windows: Claude chiederà a Daniel di
   rifare i gesti e manderà il file, così i difetti si vedono sui suoi eventi veri.
2. **R189, il touchpad.** Lo scorrimento a due dita a destra e a sinistra fa «strani saltelli»: trova perché
   (per esempio gli assi trattati in modo diverso, un evento che cambia significato a metà gesto, accumuli) e
   correggi; lo spostamento deve seguire le dita, liscio, nei due assi. Niente rotazione con il touchpad (si ruota con
   i comandi di R174 e R183). Il pizzico ingrandisce attorno al punto sotto il cursore, sia come gesto nativo sia come
   rotella con Ctrl, e il punto sotto il cursore resta fermo. Prove con le sequenze di eventi di Windows e di Wayland.
3. **R190, Spazio con il movimento.** Compare la manina ma la vista resta bloccata. Trova perché (per esempio la
   ripetizione automatica del tasto su Windows, che manda pressioni e rilasci finti, o il mouse non catturato) e
   correggi: con Spazio premuto la vista segue il mouse, al rilascio torna lo strumento di prima. Prove con la
   ripetizione automatica simulata.
4. **R191, la mappa da lontano.** Solo se nella riga R191 del registro c'è la scelta di Daniel: realizza quella, con le
   foto a più scale (tetto, regione, Europa, mondo). Se la scelta non c'è, salta il punto e scrivilo nell'esito.
5. **Chiusura.** Registro, CHANGELOG, po/it.po, esito in docs/revisioni/kimi-incarico-23-esito.md con le sequenze di
   eventi provate, tutti i gruppi di prove, ruff, msgfmt.
