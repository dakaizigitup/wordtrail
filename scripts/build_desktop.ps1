$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
. (Join-Path $PSScriptRoot 'env_native.ps1')
python scripts/prepare_data.py
if($LASTEXITCODE -ne 0){throw 'Data preparation failed'}
cargo build --locked --offline -p wordtrail-windows-server --release
if($LASTEXITCODE -ne 0){throw 'Desktop build failed'}
Write-Output 'Built target/release/qingjian-server.exe. Package only after runtime validation.'
