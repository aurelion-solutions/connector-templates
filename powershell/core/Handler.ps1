function Invoke-CommandHandler {
    param(
        [hashtable]$Command,
        [string]$InstanceId,
        [object]$Ops,
        [scriptblock]$SendResponse
    )

    $correlationId          = $Command['correlation_id']
    $operation              = $Command['operation']
    $resultStorageRequested = [bool]$Command['result_storage_requested']
    $payload                = $Command['payload']
    if ($null -eq $payload) { $payload = @{} }

    if ($correlationId -isnot [string]) {
        & $SendResponse $Command @{
            correlation_id = $null; status = 'error'; payload = $null
            result_storage_ref = $null; error = @{ message = 'correlation_id not provided' }
        }
        return
    }

    if (-not $operation) {
        & $SendResponse $Command @{
            correlation_id = $correlationId; status = 'error'; payload = $null
            result_storage_ref = $null; error = @{ message = 'operation is required' }
        }
        return
    }

    $trace = Get-CommandTrace -Command $Command
    if ($trace) {
        $initT = $trace.InitiatorType
        $initI = $trace.InitiatorId
        $tgtT  = $trace.TargetType
        $tgtI  = $trace.TargetId
        $causationParent = $trace.ParentEventId
    } else {
        $initT = 'system'
        $initI = 'platform'
        $tgtT  = 'system'
        $tgtI  = $operation
        $causationParent = $null
    }

    $receivedId = Send-ConnectorLog -Level 'info' -EventType 'connector.command.received' `
        -Message 'Command received' `
        -Payload @{ instance_id = $InstanceId; operation = $operation } `
        -CorrelationId $correlationId -CausationId $causationParent `
        -InitiatorType $initT -InitiatorId $initI `
        -ActorType 'connector' -ActorId $InstanceId `
        -TargetType $tgtT -TargetId $tgtI

    try {
        $result = $Ops.Execute($operation, $payload, $resultStorageRequested, $correlationId)

        $response = @{
            correlation_id     = $correlationId
            status             = 'ok'
            payload            = $result.Payload
            result_storage_ref = $result.StorageRef
            error              = $null
        }

        Send-ConnectorLog -Level 'info' -EventType 'connector.command.completed' `
            -Message 'Command completed' `
            -Payload @{
                instance_id = $InstanceId; operation = $operation
                stored      = $null -ne $result.StorageRef
            } `
            -CorrelationId $correlationId -CausationId $receivedId `
            -InitiatorType $initT -InitiatorId $initI `
            -ActorType 'connector' -ActorId $InstanceId `
            -TargetType $tgtT -TargetId $tgtI | Out-Null

        & $SendResponse $Command $response
    }
    catch {
        $errorMessage = $_.Exception.Message

        Send-ConnectorLog -Level 'error' -EventType 'connector.command.failed' `
            -Message 'Command failed' `
            -Payload @{
                instance_id = $InstanceId; operation = $operation
                error       = $errorMessage
            } `
            -CorrelationId $correlationId -CausationId $receivedId `
            -InitiatorType $initT -InitiatorId $initI `
            -ActorType 'connector' -ActorId $InstanceId `
            -TargetType $tgtT -TargetId $tgtI | Out-Null

        & $SendResponse $Command @{
            correlation_id = $correlationId; status = 'error'; payload = $null
            result_storage_ref = $null; error = @{ message = $errorMessage }
        }
    }
}

function Get-CommandTrace {
    param([hashtable]$Command)

    $rawParent = $Command['trace_parent_event_id']
    if ($rawParent -isnot [string] -or -not $rawParent.Trim()) { return $null }

    $guid = [guid]::Empty
    if (-not [guid]::TryParse($rawParent.Trim(), [ref]$guid)) { return $null }

    $it = $Command['trace_initiator_type']
    $ii = $Command['trace_initiator_id']
    $tt = $Command['trace_target_type']
    $ti = $Command['trace_target_id']

    foreach ($v in @($it, $ii, $tt, $ti)) {
        if ($v -isnot [string] -or -not $v.Trim()) { return $null }
    }

    return [PSCustomObject]@{
        InitiatorType = $it.Trim().ToLower()
        InitiatorId   = $ii.Trim()
        TargetType    = $tt.Trim().ToLower()
        TargetId      = $ti.Trim()
        ParentEventId = $rawParent.Trim()
    }
}
