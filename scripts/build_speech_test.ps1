$ErrorActionPreference='Stop'
$speechSource='D:\codex-mobile-build\source'
$speechSdk='D:\codex-mobile-build\sdk'
$speechTools=Join-Path $speechSdk 'build-tools\35.0.0'
$speechJar=Join-Path $speechSdk 'platforms\android-35\android.jar'
$speechBuild=Join-Path $speechSource 'build\speech-test'
$env:JAVA_HOME='D:\codex-mobile-build\jdk'
$env:Path=$env:JAVA_HOME+'\bin;'+$env:Path
function Invoke-SpeechTestTool([string]$Exe,[string[]]$Values){& $Exe @Values; if($LASTEXITCODE -ne 0){throw $Exe}}
New-Item -ItemType Directory -Path (Join-Path $speechBuild 'classes'),(Join-Path $speechBuild 'dex') -Force | Out-Null
Invoke-SpeechTestTool (Join-Path $speechTools 'aapt2.exe') @('link','-I',$speechJar,'--manifest',(Join-Path $speechSource 'tests\speech-service\AndroidManifest.xml'),'-o',(Join-Path $speechBuild 'base.apk'))
$speechJava=@(Get-ChildItem -LiteralPath (Join-Path $speechSource 'tests\speech-service') -Filter '*.java' | ForEach-Object {$_.FullName})
Invoke-SpeechTestTool 'javac' (@('-encoding','UTF-8','-source','17','-target','17','-classpath',$speechJar,'-d',(Join-Path $speechBuild 'classes'))+$speechJava)
$speechClasses=@(Get-ChildItem -LiteralPath (Join-Path $speechBuild 'classes') -Recurse -Filter '*.class' | ForEach-Object {$_.FullName})
Invoke-SpeechTestTool (Join-Path $speechTools 'd8.bat') (@('--lib',$speechJar,'--min-api','26','--output',(Join-Path $speechBuild 'dex'))+$speechClasses)
Invoke-SpeechTestTool 'python' @('-c',"import zipfile; p=r'$speechBuild'; z=zipfile.ZipFile(p+'/base.apk','a'); z.write(p+'/dex/classes.dex','classes.dex',zipfile.ZIP_DEFLATED); z.close()")
Invoke-SpeechTestTool (Join-Path $speechTools 'zipalign.exe') @('-f','4',(Join-Path $speechBuild 'base.apk'),(Join-Path $speechBuild 'aligned.apk'))
Invoke-SpeechTestTool (Join-Path $speechTools 'apksigner.bat') @('sign','--ks','D:\soft\英语输入法\mobile-toolchain\wordtrail-debug.keystore','--ks-pass','pass:android','--ks-key-alias','wordtrail','--out',(Join-Path $speechBuild 'speech-test.apk'),(Join-Path $speechBuild 'aligned.apk'))
