#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location -LiteralPath $ProjectRoot

try {
    # Keep the original app and invoice paths unchanged.
    $ServerPath = Join-Path $ProjectRoot 'app\server.py'
    $RequirementsPath = Join-Path $ProjectRoot 'requirements.txt'
    $ManifestPath = Join-Path $ProjectRoot 'data\manifests\invoice_manifest.csv'
    $PdfDir = Join-Path $ProjectRoot 'data\pdfs'

    if (-not (Test-Path -LiteralPath $ServerPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $RequirementsPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $ManifestPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $PdfDir -PathType Container)) {
        throw 'Thieu file du an hoac thu muc data\pdfs. Hay dat start_labeler.ps1 vao thu muc goc da giai nen (cung cap voi app, data va requirements.txt).'
    }
    $SamplePdf = Get-ChildItem -LiteralPath $PdfDir -Filter '*.pdf' -File | Select-Object -First 1
    if (-not $SamplePdf) {
        throw 'Thu muc data\pdfs khong co file PDF. Hay kiem tra da giai nen day du du lieu hoa don.'
    }

    $Port = 8767
    $Existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @('127.0.0.1', '0.0.0.0', '::') } |
        Select-Object -First 1
    if ($Existing) {
        throw 'Cong 8767 dang duoc su dung, co the la app da mo tu thu muc cu. Hay dong cua so PowerShell/server dang chay, sau do chay lai file nay de tai dung hoa don.'
    }

    $VenvDir = Join-Path $ProjectRoot '.venv'
    $PythonExe = Join-Path $VenvDir 'Scripts\python.exe'
    $VersionCheck = 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'

    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        $Candidates = @(
            @{ Command = 'py'; Args = @('-3') },
            @{ Command = 'python'; Args = @() },
            @{ Command = 'python3'; Args = @() }
        )
        $SelectedCommand = $null
        $SelectedArgs = @()
        foreach ($Candidate in $Candidates) {
            $CommandName = $Candidate.Command
            $CommandArgs = $Candidate.Args
            if (-not (Get-Command -Name $CommandName -ErrorAction SilentlyContinue)) { continue }
            try {
                & $CommandName @CommandArgs -c $VersionCheck 2>$null
                if ($LASTEXITCODE -eq 0) {
                    $SelectedCommand = $CommandName
                    $SelectedArgs = $CommandArgs
                    break
                }
            } catch { }
        }
        if (-not $SelectedCommand) {
            throw 'Khong tim thay Python 3.11 tro len. Hay cai Python va bat tuy chon Add Python to PATH.'
        }
        Write-Host 'Dang tao moi truong Python .venv (chi lan dau)...' -ForegroundColor Cyan
        & $SelectedCommand @SelectedArgs -m venv $VenvDir
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
            throw 'Khong tao duoc moi truong Python .venv.'
        }
    }

    & $PythonExe -c $VersionCheck
    if ($LASTEXITCODE -ne 0) {
        throw 'Python trong .venv phai la 3.11 tro len.'
    }

    # Pillow is needed by pypdfium2's bitmap.to_pil() to show invoice pages.
    # Use a quiet import probe so a missing package does not crash PowerShell 5.1.
    $DependencyCheck = @'
import sys
try:
    import pypdfium2
    from PIL import Image
except Exception:
    sys.exit(1)
'@
    & $PythonExe -c $DependencyCheck
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Dang cai thu vien de hien thi anh hoa don (pypdfium2 va Pillow)...' -ForegroundColor Cyan
        & $PythonExe -m pip install -r $RequirementsPath
        if ($LASTEXITCODE -ne 0) { throw 'Cai pypdfium2 that bai.' }
        & $PythonExe -m pip install 'Pillow>=10'
        if ($LASTEXITCODE -ne 0) { throw 'Cai Pillow that bai. Kiem tra mang Internet.' }
        & $PythonExe -c $DependencyCheck
        if ($LASTEXITCODE -ne 0) { throw 'Khong import duoc pypdfium2 hoac Pillow sau khi cai.' }
    }

    $Url = "http://127.0.0.1:$Port/"
    Write-Host "Dang khoi dong app tai $Url" -ForegroundColor Green
    Write-Host 'Giu cua so PowerShell nay mo trong khi su dung. Nhan Ctrl+C de dung app.'
    Start-Process $Url
    & $PythonExe -m app.server
    if ($LASTEXITCODE -ne 0) { throw "App dung voi ma loi $LASTEXITCODE." }
}
finally {
    Pop-Location
}
