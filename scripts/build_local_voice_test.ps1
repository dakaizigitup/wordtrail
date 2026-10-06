$ErrorActionPreference='Stop'
$qjSource='D:\codex-mobile-build\source'
$qjSdk='D:\codex-mobile-build\sdk'
$qjTools=Join-Path $qjSdk 'build-tools\35.0.0'
$qjJar=Join-Path $qjSdk 'platforms\android-35\android.jar'
$qjBuild=Join-Path $qjSource 'build\local-voice-test'
$qjToolchain=Get-ChildItem -LiteralPath 'D:\soft' -Directory | ForEach-Object { Join-Path $_.FullName 'mobile-toolchain' } | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'toolchain.json') } | Select-Object -First 1
if(-not $qjToolchain){throw 'Wordtrail mobile-toolchain was not found under D:\soft'}
$qjSigningKey=Join-Path $qjToolchain 'wordtrail-debug.keystore'
if(-not (Test-Path -LiteralPath $qjSigningKey)){throw 'Wordtrail development signing key is missing'}
$env:JAVA_HOME='D:\codex-mobile-build\jdk'
$env:Path=$env:JAVA_HOME+'\bin;'+$env:Path
function Run([string]$Exe,[string[]]$Values){& $Exe @Values;if($LASTEXITCODE -ne 0){throw $Exe}}
New-Item -ItemType Directory -Path (Join-Path $qjBuild 'classes'),(Join-Path $qjBuild 'dex') -Force | Out-Null
Run (Join-Path $qjTools 'aapt2.exe') @('link','-I',$qjJar,'--manifest',(Join-Path $qjSource 'tests\local-voice\AndroidManifest.xml'),'-o',(Join-Path $qjBuild 'base.apk'))
Run 'javac' @('-encoding','UTF-8','-source','17','-target','17','-classpath',$qjJar,'-d',(Join-Path $qjBuild 'classes'),(Join-Path $qjSource 'tests\local-voice\LocalVoiceProbe.java'))
$qjClasses=@(Get-ChildItem -LiteralPath (Join-Path $qjBuild 'classes') -Recurse -Filter '*.class' | ForEach-Object {$_.FullName})
Run (Join-Path $qjTools 'd8.bat') (@('--lib',$qjJar,'--min-api','26','--output',(Join-Path $qjBuild 'dex'))+$qjClasses)
Run 'python' @('-c',"import zipfile; p=r'$qjBuild'; z=zipfile.ZipFile(p+'/base.apk','a'); z.write(p+'/dex/classes.dex','classes.dex',zipfile.ZIP_DEFLATED); z.write(r'$qjSource/build/voice-model/test_wavs/zh.wav','assets/zh.wav'); z.write(r'$qjSource/build/voice-model/test_wavs/en.wav','assets/en.wav'); z.close()")
Run (Join-Path $qjTools 'zipalign.exe') @('-f','4',(Join-Path $qjBuild 'base.apk'),(Join-Path $qjBuild 'aligned.apk'))
Run (Join-Path $qjTools 'apksigner.bat') @('sign','--ks',$qjSigningKey,'--ks-pass','pass:android','--key-pass','pass:android','--ks-key-alias','wordtrail','--out',(Join-Path $qjBuild 'local-voice-test.apk'),(Join-Path $qjBuild 'aligned.apk'))
