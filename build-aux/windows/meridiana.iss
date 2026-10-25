; Inno Setup script for Meridiana (Inno Setup 6.4 or later: the windows-2025 runner has 6.7).
; Compiled by the CI with:  ISCC.exe /DAppVersion=X.Y.Z build-aux\windows\meridiana.iss
; Expects the PyInstaller output in dist\Meridiana (repository root) and build-aux\windows\meridiana.ico
; (tools/make_ico.py).
;
; The settings (%APPDATA%\Meridiana) and the program's own files (%LOCALAPPDATA%\Meridiana: the state, the
; recovery copies, the caches, the voice's model) stay when the program is uninstalled: they are the user's, and a
; reinstall goes on from them.

#ifndef AppVersion
  #define AppVersion "dev"
#endif
; the program's identity (src/meridiana/__init__.py): the AppUserModelID of its taskbar button, and the name of the
; mutex it holds while it runs (app.py), which tells an update whether to start it again
#define AppId "io.github.daniel_g_carrasco.meridiana"
#define ProgId "Meridiana.Project"

[Setup]
AppId={{BC7761C0-15BD-40FC-87D1-98D297118957}
AppName=Meridiana
AppVersion={#AppVersion}
AppPublisher=Daniel Grasso
AppPublisherURL=https://github.com/daniel-g-carrasco/meridiana
AppSupportURL=https://github.com/daniel-g-carrasco/meridiana/issues
AppUpdatesURL=https://github.com/daniel-g-carrasco/meridiana/releases
DefaultDirName={autopf}\Meridiana
DefaultGroupName=Meridiana
DisableProgramGroupPage=yes
; per-user install by default (no UAC); the dialog lets the user elevate,
; and the command line (/CURRENTUSER, as the program's own update passes it)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
OutputDir=..\..\dist
OutputBaseFilename=meridiana-setup-v{#AppVersion}-windows-x64
SetupIconFile=meridiana.ico
UninstallDisplayIcon={app}\Meridiana.exe
Compression=lzma2/max
SolidCompression=yes
LZMAUseSeparateProcess=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763
; an update closes the running program (CloseApplications asks the Restart Manager); the program asks to save the
; project before it starts Setup (the update's dialog), and its recovery copy covers the rest
CloseApplications=yes
RestartApplications=no
; the .meridiana files open with Meridiana: Explorer is told when the associations change
ChangesAssociations=yes

[Languages]
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
italian.AppDescription=Progettazione fotovoltaica: mappa, modello dell'edificio, percorso del sole, posa dei moduli e norme italiane
english.AppDescription=Photovoltaic design: map, building model, sun path, module layout and Italian standards
italian.ProjectType=Progetto Meridiana
english.ProjectType=Meridiana project
italian.AssociateFiles=Apri i file .meridiana con Meridiana
english.AssociateFiles=Open .meridiana files with Meridiana

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked
Name: "associate"; Description: "{cm:AssociateFiles}"

[InstallDelete]
; the version before's libraries and modules (PyInstaller's _internal) go
; first: one the new version no longer ships must not stay there and be
; loaded. The program has quit by then (CloseApplications); its settings and
; data are not in {app}, the uninstaller is not in _internal
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\..\dist\Meridiana\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
; the AppUserModelID the program's window carries: its taskbar button groups with the shortcut
Name: "{group}\Meridiana"; Filename: "{app}\Meridiana.exe"; Comment: "{cm:AppDescription}"; AppUserModelID: "{#AppId}"
Name: "{autodesktop}\Meridiana"; Filename: "{app}\Meridiana.exe"; Tasks: desktopicon; AppUserModelID: "{#AppId}"

[Registry]
; the type of the project files (HKA: the user's classes for a per-user install, the machine's for all users); a
; ProgID of its own, the extension pointing to it, and the program among those that open it; the uninstaller
; takes them away, the extension's key only when nothing else is left in it
Root: HKA; Subkey: "Software\Classes\.meridiana"; ValueType: string; ValueName: ""; ValueData: "{#ProgId}"; Flags: uninsdeletevalue uninsdeletekeyifempty; Tasks: associate
Root: HKA; Subkey: "Software\Classes\.meridiana"; ValueType: string; ValueName: "Content Type"; ValueData: "application/x-meridiana"; Flags: uninsdeletevalue; Tasks: associate
Root: HKA; Subkey: "Software\Classes\.meridiana\OpenWithProgids"; ValueType: string; ValueName: "{#ProgId}"; ValueData: ""; Flags: uninsdeletevalue uninsdeletekeyifempty; Tasks: associate
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: ""; ValueData: "{cm:ProjectType}"; Flags: uninsdeletekey; Tasks: associate
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: "AppUserModelID"; ValueData: "{#AppId}"; Tasks: associate
Root: HKA; Subkey: "Software\Classes\{#ProgId}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\Meridiana.exe,0"; Tasks: associate
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Meridiana.exe"" ""%1"""; Tasks: associate
Root: HKA; Subkey: "Software\Classes\Applications\Meridiana.exe\SupportedTypes"; ValueType: string; ValueName: ".meridiana"; ValueData: ""; Flags: uninsdeletekey

[Run]
Filename: "{app}\Meridiana.exe"; Description: "{cm:LaunchProgram,Meridiana}"; Flags: nowait postinstall skipifsilent; Check: not AppWasRunning
; an update (from the program's own dialog, /SILENT) starts again the program it closed
Filename: "{app}\Meridiana.exe"; Flags: nowait runasoriginaluser; Check: AppWasRunning

[Code]
var
  WasRunning: Boolean;

function AppWasRunning(): Boolean;
begin
  Result := WasRunning;
end;

{ Was the program running when Setup started? The Restart Manager closes it
  (CloseApplications); this only remembers whether to start it again. The
  program holds a mutex named as its AppId while it runs (app.py). }
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  WasRunning := CheckForMutexes('{#AppId}');
  Result := '';
end;
