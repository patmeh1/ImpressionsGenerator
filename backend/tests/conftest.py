"""Shared pytest fixtures for backend tests."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Event‑loop fixture (session‑scoped so all async tests share one loop)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------
SAMPLE_DOCTOR = {
    "id": "doctor-001",
    "name": "Dr. Jane Smith",
    "specialty": "Radiology",
    "department": "Diagnostic Imaging",
    "created_at": datetime.utcnow().isoformat(),
}

SAMPLE_DOCTOR_B = {
    "id": "doctor-002",
    "name": "Dr. Bob Jones",
    "specialty": "Cardiology",
    "department": "Heart Center",
    "created_at": datetime.utcnow().isoformat(),
}

SAMPLE_NOTE = {
    "id": "note-001",
    "doctor_id": "doctor-001",
    "content": (
        "CT Abdomen without contrast. Liver measures 15.2 cm in craniocaudal "
        "dimension. No focal hepatic lesion. Gallbladder is unremarkable. "
        "Spleen measures 11.0 cm. Kidneys are normal in size. "
        "3.2 cm hypodense mass in the right adrenal gland. "
        "No hydronephrosis. No free fluid."
    ),
    "source_type": "upload",
    "file_name": "report_jan2024.pdf",
    "created_at": datetime.utcnow().isoformat(),
}

SAMPLE_NOTES_MULTIPLE = [
    {
        "id": f"note-{i:03d}",
        "doctor_id": "doctor-001",
        "content": f"Sample radiology note #{i} with findings and impressions.",
        "source_type": "paste",
        "file_name": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    for i in range(1, 6)
]

SAMPLE_DICTATION = (
    "CT abdomen pelvis with contrast. The liver is normal in size measuring "
    "14.5 cm. There is a 3.2 cm mass in the right adrenal gland, unchanged "
    "from prior study dated 2024-01-15. Kidneys are normal bilaterally. "
    "No hydronephrosis. Spleen measures 10.8 cm. No free fluid. "
    "A 2.1 cm lymph node is noted in the retroperitoneum. "
    "Impression: Stable 3.2 cm right adrenal mass. 2.1 cm retroperitoneal "
    "lymph node, recommend follow-up in 6 months."
)

SAMPLE_STYLE_PROFILE = {
    "doctor_id": "doctor-001",
    "vocabulary_patterns": ["unremarkable", "within normal limits", "no acute"],
    "abbreviation_map": {"CT": "computed tomography", "MRI": "magnetic resonance imaging"},
    "sentence_structure": ["short declarative", "uses semicolons"],
    "section_ordering": ["findings", "impressions", "recommendations"],
    "sample_phrases": [
        "No acute abnormality.",
        "Recommend clinical correlation.",
        "Stable compared to prior.",
    ],
    "updated_at": datetime.utcnow().isoformat(),
}

SAMPLE_REPORT = {
    "id": "report-001",
    "doctor_id": "doctor-001",
    "input_text": SAMPLE_DICTATION,
    "findings": (
        "The liver measures 14.5 cm and is normal in size. A 3.2 cm mass is "
        "present in the right adrenal gland, unchanged from 2024-01-15. "
        "Kidneys are normal bilaterally without hydronephrosis. "
        "Spleen measures 10.8 cm. No free fluid. A 2.1 cm retroperitoneal "
        "lymph node is identified."
    ),
    "impressions": (
        "1. Stable 3.2 cm right adrenal mass.\n"
        "2. 2.1 cm retroperitoneal lymph node."
    ),
    "recommendations": "Recommend follow-up imaging in 6 months.",
    "report_type": "CT",
    "body_region": "Abdomen",
    "status": "draft",
    "versions": [],
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat(),
}


# ---------------------------------------------------------------------------
# Mock JWT / auth helpers
# ---------------------------------------------------------------------------
def _make_claims(
    user_id: str = "doctor-001",
    name: str = "Dr. Jane Smith",
    email: str = "jane.smith@hospital.org",
    roles: list[str] | None = None,
    expired: bool = False,
) -> dict[str, Any]:
    now = datetime.utcnow()
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    return {
        "oid": user_id,
        "name": name,
        "preferred_username": email,
        "roles": roles or ["Doctor"],
        "tid": "test-tenant-id",
        "exp": exp.timestamp(),
        "iat": now.timestamp(),
        "iss": "https://sts.windows.net/test-tenant-id/",
        "aud": "api://test-client-id",
    }


@pytest.fixture()
def doctor_claims():
    return _make_claims()


@pytest.fixture()
def admin_claims():
    return _make_claims(
        user_id="admin-001",
        name="Admin User",
        email="admin@hospital.org",
        roles=["Admin"],
    )


@pytest.fixture()
def expired_claims():
    return _make_claims(expired=True)


# ---------------------------------------------------------------------------
# Mock Azure services
# ---------------------------------------------------------------------------
@pytest.fixture()
def mock_cosmos_client():
    client = MagicMock()
    db = MagicMock()
    container = MagicMock()
    container.create_item = AsyncMock()
    container.read_item = AsyncMock()
    container.query_items = MagicMock(return_value=iter([]))
    container.upsert_item = AsyncMock()
    container.delete_item = AsyncMock()
    db.get_container_client = MagicMock(return_value=container)
    client.get_database_client = MagicMock(return_value=db)
    return client


@pytest.fixture()
def mock_blob_client():
    client = MagicMock()
    blob = MagicMock()
    blob.upload_blob = AsyncMock()
    blob.download_blob = AsyncMock()
    blob.delete_blob = AsyncMock()
    container = MagicMock()
    container.get_blob_client = MagicMock(return_value=blob)
    client.get_container_client = MagicMock(return_value=container)
    return client


@pytest.fixture()
def mock_openai_client():
    client = AsyncMock()
    choice = MagicMock()
    choice.message.content = (
        '{"findings": "Normal liver.", '
        '"impressions": "No acute findings.", '
        '"recommendations": "No follow-up needed."}'
    )
    response = MagicMock()
    response.choices = [choice]
    client.chat.completions.create = AsyncMock(return_value=response)
    return client


@pytest.fixture()
def mock_search_client():
    client = AsyncMock()
    client.search = AsyncMock(return_value=[])
    client.upload_documents = AsyncMock()
    client.delete_documents = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Test HTTP client
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def test_client(
    doctor_claims,
    mock_cosmos_client,
    mock_blob_client,
    mock_openai_client,
    mock_search_client,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an httpx AsyncClient wired to the FastAPI app with mocked deps."""
    with (
        patch("app.auth.entra_id.validate_token", new_callable=AsyncMock) as mock_validate,
        patch("app.auth.entra_id._get_signing_keys", new_callable=AsyncMock),
    ):
        mock_validate.return_value = doctor_claims

        # Import app lazily so patches are in effect
        from app.config import settings  # noqa: F401

        try:
            from app.main import app
        except ImportError:
            # If main.py doesn't exist yet, create a minimal FastAPI app
            from fastapi import FastAPI
            app = FastAPI(title="Impressions Generator – test stub")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["Authorization"] = "Bearer test-token"
            yield ac
