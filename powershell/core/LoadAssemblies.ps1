$libPath = Join-Path $PSScriptRoot '..' 'deps' 'lib'

if (-not (Test-Path $libPath)) {
    throw "Dependencies not found at '$libPath'. Run setup.ps1 first."
}

$resolveHandler = [System.ResolveEventHandler]{
    param($sender, $args)
    $name = [System.Reflection.AssemblyName]::new($args.Name).Name
    $dll  = Join-Path $libPath "$name.dll"
    if (Test-Path $dll) {
        return [System.Reflection.Assembly]::LoadFrom($dll)
    }
    return $null
}
[System.AppDomain]::CurrentDomain.add_AssemblyResolve($resolveHandler)

Add-Type -Path (Join-Path $libPath 'Microsoft.Data.Sqlite.dll')
Add-Type -Path (Join-Path $libPath 'RabbitMQ.Client.dll')

try { [SQLitePCL.Batteries_V2]::Init() } catch {}
