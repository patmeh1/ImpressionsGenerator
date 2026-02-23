"""Tests for Azure AI Search vector index service."""

from unittest.mock import MagicMock

import pytest

from app.services.ai_search import AzureAISearchService, VECTOR_DIMENSIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
FAKE_EMBEDDING = [0.1] * VECTOR_DIMENSIONS

SAMPLE_NOTE_DOC = {
    "id": "note-001",
    "doctor_id": "doctor-001",
    "content": "CT Abdomen: Liver unremarkable. No acute abnormality.",
    "report_type": "",
    "body_region": "",
    "findings": "",
    "impressions": "",
    "recommendations": "",
    "created_at": "2024-01-15T10:00:00",
}

SAMPLE_REPORT = {
    "id": "report-001",
    "doctor_id": "doctor-001",
    "input_text": "CT abdomen pelvis with contrast.",
    "report_type": "CT",
    "body_region": "Abdomen",
    "findings": "Normal liver.",
    "impressions": "No acute findings.",
    "recommendations": "No follow-up needed.",
    "created_at": "2024-02-01T12:00:00",
}


def _make_search_result(doc: dict) -> dict:
    """Create a mock search result dict."""
    result = {**doc, "@search.score": 0.95}
    return result


def _build_service() -> AzureAISearchService:
    """Build a service with mocked clients for unit testing."""
    svc = AzureAISearchService()
    svc._search_client = MagicMock()
    svc._openai_client = MagicMock()

    # Mock embedding generation
    embed_response = MagicMock()
    embed_data = MagicMock()
    embed_data.embedding = FAKE_EMBEDDING
    embed_response.data = [embed_data]
    svc._openai_client.embeddings.create = MagicMock(return_value=embed_response)

    return svc


# ---------------------------------------------------------------------------
# Embedding generation
# ---------------------------------------------------------------------------
def test_generate_embedding_returns_vector():
    """_generate_embedding should return a list of floats with correct dimensions."""
    svc = _build_service()
    embedding = svc._generate_embedding("test text")
    assert isinstance(embedding, list)
    assert len(embedding) == VECTOR_DIMENSIONS


def test_generate_embedding_truncates_long_text():
    """Very long text should be truncated before sending to the embeddings API."""
    svc = _build_service()
    long_text = "x" * 50000
    svc._generate_embedding(long_text)

    call_args = svc._openai_client.embeddings.create.call_args
    sent_text = call_args.kwargs.get("input") or call_args[1].get("input")
    assert len(sent_text) <= 30000


def test_generate_embedding_raises_when_not_initialized():
    """_generate_embedding should raise RuntimeError if service is not initialized."""
    svc = AzureAISearchService()
    with pytest.raises(RuntimeError, match="not initialized"):
        svc._generate_embedding("test")


# ---------------------------------------------------------------------------
# Index note with embedding
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_index_note_generates_embedding():
    """index_note should generate an embedding and include it in the document."""
    svc = _build_service()
    doc = {**SAMPLE_NOTE_DOC}

    await svc.index_note(doc)

    # Embedding should have been added to the document
    assert "embedding" in doc
    assert len(doc["embedding"]) == VECTOR_DIMENSIONS

    # Document should have been uploaded
    svc._search_client.upload_documents.assert_called_once()
    uploaded = svc._search_client.upload_documents.call_args.kwargs.get("documents")
    if uploaded is None:
        uploaded = svc._search_client.upload_documents.call_args[1].get("documents")
    if uploaded is None:
        uploaded = svc._search_client.upload_documents.call_args[0][0]


@pytest.mark.asyncio
async def test_index_note_raises_when_not_initialized():
    """index_note should raise RuntimeError if search client is not set."""
    svc = AzureAISearchService()
    with pytest.raises(RuntimeError, match="not initialized"):
        await svc.index_note(SAMPLE_NOTE_DOC)


