import {
  deleteAccount,
  initDb,
  insertAccount,
  listAccounts,
  listEmployments,
  listPersons,
  listPrivileges,
  listRoles,
} from './backend.js';
import { writeRecords } from './core/storage.js';
import type { OperationExecutor, OperationResult } from './core/types.js';

type Handler = (
  payload: Record<string, unknown>,
  resultStorageRequested: boolean,
  correlationId: string | null,
) => OperationResult;

export class Service implements OperationExecutor {
  private readonly dbPath: string | undefined;
  private readonly registry: Map<string, Handler>;

  constructor(dbPath?: string, autoSeedMock = true) {
    this.dbPath = dbPath;
    initDb(dbPath, autoSeedMock);
    this.registry = new Map<string, Handler>([
      ['create_account', this.createAccount.bind(this)],
      ['delete_account', this.deleteAccountOp.bind(this)],
      ['list_accounts', this.listAccountsOp.bind(this)],
      ['list_roles', this.listRolesOp.bind(this)],
      ['list_privileges', this.listPrivilegesOp.bind(this)],
      ['list_persons', this.listPersonsOp.bind(this)],
      ['list_employments', this.listEmploymentsOp.bind(this)],
    ]);
  }

  execute(
    operation: string,
    payload: Record<string, unknown>,
    resultStorageRequested: boolean,
    correlationId: string | null = null,
  ): OperationResult {
    const handler = this.registry.get(operation);
    if (!handler) throw new Error(`unsupported operation: '${operation}'`);
    return handler(payload, resultStorageRequested, correlationId);
  }

  private createAccount(payload: Record<string, unknown>): OperationResult {
    const username = payload['username'];
    const email = payload['email'];
    if (typeof username !== 'string' || !username) throw new Error('username is required');
    if (typeof email !== 'string' || !email) throw new Error('email is required');

    insertAccount(username, email, this.dbPath);
    return { payload: { username, email }, storageRef: null };
  }

  private deleteAccountOp(payload: Record<string, unknown>): OperationResult {
    const username = payload['username'];
    if (typeof username !== 'string' || !username) throw new Error('username is required');

    deleteAccount(username, this.dbPath);
    return { payload: { username }, storageRef: null };
  }

  private listRecords(
    datasetType: string,
    records: Record<string, unknown>[],
    resultStorageRequested: boolean,
    correlationId: string | null,
  ): OperationResult {
    if (resultStorageRequested) {
      return {
        payload: null,
        storageRef: writeRecords(datasetType, records, correlationId),
      };
    }
    return { payload: records, storageRef: null };
  }

  private listAccountsOp(
    _payload: Record<string, unknown>,
    resultStorageRequested: boolean,
    correlationId: string | null,
  ): OperationResult {
    return this.listRecords('accounts', listAccounts(this.dbPath), resultStorageRequested, correlationId);
  }

  private listRolesOp(
    _payload: Record<string, unknown>,
    resultStorageRequested: boolean,
    correlationId: string | null,
  ): OperationResult {
    return this.listRecords('roles', listRoles(this.dbPath), resultStorageRequested, correlationId);
  }

  private listPrivilegesOp(
    _payload: Record<string, unknown>,
    resultStorageRequested: boolean,
    correlationId: string | null,
  ): OperationResult {
    return this.listRecords('privileges', listPrivileges(this.dbPath), resultStorageRequested, correlationId);
  }

  private listPersonsOp(
    _payload: Record<string, unknown>,
    resultStorageRequested: boolean,
    correlationId: string | null,
  ): OperationResult {
    return this.listRecords('persons', listPersons(this.dbPath), resultStorageRequested, correlationId);
  }

  private listEmploymentsOp(
    _payload: Record<string, unknown>,
    resultStorageRequested: boolean,
    correlationId: string | null,
  ): OperationResult {
    return this.listRecords('employments', listEmployments(this.dbPath), resultStorageRequested, correlationId);
  }
}
