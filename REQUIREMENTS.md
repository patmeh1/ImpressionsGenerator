# Impressions Generator — Requirements Document

## 1. Business Requirements

### 1.1 Problem Statement

Radiologists and oncologists spend significant time writing structured clinical reports (findings, impressions, and recommendations). Each physician has a distinct writing style, and current tools do not preserve individual documentation patterns. Manual report writing is time-consuming and inconsistent.

### 1.2 Solution Overview

The Impressions Generator allows doctors to:

- Upload or paste their historical clinical notes so the system can learn their unique writing style.
- Dictate or input clinical observations for a new case.
- Receive AI-generated report sections (findings, impressions, recommendations) that match their personal documentation style.
- Review, edit, and finalize generated reports before saving.

### 1.3 Key Business Rules

- **No hallucinated clinical data.** The system must only generate text grounded in the doctor's input and historical style patterns. It must never fabricate diagnoses, measurements, or clinical findings.
- **Doctor ownership.** Each doctor's style profile and historical notes are private to that doctor and administrators.
- **Auditability.** All generated reports must be versioned, and the original input must be preserved alongside the generated output.

---

## 2. Functional Requirements

### 2.1 Authentication and Authorization

| ID | Requirement |
|---|---|
| FR-01 | Users authenticate via Microsoft Entra ID (Azure AD). |
| FR-02 | Two roles: **Doctor** and **Admin**. Doctors access their own data; Admins access all data. |
| FR-03 | Unauthenticated users are redirected to the login page. |
| FR-04 | Session tokens are validated on every API request. |

### 2.2 Doctor Profiles

| ID | Requirement |
|---|---|
| FR-05 | Each doctor has a profile containing: name, specialty (radiology/oncology), style preferences, and associated historical notes. |
| FR-06 | Doctors can view and update their profile settings. |

### 2.3 Historical Note Upload

| ID | Requirement |
|---|---|
| FR-07 | Doctors can upload historical clinical notes in **PDF**, **DOCX**, or **TXT** format. |
| FR-08 | Doctors can paste note text directly into the application. |
| FR-09 | Uploaded files are stored in Azure Blob Storage and indexed in Azure AI Search. |
| FR-10 | The system extracts and indexes the text content from uploaded documents. |
| FR-11 | Doctors can view, search, and delete their uploaded notes. |

### 2.4 Style Extraction

| ID | Requirement |
|---|---|
| FR-12 | The system analyzes a doctor's historical notes to extract their writing style profile (tone, terminology, structure, formatting patterns). |
| FR-13 | Style profiles are stored in Cosmos DB and updated when new notes are uploaded. |
| FR-14 | Doctors can view a summary of their extracted style profile. |

### 2.5 Report Generation

| ID | Requirement |
|---|---|
| FR-15 | Doctors provide clinical input (free text or dictation transcript) for a new case. |
| FR-16 | The system generates three report sections: **Findings**, **Impressions**, and **Recommendations**. |
| FR-17 | Generated output matches the doctor's extracted writing style. |
| FR-18 | The system uses retrieval-augmented generation (RAG) with Azure AI Search to ground output in the doctor's historical notes. |

### 2.6 Grounding Validation

| ID | Requirement |
|---|---|
| FR-19 | The system validates that generated content does not contain hallucinated clinical data (e.g., fabricated measurements, diagnoses, or patient identifiers). |
| FR-20 | A confidence score is returned with each generated section indicating grounding quality. |

### 2.7 Review and Edit

| ID | Requirement |
|---|---|
| FR-21 | Doctors can review generated report sections in a side-by-side view (input vs. generated output). |
| FR-22 | Doctors can edit any generated section before finalizing. |
| FR-23 | Doctors can regenerate individual sections with adjusted parameters. |

### 2.8 Report Versioning

| ID | Requirement |
|---|---|
| FR-24 | Every generated and edited report is saved as a versioned record in Cosmos DB. |
| FR-25 | Doctors can view the version history of any report. |
| FR-26 | Doctors can revert to a previous version of a report. |

### 2.9 Admin Dashboard

| ID | Requirement |
|---|---|
| FR-27 | Admins can view a list of all doctors and their profiles. |
| FR-28 | Admins can view usage statistics (reports generated, notes uploaded, active users). |
| FR-29 | Admins can manage doctor accounts (activate, deactivate). |
| FR-30 | Admins can view system health and Azure service status. |

---

