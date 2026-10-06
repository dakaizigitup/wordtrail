param([string]$InstallDirectory='C:\Program Files\Qingjian',[switch]$Rollback)
$ErrorActionPreference='Stop'
$qjResult=Join-Path $PSScriptRoot 'install-result.json'
$qjPrincipal=[Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if(-not $qjPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
    $qjArgs=@('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-InstallDirectory',('"'+$InstallDirectory+'"'))
    if($Rollback){$qjArgs+='-Rollback'}
    try{$qjElevated=Start-Process -FilePath 'powershell.exe' -ArgumentList $qjArgs -Verb RunAs -WindowStyle Hidden -PassThru;$qjElevated.WaitForExit();exit $qjElevated.ExitCode}
    catch{@{ok=$false;error=$_.Exception.Message;needs_administrator=$true}|ConvertTo-Json|Set-Content -LiteralPath $qjResult -Encoding UTF8;exit 1}
}
$qjInstall=(Resolve-Path -LiteralPath $InstallDirectory).Path
$qjServer=Join-Path $qjInstall 'qingjian-server.exe'
$qjIpa=Join-Path $qjInstall 'data\pronunciation-en.qj'
$qjDictionary=Join-Path $qjInstall 'data\generated\dict.qj'
$qjBackup=Join-Path $PSScriptRoot 'backup'
$qjManifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'SHA256.json') -Raw|ConvertFrom-Json
function Stop-QjServer {
    Get-CimInstance Win32_Process -Filter "Name = 'qingjian-server.exe'"|Where-Object{$_.ExecutablePath -eq $qjServer}|ForEach-Object{
        $qjRunning=[Diagnostics.Process]::GetProcessById($_.ProcessId)
        $qjRunning.Kill()
        if(-not $qjRunning.WaitForExit(10000)){throw 'Server did not stop within 10 seconds'}
        $qjRunning.Dispose()
    }
}
function Start-QjServer {
    $qjProcess=Start-Process -FilePath $qjServer -WorkingDirectory $qjInstall -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 3
    if(-not $qjProcess.HasExited){return $qjProcess.Id}
    # A connected TSF client may have already restarted the installed server.
    $qjExisting=Get-CimInstance Win32_Process -Filter "Name = 'qingjian-server.exe'"|Where-Object{$_.ExecutablePath -eq $qjServer}|Select-Object -First 1
    if($qjExisting){return $qjExisting.ProcessId}
    throw 'Updated server did not remain running'
}
try{
    if(-not(Test-Path -LiteralPath $qjServer -PathType Leaf)){throw 'Install Qingjian Windows 0.1.4 first'}
    if($Rollback){
        if(-not(Test-Path -LiteralPath (Join-Path $qjBackup 'qingjian-server.exe'))){throw 'No backup is available'}
        if(-not(Test-Path -LiteralPath (Join-Path $qjBackup 'dict.qj'))){throw 'No dictionary backup is available'}
        Stop-QjServer
        Copy-Item -LiteralPath (Join-Path $qjBackup 'qingjian-server.exe') -Destination $qjServer -Force
        if(Test-Path -LiteralPath (Join-Path $qjBackup 'pronunciation-en.qj')){Copy-Item -LiteralPath (Join-Path $qjBackup 'pronunciation-en.qj') -Destination $qjIpa -Force}
        elseif(Test-Path -LiteralPath $qjIpa){Remove-Item -LiteralPath $qjIpa}
        Copy-Item -LiteralPath (Join-Path $qjBackup 'dict.qj') -Destination $qjDictionary -Force
    }else{
        foreach($qjFile in @('qingjian-server.exe','pronunciation-en.qj','dict.qj')){
            $qjPayload=Join-Path $PSScriptRoot $qjFile
            if((Get-FileHash -LiteralPath $qjPayload -Algorithm SHA256).Hash.ToLowerInvariant() -ne $qjManifest.artifacts.$qjFile.sha256){throw ('Payload checksum mismatch: '+$qjFile)}
        }
        if(-not(Test-Path -LiteralPath $qjDictionary -PathType Leaf)){throw 'Installed Qingjian dictionary is missing'}
        $qjCurrentDictionary=(Get-FileHash -LiteralPath $qjDictionary -Algorithm SHA256).Hash.ToLowerInvariant()
        if($qjCurrentDictionary -ne $qjManifest.original_dictionary_sha256 -and $qjCurrentDictionary -ne $qjManifest.artifacts.'dict.qj'.sha256 -and $qjManifest.supported_previous_dictionary_sha256 -notcontains $qjCurrentDictionary){throw 'Installed dictionary differs from the supported Qingjian or Wordtrail build'}
        $qjCurrent=(Get-FileHash -LiteralPath $qjServer -Algorithm SHA256).Hash.ToLowerInvariant()
        if($qjCurrent -ne $qjManifest.original_server_sha256 -and $qjCurrent -ne $qjManifest.artifacts.'qingjian-server.exe'.sha256 -and $qjManifest.supported_previous_server_sha256 -notcontains $qjCurrent){throw 'Installed server differs from the supported Qingjian 0.1.4 or Wordtrail patch build'}
        New-Item -ItemType Directory -Path $qjBackup -Force|Out-Null
        if(-not(Test-Path -LiteralPath (Join-Path $qjBackup 'qingjian-server.exe'))){Copy-Item -LiteralPath $qjServer -Destination (Join-Path $qjBackup 'qingjian-server.exe');if(Test-Path -LiteralPath $qjIpa){Copy-Item -LiteralPath $qjIpa -Destination (Join-Path $qjBackup 'pronunciation-en.qj')}}
        if(-not(Test-Path -LiteralPath (Join-Path $qjBackup 'pronunciation-en.qj')) -and (Test-Path -LiteralPath $qjIpa)){Copy-Item -LiteralPath $qjIpa -Destination (Join-Path $qjBackup 'pronunciation-en.qj')}
        if(-not(Test-Path -LiteralPath (Join-Path $qjBackup 'dict.qj'))){Copy-Item -LiteralPath $qjDictionary -Destination (Join-Path $qjBackup 'dict.qj')}
        Stop-QjServer
        try{Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'qingjian-server.exe') -Destination $qjServer -Force;Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'pronunciation-en.qj') -Destination $qjIpa -Force;Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'dict.qj') -Destination $qjDictionary -Force}
        catch{Copy-Item -LiteralPath (Join-Path $qjBackup 'qingjian-server.exe') -Destination $qjServer -Force;Copy-Item -LiteralPath (Join-Path $qjBackup 'dict.qj') -Destination $qjDictionary -Force;if(Test-Path -LiteralPath (Join-Path $qjBackup 'pronunciation-en.qj')){Copy-Item -LiteralPath (Join-Path $qjBackup 'pronunciation-en.qj') -Destination $qjIpa -Force}elseif(Test-Path -LiteralPath $qjIpa){Remove-Item -LiteralPath $qjIpa};Start-QjServer|Out-Null;throw}
    }
    try{$qjStarted=Start-QjServer}
    catch{
        $qjStartupError=$_.Exception.Message
        if(-not $Rollback){
            Stop-QjServer
            Copy-Item -LiteralPath (Join-Path $qjBackup 'qingjian-server.exe') -Destination $qjServer -Force
            Copy-Item -LiteralPath (Join-Path $qjBackup 'dict.qj') -Destination $qjDictionary -Force
            if(Test-Path -LiteralPath (Join-Path $qjBackup 'pronunciation-en.qj')){Copy-Item -LiteralPath (Join-Path $qjBackup 'pronunciation-en.qj') -Destination $qjIpa -Force}
            elseif(Test-Path -LiteralPath $qjIpa){Remove-Item -LiteralPath $qjIpa}
            Start-QjServer|Out-Null
        }
        throw $qjStartupError
    }
    @{ok=$true;rollback=[bool]$Rollback;process_id=$qjStarted;server=$qjServer;sha256=(Get-FileHash -LiteralPath $qjServer -Algorithm SHA256).Hash.ToLowerInvariant();dictionary_sha256=(Get-FileHash -LiteralPath $qjDictionary -Algorithm SHA256).Hash.ToLowerInvariant();user_data_unchanged=$true}|ConvertTo-Json|Set-Content -LiteralPath $qjResult -Encoding UTF8
}catch{@{ok=$false;error=$_.Exception.Message}|ConvertTo-Json|Set-Content -LiteralPath $qjResult -Encoding UTF8;exit 1}
