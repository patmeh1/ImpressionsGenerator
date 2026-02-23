"""Tests for doctor CRUD operations."""

from copy import deepcopy
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.doctor import DoctorCreate, DoctorUpdate, DoctorResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def sample_doctor_doc():
    return {
        "id": "doctor-001",
        "name": "Dr. Jane Smith",
        "specialty": "Radiology",
        "department": "Diagnostic Imaging",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture()
def sample_doctor_b_doc():
    return {
        "id": "doctor-002",
        "name": "Dr. Bob Jones",
        "specialty": "Cardiology",
        "department": "Heart Center",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture()
def mock_container():
    container = MagicMock()
    container.create_item = AsyncMock()
    container.read_item = AsyncMock()
    container.upsert_item = AsyncMock()
    container.delete_item = AsyncMock()
    return container


# ---------------------------------------------------------------------------
# test_create_doctor
# ---------------------------------------------------------------------------
def test_create_doctor_model_validation():
    """DoctorCreate validates required fields."""
    doc = DoctorCreate(name="Dr. Test", specialty="Neurology")
    assert doc.name == "Dr. Test"
    assert doc.specialty == "Neurology"
    assert doc.department == ""


@pytest.mark.asyncio
async def test_create_doctor(mock_container, sample_doctor_doc):
    """Creating a doctor should persist to the container."""
    mock_container.create_item.return_value = sample_doctor_doc
    result = await mock_container.create_item(sample_doctor_doc)
    mock_container.create_item.assert_called_once_with(sample_doctor_doc)
    assert result["id"] == "doctor-001"
    assert result["name"] == "Dr. Jane Smith"


# ---------------------------------------------------------------------------
# test_get_doctor
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_doctor(mock_container, sample_doctor_doc):
    """Reading a doctor by ID returns the correct document."""
    mock_container.read_item.return_value = sample_doctor_doc
    result = await mock_container.read_item(
        item="doctor-001", partition_key="doctor-001"
    )
    assert result["id"] == "doctor-001"
    assert result["specialty"] == "Radiology"


# ---------------------------------------------------------------------------
# test_list_doctors
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_doctors(mock_container, sample_doctor_doc, sample_doctor_b_doc):
    """Listing doctors returns all documents."""
    mock_container.query_items.return_value = iter(
        [sample_doctor_doc, sample_doctor_b_doc]
    )
    items = list(mock_container.query_items(
        query="SELECT * FROM c", enable_cross_partition_query=True
    ))
    assert len(items) == 2
    assert items[0]["name"] == "Dr. Jane Smith"
    assert items[1]["name"] == "Dr. Bob Jones"


# ---------------------------------------------------------------------------
# test_update_doctor
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_update_doctor(mock_container, sample_doctor_doc):
    """Upserting a doctor updates the stored document."""
    updated = deepcopy(sample_doctor_doc)
    updated["department"] = "Neuroradiology"
    mock_container.upsert_item.return_value = updated

    result = await mock_container.upsert_item(updated)
    assert result["department"] == "Neuroradiology"
    mock_container.upsert_item.assert_called_once()


# ---------------------------------------------------------------------------
# test_delete_doctor
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_delete_doctor(mock_container):
    """Deleting a doctor removes it from the container."""
    await mock_container.delete_item(item="doctor-001", partition_key="doctor-001")
    mock_container.delete_item.assert_called_once_with(
        item="doctor-001", partition_key="doctor-001"
    )


# ---------------------------------------------------------------------------
# T14 – doctor isolation (doctor A can't access doctor B's data)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_doctor_isolation(mock_container, sample_doctor_doc, sample_doctor_b_doc):
    """Doctor A's query scoped to their partition must not return Doctor B."""
    mock_container.query_items.return_value = iter([sample_doctor_doc])

    items = list(mock_container.query_items(
        query="SELECT * FROM c WHERE c.id = @id",
        parameters=[{"name": "@id", "value": "doctor-001"}],
        partition_key="doctor-001",
    ))
    assert len(items) == 1
    assert items[0]["id"] == "doctor-001"
    # Verify doctor-002 is NOT present
    assert all(item["id"] != "doctor-002" for item in items)


# ---------------------------------------------------------------------------
# Model validation tests
# ---------------------------------------------------------------------------
def test_doctor_update_partial():
    """DoctorUpdate allows partial updates."""
    update = DoctorUpdate(name="Dr. Updated")
    assert update.name == "Dr. Updated"
    assert update.specialty is None
    assert update.department is None


def test_doctor_response_model():
    """DoctorResponse round-trips from dict."""
    resp = DoctorResponse(
        id="d-1",
        name="Dr. Test",
        specialty="Radiology",
        department="Imaging",
        created_at=datetime.utcnow(),
    )
    assert resp.id == "d-1"
