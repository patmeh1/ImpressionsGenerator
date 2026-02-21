// ============================================================================
// Main Orchestrator — Impressions Generator Infrastructure
// Healthcare application (HIPAA considerations) deployed to swedencentral
// Deploys all modules in dependency order via subscription-scoped deployment
// ============================================================================

targetScope = 'subscription'

@allowed(['dev', 'staging', 'prod'])
@description('Deployment environment')
param environmentName string

@description('Azure region for all resources')
param location string = 'swedencentral'

@description('Project name used for resource naming')
param projectName string = 'impgen'

// --- Resource Group ---
resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: '${projectName}-rg-${environmentName}'
  location: location
  tags: {
    environment: environmentName
    project: projectName
    compliance: 'HIPAA'
    managedBy: 'bicep'
  }
}

// --- 1. Monitoring (Log Analytics + App Insights) ---
module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- 2. Storage Account ---
module storage 'modules/storage.bicep' = {
  name: 'storage-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- 3. Cosmos DB ---
module cosmosdb 'modules/cosmosdb.bicep' = {
  name: 'cosmosdb-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- 4. Azure OpenAI ---
module openai 'modules/openai.bicep' = {
  name: 'openai-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- 5. AI Search ---
module aiSearch 'modules/ai-search.bicep' = {
  name: 'ai-search-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- 6. Container Apps (depends on monitoring, storage, cosmosdb, openai, ai-search) ---
module containerApps 'modules/container-apps.bicep' = {
  name: 'container-apps-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
    cosmosEndpoint: cosmosdb.outputs.cosmosEndpoint
    storageAccountName: storage.outputs.storageAccountName
    blobEndpoint: storage.outputs.blobEndpoint
    openaiEndpoint: openai.outputs.openaiEndpoint
    openaiDeploymentName: openai.outputs.openaiDeploymentName
    searchEndpoint: aiSearch.outputs.searchEndpoint
    searchServiceName: aiSearch.outputs.searchServiceName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
  }
}

// --- 7. Key Vault (depends on container apps for principal ID) ---
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
    containerAppPrincipalId: containerApps.outputs.containerAppPrincipalId
    cosmosEndpoint: cosmosdb.outputs.cosmosEndpoint
    storageAccountName: storage.outputs.storageAccountName
    openaiEndpoint: openai.outputs.openaiEndpoint
    searchEndpoint: aiSearch.outputs.searchEndpoint
  }
}

// --- 8. Static Web App ---
module staticWebApp 'modules/static-web-app.bicep' = {
  name: 'static-web-app-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- Outputs ---
output resourceGroupName string = resourceGroup.name
output containerAppUrl string = containerApps.outputs.containerAppUrl
output staticWebAppUrl string = staticWebApp.outputs.staticWebAppUrl
output cosmosEndpoint string = cosmosdb.outputs.cosmosEndpoint
output openaiEndpoint string = openai.outputs.openaiEndpoint
output searchEndpoint string = aiSearch.outputs.searchEndpoint
output keyVaultUri string = keyvault.outputs.keyVaultUri
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString
output storageAccountName string = storage.outputs.storageAccountName
