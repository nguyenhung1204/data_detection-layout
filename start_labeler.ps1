$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

$PythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $PythonExe)) {
    $Launcher = Get-Command py -ErrorAction SilentlyContinue
    if (-not $Launcher) { throw 'Cần cài Python 3.11 trở lên trước khi chạy.' }
    & py -3 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Không tạo được môi trường Python.' }
}
if (-not (Test-Path -LiteralPath $PythonExe)) { throw 'Không tìm thấy Python trong .venv.' }
& $PythonExe -c 'import pypdfium2' 2>$null
if ($LASTEXITCODE -ne 0) {
    & $PythonExe -m pip install --upgrade pip
    & $PythonExe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Cài thư viện thất bại.' }
}
$Port = 8767
$Existing = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($Existing) { Write-Host "App có vẻ đang chạy tại http://127.0.0.1:$Port"; Start-Process "http://127.0.0.1:$Port"; exit 0 }
Write-Host "Đang khởi động app tại http://127.0.0.1:$Port — đóng cửa sổ này để dừng app."
Start-Process "http://127.0.0.1:$Port"
& $PythonExe -m app.server
