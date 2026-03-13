using System.Text;
using System.Text.Json;
using RabbitMQ.Client;

namespace Aurelion.Connector.Core;

public static class MqPublisher
{
    public static void PublishJson(ConnectorConfig cfg, string exchange, string exchangeType,
                                    string routingKey, Dictionary<string, object?> message,
                                    string? correlationId)
    {
        var factory = new ConnectionFactory
        {
            HostName = cfg.RabbitMqHost,
            Port = cfg.RabbitMqPort,
            UserName = cfg.RabbitMqUsername,
            Password = cfg.RabbitMqPassword,
        };

        try
        {
            using var connection = factory.CreateConnection();
            using var channel = connection.CreateModel();
            channel.ExchangeDeclare(exchange, exchangeType, durable: true);

            var props = channel.CreateBasicProperties();
            props.ContentType = "application/json";
            props.DeliveryMode = 2;
            props.CorrelationId = correlationId ?? "";
            props.MessageId = Guid.NewGuid().ToString();

            var body = Encoding.UTF8.GetBytes(
                JsonSerializer.Serialize(message, new JsonSerializerOptions { WriteIndented = false }));
            channel.BasicPublish(exchange, routingKey, props, body);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"MQ publish failed: {ex.Message}");
        }
    }
}
