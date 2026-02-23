// ============================================================================
// Monitoring Module — Log Analytics Workspace + Application Insights
// + Azure Monitor Dashboard, Alert Rules, and Log Analytics Saved Queries
// Healthcare app: retains logs for 90 days (HIPAA audit trail)
// ============================================================================

@description('Azure region for all resources')
param location string

@allowed(['dev', 'staging', 'prod'])
@description('Environment name')
param environmentName string

@description('Project name used for resource naming')
param projectName string

@description('Email address for alert notifications')
param alertEmail string = 'ops-team@example.com'

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

// --- Action Group for alert notifications ---
resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: '${projectName}-ag-${environmentName}'
  location: 'global'
  properties: {
    groupShortName: 'ImpGenAlerts'
    enabled: true
    emailReceivers: [
      {
        name: 'OpsTeam'
        emailAddress: alertEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

// --- Alert: Error rate > 1% ---
resource errorRateAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-alert-errorrate-${environmentName}'
  location: location
  properties: {
    displayName: 'API Error Rate > 1%'
    description: 'Fires when the percentage of 5xx responses exceeds 1% over 5 minutes.'
    severity: 2
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    scopes: [
      appInsights.id
    ]
    criteria: {
      allOf: [
        {
          query: '''
            requests
            | summarize totalCount = count(), failedCount = countif(toint(resultCode) >= 500)
            | extend errorPct = (todouble(failedCount) / todouble(totalCount)) * 100
            | where errorPct > 1
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
  }
}

// --- Alert: P95 latency > 10s ---
resource latencyAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-alert-latency-${environmentName}'
  location: location
  properties: {
    displayName: 'P95 Latency > 10s'
    description: 'Fires when P95 request duration exceeds 10 seconds.'
    severity: 3
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    scopes: [
      appInsights.id
    ]
    criteria: {
      allOf: [
        {
          query: '''
            requests
            | summarize p95_duration = percentile(duration, 95)
            | where p95_duration > 10000
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
  }
}

// --- Alert: OpenAI token budget > 80% ---
resource tokenBudgetAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-alert-tokenbudget-${environmentName}'
  location: location
  properties: {
    displayName: 'OpenAI Token Budget > 80%'
    description: 'Fires when daily cumulative token usage exceeds 80% of the 1M budget.'
    severity: 3
    enabled: true
    evaluationFrequency: 'PT15M'
    windowSize: 'PT1H'
    scopes: [
      appInsights.id
    ]
    criteria: {
      allOf: [
        {
          query: '''
            customMetrics
            | where name == "openai.total_tokens"
            | where timestamp > ago(1d)
            | summarize dailyTokens = sum(valueSum)
            | where dailyTokens > 800000
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
  }
}

// --- Alert: Service health degradation (availability < 99%) ---
resource healthAlert 'Microsoft.Insights/scheduledQueryRules@2023-03-15-preview' = {
  name: '${projectName}-alert-health-${environmentName}'
  location: location
  properties: {
    displayName: 'Service Health Degradation'
    description: 'Fires when /health availability drops below 99% over 5 minutes.'
    severity: 1
    enabled: true
    evaluationFrequency: 'PT5M'
    windowSize: 'PT5M'
    scopes: [
      appInsights.id
    ]
    criteria: {
      allOf: [
        {
          query: '''
            requests
            | where url has "/health"
            | summarize total = count(), success = countif(toint(resultCode) < 400)
            | extend availability = (todouble(success) / todouble(total)) * 100
            | where availability < 99
          '''
          timeAggregation: 'Count'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
        }
      ]
    }
    actions: {
      actionGroups: [
        actionGroup.id
      ]
    }
  }
}

// --- Azure Monitor Dashboard ---
resource dashboard 'Microsoft.Portal/dashboards@2020-09-01-preview' = {
  name: '${projectName}-dashboard-${environmentName}'
  location: location
  tags: {
    'hidden-title': 'Impressions Generator – ${environmentName}'
  }
  properties: {
    lenses: [
      {
        order: 0
        parts: [
          {
            position: { x: 0, y: 0, colSpan: 6, rowSpan: 4 }
            metadata: {
              type: 'Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart'
              inputs: [
                { name: 'resourceTypeMode', value: 'workspace' }
                { name: 'ComponentId', value: logAnalytics.id }
                { name: 'Query', value: 'requests | summarize count() by bin(timestamp, 5m), resultCode | render timechart' }
                { name: 'PartTitle', value: 'API Health – Request Count by Status' }
              ]
            }
          }
          {
            position: { x: 6, y: 0, colSpan: 6, rowSpan: 4 }
            metadata: {
              type: 'Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart'
              inputs: [
                { name: 'resourceTypeMode', value: 'workspace' }
                { name: 'ComponentId', value: logAnalytics.id }
                { name: 'Query', value: 'requests | where toint(resultCode) >= 500 | summarize errorCount = count() by bin(timestamp, 5m) | render timechart' }
                { name: 'PartTitle', value: 'Error Rate (5xx)' }
              ]
            }
          }
          {
            position: { x: 0, y: 4, colSpan: 6, rowSpan: 4 }
            metadata: {
              type: 'Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart'
              inputs: [
                { name: 'resourceTypeMode', value: 'workspace' }
                { name: 'ComponentId', value: logAnalytics.id }
                { name: 'Query', value: 'requests | summarize p50=percentile(duration,50), p90=percentile(duration,90), p95=percentile(duration,95), p99=percentile(duration,99) by bin(timestamp, 5m) | render timechart' }
                { name: 'PartTitle', value: 'Latency Percentiles' }
              ]
            }
          }
          {
            position: { x: 6, y: 4, colSpan: 6, rowSpan: 4 }
            metadata: {
              type: 'Extension/Microsoft_OperationsManagementSuite_Workspace/PartType/LogsDashboardPart'
              inputs: [
                { name: 'resourceTypeMode', value: 'workspace' }
                { name: 'ComponentId', value: logAnalytics.id }
                { name: 'Query', value: 'requests | summarize dcount(client_IP) by bin(timestamp, 1h) | render timechart' }
                { name: 'PartTitle', value: 'Active Users (hourly)' }
              ]
            }
          }
        ]
      }
    ]
  }
}

// --- Log Analytics Saved Queries ---
resource queryPack 'Microsoft.OperationalInsights/queryPacks@2019-09-01' = {
  name: '${projectName}-qp-${environmentName}'
  location: location
  properties: {}
}

resource querySlowRequests 'Microsoft.OperationalInsights/queryPacks/queries@2019-09-01' = {
  parent: queryPack
  name: guid('${projectName}-slow-requests-${environmentName}')
  properties: {
    displayName: 'Slow Requests (> 5s)'
    description: 'Find requests taking longer than 5 seconds.'
    body: 'requests | where duration > 5000 | project timestamp, name, url, duration, resultCode | order by duration desc | take 50'
    tags: {
      labels: ['troubleshooting']
    }
  }
}

resource queryFailedGenerations 'Microsoft.OperationalInsights/queryPacks/queries@2019-09-01' = {
  parent: queryPack
  name: guid('${projectName}-failed-gens-${environmentName}')
  properties: {
    displayName: 'Failed Report Generations'
    description: 'Find failed generation requests with error details.'
    body: 'requests | where url has "/generate" and toint(resultCode) >= 400 | project timestamp, url, resultCode, duration | order by timestamp desc | take 50'
    tags: {
      labels: ['troubleshooting']
    }
  }
}

resource queryTokenUsage 'Microsoft.OperationalInsights/queryPacks/queries@2019-09-01' = {
  parent: queryPack
  name: guid('${projectName}-token-usage-${environmentName}')
  properties: {
    displayName: 'OpenAI Token Usage (daily)'
    description: 'Daily OpenAI token consumption breakdown.'
    body: 'customMetrics | where name startswith "openai." | summarize totalTokens = sum(valueSum) by name, bin(timestamp, 1d) | order by timestamp desc'
    tags: {
      labels: ['cost', 'openai']
    }
  }
}

resource queryPipelineTracing 'Microsoft.OperationalInsights/queryPacks/queries@2019-09-01' = {
  parent: queryPack
  name: guid('${projectName}-pipeline-trace-${environmentName}')
  properties: {
    displayName: 'Generation Pipeline Trace'
    description: 'End-to-end trace of generation pipeline steps.'
    body: 'dependencies | where name in ("style_retrieval", "few_shot_retrieval", "openai_call", "grounding_validation", "persist_report") | project timestamp, name, duration, success, operation_Id | order by timestamp desc | take 100'
    tags: {
      labels: ['tracing', 'troubleshooting']
    }
  }
}

// --- Outputs ---
output logAnalyticsWorkspaceId string = logAnalytics.id
output appInsightsConnectionString string = appInsights.properties.ConnectionString
output appInsightsInstrumentationKey string = appInsights.properties.InstrumentationKey
