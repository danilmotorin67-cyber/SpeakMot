; Установщик SpeakMotor. Собирается через ISCC installer.iss после PyInstaller.
#define AppName "SpeakMotor"
#define AppVersion "0.12.0"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=SpeakMotor
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer
#ifdef BundleModel
OutputBaseFilename=SpeakMotor-setup-{#AppVersion}-small
#else
OutputBaseFilename=SpeakMotor-setup-{#AppVersion}
#endif
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
#ifdef BundleModel
; модель кладётся туда же, куда её скачала бы сама программа;
; при удалении программы остаётся, как и скачанные вручную
Source: "bundle\models\*"; DestDir: "{%USERPROFILE}\.speakmot\models"; Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall
#endif

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\SpeakMotor.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\SpeakMotor.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\SpeakMotor.exe"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
