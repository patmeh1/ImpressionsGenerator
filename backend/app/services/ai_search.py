"""Azure AI Search service for RAG-based few-shot retrieval."""

import logging
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)

from app.config import settings

logger = logging.getLogger(__name__)


class AISearchService:
    """Manages Azure AI Search for indexing and retrieving doctor notes."""

    def __init__(self) -> None:
        self._search_client: SearchClient | None = None
        self._index_client: SearchIndexClient | None = None

    async def initialize(self) -> None:
        """Initialize search clients and ensure the index exists."""
        credential = AzureKeyCredential(settings.AI_SEARCH_API_KEY)

        self._index_client = SearchIndexClient(
            endpoint=settings.AI_SEARCH_ENDPOINT,
            credential=credential,
        )
        self._ensure_index()

        self._search_client = SearchClient(
            endpoint=settings.AI_SEARCH_ENDPOINT,
            index_name=settings.AI_SEARCH_INDEX_NAME,
            credential=credential,
        )
        logger.info("AI Search initialized with index '%s'", settings.AI_SEARCH_INDEX_NAME)

    def _ensure_index(self) -> None:
        """Create the search index if it doesn't already exist."""
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
        ]

        index = SearchIndex(name=index_name, fields=fields)
        self._index_client.create_index(index)
        logger.info("Created search index '%s'", index_name)

    async def index_note(self, document: dict[str, Any]) -> None:
        """Index a note document for search retrieval."""
        if self._search_client is None:
            raise RuntimeError("AISearchService not initialized")

        self._search_client.upload_documents(documents=[document])
        logger.info("Indexed document '%s'", document.get("id"))

    async def index_report(self, report: dict[str, Any]) -> None:
        """Index a completed report for few-shot retrieval."""
        if self._search_client is None:
            raise RuntimeError("AISearchService not initialized")

        doc = {
            "id": report["id"],
            "doctor_id": report.get("doctor_id", ""),
            "content": report.get("input_text", ""),
            "report_type": report.get("report_type", ""),
            "body_region": report.get("body_region", ""),
            "findings": report.get("findings", ""),
            "impressions": report.get("impressions", ""),
            "recommendations": report.get("recommendations", ""),
            "created_at": report.get("created_at", ""),
        }
        self._search_client.upload_documents(documents=[doc])
        logger.info("Indexed report '%s'", report["id"])

    async def search_similar_notes(
        self,
        doctor_id: str,
        query_text: str,
        report_type: str | None = None,
        body_region: str | None = None,
        top: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search for similar notes by a specific doctor for RAG few-shot retrieval.

        Filters by doctor_id and optionally by report_type and body_region.
        """
        if self._search_client is None:
            raise RuntimeError("AISearchService not initialized")

        filter_parts = [f"doctor_id eq '{doctor_id}'"]
        if report_type:
            filter_parts.append(f"report_type eq '{report_type}'")
        if body_region:
            filter_parts.append(f"body_region eq '{body_region}'")

        filter_expr = " and ".join(filter_parts)

        results = self._search_client.search(
            search_text=query_text,
            filter=filter_expr,
            top=top,
            select=["id", "content", "findings", "impressions", "recommendations",
                    "report_type", "body_region"],
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
            })

        logger.info(
            "Found %d similar notes for doctor %s (query: %.50s...)",
            len(docs), doctor_id, query_text,
        )
        return docs

    async def delete_document(self, doc_id: str) -> None:
        """Delete a document from the search index."""
        if self._search_client is None:
            raise RuntimeError("AISearchService not initialized")

        self._search_client.delete_documents(documents=[{"id": doc_id}])
        logger.info("Deleted document '%s' from search index", doc_id)


# Singleton instance
ai_search_service = AISearchService()
