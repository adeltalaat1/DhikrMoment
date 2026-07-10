#define AppName "لحظة ذكر"
#define AppEnglishName "DhikrMoment"
#define AppVersion "1.0.1"
#define AppPublisher "Adel"

[Setup]
AppId={{D90F9B7E-2F4C-4B6F-80AF-247B1DBF6D8A}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppEnglishName}
DefaultGroupName={#AppName}
OutputDir=release
OutputBaseFilename=DhikrMomentSetup
SetupIconFile=assets\app_icon.ico
UninstallDisplayIcon={app}\DhikrMoment.exe
UninstallDisplayName={#AppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
DisableDirPage=no
DisableProgramGroupPage=no
CloseApplications=yes
CloseApplicationsFilter=DhikrMoment.exe
RestartIfNeededByRun=no
VersionInfoVersion={#AppVersion}.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Tasks]
Name: "startup"; Description: "تشغيل {#AppName} مع ويندوز"; GroupDescription: "مهام إضافية:"; Flags: checkedonce
Name: "desktopicon"; Description: "إنشاء اختصار على سطح المكتب"; GroupDescription: "مهام إضافية:"; Flags: unchecked

[Files]
Source: "dist\DhikrMoment\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\DhikrMoment.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\DhikrMoment.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\DhikrMoment.exe"; WorkingDir: "{app}"; Tasks: startup

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "DhikrMoment"; Flags: deletevalue uninsdeletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\DhikrMoment"; Flags: deletekey

[InstallDelete]
Type: files; Name: "{app}\DhikrMomentUninstall.exe"

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c taskkill /IM DhikrMoment.exe /F"; Flags: runhidden; RunOnceId: "StopDhikrMoment"

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\DhikrMoment"

[Run]
Filename: "{app}\DhikrMoment.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
