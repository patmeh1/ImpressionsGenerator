// ============================================================================
// Azure OpenAI Module — Cognitive Services account + GPT-4o deployment
// Used for generating medical impressions from clinical notes
// HIPAA: Azure OpenAI API does not use customer data for model training.
// Data is processed within the tenant boundary. BAA-eligible service.
// ============================================================================

@description('Azure region for all resources')
param location string

@allowed(['dev', 'staging', 'prod'])
@description('Environment name')
param environmentName string

@description('Project name used for resource naming')
param projectName string

// 30K TPM for dev/staging, 120K TPM for prod
var modelCapacity = environmentName == 'prod' ? 120 : 30

// --- Azure OpenAI Account ---
resource openaiAccount 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' = {
  name: '${projectName}-openai-${environmentName}'
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: '${projectName}-openai-${environmentName}'
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

// --- GPT-4o Model Deployment ---
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-04-01-preview' = {
  parent: openaiAccount
  name: 'gpt-4o'
  sku: {
    name: 'Standard'
    capacity: modelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
    raiPolicyName: 'Microsoft.DefaultV2'
  }
}

// --- Outputs ---
output openaiEndpoint string = openaiAccount.properties.endpoint
output openaiAccountId string = openaiAccount.id
output openaiDeploymentName string = gpt4oDeployment.name
