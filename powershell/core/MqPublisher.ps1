function Publish-JsonMessage {
    param(
        [PSCustomObject]$Config,
        [string]$Exchange,
        [string]$ExchangeType,
        [string]$RoutingKey,
        [hashtable]$Message,
        [string]$CorrelationId
    )

    $factory = [RabbitMQ.Client.ConnectionFactory]::new()
    $factory.HostName = $Config.RabbitMqHost
    $factory.Port     = $Config.RabbitMqPort
    $factory.UserName = $Config.RabbitMqUsername
    $factory.Password = $Config.RabbitMqPassword

    $connection = $factory.CreateConnection()
    $channel    = $connection.CreateModel()

    $channel.ExchangeDeclare($Exchange, $ExchangeType, $true)

    $props = $channel.CreateBasicProperties()
    $props.ContentType  = 'application/json'
    $props.DeliveryMode = [byte]2
    $props.MessageId    = [guid]::NewGuid().ToString()
    if ($CorrelationId) { $props.CorrelationId = $CorrelationId }

    $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes(
        ($Message | ConvertTo-Json -Depth 10 -Compress)
    )
    $channel.BasicPublish($Exchange, $RoutingKey, $false, $props, $bodyBytes)

    $channel.Close()
    $connection.Close()
}
