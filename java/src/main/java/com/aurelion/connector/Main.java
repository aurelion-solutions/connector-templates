package com.aurelion.connector;

import com.aurelion.connector.core.*;

import java.time.Instant;
import java.util.Map;

public final class Main {

    public static void main(String[] args) {
        Config cfg = Config.fromEnv("mock-connector");

        Registration registration = new Registration(cfg);
        registration.publish("connector.registered", cfg.instanceId(), cfg.tags());

        Thread heartbeat = new Thread(
                () -> registration.heartbeatLoop(cfg.instanceId(), cfg.tags(), cfg.heartbeatSeconds()),
                "HeartBeat");
        heartbeat.setDaemon(true);
        heartbeat.start();

        ConnectorLogger logger = new ConnectorLogger(cfg);
        logger.emit("info", "connector.instance.started", "Connector instance runtime started",
                Map.of("instance_id", cfg.instanceId(), "tags", cfg.tags()), null);

        System.out.printf("%s connector instance listening instance_id=%s %s %s:%d %s%n",
                Instant.now(), cfg.instanceId(), cfg.tags(),
                cfg.rabbitmqHost(), cfg.rabbitmqPort(), cfg.commandsExchange());

        Service ops = new Service(cfg.dbPath(), cfg.autoSeedMockData());
        ConnectorMqRuntime runtime = new ConnectorMqRuntime(cfg);

        CommandHandler handler = new CommandHandler(
                cfg.instanceId(), ops, logger, runtime::publishCommandResponse);

        runtime.consumeCommands(cfg.instanceId(), handler::handle);
    }
}
