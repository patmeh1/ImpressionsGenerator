"""Tests for API router endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_claims(user_id="doctor-001", roles=None):
    from datetime import timedelta

    now = datetime.utcnow()
    return {
        "oid": user_id,
        "name": "Dr. Jane Smith",
        "preferred_username": "jane@hospital.org",
        "roles": roles or ["Doctor"],
        "tid": "test-tenant",
        "exp": (now + timedelta(hours=1)).timestamp(),
        "iat": now.timestamp(),
        "iss": "https://sts.windows.net/test-tenant/",
        "aud": "api://test-client",
    }


SAMPLE_DOCTOR = {
    "id": "doctor-001",
    "name": "Dr. Jane Smith",
    "specialty": "Radiology",
    "department": "Imaging",
    "created_at": datetime.utcnow().isoformat(),
}

SAMPLE_REPORT = {
    "id": "report-001",
    "doctor_id": "doctor-001",
    "input_text": "CT abdomen",
    "findings": "Normal liver.",
    "impressions": "No acute findings.",
    "recommendations": "None.",
    "report_type": "CT",
    "body_region": "Abdomen",
    "status": "draft",
    "versions": [],
    "created_at": datetime.utcnow().isoformat(),
    "updated_at": datetime.utcnow().isoformat(),
}


@pytest_asyncio.fixture()
async def client():
    """Create test client with mocked auth and services."""
    with (
        patch("app.auth.dependencies.validate_token", new_callable=AsyncMock) as mock_validate,
        patch("app.auth.entra_id._get_signing_keys", new_callable=AsyncMock),
    ):
        mock_validate.return_value = _make_claims()
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["Authorization"] = "Bearer test-token"
            yield ac


@pytest_asyncio.fixture()
async def admin_client():
    """Create test client with admin role."""
    with (
        patch("app.auth.dependencies.validate_token", new_callable=AsyncMock) as mock_validate,
        patch("app.auth.entra_id._get_signing_keys", new_callable=AsyncMock),
    ):
        mock_validate.return_value = _make_claims(user_id="admin-001", roles=["Admin"])
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["Authorization"] = "Bearer admin-token"
            yield ac


# ===========================================================================
# Health check
# ===========================================================================
@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ===========================================================================
# Doctors router
# ===========================================================================
@pytest.mark.asyncio
async def test_list_doctors_as_doctor(client):
    with patch("app.routers.doctors.cosmos_service") as mock:
        mock.get_doctor = AsyncMock(return_value=SAMPLE_DOCTOR)
        resp = await client.get("/api/doctors")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_doctors_as_admin(admin_client):
    with patch("app.routers.doctors.cosmos_service") as mock:
        mock.list_doctors = AsyncMock(return_value=[SAMPLE_DOCTOR])
        resp = await admin_client.get("/api/doctors")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_doctor_own_profile(client):
    with patch("app.routers.doctors.cosmos_service") as mock:
        mock.get_doctor = AsyncMock(return_value=SAMPLE_DOCTOR)
        resp = await client.get("/api/doctors/doctor-001")
        assert resp.status_code == 200
        assert resp.json()["id"] == "doctor-001"


@pytest.mark.asyncio
async def test_get_doctor_other_profile_forbidden(client):
    resp = await client.get("/api/doctors/doctor-999")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_doctor_not_found(client):
    with patch("app.routers.doctors.cosmos_service") as mock:
        mock.get_doctor = AsyncMock(return_value=None)
        resp = await client.get("/api/doctors/doctor-001")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_doctor_admin_only(admin_client):
    with patch("app.routers.doctors.cosmos_service") as mock:
        mock.create_doctor = AsyncMock(return_value=SAMPLE_DOCTOR)
        resp = await admin_client.post(
            "/api/doctors",
            json={"name": "Dr. New", "specialty": "Radiology"},
        )
        assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_doctor_forbidden_for_doctor_role(client):
    resp = await client.post(
        "/api/doctors",
        json={"name": "Dr. New", "specialty": "Radiology"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_doctor(client):
    with patch("app.routers.doctors.cosmos_service") as mock:
        updated = {**SAMPLE_DOCTOR, "department": "Neuroradiology"}
        mock.update_doctor = AsyncMock(return_value=updated)
        resp = await client.put(
            "/api/doctors/doctor-001",
            json={"department": "Neuroradiology"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_doctor_not_found(client):
    with patch("app.routers.doctors.cosmos_service") as mock:
        mock.update_doctor = AsyncMock(return_value=None)
        resp = await client.put(
            "/api/doctors/doctor-001",
            json={"department": "Neuro"},
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_doctor_admin(admin_client):
    with patch("app.routers.doctors.cosmos_service") as mock:
        mock.delete_doctor = AsyncMock(return_value=True)
        resp = await admin_client.delete("/api/doctors/doctor-001")
        assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_doctor_not_found(admin_client):
    with patch("app.routers.doctors.cosmos_service") as mock:
        mock.delete_doctor = AsyncMock(return_value=False)
        resp = await admin_client.delete("/api/doctors/doctor-001")
        assert resp.status_code == 404


# ===========================================================================
# Reports router
# ===========================================================================
@pytest.mark.asyncio
async def test_list_reports_as_doctor(client):
    with patch("app.routers.reports.cosmos_service") as mock:
        mock.list_reports = AsyncMock(return_value=[SAMPLE_REPORT])
        resp = await client.get("/api/reports")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_report(client):
    with patch("app.routers.reports.cosmos_service") as mock:
        mock.get_report = AsyncMock(return_value=SAMPLE_REPORT)
        resp = await client.get("/api/reports/report-001")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_report_not_found(client):
    with patch("app.routers.reports.cosmos_service") as mock:
        mock.get_report = AsyncMock(return_value=None)
        mock.list_reports = AsyncMock(return_value=[])
        resp = await client.get("/api/reports/nonexistent")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_report(client):
    updated = {
        **SAMPLE_REPORT,
        "findings": "Updated.",
        "status": "edited",
        "versions": [
            {
                "version": 1,
                "findings": "Normal liver.",
                "impressions": "No acute findings.",
                "recommendations": "None.",
                "status": "draft",
                "edited_at": datetime.utcnow().isoformat(),
            },
        ],
    }
    with patch("app.routers.reports.cosmos_service") as mock:
        mock.get_report = AsyncMock(return_value=SAMPLE_REPORT)
        mock.update_report = AsyncMock(return_value=updated)
        resp = await client.put(
            "/api/reports/report-001",
            json={"findings": "Updated."},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_approve_report(client):
    approved = {**SAMPLE_REPORT, "status": "final"}
    with patch("app.routers.reports.cosmos_service") as mock:
        mock.get_report = AsyncMock(return_value=SAMPLE_REPORT)
        mock.approve_report = AsyncMock(return_value=approved)
        resp = await client.post("/api/reports/report-001/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "final"


@pytest.mark.asyncio
async def test_get_report_versions(client):
    report_with_versions = {
        **SAMPLE_REPORT,
        "versions": [
            {"version": 1, "findings": "V1.", "impressions": "V1.",
             "recommendations": "V1.", "status": "draft",
             "edited_at": datetime.utcnow().isoformat()},
        ],
    }
    with patch("app.routers.reports.cosmos_service") as mock:
        mock.get_report = AsyncMock(return_value=report_with_versions)
        resp = await client.get("/api/reports/report-001/versions")
        assert resp.status_code == 200
        assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_report_access_forbidden(client):
    """Doctor cannot access another doctor's report."""
    other_report = {**SAMPLE_REPORT, "doctor_id": "doctor-999"}
    with patch("app.routers.reports.cosmos_service") as mock:
        mock.get_report = AsyncMock(return_value=other_report)
        resp = await client.get("/api/reports/report-001")
        assert resp.status_code == 403


