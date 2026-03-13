namespace Aurelion.Connector.Core;

public sealed class CommandHandler
{
    private readonly string _instanceId;
    private readonly IOperationExecutor _ops;
    private readonly ConnectorLogger _logger;
    private readonly Action<Dictionary<string, object?>, Dictionary<string, object?>> _responseSender;

    public CommandHandler(string instanceId, IOperationExecutor ops,
                          ConnectorLogger logger,
                          Action<Dictionary<string, object?>, Dictionary<string, object?>> responseSender)
    {
        _instanceId = instanceId;
        _ops = ops;
        _logger = logger;
        _responseSender = responseSender;
    }

    public void Handle(Dictionary<string, object?> command)
    {
        var correlationId = AsString(command, "correlation_id");
        var operation = AsString(command, "operation");
        var resultStorageRequested = command.TryGetValue("result_storage_requested", out var rsr)
                                    && (rsr is true || (rsr is string s && s.Equals("true", StringComparison.OrdinalIgnoreCase)));
        var payload = command.TryGetValue("payload", out var p) && p is Dictionary<string, object?> dict
            ? dict : new Dictionary<string, object?>();

        if (correlationId is null)
        {
            _responseSender(command, ErrorResponse(null, "correlation_id not provided"));
            return;
        }
        if (string.IsNullOrWhiteSpace(operation))
        {
            _responseSender(command, ErrorResponse(correlationId, "operation is required"));
            return;
        }

        var trace = ParseCommandTrace(command);
        string initT, initI, tgtT, tgtI;
        string? causationParent = null;
        if (trace is not null)
        {
            initT = trace.Value.InitiatorType;
            initI = trace.Value.InitiatorId;
            tgtT = trace.Value.TargetType;
            tgtI = trace.Value.TargetId;
            causationParent = trace.Value.ParentEventId;
        }
        else
        {
            initT = "system";
            initI = "platform";
            tgtT = "system";
            tgtI = operation;
        }

        var receivedId = _logger.Emit("info", "connector.command.received", "Command received",
            new() { ["instance_id"] = _instanceId, ["operation"] = operation },
            correlationId,
            causationId: causationParent,
            initiatorType: initT, initiatorId: initI,
            actorType: "connector", actorId: _instanceId,
            targetType: tgtT, targetId: tgtI);

        try
        {
            var result = _ops.Execute(operation, payload, resultStorageRequested, correlationId);
            var response = SuccessResponse(correlationId, result.Payload, result.StorageRef);

            _logger.Emit("info", "connector.command.completed", "Command completed",
                new() { ["instance_id"] = _instanceId, ["operation"] = operation,
                         ["stored"] = result.StorageRef is not null },
                correlationId,
                causationId: receivedId,
                initiatorType: initT, initiatorId: initI,
                actorType: "connector", actorId: _instanceId,
                targetType: tgtT, targetId: tgtI);

            _responseSender(command, response);
        }
        catch (Exception ex)
        {
            _logger.Emit("error", "connector.command.failed", "Command failed",
                new() { ["instance_id"] = _instanceId, ["operation"] = operation, ["error"] = ex.Message },
                correlationId,
                causationId: receivedId,
                initiatorType: initT, initiatorId: initI,
                actorType: "connector", actorId: _instanceId,
                targetType: tgtT, targetId: tgtI);
            _responseSender(command, ErrorResponse(correlationId, ex.Message));
        }
    }

    private record struct TraceContext(string InitiatorType, string InitiatorId,
                                         string TargetType, string TargetId, string ParentEventId);

    private static TraceContext? ParseCommandTrace(Dictionary<string, object?> command)
    {
        var raw = AsString(command, "trace_parent_event_id");
        if (string.IsNullOrWhiteSpace(raw)) return null;
        if (!Guid.TryParse(raw.Trim(), out _)) return null;

        var it = AsString(command, "trace_initiator_type");
        var ii = AsString(command, "trace_initiator_id");
        var tt = AsString(command, "trace_target_type");
        var ti = AsString(command, "trace_target_id");
        if (string.IsNullOrWhiteSpace(it) || string.IsNullOrWhiteSpace(ii)
            || string.IsNullOrWhiteSpace(tt) || string.IsNullOrWhiteSpace(ti))
            return null;

        return new TraceContext(
            it.Trim().ToLowerInvariant(),
            ii.Trim(),
            tt.Trim().ToLowerInvariant(),
            ti.Trim(),
            raw.Trim());
    }

    private static Dictionary<string, object?> ErrorResponse(string? correlationId, string message) => new()
    {
        ["correlation_id"] = correlationId,
        ["status"] = "error",
        ["payload"] = null,
        ["result_storage_ref"] = null,
        ["error"] = new Dictionary<string, object?> { ["message"] = message },
    };

    private static Dictionary<string, object?> SuccessResponse(string correlationId, object? payload,
                                                                 Dictionary<string, string>? storageRef) => new()
    {
        ["correlation_id"] = correlationId,
        ["status"] = "ok",
        ["payload"] = payload,
        ["result_storage_ref"] = storageRef,
        ["error"] = null,
    };

    private static string? AsString(Dictionary<string, object?> map, string key)
        => map.TryGetValue(key, out var val) && val is string s ? s : null;
}