## 3. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-01 | **HIPAA Compliance** | All data handling, storage, and transmission must comply with HIPAA regulations. BAA must be in place with Azure. |
| NFR-02 | **Response Time** | Report generation must complete in < 30 seconds. |
| NFR-03 | **Concurrent Users** | The system must support at least 10 concurrent users. |
| NFR-04 | **Accessibility** | The frontend must conform to WCAG 2.1 Level AA. |
| NFR-05 | **Encryption in Transit** | All communication must use TLS 1.2 or higher. |
| NFR-06 | **Encryption at Rest** | All stored data (Cosmos DB, Blob Storage) must be encrypted at rest using Azure-managed keys. |
| NFR-07 | **Availability** | 99.9% uptime SLA for production deployment. |
| NFR-08 | **Audit Logging** | All user actions (login, generation, edits) must be logged to Azure Monitor. |
| NFR-09 | **Data Residency** | All data must remain in the **swedencentral** Azure region. |
| NFR-10 | **Backup** | Cosmos DB continuous backup enabled with 7-day retention. |

---

## 4. Frontend Requirements

### 4.1 Pages and Routes

| Route | Page | Description | Access |
|---|---|---|---|
| `/` | Landing / Login | Welcome page with Entra ID sign-in button. | Public |
| `/dashboard` | Dashboard | Overview of recent reports, quick actions, and stats. | Doctor, Admin |
| `/generate` | Generate Report | Input clinical observations and generate report sections. | Doctor |
| `/review/:id` | Review Report | Side-by-side view of input and generated output; edit and finalize. | Doctor |
| `/history` | Report History | Searchable list of past reports with version history. | Doctor |
| `/profile/notes` | Profile & Notes | Manage profile settings and historical note uploads. | Doctor |
| `/admin` | Admin Dashboard | System-wide usage stats, doctor list, and system health. | Admin |
| `/admin/doctors/:id` | Doctor Detail (Admin) | View and manage a specific doctor's profile and activity. | Admin |

### 4.2 UI Components

| Component | Description |
|---|---|
| `LoginButton` | Entra ID sign-in trigger. |
| `Navbar` | Top navigation with role-based menu items. |
| `ReportInput` | Textarea / dictation input for clinical observations. |
| `ReportOutput` | Rendered generated sections (Findings, Impressions, Recommendations). |
| `ReportEditor` | Rich-text editor for reviewing and editing generated sections. |
| `NoteUploader` | Drag-and-drop file upload for PDF/DOCX/TXT with paste support. |
| `NoteList` | Searchable table of uploaded historical notes. |
| `StyleSummary` | Display of the doctor's extracted writing style profile. |
| `VersionTimeline` | Visual timeline of report versions. |
| `ConfidenceBadge` | Displays grounding confidence score per section. |
| `StatsCards` | Dashboard summary cards (reports generated, notes count, etc.). |
| `DoctorTable` | Admin table listing all doctors with status and actions. |
| `SystemHealth` | Admin view of Azure service health indicators. |

### 4.3 UX Requirements

- Responsive design for desktop and tablet (minimum 768px width).
- Loading spinners and skeleton screens during API calls.
- Toast notifications for success, error, and warning states.
- Keyboard-navigable interface for accessibility.
- Dark mode support (optional, phase 2).

---

## 5. Azure Infrastructure

### 5.1 Resource Deployment

All Azure resources are deployed in the **swedencentral** region using **Bicep** templates.

| Resource | Bicep Module | Notes |
|---|---|---|
| Resource Group | `main.bicep` | `rg-impressions-generator` |
| Azure OpenAI | `modules/openai.bicep` | GPT-4o deployment |
| Azure Cosmos DB | `modules/cosmosdb.bicep` | NoSQL API, continuous backup |
| Azure AI Search | `modules/search.bicep` | Standard tier, semantic ranking |
| Azure Blob Storage | `modules/storage.bicep` | Hot tier, `clinical-notes` container |
| Azure App Service | `modules/appservice.bicep` | Python 3.11 runtime |
| Azure Static Web Apps | `modules/swa.bicep` | Next.js frontend |
| Azure Key Vault | `modules/keyvault.bicep` | Secrets management |
| Application Insights | `modules/monitoring.bicep` | Connected to App Service |

### 5.2 Managed Identities

- The App Service uses a **system-assigned managed identity** to access Cosmos DB, Blob Storage, AI Search, Azure OpenAI, and Key Vault.
- No API keys are stored in application configuration in production; all secrets are fetched from Key Vault via managed identity.

### 5.3 Networking

- All services use private endpoints where available.
- The App Service and Static Web Apps communicate over Azure backbone networking.

---

## 6. Test Requirements

### 6.1 Unit Tests — Backend (T01–T15)

