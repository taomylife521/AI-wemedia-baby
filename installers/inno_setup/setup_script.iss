; 媒小宝 (WeMediaBaby) Inno Setup 脚本 template
; 用于“迭代期”快速生成安装包
; 文档: docs/软件打包实施方案.md

#define MyAppName "WeMediaBaby"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "MediaBaby Team"
#define MyAppURL "https://github.com/your-repo/wemedia-baby"
#define MyAppExeName "WeMediaBaby.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{E6F78A12-3456-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DisableProgramGroupPage=yes
; 使用非管理员安装模式（安装到当前用户目录，无需管理员权限）
PrivilegesRequired=lowest
OutputDir=..\..\dist\installers
OutputBaseFilename=WeMediaBaby_Setup_Fast_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
; Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 这里的 Source 路径是相对于 .iss 文件的
; 确保先运行了 .\scripts\build_fast.ps1
Source: "..\..\dist\fast\WeMediaBaby\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\fast\WeMediaBaby\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
; 用户级别的快捷方式（非管理员安装）
Name: "{userprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent
