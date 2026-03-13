# Aurelion Connector Templates

Reference implementations of an Aurelion connector in five languages: **Python**, **Java**, **C#**, **TypeScript**, and **PowerShell**.

All five connectors are functionally identical — they manage user accounts in a local SQLite database and communicate with the Aurelion platform over RabbitMQ.

## Architecture

Each connector follows the same two-layer structure:

```
<language>/
├── core/               # Reusable infrastructure (copy as-is to a new connector)
│   ├── config           # Environment-based configuration
│   ├── handler          # Command dispatch and response formatting
│   ├── mq               # RabbitMQ consumer and publisher
│   ├── logger           # Structured log emitter
│   └── registration     # Instance registration and heartbeat
│
├── main                 # Entry point — creates config and calls bootstrap
├── backend              # Managed system adapter (SQLite in this example)
└── service / operations # Business logic — implements OperationExecutor
```

**`core/`** contains platform protocol logic that does not change between connectors.
Only **`main`**, **`backend`**, and **`service`** need to be modified when building a new connector.

### Dependency Inversion

`core/handler` depends on an `OperationExecutor` interface (Protocol in Python, interface in Java/C#/TypeScript, duck-typed class in PowerShell), not on a concrete service class. The entry point wires the concrete implementation at startup.

## Supported Operations

| Operation          | Description                          |
|--------------------|--------------------------------------|
| `create_account`   | Create a user account                |
| `delete_account`   | Delete a user account by username    |
| `list_accounts`    | List all accounts                    |
| `list_roles`       | List roles (stub, returns empty)     |
| `list_privileges`  | List privileges (stub, returns empty)|

## Shared Database

All five implementations share a single SQLite database at `_mock-data/mock_connector.db`. It is created automatically on first startup and seeded from `_mock-data/seed.sql` when empty.

The `_mock-data/` directory holds everything dataset-related:

```
_mock-data/
├── seed.sql              # deterministic seed (generated, checked in)
├── mock_connector.db     # shared SQLite DB (created on first run)
└── mock_dataset/         # Python generator for seed.sql
```

To regenerate `seed.sql`:

```bash
cd _mock-data
python -m mock_dataset
```

## Configuration

Configuration is read from environment variables (Python and TypeScript also support `.env` files via `dotenv`):

| Variable                                | Default                          | Description                    |
|-----------------------------------------|----------------------------------|--------------------------------|
| `AURELION_RABBITMQ_HOST`               | `localhost`                      | RabbitMQ host                  |
| `AURELION_RABBITMQ_PORT`               | `5672`                           | RabbitMQ port                  |
| `AURELION_RABBITMQ_USERNAME`           | —                                | RabbitMQ username              |
| `AURELION_RABBITMQ_PASSWORD`           | —                                | RabbitMQ password              |
| `AURELION_CONNECTOR_INSTANCE_ID`       | —                                | Unique instance identifier     |
| `AURELION_CONNECTOR_TAGS`              | —                                | Comma-separated tags           |
| `AURELION_CONNECTOR_COMPONENT`         | —                                | Component name for logging     |
| `AURELION_CONNECTOR_HEARTBEAT_SECONDS` | `60`                             | Heartbeat interval in seconds  |
| `MOCK_CONNECTOR_DB`                    | `_mock-data/mock_connector.db`    | SQLite database path           |
| `MOCK_CONNECTOR_SEED_SQL`              | `_mock-data/seed.sql`             | Seed SQL file path             |

## Running

### Python

```bash
cd python
pip install -r requirements.txt   # pika, python-dotenv
python main.py
```

### Java

```bash
cd java
mvn package
java -jar target/mock-connector-1.0.jar
```

### C#

```bash
cd csharp
dotnet run
```

### TypeScript

```bash
cd typescript
npm install
npm run build
npm start
```

### PowerShell

Requires PowerShell 7+ and .NET SDK 8.0+.

```bash
cd powershell
pwsh setup.ps1        # download .NET dependencies (one-time)
pwsh main.ps1
```

## Creating a New Connector

1. Copy the `core/` directory from the language of your choice.
2. Create a new `main` entry point — configure `component` name and backend-specific settings.
3. Implement `backend` — the adapter to your managed system (API client, database driver, SDK wrapper, etc.).
4. Implement `service` / `ConnectorOperations` — map operation names to your backend calls. The class must implement the `OperationExecutor` interface.
5. Update environment variables as needed.
