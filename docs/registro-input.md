# Registro degli eventi di pianta e 3D

Per diagnosticare il touchpad, la rotella, i gesti e Spazio, Meridiana può scrivere gli eventi grezzi che riceve da Qt. Il registro è spento di serie. Si attiva soltanto con la variabile d'ambiente `MERIDIANA_INPUT_LOG`.

Ogni riga del file è un oggetto JSON con:

- data e ora UTC, vista (`plan` o `3d`) e tipo dell'evento;
- `angleDelta`, `pixelDelta`, fase e sorgente della rotella;
- modificatori, tipo e valore del gesto, tasto, testo e ripetizione automatica;
- pulsanti, posizione nella vista e posizione globale del mouse.

## Su Windows

1. Chiudi Meridiana e apri **PowerShell**.
2. Incolla questi comandi. Per lo zip portabile, cambia `$exe` con il percorso del suo `Meridiana.exe`.

   ```powershell
   $exe = "$env:LOCALAPPDATA\Programs\Meridiana\Meridiana.exe"
   $env:MERIDIANA_INPUT_LOG = "$env:TEMP\meridiana-input.jsonl"
   & $exe
   ```

3. Nella pianta e nella 3D rifai lentamente i gesti difettosi: scorrimento orizzontale e verticale con due dita, pizzico, Spazio e trascinamento.
4. Chiudi Meridiana. Il file si trova in `%TEMP%\meridiana-input.jsonl`. Per aprire la cartella:

   ```powershell
   explorer $env:TEMP
   ```

5. Manda `meridiana-input.jsonl` a chi segue la diagnosi. Il file contiene gli eventi e le loro posizioni, non il contenuto del progetto.
6. Nella stessa PowerShell togli la variabile, così un altro avvio da quella finestra non continua a scrivere:

   ```powershell
   Remove-Item Env:MERIDIANA_INPUT_LOG
   ```

Se il programma era già aperto, il registro non si attiva: la variabile viene letta quando vengono create le viste.
