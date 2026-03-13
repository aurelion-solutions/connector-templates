function Start-ConnectorBootstrap {
    param(
        [PSCustomObject]$Config,
        [object]$Ops
    )

    $cfg = Initialize-ConnectorConfig -Config $Config

    Publish-ConnectorRegistration -EventType 'connector.registered' `
        -InstanceId $cfg.InstanceId -Tags $cfg.Tags

    Start-HeartbeatLoop -Config $cfg -InstanceId $cfg.InstanceId `
        -Tags $cfg.Tags -IntervalSeconds $cfg.HeartbeatSeconds

    Send-ConnectorLog -Level 'info' -EventType 'connector.instance.started' `
        -Message 'Connector instance runtime started' `
        -Payload @{ instance_id = $cfg.InstanceId; tags = $cfg.Tags }

    $ts = [DateTimeOffset]::UtcNow.ToString('o')
    Write-Host "$ts connector instance listening instance_id=$($cfg.InstanceId) [$($cfg.Tags -join ', ')] $($cfg.RabbitMqHost):$($cfg.RabbitMqPort) $($cfg.CommandsExchange)"

    $runtime = New-ConnectorMqRuntime -Config $cfg

    $sendResponse = {
        param($command, $response)
        Publish-CommandResponse -Config $cfg -Command $command -Response $response
    }.GetNewClosure()

    Start-CommandConsumer -Runtime $runtime -InstanceId $cfg.InstanceId -OnCommand {
        param($command)
        Invoke-CommandHandler -Command $command -InstanceId $cfg.InstanceId `
            -Ops $Ops -SendResponse $sendResponse
    }.GetNewClosure()
}
