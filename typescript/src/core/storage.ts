import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { randomUUID } from 'node:crypto';

const DEFAULT_BASE = '.lake';

function resolveBasePath(): string {
  return process.env['AURELION_LAKE_PATH'] || join(process.cwd(), DEFAULT_BASE);
}

function sanitizeDatasetType(datasetType: string): string {
  if (datasetType.includes('..') || datasetType.includes('/') || datasetType.includes('\\')) {
    throw new Error(`Invalid dataset_type: ${datasetType}`);
  }
  return datasetType;
}

export function writeRecords(
  datasetType: string,
  records: Record<string, unknown>[],
  correlationId: string | null = null,
): Record<string, string> {
  const basePath = resolveBasePath();
  const key = randomUUID();
  const safe = sanitizeDatasetType(datasetType);
  const filePath = join(basePath, safe, `${key}.jsonl`);

  mkdirSync(dirname(filePath), { recursive: true });

  const content = records.map((r) => JSON.stringify(r)).join('\n') + (records.length ? '\n' : '');
  writeFileSync(filePath, content, 'utf-8');

  const cidLabel = correlationId ? `[correlation_id: ${correlationId}]` : '[correlation_id: n/a]';
  console.log(new Date().toISOString(), cidLabel, 'datalake write', `${safe}/${key}`);

  return {
    provider: 'file',
    storage_key: `${safe}/${key}`,
  };
}
