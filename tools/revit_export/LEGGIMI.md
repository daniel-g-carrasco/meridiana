# Da .rvt a IFC con il Revit di questo PC

Preparato, compilato, **mai provato**: l'avvio di Revit occupa una licenza e apre finestre, quindi aspetta Daniel
(studio 32). L'add-in non fa nulla se la variabile `MERIDIANA_RVT_JOB` non è impostata: un Revit aperto a mano non si
accorge della sua presenza.

## Limite che decide

Revit 2023 apre solo file salvati fino alla 2023. Il dato misurato sul server è nello studio 32, sezione 2.

## Compilare (non serve Revit acceso, legge solo le due DLL)

```powershell
& "C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:library `
  /out:"$env:USERPROFILE\dev\meridiana-prove\revit-export\MeridianaIfcExport.dll" `
  /reference:"C:\Program Files\Autodesk\Revit 2023\RevitAPI.dll" `
  /reference:"C:\Program Files\Autodesk\Revit 2023\RevitAPIUI.dll" `
  tools\revit_export\MeridianaIfcExport.cs
```

## Provare, una volta sola, con Daniel davanti

1. Copiare in locale un .rvt salvato con la 2023 o prima. Mai il file del server.
2. Scrivere il lavoro in un file, per esempio `C:\Temp\lavoro.txt`:
   ```
   source=C:\Temp\modello.rvt
   folder=C:\Temp\uscita
   name=modello
   version=IFC2x3CV2
   ```
3. Copiare `MeridianaIfcExport.addin` in `%APPDATA%\Autodesk\Revit\Addins\2023\`, con il percorso vero della DLL.
4. Avviare Revit con la variabile impostata solo per quel processo:
   ```powershell
   $env:MERIDIANA_RVT_JOB = "C:\Temp\lavoro.txt"
   & "C:\Program Files\Autodesk\Revit 2023\Revit.exe" /nosplash
   ```
5. Aspettare che Revit si chiuda da solo, poi leggere `C:\Temp\uscita\modello.esito.txt`.
6. Importare `C:\Temp\uscita\modello.ifc` in Meridiana.

Per togliere tutto: cancellare il file `.addin` da `%APPDATA%\Autodesk\Revit\Addins\2023\`.

## Cosa non è stato verificato

- Che Revit si avvii e si chiuda senza fermarsi su una finestra: la licenza, gli avvisi di aggiornamento e i link mancanti
  possono chiedere qualcosa che l'add-in non intercetta.
- Il tempo: l'apertura di un modello grande può richiedere minuti.
- Che funzioni su un desktop separato, per non coprire lo schermo.
