# Impressions Generator

A healthcare web application for radiology and oncology that generates clinical report sections — findings, impressions, and recommendations — in each doctor's unique writing style using Azure OpenAI.

Doctors upload or paste their historical clinical notes, and the system learns their individual documentation patterns. When generating new reports, the application produces structured output that matches the physician's tone, terminology, and formatting preferences while ensuring no clinical data is hallucinated.

## Architecture Overview

```
┌─────────────────────┐      ┌─────────────────────┐
│   React / Next.js   │◄────►│   FastAPI Backend    │
│   Frontend (SWA)    │      │   (App Service)      │
└─────────────────────┘      └──────────┬──────────┘
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 │                      │                      │
        ┌────────▼────────┐   ┌────────▼────────┐   ┌────────▼────────┐
        │  Azure OpenAI   │   │   Cosmos DB      │   │  Azure Blob     │
        │  (GPT-4o)       │   │   (NoSQL)        │   │  Storage        │
        └─────────────────┘   └─────────────────┘   └─────────────────┘
                 │
        ┌────────▼────────┐
        │  Azure AI       │
        │  Search         │
        └─────────────────┘
```

**Frontend:** React / Next.js hosted on Azure Static Web Apps  
**Backend:** Python FastAPI hosted on Azure App Service  
**AI:** Azure OpenAI (GPT-4o) for report generation and style extraction  
**Database:** Azure Cosmos DB (NoSQL) for doctor profiles, reports, and versioning  
**Search:** Azure AI Search for indexing and retrieving historical notes  
**Storage:** Azure Blob Storage for uploaded documents (PDF, DOCX, TXT)  
**Auth:** Microsoft Entra ID (Azure AD) for authentication and authorization  

## Azure Services

All services are deployed in the **swedencentral** region.

| Service | Purpose |
|---|---|
| Azure OpenAI | GPT-4o model for generating report sections and extracting writing styles |
| Azure Cosmos DB | Store doctor profiles, generated reports, report versions, and metadata |
| Azure AI Search | Index historical notes for retrieval-augmented generation (RAG) |
| Azure Blob Storage | Store uploaded clinical note files (PDF, DOCX, TXT) |
| Azure App Service | Host the FastAPI backend |
| Azure Static Web Apps | Host the Next.js frontend |
| Microsoft Entra ID | Authentication and role-based access control |
| Azure Key Vault | Secure storage of secrets and connection strings |
| Azure Monitor / Application Insights | Logging, tracing, and performance monitoring |

## Prerequisites

- **Node.js** 20+ and npm 10+
- **Python** 3.11+
- **Azure CLI** 2.50+
- **Azure subscription** with access to Azure OpenAI
- **Git** 2.40+
- **Docker** (optional, for containerized local development)

## Local Development Setup

### Backend (FastAPI)

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and fill in values
cp .env.example .env

# Run the development server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### Frontend (Next.js)

```bash
cd frontend

# Install dependencies
npm install

# Copy environment template and fill in values
cp .env.example .env.local

# Run the development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

## Azure Deployment

### Using Bicep

1. **Login to Azure CLI:**

   ```bash
   az login
   az account set --subscription <your-subscription-id>
   ```

2. **Create the resource group:**

   ```bash
   az group create --name rg-impressions-generator --location swedencentral
   ```

3. **Deploy infrastructure:**

   ```bash
   az deployment group create \
     --resource-group rg-impressions-generator \
     --template-file infra/main.bicep \
     --parameters infra/parameters.json
   ```

4. **Deploy the backend:**

   ```bash
   cd backend
   az webapp up --name <app-service-name> --resource-group rg-impressions-generator --runtime "PYTHON:3.11"
   ```

5. **Deploy the frontend:**

   ```bash
   cd frontend
   npm run build
   swa deploy --app-name <swa-name> --resource-group rg-impressions-generator
   ```

## Environment Variables

### Backend

| Variable | Description | Example |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint | `https://<name>.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | `sk-...` |
| `AZURE_OPENAI_DEPLOYMENT` | GPT-4o deployment name | `gpt-4o` |
| `AZURE_OPENAI_API_VERSION` | API version | `2024-02-01` |
| `COSMOS_DB_ENDPOINT` | Cosmos DB endpoint | `https://<name>.documents.azure.com:443/` |
| `COSMOS_DB_KEY` | Cosmos DB primary key | `...` |
| `COSMOS_DB_DATABASE` | Database name | `impressions` |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob Storage connection string | `DefaultEndpointsProtocol=https;...` |
| `AZURE_STORAGE_CONTAINER` | Blob container name | `clinical-notes` |
| `AZURE_SEARCH_ENDPOINT` | AI Search endpoint | `https://<name>.search.windows.net` |
| `AZURE_SEARCH_API_KEY` | AI Search admin key | `...` |
| `AZURE_SEARCH_INDEX` | Search index name | `notes-index` |
| `AZURE_CLIENT_ID` | Entra ID app client ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_TENANT_ID` | Entra ID tenant ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `SECRET_KEY` | FastAPI session secret | `...` |

### Frontend

| Variable | Description | Example |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |
| `NEXT_PUBLIC_AZURE_CLIENT_ID` | Entra ID app client ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `NEXT_PUBLIC_AZURE_TENANT_ID` | Entra ID tenant ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `NEXT_PUBLIC_AZURE_REDIRECT_URI` | OAuth redirect URI | `http://localhost:3000` |

## Project Structure

```
ImpressionsGenerator/
├── .github/
│   └── ISSUE_TEMPLATE/
│       ├── feature.md
│       └── bug.md
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry point
│   │   ├── routers/             # API route handlers
│   │   ├── services/            # Business logic (generation, style extraction)
│   │   ├── models/              # Pydantic data models
│   │   ├── auth/                # Entra ID authentication
│   │   └── utils/               # Shared utilities
│   ├── tests/                   # Backend tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   ├── components/          # React components
│   │   ├── hooks/               # Custom React hooks
│   │   ├── services/            # API client services
│   │   ├── types/               # TypeScript type definitions
│   │   └── utils/               # Frontend utilities
│   ├── public/                  # Static assets
│   ├── package.json
│   └── .env.example
├── infra/
│   ├── main.bicep               # Azure infrastructure as code
│   ├── modules/                 # Bicep modules per service
│   └── parameters.json          # Deployment parameters
├── .gitignore
├── README.md
└── REQUIREMENTS.md
```

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes and add tests.
4. Ensure all tests pass: `pytest` (backend) and `npm test` (frontend).
5. Commit with clear messages: `git commit -m "feat: add style extraction endpoint"`
6. Push to your fork and open a Pull Request.
7. Use the issue templates for bugs and feature requests.

Please follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages.

## License

This project is licensed under the [MIT License](LICENSE).
