// ============================================================================
// Static Web App Module — Frontend hosting for the React/SPA application
// Free tier for dev/staging, Standard tier for prod
// ============================================================================

@description('Azure region for all resources')
param location string

@allowed(['dev', 'staging', 'prod'])
@description('Environment name')
param environmentName string

@description('Project name used for resource naming')
param projectName string

var skuName = environmentName == 'prod' ? 'Standard' : 'Free'
var skuTier = environmentName == 'prod' ? 'Standard' : 'Free'

// --- Azure Static Web App ---
resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: '${projectName}-swa-${environmentName}'
  location: location
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    stagingEnvironmentPolicy: 'Enabled'
    allowConfigFileUpdates: true
    enterpriseGradeCdnStatus: 'Disabled'
  }
}

// --- Outputs ---
output staticWebAppUrl string = 'https://${staticWebApp.properties.defaultHostname}'
output staticWebAppDefaultHostname string = staticWebApp.properties.defaultHostname