| ID | Test Case | Description | Expected Result |
|---|---|---|---|
| T01 | Auth token validation | Validate a correct Entra ID JWT token. | Token accepted, user context returned. |
| T02 | Auth token rejection | Validate an expired or malformed JWT token. | 401 Unauthorized returned. |
| T03 | Role extraction | Extract role (Doctor/Admin) from token claims. | Correct role returned. |
| T04 | Doctor profile creation | Create a new doctor profile via service layer. | Profile stored in Cosmos DB with correct fields. |
| T05 | Doctor profile update | Update specialty and preferences. | Updated fields persisted. |
| T06 | File upload — PDF | Upload a PDF file and extract text. | Text extracted and stored in Blob Storage. |
| T07 | File upload — DOCX | Upload a DOCX file and extract text. | Text extracted and stored in Blob Storage. |
| T08 | File upload — TXT | Upload a TXT file. | Content stored in Blob Storage. |
| T09 | File upload — invalid type | Upload an unsupported file type (e.g., .exe). | 400 Bad Request returned. |
| T10 | Style extraction | Run style extraction on a set of historical notes. | Style profile JSON returned with tone, structure, terminology. |
| T11 | Report generation | Generate findings, impressions, recommendations from clinical input. | Three non-empty sections returned. |
| T12 | Report generation — empty input | Generate report with empty clinical input. | 422 Validation Error returned. |
| T13 | Grounding validation — pass | Validate generated text with no hallucinations. | Confidence score ≥ 0.8. |
| T14 | Grounding validation — fail | Validate generated text containing fabricated data. | Confidence score < 0.5, warning flag set. |
| T15 | Report versioning | Save two versions of a report and retrieve version history. | Two versions returned in chronological order. |

### 6.2 Unit Tests — Frontend (T16–T22)

| ID | Test Case | Description | Expected Result |
|---|---|---|---|
| T16 | Login button render | Render the LoginButton component. | Button displays "Sign in with Microsoft". |
| T17 | Navbar — Doctor role | Render Navbar for a Doctor user. | Shows Dashboard, Generate, History, Profile links. |
| T18 | Navbar — Admin role | Render Navbar for an Admin user. | Shows Dashboard, Admin links. |
| T19 | ReportInput validation | Submit ReportInput with empty text. | Validation error displayed, submit disabled. |
| T20 | ReportOutput rendering | Render ReportOutput with mock data. | Findings, Impressions, Recommendations sections displayed. |
| T21 | NoteUploader — valid file | Drop a .pdf file onto NoteUploader. | File accepted, upload initiated. |
| T22 | NoteUploader — invalid file | Drop a .exe file onto NoteUploader. | Error message displayed, upload rejected. |

### 6.3 Integration Tests (T23–T26)

| ID | Test Case | Description | Expected Result |
|---|---|---|---|
| T23 | End-to-end note upload | Upload a PDF → verify stored in Blob Storage → verify indexed in AI Search. | File accessible in Blob, searchable in AI Search index. |
| T24 | Style extraction pipeline | Upload 5 notes → trigger style extraction → verify style profile saved. | Style profile in Cosmos DB matches expected structure. |
| T25 | Report generation pipeline | Provide input → generate report → verify report saved with version 1. | Report in Cosmos DB with version 1 and three sections. |
| T26 | Auth flow | Authenticate via Entra ID → call protected API endpoint. | API returns 200 with user-specific data. |

### 6.4 End-to-End Tests (T27–T30)

| ID | Test Case | Description | Expected Result |
|---|---|---|---|
| T27 | Doctor full workflow | Login → upload notes → generate report → review → finalize. | Report saved with correct doctor ID and version. |
| T28 | Report editing | Generate report → edit impressions section → save as new version. | Version 2 created with edited content. |
| T29 | Admin doctor management | Admin login → view doctor list → deactivate a doctor. | Doctor status updated to inactive. |
| T30 | Report history navigation | Login → navigate to history → view a past report → view version timeline. | All versions displayed in correct order. |

### 6.5 Non-Functional Tests (T31–T35)

| ID | Test Case | Description | Expected Result |
|---|---|---|---|
| T31 | Response time | Generate a report and measure end-to-end latency. | Latency < 30 seconds. |
| T32 | Concurrent users | Simulate 10 concurrent report generation requests. | All requests complete successfully without errors. |
| T33 | Accessibility audit | Run axe-core against all frontend pages. | No WCAG 2.1 AA violations. |
| T34 | TLS verification | Verify all endpoints enforce TLS 1.2+. | Connections using TLS < 1.2 are rejected. |
| T35 | Data encryption at rest | Verify Cosmos DB and Blob Storage encryption settings. | Encryption at rest enabled with Azure-managed keys. |
