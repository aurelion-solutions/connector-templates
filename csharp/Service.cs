using Aurelion.Connector.Core;

namespace Aurelion.Connector;

public sealed class Service : IOperationExecutor
{
    private readonly Backend _backend;
    private readonly Dictionary<string, Func<Dictionary<string, object?>, bool, string?, OperationResult>> _registry;

    public Service(string? dbPath, bool autoSeedMock = true)
    {
        _backend = new Backend(dbPath);
        _backend.InitDb(autoSeedMock);
        _registry = new()
        {
            ["create_account"] = CreateAccount,
            ["delete_account"] = DeleteAccount,
            ["list_accounts"] = ListAccountsOp,
            ["list_roles"] = ListRolesOp,
            ["list_privileges"] = ListPrivilegesOp,
            ["list_persons"] = ListPersonsOp,
            ["list_employments"] = ListEmploymentsOp,
        };
    }

    public OperationResult Execute(string operation, Dictionary<string, object?> payload,
                                    bool resultStorageRequested, string? correlationId = null)
    {
        if (!_registry.TryGetValue(operation, out var handler))
            throw new ArgumentException($"unsupported operation: '{operation}'");
        return handler(payload, resultStorageRequested, correlationId);
    }

    private OperationResult CreateAccount(Dictionary<string, object?> payload, bool _, string? __)
    {
        var username = AsString(payload, "username");
        var email = AsString(payload, "email");
        if (string.IsNullOrWhiteSpace(username)) throw new ArgumentException("username is required");
        if (string.IsNullOrWhiteSpace(email)) throw new ArgumentException("email is required");

        _backend.InsertAccount(username, email);
        return new(new Dictionary<string, object?> { ["username"] = username, ["email"] = email }, null);
    }

    private OperationResult DeleteAccount(Dictionary<string, object?> payload, bool _, string? __)
    {
        var username = AsString(payload, "username");
        if (string.IsNullOrWhiteSpace(username)) throw new ArgumentException("username is required");

        _backend.DeleteAccount(username);
        return new(new Dictionary<string, object?> { ["username"] = username }, null);
    }

    private OperationResult ListRecords(
        string datasetType,
        List<Dictionary<string, object?>> records,
        bool resultStorageRequested,
        string? correlationId)
    {
        if (resultStorageRequested)
            return new(null, Storage.WriteRecords(datasetType, records, correlationId));
        return new(records, null);
    }

    private OperationResult ListAccountsOp(Dictionary<string, object?> _, bool rsr, string? cid)
        => ListRecords("accounts", _backend.ListAccounts(), rsr, cid);

    private OperationResult ListRolesOp(Dictionary<string, object?> _, bool rsr, string? cid)
        => ListRecords("roles", _backend.ListRoles(), rsr, cid);

    private OperationResult ListPrivilegesOp(Dictionary<string, object?> _, bool rsr, string? cid)
        => ListRecords("privileges", _backend.ListPrivileges(), rsr, cid);

    private OperationResult ListPersonsOp(Dictionary<string, object?> _, bool rsr, string? cid)
        => ListRecords("persons", _backend.ListPersons(), rsr, cid);

    private OperationResult ListEmploymentsOp(Dictionary<string, object?> _, bool rsr, string? cid)
        => ListRecords("employments", _backend.ListEmployments(), rsr, cid);

    private static string? AsString(Dictionary<string, object?> map, string key)
        => map.TryGetValue(key, out var val) && val is string s ? s : null;
}
