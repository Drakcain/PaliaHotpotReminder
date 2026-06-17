#ifndef MyAppVersion
#define MyAppVersion "3.1.2"
#endif
#ifndef MyPayloadDir
  #define MyPayloadDir "..\build\installer-payload"
#endif

#define MyAppName "Palia Hotpot Reminder"
#define MyAppPublisher "Drakcain"
#define MyAppURL "https://github.com/Drakcain/PaliaHotpotReminder"

[Setup]
AppId=PaliaHotpotReminder
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName=C:\Tools\PaliaHotpotReminder
DefaultGroupName=Palia Hotpot Reminder
OutputDir=..\dist
OutputBaseFilename=PaliaHotpotReminder-Setup-v3.1.2
SetupIconFile=..\assets\App Icon\HPR_Icon.ico
UninstallDisplayIcon={app}\Hotpot-Remind.exe
Compression=lzma2/ultra64
SolidCompression=yes
DisableProgramGroupPage=no
DisableDirPage=no
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
SetupLogging=yes
Uninstallable=yes
UninstallDisplayName=Palia Hotpot Reminder
MinVersion=10.0.17763
InfoBeforeFile=..\INSTALL-NOTICE.txt
CloseApplications=no

[Files]
Source: "{#MyPayloadDir}\*"; DestDir: "{app}"; Excludes: "config\settings.json,config\recall_state.json,logs\*,debug\*,exports\*"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#MyPayloadDir}\config\settings.json"; DestDir: "{app}\config"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "..\INSTALL-NOTICE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD-PARTY-NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\SIGNING.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\VERSION"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\config"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\logs"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\debug"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\exports"; Permissions: users-modify; Flags: uninsneveruninstall

[Icons]
Name: "{group}\Palia Hotpot Reminder"; Filename: "{app}\Hotpot-Remind.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\Palia Hotpot Reminder"; Filename: "{app}\Hotpot-Remind.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\Logs"; Filename: "{app}\logs"
Name: "{group}\Debug"; Filename: "{app}\debug"
Name: "{group}\Third-Party Notices"; Filename: "{sys}\notepad.exe"; Parameters: """{app}\THIRD-PARTY-NOTICES.md"""; WorkingDir: "{app}"
Name: "{group}\Signing and Windows Warnings"; Filename: "{sys}\notepad.exe"; Parameters: """{app}\SIGNING.md"""; WorkingDir: "{app}"
Name: "{group}\Uninstall Palia Hotpot Reminder"; Filename: "{uninstallexe}"
Name: "{group}\PaliaHotpotReminder on GitHub"; Filename: "{#MyAppURL}"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[Run]
Filename: "{app}\Hotpot-Remind.exe"; Description: "Launch Palia Hotpot Reminder"; Flags: nowait postinstall skipifsilent

[Code]
const
  HPRProcessName = 'Hotpot-Remind.exe';

function RunHidden(const FileName: string; const Parameters: string): Integer;
var
  ResultCode: Integer;
begin
  ResultCode := 0;
  if not Exec(FileName, Parameters, '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    ResultCode := -1;
  Result := ResultCode;
end;

function IsHPRRunning(): Boolean;
var
  ResultCode: Integer;
begin
  ResultCode := RunHidden(
    ExpandConstant('{cmd}'),
    '/C tasklist /FI "IMAGENAME eq ' + HPRProcessName + '" | find /I "' + HPRProcessName + '" >nul 2>&1'
  );
  Result := ResultCode = 0;
end;

procedure KillRunningHPR();
begin
  Log('Installer close-app hardening: checking for running ' + HPRProcessName);
  if not IsHPRRunning() then
  begin
    Log('Installer close-app hardening: no running HPR process detected.');
    exit;
  end;

  Log('Installer close-app hardening: attempting graceful close for ' + HPRProcessName);
  RunHidden(
    ExpandConstant('{cmd}'),
    '/C taskkill /IM "' + HPRProcessName + '" >nul 2>&1'
  );
  Sleep(1500);

  if not IsHPRRunning() then
  begin
    Log('Installer close-app hardening: graceful close succeeded.');
    exit;
  end;

  Log('Installer close-app hardening: graceful close did not finish; forcing shutdown for ' + HPRProcessName);
  RunHidden(
    ExpandConstant('{cmd}'),
    '/C taskkill /IM "' + HPRProcessName + '" /T /F >nul 2>&1'
  );
  Sleep(1200);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  KillRunningHPR();
  if IsHPRRunning() then
  begin
    Log('Installer close-app hardening: ' + HPRProcessName + ' is still running after forced shutdown attempt.');
    Result :=
      'Setup could not close ' + HPRProcessName + ' automatically. Close Palia Hotpot Reminder and run Setup again.';
    exit;
  end;

  Log('Installer close-app hardening: setup may continue.');
  Result := '';
end;
