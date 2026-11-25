# Run from a normal PowerShell after Docker Desktop is installed and running.
# Does not install software, change Windows features, or accept license terms.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = $PSScriptRoot
$runName = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$evidenceRoot = Join-Path $projectRoot "docker-evidence/$runName"
New-Item -ItemType Directory -Force -Path $evidenceRoot | Out-Null
$logPath = Join-Path $evidenceRoot 'docker.log'
$reportPath = Join-Path $evidenceRoot 'result.json'
Set-Content -LiteralPath $logPath -Value "Docker verification started: $runName" -Encoding UTF8
$report = [ordered]@{status='RUNNING'; startedAt=(Get-Date).ToString('o'); checks=@(); error=$null}
$environmentBackup = @{}
$variableValues = @{
    DOTA_API_PORT='18000'; DOTA_FRONTEND_PORT='18501'; DOTA_MLFLOW_PORT='15000'
    DOTA_MODELS_DIR='./docker-state/models'; DOTA_TRACKING_DIR='./docker-state/tracking'; DOTA_MLRUNS_DIR='./docker-state/mlruns'
}

function Save-Report {
    $report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}

function Invoke-Docker {
    param([string[]]$DockerArguments)
    # Windows PowerShell 5 may represent native stderr as ErrorRecords even on success.
    # The exit code, rather than the stream used by Docker progress, is authoritative.
    $ErrorActionPreference = 'Continue'
    & $script:dockerPath @DockerArguments 2>&1 | Tee-Object -FilePath $logPath -Append | Out-Host
    $nativeExitCode = $LASTEXITCODE
    if ($nativeExitCode -ne 0) { throw "docker exited with code $nativeExitCode; see $logPath" }
}

function Invoke-Compose {
    param([string[]]$ComposeArguments)
    Invoke-Docker -DockerArguments (@('compose', '--project-name', 'dota-course-verify', '--project-directory', $projectRoot, '-f', (Join-Path $projectRoot 'compose.yaml')) + $ComposeArguments)
}

