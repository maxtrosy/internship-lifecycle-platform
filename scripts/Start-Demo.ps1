[CmdletBinding()]
param(
    [switch]$Reset
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$composeFile = Join-Path $repoRoot "docker-compose.demo.yml"
if (-not (Test-Path -LiteralPath $composeFile)) {
    throw "Demo Compose file not found: $composeFile"
}

$composeArgs = @("compose", "-p", "dh05-demo", "-f", $composeFile)
$configText = & docker @composeArgs config --format json
if ($LASTEXITCODE -ne 0) { throw "Could not validate the isolated demo Compose project." }
$config = $configText | ConvertFrom-Json
$apiDatabaseUrl = [string]$config.services.api.environment.DATABASE_URL
if ($apiDatabaseUrl -notmatch '^postgresql://[^@]+@db:5432/dh05_demo$') {
    throw "Demo safety check failed: API must target service db and database dh05_demo."
}
if (-not $config.services.db.volumes -or -not $config.volumes.dh05_demo_data) {
    throw "Demo safety check failed: isolated named database volume is missing."
}

if ($Reset) {
    $confirmation = Read-Host "This removes only project dh05-demo and its named demo volume. Type RESET DH05 DEMO to continue"
    if ($confirmation -cne "RESET DH05 DEMO") {
        throw "Reset cancelled; no demo data was removed."
    }
    & docker @composeArgs down --volumes --remove-orphans
    if ($LASTEXITCODE -ne 0) { throw "Could not stop/reset the isolated demo project." }
}

& docker @composeArgs up --build --detach
if ($LASTEXITCODE -ne 0) { throw "Could not start the isolated demo project." }

$deadline = (Get-Date).AddSeconds(120)
do {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8001/health" -TimeoutSec 3
        if ($health.status -eq "ok") { break }
    } catch {
        Start-Sleep -Seconds 2
    }
} while ((Get-Date) -lt $deadline)
if (-not $health -or $health.status -ne "ok") {
    throw "Demo API did not become healthy. Inspect: docker compose -p dh05-demo -f docker-compose.demo.yml logs api"
}

$accountCountText = & docker @composeArgs exec -T db psql -U postgres -d dh05_demo -Atqc "SELECT count(*) FROM user_account"
if ($LASTEXITCODE -ne 0) { throw "Could not inspect the isolated demo database." }
$accountCount = [int]([string]$accountCountText).Trim()
if ($accountCount -eq 0) {
    & docker @composeArgs exec -T api python -m app.demo_seed
    if ($LASTEXITCODE -ne 0) { throw "Demo seed refused or failed; see the API output above." }
} elseif ($accountCount -ne 14) {
    throw "Demo database has $accountCount accounts, expected 0 or 14. No seed or cleanup was attempted."
} else {
    Write-Host "Existing clean demo accounts found; seed skipped."
}

Write-Host "Demo is ready: http://localhost:5174 (API http://localhost:8001)."
Write-Host "Target verified by Compose and the seed guard: db/dh05_demo; local project: dh05-demo."
