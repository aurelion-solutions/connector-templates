function Publish-ConnectorRegistration {
    param(
        [string]$EventType,
        [string]$InstanceId,
        [string[]]$Tags = @()
    )

    $cfg = Get-ConnectorConfig

    Publish-JsonMessage -Config $cfg `
        -Exchange $cfg.RegistryExchange -ExchangeType 'topic' `
        -RoutingKey $EventType `
        -Message @{
            event_type  = $EventType
            instance_id = $InstanceId
            tags        = $Tags
        }
}

function Start-HeartbeatLoop {
    param(
        [PSCustomObject]$Config,
        [string]$InstanceId,
        [string[]]$Tags,
        [int]$IntervalSeconds
    )

    Start-ThreadJob -ScriptBlock {
        param($host_, $port, $user, $pass, $exchange, $instanceId, $tags, $interval)
        while ($true) {
            try {
                $factory = [RabbitMQ.Client.ConnectionFactory]::new()
                $factory.HostName = $host_
                $factory.Port     = $port
                $factory.UserName = $user
                $factory.Password = $pass
                $conn = $factory.CreateConnection()
                $ch   = $conn.CreateModel()
                $ch.ExchangeDeclare($exchange, 'topic', $true)

                $msg = @{
                    event_type  = 'connector.heartbeat'
                    instance_id = $instanceId
                    tags        = $tags
                } | ConvertTo-Json -Depth 5 -Compress

                $body  = [System.Text.Encoding]::UTF8.GetBytes($msg)
                $props = $ch.CreateBasicProperties()
                $props.ContentType  = 'application/json'
                $props.DeliveryMode = [byte]2
                $props.MessageId    = [guid]::NewGuid().ToString()
                $ch.BasicPublish($exchange, 'connector.heartbeat', $false, $props, $body)
                $ch.Close()
                $conn.Close()
            } catch {}
            Start-Sleep -Seconds $interval
        }
    } -ArgumentList $Config.RabbitMqHost, $Config.RabbitMqPort, `
        $Config.RabbitMqUsername, $Config.RabbitMqPassword, `
        $Config.RegistryExchange, $InstanceId, $Tags, $IntervalSeconds | Out-Null
}
