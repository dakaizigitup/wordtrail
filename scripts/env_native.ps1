$qjTools=Get-ChildItem -LiteralPath 'D:\soft' -Directory | ForEach-Object { Join-Path $_.FullName 'mobile-toolchain' } | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'toolchain.json') } | Select-Object -First 1
if(-not $qjTools){throw 'Wordtrail mobile-toolchain was not found under D:\soft'}
$env:RUSTUP_HOME=Join-Path $qjTools 'rustup'
$env:CARGO_HOME=Join-Path $qjTools 'cargo'
$qjLlvm=(Get-ChildItem -LiteralPath (Join-Path $qjTools 'llvm-mingw-msvcrt') -Directory | Select-Object -First 1).FullName
$env:Path=(Join-Path $env:CARGO_HOME 'bin')+';'+(Join-Path $qjLlvm 'bin')+';'+$env:Path
$env:CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER=Join-Path $qjTools 'host-link.cmd'
$env:PYTHONIOENCODING='utf-8'
python (Join-Path $PSScriptRoot 'apply_upstream.py')
if($LASTEXITCODE -ne 0){throw 'Upstream overlay validation failed'}
