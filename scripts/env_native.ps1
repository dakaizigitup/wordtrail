$qjTools='D:\soft\英语输入法\mobile-toolchain'
$qjConfig=Get-Content -LiteralPath (Join-Path $qjTools 'toolchain.json') -Raw | ConvertFrom-Json
$env:RUSTUP_HOME=$qjConfig.rustup_home
$env:CARGO_HOME=$qjConfig.cargo_home
$qjLlvm=(Get-ChildItem -LiteralPath (Join-Path $qjTools 'llvm-mingw-msvcrt') -Directory | Select-Object -First 1).FullName
$env:Path=(Join-Path $env:CARGO_HOME 'bin')+';'+(Join-Path $qjLlvm 'bin')+';'+$env:Path
$env:CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER=Join-Path $qjTools 'host-link.cmd'
$env:PYTHONIOENCODING='utf-8'
python (Join-Path $PSScriptRoot 'apply_upstream.py')
if($LASTEXITCODE -ne 0){throw 'Upstream overlay validation failed'}
