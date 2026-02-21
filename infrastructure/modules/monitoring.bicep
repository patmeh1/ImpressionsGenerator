// ============================================================================
// Monitoring Module — Log Analytics Workspace + Application Insights
// Healthcare app: retains logs for 90 days (HIPAA audit trail)
// ============================================================================

@description('Azure region for all resources')
param location string

@allowed(['dev', 'staging', 'prod'])
@description('Environment name')
param environmentName string

@description('Project name used for resource naming')
param projectName string

// --- Log Analytics Workspace ---
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${projectName}-log-${environmentName}'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: environmentName == 'prod' ? 90 : 30
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

// --- Application Insights (workspace-based) ---
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${projectName}-appi-${environmentName}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
    RetentionInDays: environmentName == 'prod' ? 90 : 30
    DisableIpMasking: false
  }
}

// --- Outputs ---
output logAnalyticsWorkspaceId string = logAnalytics.id
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
