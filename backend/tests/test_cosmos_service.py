"""Tests for CosmosDBService CRUD operations."""

from copy import deepcopy
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.services.cosmos_db import CosmosDBService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def cosmos_svc():
    """Create a CosmosDBService with mocked containers."""
    svc = CosmosDBService()
    containers = {}
    for name in ("doctors", "notes", "reports", "style_profiles"):
        c = MagicMock()
        c.create_item = MagicMock()
        c.read_item = MagicMock()
        c.replace_item = MagicMock()
        c.delete_item = MagicMock()
        c.upsert_item = MagicMock()
        c.query_items = MagicMock(return_value=iter([]))
        containers[name] = c
    svc._containers = containers
    return svc


@pytest.fixture()
def sample_doctor():
    return {
        "id": "doctor-001",
        "name": "Dr. Jane Smith",
        "specialty": "Radiology",
        "department": "Imaging",
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture()
def sample_report():
    now = datetime.utcnow().isoformat()
    return {
        "id": "report-001",
        "doctor_id": "doctor-001",
        "input_text": "CT abdomen findings",
        "findings": "Liver is normal.",
        "impressions": "No acute findings.",
        "recommendations": "None.",
        "report_type": "CT",
        "body_region": "Abdomen",
        "status": "draft",
        "versions": [],
        "created_at": now,
        "updated_at": now,
    }


# ---------------------------------------------------------------------------
# Doctor operations
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_doctor(cosmos_svc):
    data = {"name": "Dr. Test", "specialty": "Neurology", "department": "Neuro"}
    result = await cosmos_svc.create_doctor(data)
    assert result["name"] == "Dr. Test"
    assert "id" in result
    assert "created_at" in result
    cosmos_svc._containers["doctors"].create_item.assert_called_once()


@pytest.mark.asyncio
async def test_get_doctor_found(cosmos_svc, sample_doctor):
    cosmos_svc._containers["doctors"].read_item.return_value = sample_doctor
    result = await cosmos_svc.get_doctor("doctor-001")
    assert result["id"] == "doctor-001"


@pytest.mark.asyncio
async def test_get_doctor_not_found(cosmos_svc):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    cosmos_svc._containers["doctors"].read_item.side_effect = CosmosResourceNotFoundError()
    result = await cosmos_svc.get_doctor("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_doctors(cosmos_svc, sample_doctor):
    cosmos_svc._containers["doctors"].query_items.return_value = iter([sample_doctor])
    result = await cosmos_svc.list_doctors()
    assert len(result) == 1
    assert result[0]["name"] == "Dr. Jane Smith"


@pytest.mark.asyncio
async def test_update_doctor_found(cosmos_svc, sample_doctor):
    cosmos_svc._containers["doctors"].read_item.return_value = deepcopy(sample_doctor)
    result = await cosmos_svc.update_doctor("doctor-001", {"department": "Neuroradiology"})
    assert result is not None
    assert result["department"] == "Neuroradiology"
    cosmos_svc._containers["doctors"].replace_item.assert_called_once()


@pytest.mark.asyncio
async def test_update_doctor_not_found(cosmos_svc):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    cosmos_svc._containers["doctors"].read_item.side_effect = CosmosResourceNotFoundError()
    result = await cosmos_svc.update_doctor("nonexistent", {"name": "Dr. Nobody"})
    assert result is None


@pytest.mark.asyncio
async def test_delete_doctor_success(cosmos_svc):
    result = await cosmos_svc.delete_doctor("doctor-001")
    assert result is True
    cosmos_svc._containers["doctors"].delete_item.assert_called_once()


@pytest.mark.asyncio
async def test_delete_doctor_not_found(cosmos_svc):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    cosmos_svc._containers["doctors"].delete_item.side_effect = CosmosResourceNotFoundError()
    result = await cosmos_svc.delete_doctor("nonexistent")
    assert result is False


# ---------------------------------------------------------------------------
# Note operations
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_note(cosmos_svc):
    data = {"content": "CT chest findings", "source_type": "paste", "file_name": None}
    result = await cosmos_svc.create_note("doctor-001", data)
    assert result["doctor_id"] == "doctor-001"
    assert "id" in result
    cosmos_svc._containers["notes"].create_item.assert_called_once()


@pytest.mark.asyncio
async def test_list_notes(cosmos_svc):
    note = {"id": "n-1", "doctor_id": "doctor-001", "content": "Note text"}
    cosmos_svc._containers["notes"].query_items.return_value = iter([note])
    result = await cosmos_svc.list_notes("doctor-001")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_note_found(cosmos_svc):
    note = {"id": "n-1", "doctor_id": "doctor-001", "content": "Note"}
    cosmos_svc._containers["notes"].read_item.return_value = note
    result = await cosmos_svc.get_note("doctor-001", "n-1")
    assert result["id"] == "n-1"


@pytest.mark.asyncio
async def test_get_note_not_found(cosmos_svc):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    cosmos_svc._containers["notes"].read_item.side_effect = CosmosResourceNotFoundError()
    result = await cosmos_svc.get_note("doctor-001", "nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_delete_note_success(cosmos_svc):
    result = await cosmos_svc.delete_note("doctor-001", "n-1")
    assert result is True


@pytest.mark.asyncio
async def test_delete_note_not_found(cosmos_svc):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    cosmos_svc._containers["notes"].delete_item.side_effect = CosmosResourceNotFoundError()
    result = await cosmos_svc.delete_note("doctor-001", "nonexistent")
    assert result is False


# ---------------------------------------------------------------------------
# Report operations
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_create_report(cosmos_svc):
    data = {
        "doctor_id": "doctor-001",
        "input_text": "CT abdomen",
        "findings": "Normal.",
        "impressions": "None.",
        "recommendations": "None.",
    }
    result = await cosmos_svc.create_report(data)
    assert result["status"] == "draft"
    assert result["versions"] == []
    assert "id" in result
    assert "created_at" in result


@pytest.mark.asyncio
async def test_get_report_found(cosmos_svc, sample_report):
    cosmos_svc._containers["reports"].read_item.return_value = sample_report
    result = await cosmos_svc.get_report("report-001", "doctor-001")
    assert result["id"] == "report-001"


@pytest.mark.asyncio
async def test_get_report_not_found(cosmos_svc):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    cosmos_svc._containers["reports"].read_item.side_effect = CosmosResourceNotFoundError()
    result = await cosmos_svc.get_report("nonexistent", "doctor-001")
    assert result is None


@pytest.mark.asyncio
async def test_list_reports_by_doctor(cosmos_svc, sample_report):
    cosmos_svc._containers["reports"].query_items.return_value = iter([sample_report])
    result = await cosmos_svc.list_reports(doctor_id="doctor-001")
    assert len(result) == 1


@pytest.mark.asyncio
async def test_list_reports_all(cosmos_svc, sample_report):
    cosmos_svc._containers["reports"].query_items.return_value = iter([sample_report])
    result = await cosmos_svc.list_reports()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_update_report_creates_version(cosmos_svc, sample_report):
    """T15: Updating a report should create a version snapshot."""
    cosmos_svc._containers["reports"].read_item.return_value = deepcopy(sample_report)
    result = await cosmos_svc.update_report(
        report_id="report-001",
        doctor_id="doctor-001",
        data={"findings": "Updated findings."},
    )
    assert result is not None
    assert len(result["versions"]) == 1
    assert result["versions"][0]["version"] == 1
    assert result["versions"][0]["findings"] == "Liver is normal."
    assert result["findings"] == "Updated findings."
    assert result["status"] == "edited"
    cosmos_svc._containers["reports"].replace_item.assert_called_once()


@pytest.mark.asyncio
async def test_update_report_not_found(cosmos_svc):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    cosmos_svc._containers["reports"].read_item.side_effect = CosmosResourceNotFoundError()
    result = await cosmos_svc.update_report("nonexistent", "doctor-001", {"findings": "New"})
    assert result is None


@pytest.mark.asyncio
async def test_approve_report(cosmos_svc, sample_report):
    cosmos_svc._containers["reports"].read_item.return_value = deepcopy(sample_report)
    result = await cosmos_svc.approve_report("report-001", "doctor-001")
    assert result is not None
    assert result["status"] == "final"


@pytest.mark.asyncio
async def test_approve_report_not_found(cosmos_svc):
    from azure.cosmos.exceptions import CosmosResourceNotFoundError

    cosmos_svc._containers["reports"].read_item.side_effect = CosmosResourceNotFoundError()
    result = await cosmos_svc.approve_report("nonexistent", "doctor-001")
    assert result is None


# ---------------------------------------------------------------------------
# Style profile operations
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_style_profile_found(cosmos_svc):
    profile = {"doctor_id": "doctor-001", "vocabulary_patterns": ["unremarkable"]}
    cosmos_svc._containers["style_profiles"].query_items.return_value = iter([profile])
    result = await cosmos_svc.get_style_profile("doctor-001")
    assert result is not None
    assert result["doctor_id"] == "doctor-001"


@pytest.mark.asyncio
async def test_get_style_profile_not_found(cosmos_svc):
    cosmos_svc._containers["style_profiles"].query_items.return_value = iter([])
    result = await cosmos_svc.get_style_profile("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_upsert_style_profile(cosmos_svc):
    data = {"doctor_id": "doctor-001", "vocabulary_patterns": ["within normal limits"]}
    result = await cosmos_svc.upsert_style_profile(data)
    assert "updated_at" in result
    assert "id" in result
    cosmos_svc._containers["style_profiles"].upsert_item.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_style_profile_with_existing_id(cosmos_svc):
    data = {"id": "sp-001", "doctor_id": "doctor-001", "vocabulary_patterns": []}
    result = await cosmos_svc.upsert_style_profile(data)
    assert result["id"] == "sp-001"


# ---------------------------------------------------------------------------
# Container not initialized
# ---------------------------------------------------------------------------
def test_container_not_initialized_raises():
    svc = CosmosDBService()
    with pytest.raises(RuntimeError, match="not initialized"):
        svc._container("doctors")


# ---------------------------------------------------------------------------
# Admin statistics
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_get_stats(cosmos_svc, sample_doctor, sample_report):
    cosmos_svc._containers["doctors"].query_items.return_value = iter([sample_doctor])
    cosmos_svc._containers["reports"].query_items.return_value = iter([5])
    cosmos_svc._containers["notes"].query_items.return_value = iter([10])
    result = await cosmos_svc.get_stats()
    assert "total_doctors" in result
    assert "total_reports" in result
    assert "total_notes" in result


@pytest.mark.asyncio
async def test_get_doctors_with_stats(cosmos_svc, sample_doctor):
    cosmos_svc._containers["doctors"].query_items.return_value = iter([deepcopy(sample_doctor)])
    cosmos_svc._containers["notes"].query_items.return_value = iter([])
    cosmos_svc._containers["reports"].query_items.return_value = iter([])
    result = await cosmos_svc.get_doctors_with_stats()
    assert len(result) == 1
    assert "note_count" in result[0]
    assert "report_count" in result[0]
