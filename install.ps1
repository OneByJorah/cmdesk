#Requires -Version 5.1
<#
.SYNOPSIS
    Windows installer for cmdesk via Docker Desktop.
#>
param(
    [switch]$SkipStart
)

$ErrorActionPreference = "Stop"

Write-Host "=== Installing cmdesk ===" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker Desktop is required but not found. Install it from https://www.docker.com/products/docker-desktop/"
}

$envFile = Join-Path $PSScriptRoot ".env"
$envExample = Join-Path $PSScriptRoot ".env.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "Created .env from .env.example. Review values before production use." -ForegroundColor Yellow
    } else {
        New-Item -ItemType File -Path $envFile -Force | Out-Null
    }
}

$composeCmd = if (Get-Command "docker" -ErrorAction SilentlyContinue) { "docker compose" } else { "docker-compose" }

if (-not $SkipStart) {
    Write-Host "Building and starting cmdesk on port 8080..." -ForegroundColor Green
    Invoke-Expression "$composeCmd up --build -d"
    Write-Host "cmdesk installed. Access: http://localhost:8080" -ForegroundColor Green
} else {
    Write-Host "Skipped start. Run '$composeCmd up --build -d' when ready." -ForegroundColor Yellow
}
