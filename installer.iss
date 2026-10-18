; Skrip Inno Setup untuk Sistem Antrian Klinik
; Dipanggil oleh GitHub Actions: ISCC.exe /DAppVersion=1.0.0 installer.iss
#define AppName "Sistem Antrian Klinik"
#define AppExe "SistemAntrianKlinik.exe"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6E1B5C2A-8D4F-4B7E-9A31-2F5D7C9E0B14}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=iman.mn_
AppCopyright=@copyright iman.mn_
DefaultDirName={autopf}\SistemAntrianKlinik
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=SistemAntrianKlinik-Setup-{#AppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Tasks]
Name: "desktopicon"; Description: "Buat ikon di Desktop"; GroupDescription: "Pintasan:"
Name: "autostart"; Description: "Jalankan otomatis saat Windows dinyalakan (untuk PC layar antrian)"; GroupDescription: "Pintasan:"; Flags: unchecked

[Files]
Source: "dist\SistemAntrianKlinik\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{autostartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "Jalankan {#AppName}"; Flags: nowait postinstall skipifsilent
