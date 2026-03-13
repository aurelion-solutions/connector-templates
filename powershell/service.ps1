class Service {
    hidden [string]$DbPath

    Service([string]$dbPath, [bool]$autoSeedMock = $true) {
        $this.DbPath = $dbPath
        Initialize-Database -Path $dbPath -AutoSeed $autoSeedMock
    }

    [hashtable] Execute([string]$operation, [hashtable]$payload, [bool]$resultStorageRequested, [string]$correlationId) {
        switch ($operation) {
            'create_account'   { return $this.CreateAccount($payload) }
            'delete_account'   { return $this.DeleteAccount($payload) }
            'list_accounts'    { return $this.ListRecords('accounts',    (Get-AccountList    -Path $this.DbPath), $resultStorageRequested, $correlationId) }
            'list_roles'       { return $this.ListRecords('roles',       (Get-RoleList       -Path $this.DbPath), $resultStorageRequested, $correlationId) }
            'list_privileges'  { return $this.ListRecords('privileges',  (Get-PrivilegeList  -Path $this.DbPath), $resultStorageRequested, $correlationId) }
            'list_persons'     { return $this.ListRecords('persons',     (Get-PersonList     -Path $this.DbPath), $resultStorageRequested, $correlationId) }
            'list_employments' { return $this.ListRecords('employments', (Get-EmploymentList -Path $this.DbPath), $resultStorageRequested, $correlationId) }
            default            { throw "unsupported operation: '$operation'" }
        }
        return $null
    }

    hidden [hashtable] CreateAccount([hashtable]$payload) {
        $username = $payload['username']
        $email    = $payload['email']
        if (-not $username) { throw 'username is required' }
        if (-not $email)    { throw 'email is required' }

        Add-Account -Username $username -Email $email -Path $this.DbPath
        return @{ Payload = @{ username = $username; email = $email }; StorageRef = $null }
    }

    hidden [hashtable] DeleteAccount([hashtable]$payload) {
        $username = $payload['username']
        if (-not $username) { throw 'username is required' }

        Remove-Account -Username $username -Path $this.DbPath
        return @{ Payload = @{ username = $username }; StorageRef = $null }
    }

    hidden [hashtable] ListRecords([string]$datasetType, [array]$records, [bool]$resultStorageRequested, [string]$correlationId) {
        if ($resultStorageRequested) {
            $ref = Write-StorageRecords -DatasetType $datasetType -Records $records -CorrelationId $correlationId
            return @{ Payload = $null; StorageRef = $ref }
        }
        return @{ Payload = $records; StorageRef = $null }
    }
}
