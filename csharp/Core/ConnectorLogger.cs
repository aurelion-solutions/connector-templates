namespace Aurelion.Connector.Core;

public sealed class ConnectorLogger
{
    private readonly ConnectorConfig _cfg;

    public ConnectorLogger(ConnectorConfig cfg) => _cfg = cfg;

    public string Emit(
        string level,
        string eventType,
        string message,
        Dictionary<string, object?> payload,
        string? correlationId,
        string? causationId = null,
        string? initiatorType = null,
        string? initiatorId = null,
        string? actorType = null,
        string? actorId = null,
        string? targetType = null,
        string? targetId = null)
    {
        var eventId = Guid.NewGuid().ToString();
        var cid = correlationId ?? Guid.NewGuid().ToString();

        var logEvent = new Dictionary<string, object?>
        {
            ["event_id"] = eventId,
            ["event_type"] = eventType,
            ["level"] = level,
            ["message"] = message,
            ["timestamp"] = DateTimeOffset.UtcNow.ToString("o"),
            ["component"] = _cfg.Component,
            ["correlation_id"] = cid,
            ["payload"] = payload,
            ["initiator_type"] = initiatorType ?? "system",
            ["initiator_id"] = initiatorId ?? "platform",
            ["actor_type"] = actorType ?? "connector",
            ["actor_id"] = actorId ?? _cfg.InstanceId,
            ["target_type"] = targetType ?? "system",
            ["target_id"] = targetId ?? _cfg.InstanceId,
        };
        if (causationId is not null) logEvent["causation_id"] = causationId;

        MqPublisher.PublishJson(_cfg, _cfg.LogsExchange, "topic",
            $"{_cfg.Component}.{level}", logEvent, cid);

        return eventId;
    }
}
