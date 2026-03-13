export type OperationResult = {
  payload: Record<string, unknown> | Record<string, unknown>[] | null;
  storageRef: Record<string, string> | null;
};

export interface OperationExecutor {
  execute(
    operation: string,
    payload: Record<string, unknown>,
    resultStorageRequested: boolean,
    correlationId?: string | null,
  ): OperationResult;
}
