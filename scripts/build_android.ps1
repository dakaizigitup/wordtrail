param(
    [string]$ToolchainDirectory='D:\soft\英语输入法\mobile-toolchain',
    [string[]]$Abis=@('arm64-v8a','x86_64'),
    [string]$AsciiBuildDirectory='D:\codex-mobile-build'
)
$ErrorActionPreference='Stop'
$qjRoot=Split-Path $PSScriptRoot -Parent
$qjConfig=Get-Content -LiteralPath (Join-Path $ToolchainDirectory 'toolchain.json') -Raw -Encoding UTF8 | ConvertFrom-Json
# Some Android SDK Windows binaries cannot open Chinese paths. Junctions keep
# all original files in place while giving those tools ASCII input/output paths.
function Get-QjAsciiAlias([string]$Name,[string]$Target) {
    New-Item -ItemType Directory -Path $AsciiBuildDirectory -Force | Out-Null
    $aliasPath=Join-Path $AsciiBuildDirectory $Name
    if(Test-Path -LiteralPath $aliasPath) {
        $existing=Get-Item -LiteralPath $aliasPath
        if($existing.LinkType -ne 'Junction' -or [string]$existing.Target -ne $Target) {
            throw ('Build alias already exists with a different target: '+$aliasPath)
        }
    } else { New-Item -ItemType Junction -Path $aliasPath -Target $Target | Out-Null }
    return $aliasPath
}
$qjRoot=Get-QjAsciiAlias 'source' $qjRoot
$qjConfig.sdk_root=Get-QjAsciiAlias 'sdk' $qjConfig.sdk_root
$qjConfig.java_home=Get-QjAsciiAlias 'jdk' $qjConfig.java_home
$env:JAVA_HOME=$qjConfig.java_home
$env:ANDROID_HOME=$qjConfig.sdk_root
$env:RUSTUP_HOME=$qjConfig.rustup_home
$env:CARGO_HOME=$qjConfig.cargo_home
$qjLlvm=(Get-ChildItem -LiteralPath (Join-Path $ToolchainDirectory 'llvm-mingw-msvcrt') -Directory | Select-Object -First 1).FullName
$env:Path=(Join-Path $env:JAVA_HOME 'bin')+';'+(Join-Path $env:CARGO_HOME 'bin')+';'+(Join-Path $qjLlvm 'bin')+';'+$env:Path
$env:CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER=Join-Path $ToolchainDirectory 'host-link.cmd'
$qjNdkBin=Join-Path $env:ANDROID_HOME ('ndk\'+$qjConfig.ndk_version+'\toolchains\llvm\prebuilt\windows-x86_64\bin')
$qjBuild=Join-Path $qjRoot 'build\android'
$qjTools=Join-Path $env:ANDROID_HOME 'build-tools\35.0.0'
$qjJar=Join-Path $env:ANDROID_HOME 'platforms\android-35\android.jar'
function Invoke-QjTool([string]$Executable,[string[]]$Arguments) {
    & $Executable @Arguments
    if($LASTEXITCODE -ne 0){throw ('Build tool failed: '+$Executable)}
}
Push-Location $qjRoot
try {
    Invoke-QjTool 'python' @((Join-Path $PSScriptRoot 'apply_upstream.py'))
    Invoke-QjTool 'python' @((Join-Path $PSScriptRoot 'prepare_data.py'),'--source',(Join-Path $qjRoot 'data'))
    Invoke-QjTool 'python' @((Join-Path $PSScriptRoot 'prepare_voice.py'))
    foreach($qjAbi in $Abis){
        if($qjAbi -eq 'arm64-v8a'){$qjTarget='aarch64-linux-android';$qjCompiler='aarch64-linux-android26-clang.cmd'}
        elseif($qjAbi -eq 'x86_64'){$qjTarget='x86_64-linux-android';$qjCompiler='x86_64-linux-android26-clang.cmd'}
        else{throw ('Unsupported ABI: '+$qjAbi)}
        $qjEnvKey='CARGO_TARGET_'+($qjTarget.ToUpperInvariant() -replace '-','_')+'_LINKER'
        Set-Item -Path ('Env:\'+$qjEnvKey) -Value (Join-Path $qjNdkBin $qjCompiler)
        $env:RUSTFLAGS='-C link-arg=-Wl,-z,max-page-size=16384'
        Invoke-QjTool 'cargo' @('build','--release','--locked','-p','wordtrail-mobile','--target',$qjTarget)
        $qjJniDir=Join-Path $qjRoot ('android\app\src\main\jniLibs\'+$qjAbi)
        New-Item -ItemType Directory -Path $qjJniDir -Force | Out-Null
        Copy-Item -LiteralPath (Join-Path $qjRoot ('target\'+$qjTarget+'\release\libwordtrail_mobile.so')) -Destination $qjJniDir
        $qjVoiceCompiler=Join-Path $qjNdkBin ($qjCompiler -replace '-clang.cmd','-clang++.cmd')
        Invoke-QjTool $qjVoiceCompiler @('-std=c++17','-shared','-fPIC','-O2','-static-libstdc++','-Wl,-z,max-page-size=16384',('-I'+(Join-Path $qjRoot 'third-party\sherpa-onnx')),(Join-Path $qjRoot 'android\voice\local_voice.cpp'),('-L'+$qjJniDir),'-lsherpa-onnx-c-api','-o',(Join-Path $qjJniDir 'libwordtrail_voice.so'))
    }
    foreach($qjSub in @('generated','classes','dex')){New-Item -ItemType Directory -Path (Join-Path $qjBuild $qjSub) -Force | Out-Null}
    $qjRes=Join-Path $qjRoot 'android\app\src\main\res'
    Invoke-QjTool (Join-Path $qjTools 'aapt2.exe') @('compile','--dir',$qjRes,'-o',(Join-Path $qjBuild 'resources.zip'))
    Invoke-QjTool (Join-Path $qjTools 'aapt2.exe') @('link','-I',$qjJar,'--manifest',(Join-Path $qjRoot 'android\app\src\main\AndroidManifest.xml'),'--java',(Join-Path $qjBuild 'generated'),'-o',(Join-Path $qjBuild 'base.apk'),'--version-code','43','--version-name','0.1.42',(Join-Path $qjRoot 'build\android\resources.zip'))
    $qjJavaFiles=@(Get-ChildItem -LiteralPath (Join-Path $qjRoot 'android\app\src\main\java'),(Join-Path $qjBuild 'generated') -Recurse -Filter '*.java' | ForEach-Object {$_.FullName})
    Invoke-QjTool 'javac' (@('-encoding','UTF-8','-source','17','-target','17','-classpath',$qjJar,'-d',(Join-Path $qjBuild 'classes'))+$qjJavaFiles)
    $qjClasses=@(Get-ChildItem -LiteralPath (Join-Path $qjBuild 'classes') -Recurse -Filter '*.class' | ForEach-Object {$_.FullName})
    Invoke-QjTool (Join-Path $qjTools 'd8.bat') (@('--lib',$qjJar,'--min-api','26','--output',(Join-Path $qjBuild 'dex'))+$qjClasses)
    Invoke-QjTool 'python' @((Join-Path $qjRoot 'scripts\package_apk.py'))
    Invoke-QjTool (Join-Path $qjTools 'zipalign.exe') @('-P','16','-f','4',(Join-Path $qjBuild 'unsigned.apk'),(Join-Path $qjBuild 'aligned.apk'))
    $qjKey=Join-Path $ToolchainDirectory 'wordtrail-debug.keystore'
    if(!(Test-Path -LiteralPath $qjKey)){
        Invoke-QjTool 'keytool' @('-genkeypair','-keystore',$qjKey,'-storepass','android','-keypass','android','-alias','wordtrail','-keyalg','RSA','-keysize','2048','-validity','10000','-dname','CN=Wordtrail Development,O=Local Development,C=CN')
    }
    $qjDist=Join-Path $qjRoot 'dist'
    New-Item -ItemType Directory -Path $qjDist -Force | Out-Null
    $qjApk=Join-Path $qjDist 'wordtrail-0.1.42-debug.apk'
    Invoke-QjTool (Join-Path $qjTools 'apksigner.bat') @('sign','--ks',$qjKey,'--ks-pass','pass:android','--ks-key-alias','wordtrail','--out',$qjApk,(Join-Path $qjBuild 'aligned.apk'))
    Invoke-QjTool (Join-Path $qjTools 'apksigner.bat') @('verify','--verbose',$qjApk)
    Invoke-QjTool (Join-Path $qjTools 'zipalign.exe') @('-c','-P','16','4',$qjApk)
    Get-FileHash -LiteralPath $qjApk -Algorithm SHA256
} finally {Pop-Location}
