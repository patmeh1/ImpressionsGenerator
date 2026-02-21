<#
.SYNOPSIS
    Deploys the Impressions Generator infrastructure to Azure.

.DESCRIPTION
    PowerShell deployment script for the Impressions Generator healthcare app.
    Uses Azure CLI to deploy Bicep templates at subscription scope.

.PARAMETER Environment
    Target environment: dev, staging, or prod.

.PARAMETER Location
    Azure region for deployment. Default: swedencentral.

.PARAMETER ProjectName
    Project name for resource naming. Default: impgen.
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('dev', 'staging', 'prod')]
    [string]$Environment,

    [Parameter(Mandatory = $false)]
    [string]$Location = 'swedencentral',

    [Parameter(Mandatory = $false)]
    [string]$ProjectName = 'impgen'
)

$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$infrastructureDir = Split-Path -Parent $scriptDir

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Impressions Generator - Infrastructure Deploy" -ForegroundColor Cyan
Write-Host " Environment: $Environment" -ForegroundColor Cyan
Write-Host " Location:    $Location" -ForegroundColor Cyan
Write-Host " Project:     $ProjectName" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# --- Check Azure CLI login ---
Write-Host "`nChecking Azure CLI login status..." -ForegroundColor Yellow
try {
    $account = az account show 2>&1 | ConvertFrom-Json
    Write-Host "Logged in as: $($account.user.name)" -ForegroundColor Green
    Write-Host "Subscription: $($account.name) ($($account.id))" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Not logged into Azure CLI. Run 'az login' first." -ForegroundColor Red
    exit 1
}

# --- Deploy Bicep template at subscription scope ---
Write-Host "`nStarting deployment..." -ForegroundColor Yellow

$deploymentName = "$ProjectName-$Environment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$templateFile = Join-Path $infrastructureDir 'main.bicep'

try {
    $result = az deployment sub create `
        --name $deploymentName `
        --location $Location `
        --template-file $templateFile `
        --parameters environmentName=$Environment location=$Location projectName=$ProjectName `
        --output json 2>&1

    $deployment = $result | ConvertFrom-Json

    if ($deployment.properties.provisioningState -eq 'Succeeded') {
        Write-Host "`n============================================" -ForegroundColor Green
        Write-Host " Deployment Succeeded!" -ForegroundColor Green
        Write-Host "============================================" -ForegroundColor Green

        $outputs = $deployment.properties.outputs

        Write-Host "`nDeployed Resource URLs:" -ForegroundColor Cyan
        Write-Host "  Resource Group:    $($outputs.resourceGroupName.value)" -ForegroundColor White
        Write-Host "  Container App:     $($outputs.containerAppUrl.value)" -ForegroundColor White
        Write-Host "  Static Web App:    $($outputs.staticWebAppUrl.value)" -ForegroundColor White
        Write-Host "  Cosmos DB:         $($outputs.cosmosEndpoint.value)" -ForegroundColor White
        Write-Host "  OpenAI:            $($outputs.openaiEndpoint.value)" -ForegroundColor White
        Write-Host "  AI Search:         $($outputs.searchEndpoint.value)" -ForegroundColor White
        Write-Host "  Key Vault:         $($outputs.keyVaultUri.value)" -ForegroundColor White
        Write-Host "  Storage Account:   $($outputs.storageAccountName.value)" -ForegroundColor White
        Write-Host "  App Insights:      (connected)" -ForegroundColor White
    }
    else {
        Write-Host "`nDeployment failed with state: $($deployment.properties.provisioningState)" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "`nERROR: Deployment failed." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
