#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

$corePath = Join-Path $PSScriptRoot 'core'

. (Join-Path $corePath 'LoadAssemblies.ps1')
. (Join-Path $corePath 'Config.ps1')
. (Join-Path $corePath 'MqPublisher.ps1')
. (Join-Path $corePath 'Logger.ps1')
. (Join-Path $corePath 'Registration.ps1')
. (Join-Path $corePath 'Storage.ps1')
. (Join-Path $corePath 'Handler.ps1')
. (Join-Path $corePath 'MqRuntime.ps1')
. (Join-Path $corePath 'Bootstrap.ps1')

. (Join-Path $PSScriptRoot 'backend.ps1')
. (Join-Path $PSScriptRoot 'service.ps1')

$cfg = New-ConnectorConfig -Overrides @{
    Component = 'mock-connector'
    DbPath    = $env:MOCK_CONNECTOR_DB
}

$ops = [Service]::new($cfg.DbPath, $cfg.AutoSeedMockData)

Start-ConnectorBootstrap -Config $cfg -Ops $ops
