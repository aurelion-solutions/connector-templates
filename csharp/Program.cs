using Aurelion.Connector;
using Aurelion.Connector.Core;

var cfg = ConnectorConfig.FromEnv(component: "mock-connector");

var registration = new Registration(cfg);
registration.Publish("connector.registered", cfg.InstanceId, cfg.Tags);

var heartbeat = new Thread(() => registration.HeartbeatLoop(cfg.InstanceId, cfg.Tags, cfg.HeartbeatSeconds))
{
    Name = "HeartBeat",
    IsBackground = true,
};
heartbeat.Start();

var logger = new ConnectorLogger(cfg);
logger.Emit("info", "connector.instance.started", "Connector instance runtime started",
    new() { ["instance_id"] = cfg.InstanceId, ["tags"] = cfg.Tags }, null);

Console.WriteLine($"{DateTimeOffset.UtcNow:o} connector instance listening " +
                  $"instance_id={cfg.InstanceId} [{string.Join(", ", cfg.Tags)}] " +
                  $"{cfg.RabbitMqHost}:{cfg.RabbitMqPort} {cfg.CommandsExchange}");

var ops = new Service(cfg.DbPath, autoSeedMock: cfg.AutoSeedMockData);
using var runtime = new ConnectorMqRuntime(cfg);

var handler = new CommandHandler(cfg.InstanceId, ops, logger, runtime.PublishCommandResponse);
runtime.ConsumeCommands(cfg.InstanceId, handler.Handle);
