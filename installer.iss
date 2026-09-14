; Установщик SpeakMot. Собирается через ISCC installer.iss после PyInstaller.
#define AppName "SpeakMotor"
#define AppVersion "0.6.0"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=SpeakMot
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=SpeakMot-setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"

[Files]
Source: "dist\SpeakMot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\SpeakMot.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\SpeakMot.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\SpeakMot.exe"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
