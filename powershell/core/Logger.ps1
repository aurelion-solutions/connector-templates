function Send-ConnectorLog {
    param(
        [string]$Level,
        [string]$EventType,
        [string]$Message,
        [hashtable]$Payload,
        [string]$CorrelationId,
        [string]$CausationId,
        [string]$InitiatorType,
        [string]$InitiatorId,
        [string]$ActorType,
        [string]$ActorId,
        [string]$TargetType,
        [string]$TargetId
    )

    $cfg = Get-ConnectorConfig
    $eventId = [guid]::NewGuid().ToString()
    $cid     = if ($CorrelationId) { $CorrelationId } else { [guid]::NewGuid().ToString() }

    $logEvent = [ordered]@{
        event_id       = $eventId
        event_type     = $EventType
        level          = $Level
        message        = $Message
        timestamp      = [DateTimeOffset]::UtcNow.ToString('o')
        component      = $cfg.Component
        correlation_id = $cid
        payload        = $Payload
        initiator_type = if ($InitiatorType) { $InitiatorType } else { 'system' }
        initiator_id   = if ($InitiatorId)   { $InitiatorId }   else { 'platform' }
        actor_type     = if ($ActorType)     { $ActorType }     else { 'connector' }
        actor_id       = if ($ActorId)       { $ActorId }       else { $cfg.InstanceId }
        target_type    = if ($TargetType)    { $TargetType }    else { 'system' }
        target_id      = if ($TargetId)      { $TargetId }      else { $cfg.InstanceId }
    }
    if ($CausationId) { $logEvent['causation_id'] = $CausationId }

    Publish-JsonMessage -Config $cfg `
        -Exchange $cfg.LogsExchange -ExchangeType 'topic' `
        -RoutingKey "$($cfg.Component).$Level" `
        -Message ([hashtable]$logEvent) -CorrelationId $cid

    return $eventId
}
