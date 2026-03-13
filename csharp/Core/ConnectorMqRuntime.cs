using System.Text;
using System.Text.Json;
using RabbitMQ.Client;
using RabbitMQ.Client.Events;

namespace Aurelion.Connector.Core;

public sealed class ConnectorMqRuntime : IDisposable
{
    private readonly ConnectorConfig _cfg;
    private readonly IConnection _connection;
    private readonly IModel _channel;

    public ConnectorMqRuntime(ConnectorConfig cfg)
    {
        _cfg = cfg;
        var factory = new ConnectionFactory
        {
            HostName = cfg.RabbitMqHost,
            Port = cfg.RabbitMqPort,
            UserName = cfg.RabbitMqUsername,
            Password = cfg.RabbitMqPassword,
        };

        _connection = factory.CreateConnection();
        _channel = _connection.CreateModel();
        _channel.ExchangeDeclare(cfg.CommandsExchange, "direct", durable: true);
    }

    public void ConsumeCommands(string instanceId, Action<Dictionary<string, object?>> onCommand)
    {
        var queueName = $"aurelion.connector.{instanceId}.commands";
        _channel.QueueDeclare(queueName, durable: true, exclusive: false, autoDelete: false);
        _channel.QueueBind(queueName, _cfg.CommandsExchange, instanceId);

        var consumer = new EventingBasicConsumer(_channel);
        consumer.Received += (_, ea) =>
        {
            try
            {
                var raw = JsonSerializer.Deserialize<Dictionary<string, object?>>(
                    Encoding.UTF8.GetString(ea.Body.ToArray()),
                    new JsonSerializerOptions { PropertyNameCaseInsensitive = false });
                if (raw is null) throw new InvalidOperationException("Payload is not a JSON object");
                onCommand(raw);
                _channel.BasicAck(ea.DeliveryTag, false);
            }
            catch
            {
                _channel.BasicNack(ea.DeliveryTag, false, false);
            }
        };

        _channel.BasicConsume(queueName, autoAck: false, consumer);
        Console.WriteLine($"Consuming commands on queue: {queueName}");
        Thread.Sleep(Timeout.Infinite);
    }

    public void PublishCommandResponse(Dictionary<string, object?> command,
                                        Dictionary<string, object?> response)
    {
        var replyExchange = AsString(command, "reply_exchange");
        var replyRoutingKey = AsString(command, "reply_routing_key");
        var correlationId = AsString(command, "correlation_id");

        if (string.IsNullOrWhiteSpace(replyExchange) || string.IsNullOrWhiteSpace(replyRoutingKey))
            return;

        MqPublisher.PublishJson(_cfg, replyExchange, "direct", replyRoutingKey,
            response, correlationId);
    }

    public void Dispose()
    {
        _channel.Dispose();
        _connection.Dispose();
    }

    private static string? AsString(Dictionary<string, object?> map, string key)
        => map.TryGetValue(key, out var val) && val is string s ? s : null;
}
