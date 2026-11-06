# ==============================================================================
# AWS Lambda Layer Build Script for Node.js (Windows PowerShell)
# Creates layer structure: nodejs/node_modules/ -> wa-layer.zip
# ==============================================================================
$ErrorActionPreference = "Stop"

Write-Host "=== 1. Cleaning previous build artifacts ===" -ForegroundColor Cyan
if (Test-Path "nodejs") { Remove-Item -Recurse -Force "nodejs" }
if (Test-Path "wa-layer.zip") { Remove-Item -Force "wa-layer.zip" }

Write-Host "=== 2. Creating required Node.js layer directory structure ===" -ForegroundColor Cyan
New-Item -ItemType Directory -Path "nodejs" | Out-Null
Copy-Item "package.json" -Destination "nodejs/"

Write-Host "=== 3. Installing production dependencies inside nodejs/ ===" -ForegroundColor Cyan
Push-Location "nodejs"
npm install --omit=dev --production
Pop-Location

Write-Host "=== 4. Packaging layer into wa-layer.zip ===" -ForegroundColor Cyan
Compress-Archive -Path "nodejs" -DestinationPath "wa-layer.zip" -Force

Write-Host "=== Done! Layer package ready: wa-layer.zip ===" -ForegroundColor Green

