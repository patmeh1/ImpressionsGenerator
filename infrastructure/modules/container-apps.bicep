// ============================================================================
// Container Apps Module — Environment + FastAPI backend container
// User-assigned managed identity for Key Vault / Cosmos / Storage access
// ============================================================================

@description('Azure region for all resources')
param location string

@allowed(['dev', 'staging', 'prod'])
@description('Environment name')
param environmentName string

@description('Project name used for resource naming')
param projectName string

@description('Container image to deploy')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('User-assigned managed identity resource ID')
param managedIdentityId string

@description('User-assigned managed identity client ID')
param managedIdentityClientId string

@description('Cosmos DB endpoint')
param cosmosEndpoint string

@description('Storage account name')
param storageAccountName string

@description('Blob storage endpoint')
param blobEndpoint string

@description('Azure OpenAI endpoint')
param openaiEndpoint string

@description('OpenAI model deployment name')
param openaiDeploymentName string

@description('AI Search endpoint')
param searchEndpoint string

@description('AI Search service name')
param searchServiceName string

@description('Application Insights connection string')
param appInsightsConnectionString string

@description('Log Analytics workspace resource ID')
param logAnalyticsWorkspaceId string

@description('Key Vault URI for secret references')
param keyVaultUri string

var isProduction = environmentName == 'prod'
var minReplicas = isProduction ? 1 : 0
var maxReplicas = isProduction ? 10 : 3

// --- Container Apps Environment ---
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${projectName}-cae-${environmentName}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2023-09-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2023-09-01').primarySharedKey
      }
    }
    zoneRedundant: isProduction
  }
}

// --- Container App (FastAPI backend) ---
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${projectName}-api-${environmentName}'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
        }
      }
      // Secrets are not stored here; app uses managed identity for service access
    }
    template: {
      containers: [
        {
          name: 'api'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'COSMOS_ENDPOINT'
              value: cosmosEndpoint
            }
            {
              name: 'COSMOS_DATABASE_NAME'
              value: 'impressions-db'
            }
            {
              name: 'STORAGE_ACCOUNT_NAME'
              value: storageAccountName
            }
            {
              name: 'BLOB_ENDPOINT'
              value: blobEndpoint
            }
            {
              name: 'OPENAI_ENDPOINT'
              value: openaiEndpoint
            }
            {
              name: 'OPENAI_DEPLOYMENT_NAME'
              value: openaiDeploymentName
            }
            {
              name: 'SEARCH_ENDPOINT'
              value: searchEndpoint
            }
            {
              name: 'SEARCH_SERVICE_NAME'
              value: searchServiceName
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsightsConnectionString
            }
            {
              name: 'ENVIRONMENT'
              value: environmentName
            }
            {
              name: 'KEY_VAULT_URI'
              value: keyVaultUri
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: managedIdentityClientId
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

// --- Outputs ---
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
