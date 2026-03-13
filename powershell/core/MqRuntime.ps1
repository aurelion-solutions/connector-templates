function New-ConnectorMqRuntime {
    param([PSCustomObject]$Config)

    $factory = [RabbitMQ.Client.ConnectionFactory]::new()
    $factory.HostName = $Config.RabbitMqHost
    $factory.Port     = $Config.RabbitMqPort
    $factory.UserName = $Config.RabbitMqUsername
    $factory.Password = $Config.RabbitMqPassword

    $connection = $factory.CreateConnection()
    $channel    = $connection.CreateModel()
    $channel.ExchangeDeclare($Config.CommandsExchange, 'direct', $true)

    return [PSCustomObject]@{
        Config     = $Config
        Connection = $connection
        Channel    = $channel
    }
}

function Start-CommandConsumer {
    param(
        [PSCustomObject]$Runtime,
        [string]$InstanceId,
        [scriptblock]$OnCommand
    )

    $channel  = $Runtime.Channel
    $exchange = $Runtime.Config.CommandsExchange
    $queueName = "aurelion.connector.$InstanceId.commands"

    [void]$channel.QueueDeclare($queueName, $true, $false, $false, $null)
    $channel.QueueBind($queueName, $exchange, $InstanceId)

    Write-Host "Consuming commands on queue: $queueName"

    while ($true) {
        $result = $channel.BasicGet($queueName, $false)
        if ($null -eq $result) {
            Start-Sleep -Milliseconds 100
            continue
        }
        try {
            $bodyStr = [System.Text.Encoding]::UTF8.GetString($result.Body.ToArray())
            $raw = $bodyStr | ConvertFrom-Json -AsHashtable
            & $OnCommand $raw
            $channel.BasicAck($result.DeliveryTag, $false)
        }
        catch {
            $channel.BasicNack($result.DeliveryTag, $false, $false)
        }
    }
}

function Publish-CommandResponse {
    param(
        [PSCustomObject]$Config,
        [hashtable]$Command,
        [hashtable]$Response
    )

    $replyExchange   = $Command['reply_exchange']
    $replyRoutingKey = $Command['reply_routing_key']
    $correlationId   = $Command['correlation_id']

    if (-not $replyExchange -or -not $replyRoutingKey) { return }

    Publish-JsonMessage -Config $Config `
        -Exchange $replyExchange -ExchangeType 'direct' `
        -RoutingKey $replyRoutingKey -Message $Response `
        -CorrelationId $correlationId
}
