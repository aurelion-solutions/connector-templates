using System.Text.Json;

namespace Aurelion.Connector.Core;

public static class Storage
{
    private const string DefaultBase = ".lake";

    public static Dictionary<string, string> WriteRecords(
        string datasetType,
        IEnumerable<Dictionary<string, object?>> records,
        string? correlationId = null)
    {
        var safe = SanitizeDatasetType(datasetType);
        var basePath = ResolveBasePath();
        var key = Guid.NewGuid().ToString();
        var dir = Path.Combine(basePath, safe);
        Directory.CreateDirectory(dir);
        var filePath = Path.Combine(dir, $"{key}.jsonl");

        using (var writer = new StreamWriter(filePath, append: false, System.Text.Encoding.UTF8))
        {
            var opts = new JsonSerializerOptions { WriteIndented = false };
            foreach (var record in records)
            {
                writer.WriteLine(JsonSerializer.Serialize(record, opts));
            }
        }

        var cidLabel = string.IsNullOrEmpty(correlationId)
            ? "[correlation_id: n/a]"
            : $"[correlation_id: {correlationId}]";
        Console.WriteLine($"{DateTimeOffset.UtcNow:o} {cidLabel} datalake write {safe}/{key}");

        return new Dictionary<string, string>
        {
            ["provider"] = "file",
            ["storage_key"] = $"{safe}/{key}",
        };
    }

    private static string ResolveBasePath()
    {
        var env = Environment.GetEnvironmentVariable("AURELION_LAKE_PATH");
        return string.IsNullOrEmpty(env) ? Path.Combine(Directory.GetCurrentDirectory(), DefaultBase) : env;
    }

    private static string SanitizeDatasetType(string datasetType)
    {
        if (datasetType.Contains("..") || datasetType.Contains('/') || datasetType.Contains('\\'))
            throw new ArgumentException($"Invalid dataset_type: '{datasetType}'");
        return datasetType;
    }
}
