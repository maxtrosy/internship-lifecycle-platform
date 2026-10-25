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
$expectedVolumeName = "dh05-demo-postgres-data"
$configText = & docker @composeArgs config --format json
if ($LASTEXITCODE -ne 0) { throw "Could not validate the isolated demo Compose project." }
$config = $configText | ConvertFrom-Json
$apiDatabaseUrl = [string]$config.services.api.environment.DATABASE_URL
if ($config.services.api.environment.APP_ENV -cne "demo" -or
    $apiDatabaseUrl -notmatch '^postgresql://[^@]+@db:5432/dh05_demo$' -or
    $config.services.db.environment.POSTGRES_DB -cne "dh05_demo") {
    throw "Demo safety check failed: API must target service db and database dh05_demo."
}
$volumeDefinition = $config.volumes.dh05_demo_data
$databaseMount = @($config.services.db.volumes | Where-Object {
    $_.type -eq "volume" -and $_.source -eq "dh05_demo_data" -and $_.target -eq "/var/lib/postgresql/data"
})
if (-not $volumeDefinition -or $volumeDefinition.name -cne $expectedVolumeName -or
    $volumeDefinition.external -eq $true -or $databaseMount.Count -ne 1) {
    throw "Demo safety check failed: database must use only the dedicated volume $expectedVolumeName."
}

$expectedPorts = @(
    @{ service = "db"; target = "5432"; published = "5433" },
    @{ service = "api"; target = "8000"; published = "8001" },
    @{ service = "frontend"; target = "80"; published = "5174" }
)
foreach ($expectedPort in $expectedPorts) {
    $ports = @($config.services.($expectedPort.service).ports)
    if ($ports.Count -ne 1 -or $ports[0].host_ip -cne "127.0.0.1" -or
        [string]$ports[0].target -cne $expectedPort.target -or
        [string]$ports[0].published -cne $expectedPort.published) {
        throw "Demo safety check failed: $($expectedPort.service) must publish only on its documented loopback port."
    }
}

$knownVolumeNames = @(& docker volume ls --format "{{.Name}}")
if ($LASTEXITCODE -ne 0) { throw "Could not verify ownership of the isolated demo volume." }
if ($knownVolumeNames -contains $expectedVolumeName) {
    $volumeLabelsText = & docker volume inspect $expectedVolumeName --format "{{json .Labels}}"
    if ($LASTEXITCODE -ne 0) { throw "Could not verify ownership of the isolated demo volume." }
    $volumeLabels = $volumeLabelsText | ConvertFrom-Json
    if ($volumeLabels.'com.docker.compose.project' -cne "dh05-demo" -or
        $volumeLabels.'com.docker.compose.volume' -cne "dh05_demo_data") {
        throw "Demo safety check failed: existing volume is not owned by the dh05-demo Compose project."
    }
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
$expectedUsernames = "dual1,ec1,f1,hm_alfa,hm_beta,legal1,pc_adm,pc_sys,s1,s2,s3,ws_alfa,ws_alfa2,ws_beta"
if ($accountCount -eq 0) {
    & docker @composeArgs exec -T api python -m app.demo_seed
    if ($LASTEXITCODE -ne 0) { throw "Demo seed refused or failed; see the API output above." }
} else {
    if ($accountCount -ne 14) {
        throw "Demo database has $accountCount accounts, expected 0 or the exact 14-account demo seed. No seed or cleanup was attempted."
    }
    $actualUsernames = & docker @composeArgs exec -T db psql -U postgres -d dh05_demo -Atqc "SELECT string_agg(username, ',' ORDER BY username) FROM user_account"
    if ($LASTEXITCODE -ne 0) { throw "Could not verify the demo account set." }
    if (([string]$actualUsernames).Trim() -cne $expectedUsernames) {
        throw "Demo database does not contain the expected synthetic account set. No seed or cleanup was attempted."
    }
    Write-Host "Expected 14 demo accounts found; current dataset preserved. Use -Reset when a clean dataset is needed."
}

Write-Host "Demo is ready: http://localhost:5174 (API http://localhost:8001)."
Write-Host "Target verified by Compose and the seed guard: db/dh05_demo; local project: dh05-demo."
