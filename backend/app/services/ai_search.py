"""Azure AI Search service for RAG-based few-shot retrieval with vector search."""

import logging
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

VECTOR_DIMENSIONS = 1536  # text-embedding-ada-002 output dimensions


class AzureAISearchService:
    """Manages Azure AI Search vector index for indexing and retrieving doctor notes."""

    def __init__(self) -> None:
        self._search_client: SearchClient | None = None
        self._index_client: SearchIndexClient | None = None
        self._openai_client: AzureOpenAI | None = None

    async def initialize(self) -> None:
        """Initialize search clients, OpenAI embeddings client, and ensure the index exists."""
        credential = AzureKeyCredential(settings.AI_SEARCH_API_KEY)

        self._index_client = SearchIndexClient(
            endpoint=settings.AI_SEARCH_ENDPOINT,
            credential=credential,
        )

        azure_credential = DefaultAzureCredential()
        token_provider = get_bearer_token_provider(
            azure_credential, "https://cognitiveservices.azure.com/.default"
        )
        self._openai_client = AzureOpenAI(
            azure_endpoint=settings.OPENAI_ENDPOINT,
            azure_ad_token_provider=token_provider,
            api_version=settings.OPENAI_API_VERSION,
        )

        self._ensure_index()

        self._search_client = SearchClient(
            endpoint=settings.AI_SEARCH_ENDPOINT,
            index_name=settings.AI_SEARCH_INDEX_NAME,
            credential=credential,
        )
        logger.info("AI Search initialized with index '%s'", settings.AI_SEARCH_INDEX_NAME)

    def _ensure_index(self) -> None:
        """Create the search index with vector search if it doesn't already exist."""
        if self._index_client is None:
            return

        index_name = settings.AI_SEARCH_INDEX_NAME
        try:
            self._index_client.get_index(index_name)
            logger.info("Search index '%s' already exists", index_name)
            return
        except Exception:
            pass

        fields = [
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
            ),
            SimpleField(
                name="doctor_id",
                type=SearchFieldDataType.String,
                filterable=True,
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                analyzer_name="en.microsoft",
            ),
            SimpleField(
                name="report_type",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="body_region",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
            ),
            SearchableField(
                name="findings",
                type=SearchFieldDataType.String,
            ),
            SearchableField(
                name="impressions",
                type=SearchFieldDataType.String,
            ),
            SearchableField(
                name="recommendations",
                type=SearchFieldDataType.String,
            ),
            SimpleField(
                name="created_at",
                type=SearchFieldDataType.String,
            ),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=VECTOR_DIMENSIONS,
                vector_search_profile_name="default-vector-profile",
            ),
            SimpleField(
                name="style_rating",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True,
            ),
        ]

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name="default-hnsw"),
            ],
            profiles=[
                VectorSearchProfile(
                    name="default-vector-profile",
                    algorithm_configuration_name="default-hnsw",
                ),
            ],
        )

        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
        )
        self._index_client.create_index(index)
        logger.info("Created search index '%s' with vector search", index_name)

    def _generate_embedding(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text using Azure OpenAI."""
        if self._openai_client is None:
            raise RuntimeError("AzureAISearchService not initialized")

        # Truncate to avoid token limits (~8191 tokens for ada-002)
        truncated = text[:30000]

        response = self._openai_client.embeddings.create(
            input=truncated,
            model=settings.OPENAI_EMBEDDING_DEPLOYMENT,
        )
        return response.data[0].embedding

    async def index_note(self, document: dict[str, Any]) -> None:
        """Index a note document with its embedding vector for search retrieval."""
        if self._search_client is None:
            raise RuntimeError("AzureAISearchService not initialized")

        content = document.get("content", "")
        embedding = self._generate_embedding(content)
        document["embedding"] = embedding

        self._search_client.upload_documents(documents=[document])
        logger.info("Indexed document '%s' with embedding", document.get("id"))

    async def index_report(self, report: dict[str, Any]) -> None:
        """Index a completed report with its embedding for few-shot retrieval."""
        if self._search_client is None:
            raise RuntimeError("AzureAISearchService not initialized")

        content = report.get("input_text", "")
        embedding = self._generate_embedding(content)

        doc = {
            "id": report["id"],
            "doctor_id": report.get("doctor_id", ""),
            "content": content,
            "report_type": report.get("report_type", ""),
            "body_region": report.get("body_region", ""),
            "findings": report.get("findings", ""),
            "impressions": report.get("impressions", ""),
            "recommendations": report.get("recommendations", ""),
            "created_at": report.get("created_at", ""),
            "embedding": embedding,
            "style_rating": float(report.get("style_rating", 0)),
        }
        self._search_client.upload_documents(documents=[doc])
        logger.info("Indexed report '%s' with embedding", report["id"])

    async def search_similar_notes(
        self,
        doctor_id: str,
        query_text: str,
        report_type: str | None = None,
        body_region: str | None = None,
        top: int = 5,
        boost_high_rated: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Search for similar notes by a specific doctor using vector similarity.

        Generates an embedding for the query text and performs a hybrid search
        (vector + keyword) filtered by doctor_id for style isolation.
        When boost_high_rated is True, results are re-ranked so higher-rated
        notes appear first.
        """
        if self._search_client is None:
            raise RuntimeError("AzureAISearchService not initialized")

        filter_parts = [f"doctor_id eq '{doctor_id}'"]
        if report_type:
            filter_parts.append(f"report_type eq '{report_type}'")
        if body_region:
            filter_parts.append(f"body_region eq '{body_region}'")

        filter_expr = " and ".join(filter_parts)

        # Fetch extra candidates when boosting so re-ranking has more to work with
        fetch_top = top * 2 if boost_high_rated else top

        query_embedding = self._generate_embedding(query_text)
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top,
            fields="embedding",
        )

        results = self._search_client.search(
            search_text=query_text,
            vector_queries=[vector_query],
            filter=filter_expr,
            top=fetch_top,
            select=["id", "content", "findings", "impressions", "recommendations",
                    "report_type", "body_region", "style_rating"],
        )

        docs = []
        for result in results:
            docs.append({
                "id": result["id"],
                "content": result.get("content", ""),
                "findings": result.get("findings", ""),
                "impressions": result.get("impressions", ""),
                "recommendations": result.get("recommendations", ""),
                "report_type": result.get("report_type", ""),
                "body_region": result.get("body_region", ""),
                "score": result.get("@search.score", 0),
                "style_rating": result.get("style_rating", 0),
            })

        if boost_high_rated and docs:
            # Re-rank: combine search relevance with style rating.
            # Normalize search score (0-1 range) and blend with rating (1-5 → 0-1).
            max_score = max(d["score"] for d in docs) or 1.0
            for d in docs:
                normalized_score = d["score"] / max_score
                rating_boost = (d.get("style_rating") or 0) / 5.0
                d["_combined"] = 0.7 * normalized_score + 0.3 * rating_boost
            docs.sort(key=lambda d: d["_combined"], reverse=True)
            for d in docs:
                d.pop("_combined", None)
            docs = docs[:top]

        logger.info(
            "Found %d similar notes for doctor %s (query: %.50s...)",
            len(docs), doctor_id, query_text,
        )
        return docs

    async def update_document_rating(self, doc_id: str, style_rating: float) -> None:
        """Update the style_rating field on an indexed document."""
        if self._search_client is None:
            raise RuntimeError("AISearchService not initialized")

        self._search_client.merge_documents(
            documents=[{"id": doc_id, "style_rating": style_rating}]
        )
        logger.info("Updated style_rating for document '%s' to %.1f", doc_id, style_rating)

    async def delete_document(self, doc_id: str) -> None:
        """Delete a document from the search index."""
        if self._search_client is None:
            raise RuntimeError("AzureAISearchService not initialized")

        self._search_client.delete_documents(documents=[{"id": doc_id}])
        logger.info("Deleted document '%s' from search index", doc_id)


# Singleton instance – importable as `ai_search_service` for backward compatibility
ai_search_service = AzureAISearchService()