try {
    Save-Report
    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
    $dockerPath = if ($dockerCommand) { $dockerCommand.Source } else { $null }
    if (-not $dockerPath) {
        foreach ($candidate in @(
            (Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/resources/bin/docker.exe'),
            'C:/Program Files/Docker/Docker/resources/bin/docker.exe'
        )) {
            if (Test-Path -LiteralPath $candidate) { $dockerPath = $candidate; break }
        }
    }
    if (-not $dockerPath) {
        $report.status = 'BLOCKED'
        throw 'Docker Desktop is not installed. Follow DOCKER-SETUP.md, then run this script again.'
    }
    $osType = & $dockerPath info --format '{{.OSType}}' 2>$null
    if ($LASTEXITCODE -ne 0 -or $osType -ne 'linux') {
        $report.status = 'BLOCKED'
        throw 'Docker Engine is not ready for Linux containers. Start Docker Desktop and wait for Engine running.'
    }
    Invoke-Docker -DockerArguments @('version')
    Invoke-Docker -DockerArguments @('compose', 'version')
    foreach ($name in $variableValues.Keys) {
        $environmentBackup[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $variableValues[$name], 'Process')
    }
    foreach ($folder in @('models','tracking','mlruns')) {
        New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot "docker-state/$folder") | Out-Null
    }
    Invoke-Compose -ComposeArguments @('config', '--quiet')
    Invoke-Compose -ComposeArguments @('build', 'api')
    $report.checks += 'Docker image built successfully'
    Invoke-Compose -ComposeArguments @('run', '--rm', 'train')
    Invoke-Compose -ComposeArguments @('run', '--rm', 'train-early')
    $report.checks += 'Both models trained and registered inside Linux containers'
    Invoke-Compose -ComposeArguments @('up', '-d', 'api', 'frontend', 'mlflow')

    $ready = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        try {
            $health = Invoke-RestMethod 'http://127.0.0.1:18000/early/health' -TimeoutSec 5
            if ($health.status -eq 'ready') { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) { throw 'Container API did not become ready within the startup deadline.' }
    $root = Invoke-RestMethod 'http://127.0.0.1:18000/' -TimeoutSec 10
    if (-not $root.model_loaded -or -not $root.early_model_loaded) { throw 'Both models must be loaded.' }
    foreach ($endpoint in @('http://127.0.0.1:18000/docs','http://127.0.0.1:18501','http://127.0.0.1:15000')) {
        if ((Invoke-WebRequest $endpoint -UseBasicParsing -TimeoutSec 30).StatusCode -ne 200) { throw "HTTP check failed: $endpoint" }
    }
    $meta = Invoke-RestMethod 'http://127.0.0.1:18000/early/metadata' -TimeoutSec 10
    $body = $meta.examples[0] | ConvertTo-Json -Depth 6
    $prediction = Invoke-RestMethod 'http://127.0.0.1:18000/predict/early' -Method Post -ContentType application/json -Body $body -TimeoutSec 30
    if ([Math]::Abs($prediction.radiant_probability + $prediction.dire_probability - 1) -gt 0.000001) { throw 'Prediction probabilities do not sum to 1.' }
    $report.checks += 'Container API root, both loaded models, Swagger, frontend HTTP, MLflow HTTP and live early prediction passed'
    Invoke-Compose -ComposeArguments @('exec', '-T', 'api', 'python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider')
    $report.checks += 'Full API and feature test suite passed inside the API container'
    $uiCode = @'
from streamlit.testing.v1 import AppTest
at = AppTest.from_file('/app/frontend.py').run(timeout=60)
assert not at.exception
assert at.button(key='early_predict').disabled
at.button(key='early_load').click().run(timeout=30)
assert not at.exception and not at.button(key='early_predict').disabled
at.button(key='early_predict').click().run(timeout=30)
assert not at.exception and len(at.metric) == 2
print('Container frontend -> container API prediction:', [x.value for x in at.metric])
'@
    Invoke-Compose -ComposeArguments @('exec', '-T', 'frontend', 'python', '-c', $uiCode)
    $report.checks += 'Streamlit AppTest executed real frontend-to-API inference inside containers'
    $registryCode = @'
from mlflow import MlflowClient
c = MlflowClient(tracking_uri='sqlite:////app/tracking/mlflow.db')
for name in ['DotaDraftClassifier', 'DotaMinuteFiveClassifier']:
    version = c.get_model_version_by_alias(name, 'champion')
    assert version.status == 'READY'
    assert c.get_run(version.run_id).info.status == 'FINISHED'
    print(name, version.version, version.status)
'@
    Invoke-Compose -ComposeArguments @('exec', '-T', 'mlflow', 'python', '-c', $registryCode)
    $report.checks += 'Both champion models READY in the container-backed MLflow registry'
    Invoke-Compose -ComposeArguments @('ps')
    $report.status = 'PASSED'
    $report.prediction = $prediction
    $report.urls = @{api='http://127.0.0.1:18000/docs'; frontend='http://127.0.0.1:18501'; mlflow='http://127.0.0.1:15000'}
    Write-Host "Docker verification PASSED. Evidence: $evidenceRoot"
    Write-Host 'Containers remain running. Native services on 8000/8501/5000 were not changed.'
} catch {
    if ($report.status -ne 'BLOCKED') { $report.status = 'FAILED' }
    $report.error = $_.Exception.Message
    Write-Error $_ -ErrorAction Continue
} finally {
    $report.completedAt = (Get-Date).ToString('o')
    Save-Report
    foreach ($name in $environmentBackup.Keys) {
        [Environment]::SetEnvironmentVariable($name, $environmentBackup[$name], 'Process')
    }
}
if ($report.status -ne 'PASSED') { exit 1 }
