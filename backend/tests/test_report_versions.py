"""Tests for report version history (T15: generate → edit → approve → verify versions)."""

import copy
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.models.report import ReportResponse, ReportStatus, ReportVersion
from app.services.cosmos_db import CosmosDBService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_report(**overrides):
    base = {
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
    base.update(overrides)
    return base


def _setup_cosmos_service(report_data):
    """Set up a CosmosDBService with a mock container that stores report_data."""
    service = CosmosDBService()
    container = MagicMock()
    # Store the report in a mutable wrapper so replace_item can update it
    store = {"doc": copy.deepcopy(report_data)}

    def read_item(item, partition_key):
        if item == store["doc"]["id"]:
            return copy.deepcopy(store["doc"])
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        raise CosmosResourceNotFoundError(message="Not found", status_code=404)

    def replace_item(item, body):
        store["doc"] = copy.deepcopy(body)

    container.read_item = MagicMock(side_effect=read_item)
    container.replace_item = MagicMock(side_effect=replace_item)
    service._containers["reports"] = container
    return service, store


# ---------------------------------------------------------------------------
# Test: ReportStatus enum includes rejected
# ---------------------------------------------------------------------------
def test_report_status_includes_rejected():
    assert ReportStatus.REJECTED.value == "rejected"
    assert set(s.value for s in ReportStatus) == {"draft", "edited", "final", "rejected"}


# ---------------------------------------------------------------------------
# Test: ReportVersion model has edited_by field
# ---------------------------------------------------------------------------
def test_report_version_has_edited_by():
    v = ReportVersion(
        version=1,
        findings="Normal liver.",
        impressions="No acute findings.",
        recommendations="No follow-up needed.",
        status=ReportStatus.DRAFT,
        edited_at=datetime.utcnow(),
        edited_by="doctor-001",
    )
    assert v.edited_by == "doctor-001"


def test_report_version_edited_by_defaults_empty():
    v = ReportVersion(
        version=1,
        findings="Normal liver.",
        impressions="No findings.",
        recommendations="None.",
        status=ReportStatus.DRAFT,
        edited_at=datetime.utcnow(),
    )
    assert v.edited_by == ""


# ---------------------------------------------------------------------------
# Test: update_report creates version with edited_by
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_update_report_creates_version_with_edited_by():
    report = _make_report()
    service, store = _setup_cosmos_service(report)

    updated = await service.update_report(
        report_id="report-001",
        doctor_id="doctor-001",
        data={"findings": "Updated findings."},
        edited_by="doctor-001",
    )

    assert updated is not None
    assert updated["status"] == "edited"
    assert len(updated["versions"]) == 1
    version = updated["versions"][0]
    assert version["version"] == 1
    assert version["findings"] == "Normal liver."  # original content
    assert version["status"] == "draft"  # original status
    assert version["edited_by"] == "doctor-001"
    assert "edited_at" in version


# ---------------------------------------------------------------------------
# Test: approve_report creates version snapshot
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_approve_report_creates_version():
    report = _make_report(status="edited")
    service, store = _setup_cosmos_service(report)

    approved = await service.approve_report(
        report_id="report-001",
        doctor_id="doctor-001",
        approved_by="doctor-001",
    )

    assert approved is not None
    assert approved["status"] == "final"
    assert len(approved["versions"]) == 1
    version = approved["versions"][0]
    assert version["status"] == "edited"  # previous status before approval
    assert version["edited_by"] == "doctor-001"


# ---------------------------------------------------------------------------
# Test: reject_report creates version snapshot
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reject_report_creates_version():
    report = _make_report(status="edited")
    service, store = _setup_cosmos_service(report)

    rejected = await service.reject_report(
        report_id="report-001",
        doctor_id="doctor-001",
        rejected_by="doctor-001",
    )

    assert rejected is not None
    assert rejected["status"] == "rejected"
    assert len(rejected["versions"]) == 1
    version = rejected["versions"][0]
    assert version["status"] == "edited"
    assert version["edited_by"] == "doctor-001"


# ---------------------------------------------------------------------------
# T15: generate → edit → approve → verify all 3 versions stored
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_t15_generate_edit_approve_versions():
    """Full lifecycle: create (draft) → edit → approve → verify 3 versions."""
    report = _make_report()
    service, store = _setup_cosmos_service(report)

    # Step 1: Edit the report (creates version 1 with draft snapshot)
    await service.update_report(
        report_id="report-001",
        doctor_id="doctor-001",
        data={"findings": "Edited findings after review."},
        edited_by="doctor-001",
    )

    # Step 2: Edit again (creates version 2 with edited snapshot)
    await service.update_report(
        report_id="report-001",
        doctor_id="doctor-001",
        data={"impressions": "Updated impressions."},
        edited_by="doctor-002",
    )

    # Step 3: Approve (creates version 3 with edited snapshot)
    result = await service.approve_report(
        report_id="report-001",
        doctor_id="doctor-001",
        approved_by="admin-001",
    )

    assert result["status"] == "final"
    assert len(result["versions"]) == 3

    # Version 1: snapshot of original draft
    v1 = result["versions"][0]
    assert v1["version"] == 1
    assert v1["status"] == "draft"
    assert v1["findings"] == "Normal liver."
    assert v1["edited_by"] == "doctor-001"

    # Version 2: snapshot after first edit
    v2 = result["versions"][1]
    assert v2["version"] == 2
    assert v2["status"] == "edited"
    assert v2["findings"] == "Edited findings after review."
    assert v2["edited_by"] == "doctor-002"

    # Version 3: snapshot before approval
    v3 = result["versions"][2]
    assert v3["version"] == 3
    assert v3["status"] == "edited"
    assert v3["edited_by"] == "admin-001"


# ---------------------------------------------------------------------------
# Test: ReportResponse includes versions
# ---------------------------------------------------------------------------
def test_report_response_includes_versions():
    now = datetime.utcnow()
    resp = ReportResponse(
        id="report-001",
        doctor_id="doctor-001",
        input_text="CT scan.",
        findings="Normal.",
        impressions="No acute.",
        recommendations="None.",
        report_type="CT",
        body_region="Abdomen",
        status=ReportStatus.EDITED,
        versions=[
            ReportVersion(
                version=1,
                findings="Original.",
                impressions="Original imp.",
                recommendations="Original rec.",
                status=ReportStatus.DRAFT,
                edited_at=now,
                edited_by="doctor-001",
            ),
        ],
        created_at=now,
        updated_at=now,
    )
    assert len(resp.versions) == 1
    assert resp.versions[0].edited_by == "doctor-001"
    assert resp.versions[0].version == 1
