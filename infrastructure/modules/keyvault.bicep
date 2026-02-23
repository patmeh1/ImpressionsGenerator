// ============================================================================
// Key Vault Module — Centralized secret management with RBAC
// HIPAA: RBAC access model, soft delete enabled, purge protection for prod
// ============================================================================

@description('Azure region for all resources')
param location string

@allowed(['dev', 'staging', 'prod'])
@description('Environment name')
param environmentName string

@description('Project name used for resource naming')
param projectName string

@description('Principal ID of the app managed identity for secret access')
param appIdentityPrincipalId string

@description('Cosmos DB endpoint to store as secret')
param cosmosEndpoint string = ''

@description('Storage account name to store as secret')
param storageAccountName string = ''

var isProduction = environmentName == 'prod'

// --- Key Vault ---
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: '${projectName}-kv-${environmentName}'
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true // RBAC access model (no access policies)
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enablePurgeProtection: isProduction ? true : null
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    publicNetworkAccess: 'Enabled'
  }
}

// --- RBAC: Grant app identity "Key Vault Secrets User" role ---
// Role definition ID for Key Vault Secrets User: 4633458b-17de-408a-b874-0445c86b69e6
resource secretsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(appIdentityPrincipalId)) {
  name: guid(keyVault.id, appIdentityPrincipalId, '4633458b-17de-408a-b874-0445c86b69e6')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6')
    principalId: appIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// --- Secrets ---
resource cosmosEndpointSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(cosmosEndpoint)) {
  parent: keyVault
  name: 'cosmos-endpoint'
  properties: {
    value: cosmosEndpoint
  }
}

resource storageAccountNameSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = if (!empty(storageAccountName)) {
  parent: keyVault
  name: 'storage-account-name'
  properties: {
    value: storageAccountName
  }
}

// --- Outputs ---
output keyVaultUri string = keyVault.properties.vaultUri
output keyVaultName string = keyVault.name
