; Установщик SpeakMotor. Собирается через ISCC installer.iss после PyInstaller.
#define AppName "SpeakMotor"
#define AppVersion "0.9.2"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=SpeakMotor
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=SpeakMotor-setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\SpeakMotor.exe
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Ярлыки:"

[Files]
Source: "dist\SpeakMotor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\SpeakMotor.exe"; IconFilename: "{app}\assets\icon.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\SpeakMotor.exe"; IconFilename: "{app}\assets\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\SpeakMotor.exe"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
