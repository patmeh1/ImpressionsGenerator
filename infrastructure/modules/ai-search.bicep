// ============================================================================
// Azure AI Search Module — Search service for indexing medical notes
// HIPAA: encryption at rest enabled by default (Azure-managed keys)
// basic SKU for dev/staging, standard for prod
// ============================================================================

@description('Azure region for all resources')
param location string

@allowed(['dev', 'staging', 'prod'])
@description('Environment name')
param environmentName string

@description('Project name used for resource naming')
param projectName string

var skuName = environmentName == 'prod' ? 'standard' : 'basic'

// --- Azure AI Search Service ---
resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: '${projectName}-search-${environmentName}'
  location: location
  sku: {
    name: skuName
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    hostingMode: 'default'
    partitionCount: 1
    replicaCount: 1
    publicNetworkAccess: 'enabled'
    encryptionWithCmk: {
      enforcement: 'Unspecified'
    }
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

// --- Outputs ---
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchServiceId string = searchService.id
output searchServiceName string = searchService.name