# ---------------------------------------------------------------------------
# Index report with embedding
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_index_report_generates_embedding():
    """index_report should generate an embedding for the report input text."""
    svc = _build_service()

    await svc.index_report(SAMPLE_REPORT)

    svc._openai_client.embeddings.create.assert_called_once()
    svc._search_client.upload_documents.assert_called_once()

    uploaded_docs = svc._search_client.upload_documents.call_args
    doc = uploaded_docs.kwargs.get("documents", uploaded_docs[1].get("documents", [None]))[0]
    if doc is None:
        doc = uploaded_docs[0][0]

    assert doc["id"] == "report-001"
    assert doc["doctor_id"] == "doctor-001"
    assert "embedding" in doc
    assert len(doc["embedding"]) == VECTOR_DIMENSIONS


# ---------------------------------------------------------------------------
# Vector search with doctor_id filter
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_search_similar_notes_uses_vector_query():
    """search_similar_notes should use vector search with doctor_id filter."""
    svc = _build_service()

    mock_result = _make_search_result({
        "id": "note-001",
        "content": "CT Abdomen findings.",
        "findings": "Normal.",
        "impressions": "No issues.",
        "recommendations": "",
        "report_type": "CT",
        "body_region": "Abdomen",
    })
    svc._search_client.search = MagicMock(return_value=iter([mock_result]))

    results = await svc.search_similar_notes(
        doctor_id="doctor-001",
        query_text="CT abdomen pelvis",
        top=3,
    )

    # Verify embedding was generated for the query
    svc._openai_client.embeddings.create.assert_called_once()

    # Verify search was called with vector_queries and filter
    search_call = svc._search_client.search.call_args
    assert "vector_queries" in search_call.kwargs
    assert "doctor_id eq 'doctor-001'" in search_call.kwargs["filter"]

    assert len(results) == 1
    assert results[0]["id"] == "note-001"
    assert results[0]["score"] == 0.95


@pytest.mark.asyncio
async def test_search_filters_by_report_type_and_body_region():
    """search_similar_notes should include report_type and body_region in filter."""
    svc = _build_service()
    svc._search_client.search = MagicMock(return_value=iter([]))

    await svc.search_similar_notes(
        doctor_id="doctor-001",
        query_text="MRI Brain scan",
        report_type="MRI",
        body_region="Brain",
        top=5,
    )

    search_call = svc._search_client.search.call_args
    filter_expr = search_call.kwargs["filter"]
    assert "doctor_id eq 'doctor-001'" in filter_expr
    assert "report_type eq 'MRI'" in filter_expr
    assert "body_region eq 'Brain'" in filter_expr


@pytest.mark.asyncio
async def test_search_returns_empty_when_no_matches():
    """search_similar_notes should return an empty list when no matches found."""
    svc = _build_service()
    svc._search_client.search = MagicMock(return_value=iter([]))

    results = await svc.search_similar_notes(
        doctor_id="doctor-999",
        query_text="something obscure",
    )
    assert results == []


@pytest.mark.asyncio
async def test_search_raises_when_not_initialized():
    """search_similar_notes should raise RuntimeError if not initialized."""
    svc = AzureAISearchService()
    with pytest.raises(RuntimeError, match="not initialized"):
        await svc.search_similar_notes("doctor-001", "query")


# ---------------------------------------------------------------------------
# Delete document
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_delete_document():
    """delete_document should call delete_documents with the doc id."""
    svc = _build_service()

    await svc.delete_document("note-001")

    svc._search_client.delete_documents.assert_called_once_with(
        documents=[{"id": "note-001"}]
    )


@pytest.mark.asyncio
async def test_delete_document_raises_when_not_initialized():
    """delete_document should raise RuntimeError if not initialized."""
    svc = AzureAISearchService()
    with pytest.raises(RuntimeError, match="not initialized"):
        await svc.delete_document("note-001")


# ---------------------------------------------------------------------------
# Class name and singleton
# ---------------------------------------------------------------------------
def test_service_class_name():
    """Service class should be named AzureAISearchService."""
    assert AzureAISearchService.__name__ == "AzureAISearchService"


def test_singleton_instance_exists():
    """Module should export a singleton ai_search_service instance."""
    from app.services.ai_search import ai_search_service
    assert isinstance(ai_search_service, AzureAISearchService)
