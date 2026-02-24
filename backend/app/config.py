from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Azure Entra ID (AAD)
    AZURE_TENANT_ID: str = ""
    AZURE_CLIENT_ID: str = ""
    AZURE_CLIENT_SECRET: str = ""

    # Azure Cosmos DB
    COSMOS_ENDPOINT: str = ""
    COSMOS_DATABASE_NAME: str = "impressions_generator"

    # Azure Blob Storage
    BLOB_STORAGE_ACCOUNT_URL: str = ""
    BLOB_CONTAINER_NAME: str = "doctor-notes"

    # Azure OpenAI
    OPENAI_ENDPOINT: str = ""
    OPENAI_API_VERSION: str = "2024-06-01"
    OPENAI_DEPLOYMENT_NAME: str = "gpt-4o"
    OPENAI_EMBEDDING_DEPLOYMENT: str = "text-embedding-ada-002"

    # Azure AI Search
    AI_SEARCH_ENDPOINT: str = ""
    AI_SEARCH_INDEX_NAME: str = "doctor-notes-index"
    AI_SEARCH_API_KEY: str = ""

    # Azure Key Vault
    KEYVAULT_URL: str = ""

    # Azure Monitor / Application Insights (audit trail)
    APPINSIGHTS_CONNECTION_STRING: str = ""

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
