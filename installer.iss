; Inno Setup Script for Shoukat Sons Garments POS
; This creates a professional Windows installer for the POS application
; 
; Download Inno Setup from: https://jrsoftware.org/isdl.php
; Compile with: ISCC.exe installer.iss

[Setup]
AppName=Shoukat Sons Garments POS
AppVersion=1.0.0
AppPublisher=Shoukat Sons Garments
AppContact=support@shoukatsons.com
AppSupportURL=https://your-domain.com/support
AppUpdatesURL=https://your-domain.com/shoukat-pos/updates.json
DefaultDirName={autopf}\ShoukatPOS
DefaultGroupName=Shoukat Sons Garments
AllowNoIcons=yes
LicenseFile=
OutputDir=.
OutputBaseFilename=ShoukatPOS_Setup
SetupIconFile=shoukat_pos\assets\logo.ico
UninstallDisplayIcon={app}\ShoukatPOS.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Main application files from PyInstaller output
Source: "dist\ShoukatPOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Note: Don't include the .exe separately - it's in the dist folder

[Icons]
Name: "{group}\Shoukat POS"; Filename: "{app}\ShoukatPOS.exe"
Name: "{group}\{cm:UninstallProgram,Shoukat POS}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Shoukat POS"; Filename: "{app}\ShoukatPOS.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Run]
Filename: "{app}\ShoukatPOS.exe"; Description: "{cm:LaunchProgram,Shoukat POS}"; Flags: nowait postinstall skipifsilent

[Code]
// Custom code for installer
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create data directory with proper permissions if needed
    // This is handled by the application on first run
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  // Add any pre-installation checks here
end;

procedure DeinitializeSetup(WasUninstalled: Boolean);
begin
  // Cleanup if needed
end;

[UninstallDelete]
; Clean up data directory on uninstall (optional - comment out to preserve data)
; Type: filesandordirs; Name: "{localappdata}\ShoukatPOS"
; Type: filesandordirs; Name: "{userdocs}\ShoukatPOS Backups"
