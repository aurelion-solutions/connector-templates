namespace Aurelion.Connector.Core;

public record OperationResult(object? Payload, Dictionary<string, string>? StorageRef);

public interface IOperationExecutor
{
    OperationResult Execute(string operation, Dictionary<string, object?> payload,
                            bool resultStorageRequested, string? correlationId = null);
}