# ===========================================================================
# Generate router
# ===========================================================================
@pytest.mark.asyncio
async def test_generate_report_endpoint(client):
    generated = {
        **SAMPLE_REPORT,
        "grounding": {"is_grounded": True, "hallucinated_values": []},
    }
    with patch("app.routers.generate.generation_service") as mock:
        mock.generate = AsyncMock(return_value=generated)
        resp = await client.post(
            "/api/generate",
            json={
                "dictated_text": "CT abdomen findings.",
                "doctor_id": "doctor-001",
                "report_type": "CT",
                "body_region": "Abdomen",
            },
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_generate_forbidden_for_other_doctor(client):
    resp = await client.post(
        "/api/generate",
        json={
            "dictated_text": "CT abdomen.",
            "doctor_id": "doctor-999",
            "report_type": "CT",
            "body_region": "Abdomen",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_generate_runtime_error(client):
    with patch("app.routers.generate.generation_service") as mock:
        mock.generate = AsyncMock(side_effect=RuntimeError("Service down"))
        resp = await client.post(
            "/api/generate",
            json={
                "dictated_text": "CT abdomen.",
                "doctor_id": "doctor-001",
                "report_type": "CT",
                "body_region": "Abdomen",
            },
        )
        assert resp.status_code == 502


@pytest.mark.asyncio
async def test_generate_unexpected_error(client):
    with patch("app.routers.generate.generation_service") as mock:
        mock.generate = AsyncMock(side_effect=Exception("Unexpected"))
        resp = await client.post(
            "/api/generate",
            json={
                "dictated_text": "CT abdomen.",
                "doctor_id": "doctor-001",
                "report_type": "CT",
                "body_region": "Abdomen",
            },
        )
        assert resp.status_code == 500


# ===========================================================================
# Notes router
# ===========================================================================
@pytest.mark.asyncio
async def test_create_note_paste(client):
    note = {
        "id": "n-1",
        "doctor_id": "doctor-001",
        "content": "CT findings",
        "source_type": "paste",
        "file_name": None,
        "created_at": datetime.utcnow().isoformat(),
    }
    with (
        patch("app.routers.notes.cosmos_service") as mock_cosmos,
        patch("app.routers.notes.ai_search_service") as mock_search,
        patch("app.routers.notes.style_extraction_service") as mock_style,
    ):
        mock_cosmos.create_note = AsyncMock(return_value=note)
        mock_search.index_note = AsyncMock()
        mock_style.extract_style = AsyncMock()
        resp = await client.post(
            "/api/doctors/doctor-001/notes",
            data={"content": "CT findings"},
        )
        assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_note_no_content_or_file(client):
    resp = await client.post("/api/doctors/doctor-001/notes")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_notes(client):
    notes = [
        {"id": "n-1", "doctor_id": "doctor-001", "content": "Note",
         "source_type": "paste", "file_name": None,
         "created_at": datetime.utcnow().isoformat()},
    ]
    with patch("app.routers.notes.cosmos_service") as mock:
        mock.list_notes = AsyncMock(return_value=notes)
        resp = await client.get("/api/doctors/doctor-001/notes")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_note(client):
    note = {"id": "n-1", "doctor_id": "doctor-001", "file_name": None}
    with (
        patch("app.routers.notes.cosmos_service") as mock_cosmos,
        patch("app.routers.notes.ai_search_service") as mock_search,
    ):
        mock_cosmos.get_note = AsyncMock(return_value=note)
        mock_cosmos.delete_note = AsyncMock(return_value=True)
        mock_search.delete_document = AsyncMock()
        resp = await client.delete("/api/doctors/doctor-001/notes/n-1")
        assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_note_not_found(client):
    with patch("app.routers.notes.cosmos_service") as mock:
        mock.get_note = AsyncMock(return_value=None)
        resp = await client.delete("/api/doctors/doctor-001/notes/n-1")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_notes_access_forbidden(client):
    """Doctor cannot access another doctor's notes."""
    resp = await client.get("/api/doctors/doctor-999/notes")
    assert resp.status_code == 403


# ===========================================================================
# Admin router
# ===========================================================================
@pytest.mark.asyncio
async def test_admin_stats(admin_client):
    with patch("app.routers.admin.cosmos_service") as mock:
        mock.get_stats = AsyncMock(return_value={
            "total_doctors": 5, "total_reports": 20, "total_notes": 50
        })
        resp = await admin_client.get("/api/admin/stats")
        assert resp.status_code == 200
        assert resp.json()["total_doctors"] == 5


@pytest.mark.asyncio
async def test_admin_stats_forbidden_for_doctor(client):
    resp = await client.get("/api/admin/stats")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_doctors_with_stats(admin_client):
    with patch("app.routers.admin.cosmos_service") as mock:
        mock.get_doctors_with_stats = AsyncMock(return_value=[
            {**SAMPLE_DOCTOR, "note_count": 3, "report_count": 2}
        ])
        resp = await admin_client.get("/api/admin/doctors")
        assert resp.status_code == 200
