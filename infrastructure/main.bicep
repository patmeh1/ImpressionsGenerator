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

// --- User-Assigned Managed Identity (shared by container app + Key Vault RBAC) ---
module managedIdentity 'modules/managed-identity.bicep' = {
  name: 'managed-identity-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
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
  dependsOn: [monitoring]
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
  dependsOn: [storage]
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- 4. Key Vault (depends on cosmosdb, storage; uses managed identity for RBAC) ---
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
    appIdentityPrincipalId: managedIdentity.outputs.principalId
    cosmosEndpoint: cosmosdb.outputs.cosmosEndpoint
    storageAccountName: storage.outputs.storageAccountName
  }
}

// --- 5. Azure OpenAI ---
module openai 'modules/openai.bicep' = {
  name: 'openai-deployment'
  scope: resourceGroup
  dependsOn: [keyvault]
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- 6. AI Search ---
module aiSearch 'modules/ai-search.bicep' = {
  name: 'ai-search-deployment'
  scope: resourceGroup
  dependsOn: [openai]
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
  }
}

// --- 7. Container Apps (depends on all upstream modules) ---
module containerApps 'modules/container-apps.bicep' = {
  name: 'container-apps-deployment'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    projectName: projectName
    managedIdentityId: managedIdentity.outputs.identityId
    managedIdentityClientId: managedIdentity.outputs.clientId
    cosmosEndpoint: cosmosdb.outputs.cosmosEndpoint
    storageAccountName: storage.outputs.storageAccountName
    blobEndpoint: storage.outputs.blobEndpoint
    openaiEndpoint: openai.outputs.openaiEndpoint
    openaiDeploymentName: openai.outputs.openaiDeploymentName
    searchEndpoint: aiSearch.outputs.searchEndpoint
    searchServiceName: aiSearch.outputs.searchServiceName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    keyVaultUri: keyvault.outputs.keyVaultUri
  }
}

// --- 8. Static Web App ---
module staticWebApp 'modules/static-web-app.bicep' = {
  name: 'static-web-app-deployment'
  scope: resourceGroup
  dependsOn: [containerApps]
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
