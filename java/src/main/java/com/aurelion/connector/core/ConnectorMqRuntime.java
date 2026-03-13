package com.aurelion.connector.core;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.rabbitmq.client.*;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeoutException;
import java.util.function.Consumer;

public final class ConnectorMqRuntime {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final Config cfg;
    private final Connection connection;
    private final Channel channel;

    public ConnectorMqRuntime(Config cfg) {
        this.cfg = cfg;
        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost(cfg.rabbitmqHost());
        factory.setPort(cfg.rabbitmqPort());
        factory.setUsername(cfg.rabbitmqUsername());
        factory.setPassword(cfg.rabbitmqPassword());

        try {
            this.connection = factory.newConnection();
            this.channel = connection.createChannel();
            channel.exchangeDeclare(cfg.commandsExchange(), "direct", true);
        } catch (IOException | TimeoutException e) {
            throw new RuntimeException("Failed to connect to RabbitMQ", e);
        }
    }

    public void consumeCommands(String instanceId, Consumer<Map<String, Object>> onCommand) {
        String queueName = "aurelion.connector." + instanceId + ".commands";

        try {
            channel.queueDeclare(queueName, true, false, false, null);
            channel.queueBind(queueName, cfg.commandsExchange(), instanceId);

            channel.basicConsume(queueName, false, new DefaultConsumer(channel) {
                @Override
                public void handleDelivery(String consumerTag, Envelope envelope,
                                           AMQP.BasicProperties properties, byte[] body)
                        throws IOException {
                    try {
                        Map<String, Object> raw = MAPPER.readValue(body,
                                new TypeReference<Map<String, Object>>() {});
                        onCommand.accept(raw);
                        channel.basicAck(envelope.getDeliveryTag(), false);
                    } catch (Exception e) {
                        channel.basicNack(envelope.getDeliveryTag(), false, false);
                    }
                }
            });

            System.out.println("Consuming commands on queue: " + queueName);
            Thread.currentThread().join();
        } catch (IOException | InterruptedException e) {
            throw new RuntimeException("Command consumption failed", e);
        }
    }

    public void publishCommandResponse(Map<String, Object> command, Map<String, Object> response) {
        Object replyExchange = command.get("reply_exchange");
        Object replyRoutingKey = command.get("reply_routing_key");
        Object correlationId = command.get("correlation_id");

        if (!(replyExchange instanceof String ex) || ex.isBlank()) return;
        if (!(replyRoutingKey instanceof String rk) || rk.isBlank()) return;

        MqPublisher.publishJson(cfg, ex, "direct", rk, response,
                correlationId instanceof String cid ? cid : null);
    }
}
