# HIPAA Compliance Posture

This document describes the HIPAA compliance configuration for the Impressions Generator healthcare application, covering the Business Associate Agreement (BAA) requirements, encryption, logging, and Azure resource security settings.

## Business Associate Agreement (BAA)

A BAA must be executed with Microsoft for all Azure subscriptions used to deploy this application. Azure services used in this project are **BAA-eligible**:

| Service              | BAA-Eligible | Notes                                                      |
|----------------------|--------------|------------------------------------------------------------|
| Azure Cosmos DB      | Yes          | NoSQL database for clinical data                           |
| Azure Blob Storage   | Yes          | Storage for historical clinical notes                      |
| Azure OpenAI         | Yes          | GPT-4o for report generation; data not used for training   |
| Azure AI Search      | Yes          | Vector search index for RAG retrieval                      |
| Azure Key Vault      | Yes          | Secret and key management                                  |
| Azure Container Apps | Yes          | Backend API hosting                                        |
| Azure Static Web Apps| Yes          | Frontend hosting                                           |
| Azure Monitor        | Yes          | Log Analytics and Application Insights                     |

> **Action required**: Before deploying to production, verify that a BAA is signed at the Azure subscription level via the Microsoft Trust Center.

## Region

All resources are deployed to **Sweden Central** (`swedencentral`), a HIPAA-eligible Azure region. This is enforced in `infrastructure/main.bicep` and `infrastructure/main.bicepparam`.

## Encryption at Rest

All data stores use **Azure-managed encryption keys** (Microsoft-managed keys):

- **Cosmos DB**: Encryption at rest is enabled by default and cannot be disabled. Uses Azure-managed keys.
- **Blob Storage**: Encryption explicitly configured with `keySource: 'Microsoft.Storage'` for blob and file services.
- **AI Search**: Encryption at rest is enabled by default with Azure-managed keys.
- **Key Vault**: Data is encrypted at rest using Microsoft-managed keys.

## Encryption in Transit

TLS 1.2 or higher is enforced on all service endpoints:

| Service          | Setting                              |
|------------------|--------------------------------------|
| Cosmos DB        | `minimalTlsVersion: 'Tls12'`        |
| Blob Storage     | `minimumTlsVersion: 'TLS1_2'`, `supportsHttpsTrafficOnly: true` |
| Container Apps   | `allowInsecure: false` (HTTPS only)  |
| Azure OpenAI     | TLS 1.2 enforced by Azure platform   |
| AI Search        | TLS 1.2 enforced by Azure platform   |

## Azure OpenAI Data Processing

Azure OpenAI is configured for HIPAA-compliant data processing:

- Customer data sent via the API is **not used for model training**.
- Data is processed within the Azure tenant boundary.
- The service is BAA-eligible when accessed through the Azure OpenAI API (not consumer ChatGPT).
- `raiPolicyName: 'Microsoft.DefaultV2'` is applied to the GPT-4o deployment.

## Key Vault Security

- **Soft delete**: Enabled (`enableSoftDelete: true`, 90-day retention)
- **Purge protection**: Enabled for all environments (`enablePurgeProtection: true`)
- **RBAC authorization**: Enabled (`enableRbacAuthorization: true`); no access policies used
- **Deployment access**: Disabled (`enabledForDeployment`, `enabledForDiskEncryption`, `enabledForTemplateDeployment` all `false`)

## Storage Account Security

- **Shared key access**: Disabled (`allowSharedKeyAccess: false`)
- **Authentication**: Managed identity only (Azure AD / Entra ID)
- **Public blob access**: Disabled (`allowBlobPublicAccess: false`)
- **HTTPS only**: Enforced (`supportsHttpsTrafficOnly: true`)
- **Soft delete**: Blob retention enabled (30 days)

## Cosmos DB Security

- **Key-based metadata write access**: Disabled (`disableKeyBasedMetadataWriteAccess: true`)
- **Managed identity**: System-assigned identity enabled
- **TLS**: Minimum version 1.2

## PHI in Application Logs

A `PHISanitizingFilter` is attached to the root Python logger to redact common PHI patterns before log emission:

- Social Security Numbers
- Medical Record Numbers (MRN)
- Phone numbers
- Email addresses
- Dates of birth
- Patient name patterns

The filter is defined in `backend/app/utils/phi_sanitizer.py` and applied in `backend/app/main.py`.

> **Best practice**: Developers must avoid logging raw clinical text (dictated notes, report content). Log only identifiers (doctor ID, report ID, note ID) and operational metadata.

## Bicep Security Enforcement

All security settings are codified in the Bicep templates under `infrastructure/modules/`. Key enforcements:

- Region locked to `swedencentral`
- TLS 1.2+ on all services
- Encryption at rest with Azure-managed keys
- Key Vault purge protection enabled
- Storage shared key access disabled
- RBAC-based access on Key Vault
- System-assigned managed identities on all services

## Compliance Checklist

- [x] All services in swedencentral (HIPAA-eligible region)
- [x] Encryption at rest: Azure-managed keys on Cosmos DB, Blob Storage, AI Search
- [x] Encryption in transit: TLS 1.2+ enforced on all endpoints
- [x] Azure OpenAI: data processed within tenant, no model training on customer data
- [x] Key Vault: soft delete and purge protection enabled
- [x] Storage: shared key access disabled (managed identity only)
- [x] PHI sanitization filter on application logs
- [x] BAA requirements documented
- [x] Bicep templates enforce all security settings
