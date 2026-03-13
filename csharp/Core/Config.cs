namespace Aurelion.Connector.Core;

public sealed record ConnectorConfig(
    string RabbitMqHost,
    int RabbitMqPort,
    string RabbitMqUsername,
    string RabbitMqPassword,
    string InstanceId,
    List<string> Tags,
    string? DbPath,
    string CommandsExchange,
    string RegistryExchange,
    string LogsExchange,
    string Component,
    int HeartbeatSeconds,
    bool AutoSeedMockData
)
{
    public static ConnectorConfig FromEnv(string? component = null)
    {
        var comp = component
            ?? Environment.GetEnvironmentVariable("AURELION_CONNECTOR_COMPONENT")
            ?? "mock-connector-csharp";

        return new ConnectorConfig(
            RabbitMqHost: Env("AURELION_RABBITMQ_HOST", "localhost"),
            RabbitMqPort: int.Parse(Env("AURELION_RABBITMQ_PORT", "5672")),
            RabbitMqUsername: Env("AURELION_RABBITMQ_USERNAME", "guest"),
            RabbitMqPassword: Env("AURELION_RABBITMQ_PASSWORD", "guest"),
            InstanceId: Env("AURELION_CONNECTOR_INSTANCE_ID", ""),
            Tags: ParseTags(Environment.GetEnvironmentVariable("AURELION_CONNECTOR_TAGS")),
            DbPath: Environment.GetEnvironmentVariable("MOCK_CONNECTOR_DB"),
            CommandsExchange: Env("AURELION_CONNECTOR_COMMANDS_EXCHANGE", "aurelion.connectors.commands"),
            RegistryExchange: Env("AURELION_CONNECTOR_REGISTRY_EXCHANGE", "aurelion.connectors.registry"),
            LogsExchange: Env("AURELION_LOGS_EXCHANGE", "aurelion.logs"),
            Component: comp,
            HeartbeatSeconds: int.Parse(Env("AURELION_CONNECTOR_HEARTBEAT_SECONDS", "60")),
            AutoSeedMockData: ResolveAutoSeed(comp)
        );
    }

    private static bool ResolveAutoSeed(string component)
    {
        var raw = Environment.GetEnvironmentVariable("AURELION_MOCK_AUTO_SEED");
        if (raw is not null)
        {
            var lower = raw.Trim().ToLowerInvariant();
            return lower is "1" or "true" or "yes";
        }
        var normalized = component.Trim().ToLowerInvariant();
        return normalized is "mock-connector" or "mock_connector";
    }

    private static string Env(string key, string defaultValue)
        => Environment.GetEnvironmentVariable(key) ?? defaultValue;

    private static List<string> ParseTags(string? value)
        => string.IsNullOrWhiteSpace(value)
            ? []
            : value.Split(',').Select(s => s.Trim()).Where(s => s.Length > 0).ToList();
}
