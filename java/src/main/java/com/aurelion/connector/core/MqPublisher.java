package com.aurelion.connector.core;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.ConnectionFactory;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeoutException;

public final class MqPublisher {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private MqPublisher() {}

    public static void publishJson(Config cfg, String exchange, String exchangeType,
                                   String routingKey, Map<String, Object> message,
                                   String correlationId) {
        ConnectionFactory factory = new ConnectionFactory();
        factory.setHost(cfg.rabbitmqHost());
        factory.setPort(cfg.rabbitmqPort());
        factory.setUsername(cfg.rabbitmqUsername());
        factory.setPassword(cfg.rabbitmqPassword());

        try (Connection conn = factory.newConnection(); Channel ch = conn.createChannel()) {
            ch.exchangeDeclare(exchange, exchangeType, true);

            AMQP.BasicProperties props = new AMQP.BasicProperties.Builder()
                    .contentType("application/json")
                    .deliveryMode(2)
                    .correlationId(correlationId)
                    .messageId(UUID.randomUUID().toString())
                    .build();

            byte[] body = MAPPER.writeValueAsBytes(message);
            ch.basicPublish(exchange, routingKey, props, body);
        } catch (IOException | TimeoutException e) {
            System.err.println("MQ publish failed: " + e.getMessage());
        }
    }
}
