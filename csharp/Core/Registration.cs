namespace Aurelion.Connector.Core;

public sealed class Registration
{
    private readonly ConnectorConfig _cfg;

    public Registration(ConnectorConfig cfg) => _cfg = cfg;

    public void Publish(string eventType, string instanceId, List<string> tags)
    {
        var message = new Dictionary<string, object?>
        {
            ["event_type"] = eventType,
            ["instance_id"] = instanceId,
            ["tags"] = tags,
        };

        MqPublisher.PublishJson(_cfg, _cfg.RegistryExchange, "topic",
            eventType, message, null);
    }

    public void HeartbeatLoop(string instanceId, List<string> tags, int intervalSeconds)
    {
        while (true)
        {
            Publish("connector.heartbeat", instanceId, tags);
            Thread.Sleep(intervalSeconds * 1000);
        }
    }
}
