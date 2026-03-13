#!/usr/bin/env pwsh
$ErrorActionPreference = 'Stop'

$depsDir = Join-Path $PSScriptRoot 'deps'
$libDir  = Join-Path $depsDir 'lib'

Write-Host 'Restoring .NET dependencies...'
dotnet publish (Join-Path $depsDir 'deps.csproj') -o $libDir --nologo -v quiet

Write-Host "Dependencies installed to deps/lib/"
