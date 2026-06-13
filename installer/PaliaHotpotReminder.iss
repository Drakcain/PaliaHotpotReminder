; PaliaHotpotReminder v2.8 installer scaffold
; Build with Inno Setup when available.

[Setup]
AppName=PaliaHotpotReminder
AppVersion=2.8
DefaultDirName={localappdata}\PaliaHotpotReminder
DefaultGroupName=PaliaHotpotReminder
OutputBaseFilename=PaliaHotpotReminder-v2.8-Setup
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=no
DisableDirPage=no
PrivilegesRequired=lowest

[Files]
Source: "..\dist\PaliaHotpotReminder-v2.8-portable\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Hotpot-Remind"; Filename: "{app}\Hotpot-Remind.exe"; WorkingDir: "{app}"
Name: "{commondesktop}\Hotpot-Remind"; Filename: "{app}\Hotpot-Remind.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked
