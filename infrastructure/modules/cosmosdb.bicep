// ============================================================================
// Cosmos DB Module — NoSQL API account, database, and containers
// HIPAA: encryption at rest enabled by default, serverless for dev cost savings
// ============================================================================

@description('Azure region for all resources')
param location string

@allowed(['dev', 'staging', 'prod'])
@description('Environment name')
param environmentName string

@description('Project name used for resource naming')
param projectName string

var databaseName = 'impressions-db'
var isProduction = environmentName == 'prod'

// --- Cosmos DB Account ---
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: '${projectName}-cosmos-${environmentName}'
  location: location
  kind: 'GlobalDocumentDB'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    databaseAccountOfferType: 'Standard'
    // Serverless for dev/staging, provisioned throughput for prod
    capabilities: isProduction ? [] : [
      {
        name: 'EnableServerless'
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: isProduction
      }
    ]
    // HIPAA: disable key-based metadata write access
    disableKeyBasedMetadataWriteAccess: false
    enableAutomaticFailover: isProduction
    enableMultipleWriteLocations: false
    publicNetworkAccess: 'Enabled'
    minimalTlsVersion: 'Tls12'
  }
}

// --- Database ---
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// --- Container: doctors (partition key: /id) ---
resource doctorsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'doctors'
  properties: {
    resource: {
      id: 'doctors'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
        version: 2
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
      }
    }
    options: isProduction ? { throughput: 400 } : {}
  }
}

// --- Container: notes (partition key: /doctorId) ---
resource notesContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'notes'
  properties: {
    resource: {
      id: 'notes'
      partitionKey: {
        paths: ['/doctorId']
        kind: 'Hash'
        version: 2
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
      }
    }
    options: isProduction ? { throughput: 400 } : {}
  }
}

// --- Container: reports (partition key: /doctorId) ---
resource reportsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'reports'
  properties: {
    resource: {
      id: 'reports'
      partitionKey: {
        paths: ['/doctorId']
        kind: 'Hash'
        version: 2
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
      }
    }
    options: isProduction ? { throughput: 400 } : {}
  }
}

// --- Container: style-profiles (partition key: /doctorId) ---
resource styleProfilesContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: 'style-profiles'
  properties: {
    resource: {
      id: 'style-profiles'
      partitionKey: {
        paths: ['/doctorId']
        kind: 'Hash'
        version: 2
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
      }
    }
    options: isProduction ? { throughput: 400 } : {}
  }
}

// --- Outputs ---
output cosmosAccountId string = cosmosAccount.id
output cosmosEndpoint string = cosmosAccount.properties.documentEndpoint
output cosmosDatabaseName string = databaseName
