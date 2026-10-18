param([switch]$Yes, [switch]$Custom, [string]$ClaudeConfig = "", [switch]$NoClaudeCode, [switch]$NoLive)

$here = $PSScriptRoot
Set-Location $here

function Say($text) { Write-Host ""; Write-Host "== $text" -ForegroundColor Cyan }
function Ask($question) {
    if ($Yes) { return $true }
    $answer = Read-Host "$question [Y/n]"
    return ($answer -eq "" -or $answer -match "^[Yy]")
}
function Have($name) { return [bool](Get-Command $name -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User") + ";$env:USERPROFILE\.local\bin"
}
function Get-Package($id, $what) {
    if (-not (Have winget)) { return }
    Write-Host "Installing $what with winget. It may ask you to agree to its terms and to allow the installer."
    winget install -e --id $id
    Refresh-Path
}
function Find-LoopMidi {
    foreach ($p in "${env:ProgramFiles(x86)}\Tobias Erichsen\loopMIDI\loopMIDI.exe", "$env:ProgramFiles\Tobias Erichsen\loopMIDI\loopMIDI.exe") {
        if (Test-Path $p) { return $p }
    }
    return $null
}

Write-Host "kuruitsugizaki setup. Folder: $here"
if ($here -like "*\Program Files*") {
    Write-Host "This folder is under Program Files, where the server cannot write its settings and renders. Move it, for example to $env:USERPROFILE\kuruitsugizaki, and run setup again." -ForegroundColor Red
    exit 1
}

Write-Host "It installs uv and loopMIDI when they are missing, builds a Python environment in this folder, copies a controller"
Write-Host "script into FL's Settings\Hardware folder, adds a loopMIDI port named kuruitsugizaki and assigns the script to it in"
Write-Host "FL's MIDI settings. It asks again before installing ffmpeg and before touching a Claude config. INSTALL.md lists each step."
if (-not (Ask "Go on?")) { exit 0 }

Say "FL Studio"
$fl = Get-ChildItem "$env:ProgramFiles\Image-Line\FL Studio*\FL64.exe" -ErrorAction SilentlyContinue | Select-Object -Last 1
if ($fl) { Write-Host "found $($fl.FullName)" }
else { Write-Host "Not found in its usual place. Setup goes on and asks for its path below." -ForegroundColor Yellow }

Say "uv (builds the Python environment)"
if (-not (Have uv)) { Get-Package "astral-sh.uv" "uv" }
if (-not (Have uv)) {
    Write-Host "Installing uv with its own installer from astral.sh."
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    Refresh-Path
}
if (-not (Have uv)) {
    Write-Host "uv could not be installed. Install it by hand (INSTALL.md, By hand, step 2) and run setup again." -ForegroundColor Red
    exit 1
}
Write-Host "found $((Get-Command uv).Source)"

Say "Python environment (the first time this downloads about 400 MB)"
$exe = Join-Path $here ".venv\Scripts\kuruitsugizaki.exe"
if (Get-Process | Where-Object { $_.Path -eq $exe }) {
    Write-Host "The server is running (an open Claude app holds it), so its exe cannot be replaced; syncing the packages and keeping the installed server, which runs this folder's code."
    uv sync --no-install-project --inexact
}
else { uv sync }
if ($LASTEXITCODE -ne 0) {
    Write-Host "uv sync failed; the lines above say why." -ForegroundColor Red
    exit 1
}

Say "loopMIDI (the virtual MIDI port FL's script loads on)"
if (-not (Find-LoopMidi)) { Get-Package "TobiasErichsen.loopMIDI" "loopMIDI" }
if (-not (Find-LoopMidi) -and -not $Yes) {
    Start-Process "https://www.tobias-erichsen.de/software/loopmidi.html"
    Read-Host "loopMIDI's page has opened. Download and install it, then press Enter" | Out-Null
}
if (Find-LoopMidi) { Write-Host "found $(Find-LoopMidi)" }
else { Write-Host "loopMIDI is still missing; the check below will say so." -ForegroundColor Yellow }

Say "ffmpeg (analyses renders; optional)"
if ((Have ffmpeg) -and (Have ffprobe)) { Write-Host "found $((Get-Command ffmpeg).Source)" }
elseif (Ask "ffmpeg is not installed. Install it?") { Get-Package "Gyan.FFmpeg" "ffmpeg" }

if ($Custom -and -not $Yes) { Say "Paths (each shows what is set or was found; Enter keeps it)" }
else { Say "Paths (the ones found are used; setup.bat -Custom asks for each)" }
$python = Join-Path $here ".venv\Scripts\python.exe"
$paths = @("scripts\setup_paths.py")
if ($Yes -or -not $Custom) { $paths += "--yes" }
& $python @paths
function Setting($expr) { return (& $python -c "import sys; sys.path.insert(0, 'scripts'); import config; print($expr)") }

Say "FL's controller script, the loopMIDI port and FL's MIDI setting"
while ((Get-Process FL64 -ErrorAction SilentlyContinue) -and -not $Yes) {
    Read-Host "FL Studio is open, and it overwrites its MIDI settings when it closes. Save your work, close FL, then press Enter" | Out-Null
}
$doctor = @("scripts\doctor.py", "--install")
$config = $ClaudeConfig
if (-not $config) { $config = Setting "config.claude_desktop()" }
if ($ClaudeConfig -or (Test-Path (Split-Path $config))) {
    if (Ask "Add kuruitsugizaki to the Claude desktop app ($config)?") { $doctor += @("--claude", $config) }
}
else { Write-Host "The Claude desktop app was not found; for another MCP client see INSTALL.md, By hand, step 4." -ForegroundColor Yellow }
if (-not $NoLive) {
    if (Ask "Start FL at the end and check that it answers? The first start can take a minute") { $doctor += "--live" }
}
& $python @doctor
$ready = ($LASTEXITCODE -eq 0)

if (-not $NoClaudeCode -and (Have claude)) {
    $codeDir = Setting "config.load().get('claude_code_dir') or ''"
    $where = if ($codeDir) { " (profile $codeDir)" } else { "" }
    if (Ask "Claude Code is installed. Add kuruitsugizaki to it too$where?") {
        $was = $env:CLAUDE_CONFIG_DIR
        if ($codeDir) { $env:CLAUDE_CONFIG_DIR = $codeDir }
        claude mcp add --scope user kuruitsugizaki -- (Join-Path $here ".venv\Scripts\kuruitsugizaki.exe")
        $env:CLAUDE_CONFIG_DIR = $was
    }
}

Say "Result"
if ($ready) {
    Write-Host "Ready. Quit the Claude app fully (tray icon, Quit) and start it again, then in a new chat ask it to read docs/INDEX.md in this folder and write something."
}
else {
    Write-Host "Something is still missing: the lines marked MISSING above say what. INSTALL.md, When something is wrong, covers the usual cases; run setup again afterwards." -ForegroundColor Yellow
    exit 1
}
