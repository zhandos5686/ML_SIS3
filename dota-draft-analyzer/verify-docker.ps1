# Run from a normal PowerShell after Docker Desktop is installed and running.
# Does not install software, change Windows features, or accept license terms.
param([switch]$Resume)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = $PSScriptRoot
$runName = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$evidenceRoot = Join-Path $projectRoot "docker-evidence/$runName"
New-Item -ItemType Directory -Force -Path $evidenceRoot | Out-Null
$logPath = Join-Path $evidenceRoot 'docker.log'
$reportPath = Join-Path $evidenceRoot 'result.json'
Set-Content -LiteralPath $logPath -Value "Docker verification started: $runName" -Encoding UTF8
$report = [ordered]@{status='RUNNING'; mode=$(if ($Resume) {'resume-checks'} else {'full'}); startedAt=(Get-Date).ToString('o'); checks=@(); error=$null}
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
    & $script:dockerPath @DockerArguments 2>&1 | ForEach-Object {
        $line = [string]$_
        Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
        Write-Host $line
    }
    $nativeExitCode = $LASTEXITCODE
    if ($nativeExitCode -ne 0) { throw "docker exited with code $nativeExitCode; see $logPath" }
}

function Invoke-Compose {
    param([string[]]$ComposeArguments)
    Invoke-Docker -DockerArguments (@('compose', '--project-name', 'dota-course-verify', '--project-directory', $projectRoot, '-f', (Join-Path $projectRoot 'compose.yaml')) + $ComposeArguments)
}

function Invoke-WebReady {
    param([string]$Uri, [string]$Method='Get', [string]$Body='')
    $lastFailure = ''
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $parameters = @{Uri=$Uri; Method=$Method; UseBasicParsing=$true; TimeoutSec=5; ErrorAction='Stop'}
            if ($Method -eq 'Post') { $parameters.Body=$Body; $parameters.ContentType='application/json' }
            $response = Invoke-WebRequest @parameters
            if ($response.StatusCode -eq 200) { return $response }
            $lastFailure = "HTTP $($response.StatusCode)"
        } catch { $lastFailure = $_.Exception.Message }
        Start-Sleep -Seconds 2
    }
    throw "Service readiness failed for $Uri : $lastFailure"
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
    $report.status = 'BLOCKED'
    $savedErrorAction = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $probeOutput = & $dockerPath info --format '{{.OSType}}' 2>&1
    $probeExit = $LASTEXITCODE
    $ErrorActionPreference = $savedErrorAction
    $probeOutput | Out-File -LiteralPath $logPath -Append -Encoding UTF8
    $osType = ($probeOutput | Out-String).Trim()
    if ($probeExit -ne 0 -or $osType -ne 'linux') {
        throw "Docker Engine is not ready for Linux containers. Start Docker Desktop and wait for Engine running. Probe: $osType"
    }
    $report.status = 'RUNNING'
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
    if ($Resume) {
        $priorEvidence = Get-ChildItem -LiteralPath (Join-Path $projectRoot 'docker-evidence') -Filter result.json -Recurse |
            Where-Object { $_.FullName -ne $reportPath } | Sort-Object LastWriteTime -Descending |
            Where-Object {
                $previous = Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json
                ($previous.checks -contains 'Docker image built successfully') -and
                ($previous.checks -contains 'Both models trained and registered inside Linux containers')
            } | Select-Object -First 1
        if (-not $priorEvidence) { throw 'Resume requires a previous report confirming both image build and container training.' }
        $report.reusedBuildTrainingEvidence = $priorEvidence.FullName
        $report.checks += 'Reused completed build and training stages recorded in the prior evidence report'
        Save-Report
    } else {
        Invoke-Compose -ComposeArguments @('build', 'api')
        $report.checks += 'Docker image built successfully'
        Save-Report
        Invoke-Compose -ComposeArguments @('run', '--rm', 'train')
        Invoke-Compose -ComposeArguments @('run', '--rm', 'train-early')
        $report.checks += 'Both models trained and registered inside Linux containers'
        Save-Report
    }
    # Retraining updates the volume; force a fresh process to load that version.
    Invoke-Compose -ComposeArguments @('up', '-d', '--force-recreate', 'api', 'frontend', 'mlflow')

    $health = (Invoke-WebReady -Uri 'http://127.0.0.1:18000/early/health').Content | ConvertFrom-Json
    if ($health.status -ne 'ready') { throw 'Minute-five model is not ready.' }
    $root = (Invoke-WebReady -Uri 'http://127.0.0.1:18000/').Content | ConvertFrom-Json
    if (-not $root.model_loaded -or -not $root.early_model_loaded) { throw 'Both models must be loaded.' }
    foreach ($endpoint in @('http://127.0.0.1:18000/docs','http://127.0.0.1:18501','http://127.0.0.1:15000')) {
        Invoke-WebReady -Uri $endpoint | Out-Null
    }
    $meta = (Invoke-WebReady -Uri 'http://127.0.0.1:18000/early/metadata').Content | ConvertFrom-Json
    $body = $meta.examples[0] | ConvertTo-Json -Depth 6
    $prediction = (Invoke-WebReady -Uri 'http://127.0.0.1:18000/predict/early' -Method Post -Body $body).Content | ConvertFrom-Json
    if ([Math]::Abs($prediction.radiant_probability + $prediction.dire_probability - 1) -gt 0.000001) { throw 'Prediction probabilities do not sum to 1.' }
    $report.checks += 'Container API root, both loaded models, Swagger, frontend HTTP, MLflow HTTP and live early prediction passed'
    Save-Report
    Invoke-Compose -ComposeArguments @('exec', '-T', 'api', 'python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider')
    $report.checks += 'Full API and feature test suite passed inside the API container'
    Save-Report
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
    Save-Report
    $registryCode = @'
from mlflow import MlflowClient
import requests
c = MlflowClient(tracking_uri='sqlite:////app/tracking/mlflow.db')
for name in ['DotaDraftClassifier', 'DotaMinuteFiveClassifier']:
    version = c.get_model_version_by_alias(name, 'champion')
    assert version.status == 'READY'
    assert c.get_run(version.run_id).info.status == 'FINISHED'
    endpoint = 'early/metadata' if name == 'DotaMinuteFiveClassifier' else 'metadata'
    response = requests.get('http://api:8000/' + endpoint, timeout=10)
    response.raise_for_status()
    assert str(response.json()['registry_version']) == str(version.version), 'API must serve the registered champion version'
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
