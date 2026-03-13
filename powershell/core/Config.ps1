$script:_connectorConfig = $null

function Get-EnvOrDefault {
    param([string]$Name, [string]$Default)
    $v = [Environment]::GetEnvironmentVariable($Name)
    if ($null -ne $v -and $v -ne '') { return $v }
    return $Default
}

function Resolve-AutoSeed {
    param([string]$Component)

    $raw = $env:AURELION_MOCK_AUTO_SEED
    if ($null -ne $raw) {
        $lower = $raw.Trim().ToLower()
        return $lower -in @('1', 'true', 'yes')
    }
    $normalized = if ($Component) { $Component.Trim().ToLower() } else { '' }
    return $normalized -in @('mock-connector', 'mock_connector')
}

function New-ConnectorConfig {
    param([hashtable]$Overrides = @{})

    $component = $null
    if ($Overrides.ContainsKey('Component')) { $component = $Overrides['Component'] }
    if (-not $component) { $component = Get-EnvOrDefault 'AURELION_CONNECTOR_COMPONENT' '' }

    $base = [PSCustomObject]@{
        RabbitMqHost      = Get-EnvOrDefault 'AURELION_RABBITMQ_HOST' 'localhost'
        RabbitMqPort      = [int](Get-EnvOrDefault 'AURELION_RABBITMQ_PORT' '5672')
        RabbitMqUsername  = Get-EnvOrDefault 'AURELION_RABBITMQ_USERNAME' 'guest'
        RabbitMqPassword  = Get-EnvOrDefault 'AURELION_RABBITMQ_PASSWORD' 'guest'
        InstanceId        = Get-EnvOrDefault 'AURELION_CONNECTOR_INSTANCE_ID' ''
        Tags              = @(if ($env:AURELION_CONNECTOR_TAGS) {
                                  $env:AURELION_CONNECTOR_TAGS -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
                              })
        DbPath            = $env:MOCK_CONNECTOR_DB
        CommandsExchange  = Get-EnvOrDefault 'AURELION_CONNECTOR_COMMANDS_EXCHANGE' 'aurelion.connectors.commands'
        RegistryExchange  = Get-EnvOrDefault 'AURELION_CONNECTOR_REGISTRY_EXCHANGE' 'aurelion.connectors.registry'
        LogsExchange      = Get-EnvOrDefault 'AURELION_LOGS_EXCHANGE' 'aurelion.logs'
        Component         = $component
        HeartbeatSeconds  = [int](Get-EnvOrDefault 'AURELION_CONNECTOR_HEARTBEAT_SECONDS' '60')
        AutoSeedMockData  = Resolve-AutoSeed -Component $component
    }

    foreach ($key in $Overrides.Keys) {
        if ($null -ne $Overrides[$key]) {
            $base.$key = $Overrides[$key]
        }
    }

    if (-not $Overrides.ContainsKey('AutoSeedMockData')) {
        $base.AutoSeedMockData = Resolve-AutoSeed -Component $base.Component
    }

    return $base
}

function Initialize-ConnectorConfig {
    param([PSCustomObject]$Config)
    $script:_connectorConfig = if ($Config) { $Config } else { New-ConnectorConfig }
    return $script:_connectorConfig
}

function Get-ConnectorConfig {
    if ($null -eq $script:_connectorConfig) {
        throw 'ConnectorConfig not initialised — call Initialize-ConnectorConfig first'
    }
    return $script:_connectorConfig
}
