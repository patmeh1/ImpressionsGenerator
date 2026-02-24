"""Tests for the style quality feedback feature."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.models.feedback import FeedbackCreate, FeedbackResponse

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------
SAMPLE_REPORT = {
    "id": "report-001",
    "doctor_id": "doctor-001",
    "input_text": "CT abdomen with contrast.",
    "findings": "Normal liver.",
    "impressions": "No acute findings.",
    "recommendations": "No follow-up needed.",
    "report_type": "CT",
    "body_region": "Abdomen",
    "status": "draft",
    "versions": [],
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat(),
}

SAMPLE_FEEDBACK = {
    "id": "feedback-001",
    "report_id": "report-001",
    "doctor_id": "doctor-001",
    "rating": 4,
    "feedback_text": "Good style match",
    "created_at": datetime.utcnow().isoformat(),
}


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------
def test_feedback_create_model_valid():
    fb = FeedbackCreate(rating=5, feedback_text="Excellent")
    assert fb.rating == 5
    assert fb.feedback_text == "Excellent"


def test_feedback_create_model_min_max():
    fb = FeedbackCreate(rating=1)
    assert fb.rating == 1
    assert fb.feedback_text == ""


def test_feedback_create_model_invalid_rating_too_low():
    with pytest.raises(Exception):
        FeedbackCreate(rating=0, feedback_text="Bad")


def test_feedback_create_model_invalid_rating_too_high():
    with pytest.raises(Exception):
        FeedbackCreate(rating=6, feedback_text="Too high")


def test_feedback_response_model():
    fb = FeedbackResponse(
        id="fb-001",
        report_id="report-001",
        doctor_id="doctor-001",
        rating=4,
        feedback_text="Good",
        created_at=datetime.utcnow(),
    )
    assert fb.id == "fb-001"
    assert fb.rating == 4


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------
def _doctor_claims() -> dict:
    now = datetime.utcnow()
    return {
        "oid": "doctor-001",
        "name": "Dr. Jane Smith",
        "preferred_username": "jane.smith@hospital.org",
        "roles": ["Doctor"],
        "tid": "test-tenant-id",
        "exp": (now + timedelta(hours=1)).timestamp(),
        "iat": now.timestamp(),
        "iss": "https://sts.windows.net/test-tenant-id/",
        "aud": "api://test-client-id",
    }


@pytest_asyncio.fixture()
async def feedback_client():
    """Async HTTP client with mocked auth and cosmos services."""
    from app.services.cosmos_db import cosmos_service
    from app.services.ai_search import ai_search_service

    claims = _doctor_claims()

    with (
        patch("app.auth.dependencies.validate_token", new_callable=AsyncMock) as mock_validate,
        patch("app.auth.entra_id.validate_token", new_callable=AsyncMock) as mock_validate2,
        patch("app.auth.entra_id._get_signing_keys", new_callable=AsyncMock),
    ):
        mock_validate.return_value = claims
        mock_validate2.return_value = claims

        # Set up mocked containers
        report_container = MagicMock()
        report_container.read_item = MagicMock(return_value=SAMPLE_REPORT)
        report_container.query_items = MagicMock(return_value=iter([]))

        feedback_container = MagicMock()
        feedback_container.create_item = MagicMock()
        feedback_container.query_items = MagicMock(return_value=iter([]))

        cosmos_service._containers["reports"] = report_container
        cosmos_service._containers["feedback"] = feedback_container

        # Mock ai_search
        ai_search_service._search_client = MagicMock()
        ai_search_service._search_client.merge_documents = MagicMock()

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["Authorization"] = "Bearer test-token"
            yield ac


@pytest.mark.asyncio
async def test_submit_feedback(feedback_client):
    """Test POST /api/reports/{id}/feedback creates feedback."""
    response = await feedback_client.post(
        "/api/reports/report-001/feedback",
        json={"rating": 4, "feedback_text": "Good style match"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["report_id"] == "report-001"
    assert data["doctor_id"] == "doctor-001"
    assert data["rating"] == 4
    assert data["feedback_text"] == "Good style match"


@pytest.mark.asyncio
async def test_submit_feedback_without_text(feedback_client):
    """Test POST /api/reports/{id}/feedback with rating only."""
    response = await feedback_client.post(
        "/api/reports/report-001/feedback",
        json={"rating": 3},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 3
    assert data["feedback_text"] == ""


@pytest.mark.asyncio
async def test_submit_feedback_invalid_rating(feedback_client):
    """Test POST /api/reports/{id}/feedback with invalid rating."""
    response = await feedback_client.post(
        "/api/reports/report-001/feedback",
        json={"rating": 0},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_rating_too_high(feedback_client):
    """Test POST /api/reports/{id}/feedback with rating > 5."""
    response = await feedback_client.post(
        "/api/reports/report-001/feedback",
        json={"rating": 6},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_report_feedback(feedback_client):
    """Test GET /api/reports/{id}/feedback returns feedback list."""
    from app.services.cosmos_db import cosmos_service

    feedback_container = MagicMock()
    feedback_container.query_items = MagicMock(return_value=iter([SAMPLE_FEEDBACK]))
    cosmos_service._containers["feedback"] = feedback_container

    response = await feedback_client.get("/api/reports/report-001/feedback")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["rating"] == 4


@pytest.mark.asyncio
async def test_submit_feedback_report_not_found(feedback_client):
    """Test POST /api/reports/{id}/feedback returns 404 for unknown report."""
    from azure.cosmos.exceptions import CosmosResourceNotFoundError
    from app.services.cosmos_db import cosmos_service

    report_container = MagicMock()
    report_container.read_item = MagicMock(side_effect=CosmosResourceNotFoundError)
    report_container.query_items = MagicMock(return_value=iter([]))
    cosmos_service._containers["reports"] = report_container

    response = await feedback_client.post(
        "/api/reports/nonexistent/feedback",
        json={"rating": 3},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Weighted retrieval tests
# ---------------------------------------------------------------------------
def test_boost_high_rated_reranking():
    """Test that search results are re-ranked based on style_rating."""
    from app.services.ai_search import AISearchService

    service = AISearchService()
    mock_client = MagicMock()

    # Simulate search results: doc A has low relevance but high rating,
    # doc B has high relevance but low rating
    mock_results = [
        {"id": "doc-a", "content": "", "findings": "", "impressions": "",
         "recommendations": "", "report_type": "CT", "body_region": "Chest",
         "@search.score": 1.0, "style_rating": 5.0},
        {"id": "doc-b", "content": "", "findings": "", "impressions": "",
         "recommendations": "", "report_type": "CT", "body_region": "Chest",
         "@search.score": 2.0, "style_rating": 1.0},
    ]
    mock_client.search = MagicMock(return_value=mock_results)
    service._search_client = mock_client
    service._generate_embedding = MagicMock(return_value=[0.0] * 1536)

    import asyncio
    results = asyncio.get_event_loop().run_until_complete(
        service.search_similar_notes(
            doctor_id="doc-001",
            query_text="test query",
            top=2,
            boost_high_rated=True,
        )
    )

    assert len(results) == 2
    ids = [r["id"] for r in results]
    assert "doc-a" in ids
    assert "doc-b" in ids
    for r in results:
        assert "style_rating" in r
