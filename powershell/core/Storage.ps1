function Write-StorageRecords {
    param(
        [string]$DatasetType,
        [array]$Records,
        [string]$CorrelationId
    )

    if ($DatasetType -match '\.\.' -or $DatasetType -match '[/\\]') {
        throw "Invalid dataset_type: '$DatasetType'"
    }

    $basePath = if ($env:AURELION_LAKE_PATH) { $env:AURELION_LAKE_PATH }
                else { Join-Path (Get-Location) '.lake' }

    $key      = [guid]::NewGuid().ToString()
    $filePath = Join-Path $basePath $DatasetType "$key.jsonl"

    $dir = Split-Path $filePath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

    $lines = $Records | ForEach-Object { $_ | ConvertTo-Json -Depth 10 -Compress }
    $lines | Set-Content -Path $filePath -Encoding utf8

    $cidLabel = if ($CorrelationId) { "[correlation_id: $CorrelationId]" } else { '[correlation_id: n/a]' }
    Write-Host "$([DateTimeOffset]::UtcNow.ToString('o')) $cidLabel datalake write $DatasetType/$key"

    return @{
        provider    = 'file'
        storage_key = "$DatasetType/$key"
    }
}
