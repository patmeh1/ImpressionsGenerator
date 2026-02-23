"""Integration tests covering full pipelines: upload→style, generation→grounding,
auth end-to-end, and multi-doctor scenarios.

T23: Full upload pipeline
T24: Full generation pipeline
T25: Auth end-to-end
T26: Multi-doctor generation
"""

import json
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Helpers
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


DOCTOR_A_CLAIMS = _make_claims()
DOCTOR_B_CLAIMS = _make_claims(
    user_id="doctor-002",
    name="Dr. Bob Jones",
    email="bob.jones@hospital.org",
)

SAMPLE_STYLE_A = {
    "id": "style-001",
    "doctor_id": "doctor-001",
    "vocabulary_patterns": ["unremarkable", "within normal limits"],
    "abbreviation_map": {"CT": "computed tomography"},
    "sentence_structure": ["short declarative"],
    "section_ordering": ["findings", "impressions", "recommendations"],
    "sample_phrases": ["No acute abnormality."],
    "updated_at": datetime.utcnow().isoformat(),
}

SAMPLE_STYLE_B = {
    "id": "style-002",
    "doctor_id": "doctor-002",
    "vocabulary_patterns": ["normal appearance", "no significant change"],
    "abbreviation_map": {"MRI": "magnetic resonance imaging"},
    "sentence_structure": ["verbose narrative"],
    "section_ordering": ["findings", "recommendations", "impressions"],
    "sample_phrases": ["Recommend close follow-up."],
    "updated_at": datetime.utcnow().isoformat(),
}

SAMPLE_GENERATED = {
    "findings": (
        "The liver measures 14.5 cm and is normal in size. "
        "A 3.2 cm mass is present in the right adrenal gland."
    ),
    "impressions": "1. Stable 3.2 cm right adrenal mass.",
    "recommendations": "Recommend follow-up imaging in 6 months.",
}

SAMPLE_DICTATION = (
    "CT abdomen pelvis with contrast. The liver is normal in size measuring "
    "14.5 cm. There is a 3.2 cm mass in the right adrenal gland, unchanged "
    "from prior study. Kidneys are normal bilaterally. "
    "No hydronephrosis. Spleen measures 10.8 cm. No free fluid."
)


def _openai_response(content: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(content)
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# Shared fixture: test client that allows swapping claims per-test
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture()
async def integration_client() -> AsyncGenerator[tuple[AsyncClient, AsyncMock], None]:
    """Create a test client with a controllable validate_token mock."""
    with (
        patch("app.auth.entra_id.validate_token", new_callable=AsyncMock),
        patch("app.auth.entra_id._get_signing_keys", new_callable=AsyncMock),
        patch("app.auth.dependencies.validate_token", new_callable=AsyncMock) as mock_validate,
    ):
        mock_validate.return_value = DOCTOR_A_CLAIMS

        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["Authorization"] = "Bearer test-token"
            yield ac, mock_validate


# ===================================================================
# T23 – Full upload pipeline
# ===================================================================
class TestT23UploadPipeline:
    """Upload file → parse → extract style → store in Cosmos DB + AI Search."""

    @pytest.mark.asyncio
    async def test_upload_txt_full_pipeline(self, integration_client):
        """Uploading a .txt file should parse it, create a note in Cosmos,
        index it in AI Search, and trigger style extraction."""
        client, mock_validate = integration_client
        mock_validate.return_value = DOCTOR_A_CLAIMS

        note_doc = {
            "id": "note-new-001",
            "doctor_id": "doctor-001",
            "content": "CT Abdomen normal. Liver 14.5 cm. No focal lesion.",
            "source_type": "upload",
            "file_name": "report.txt",
            "created_at": datetime.utcnow().isoformat(),
        }

        with (
            patch("app.routers.notes.blob_service") as mock_blob,
            patch("app.routers.notes.cosmos_service") as mock_cosmos,
            patch("app.routers.notes.ai_search_service") as mock_search,
            patch("app.routers.notes.style_extraction_service") as mock_style,
        ):
            mock_blob.upload_file = AsyncMock()
            mock_cosmos.create_note = AsyncMock(return_value=note_doc)
            mock_search.index_note = AsyncMock()
            mock_style.extract_style = AsyncMock()

            file_content = b"CT Abdomen normal. Liver 14.5 cm. No focal lesion."
            response = await client.post(
                "/api/doctors/doctor-001/notes",
                files={"file": ("report.txt", file_content, "text/plain")},
            )

            assert response.status_code == 201
            body = response.json()
            assert body["id"] == "note-new-001"
            assert body["content"] == "CT Abdomen normal. Liver 14.5 cm. No focal lesion."

            # Verify blob storage received the file
            mock_blob.upload_file.assert_called_once()
            call_kwargs = mock_blob.upload_file.call_args
            assert call_kwargs[1]["doctor_id"] == "doctor-001" or call_kwargs[0][0] == "doctor-001"

            # Verify note was stored in Cosmos DB
            mock_cosmos.create_note.assert_called_once()

            # Verify note was indexed in AI Search
            mock_search.index_note.assert_called_once()
            indexed_doc = mock_search.index_note.call_args[0][0]
            assert indexed_doc["doctor_id"] == "doctor-001"

            # Verify style extraction was triggered
            mock_style.extract_style.assert_called_once_with("doctor-001")

    @pytest.mark.asyncio
    async def test_upload_stores_content_in_cosmos(self, integration_client):
        """The parsed text content must be passed through to Cosmos create_note."""
        client, mock_validate = integration_client
        mock_validate.return_value = DOCTOR_A_CLAIMS

        note_doc = {
            "id": "note-new-002",
            "doctor_id": "doctor-001",
            "content": "Findings: Normal chest X-ray.",
            "source_type": "upload",
            "file_name": "chest.txt",
            "created_at": datetime.utcnow().isoformat(),
        }

        with (
            patch("app.routers.notes.blob_service") as mock_blob,
            patch("app.routers.notes.cosmos_service") as mock_cosmos,
            patch("app.routers.notes.ai_search_service") as mock_search,
            patch("app.routers.notes.style_extraction_service") as mock_style,
        ):
            mock_blob.upload_file = AsyncMock()
            mock_cosmos.create_note = AsyncMock(return_value=note_doc)
            mock_search.index_note = AsyncMock()
            mock_style.extract_style = AsyncMock()

            response = await client.post(
                "/api/doctors/doctor-001/notes",
                files={"file": ("chest.txt", b"Findings: Normal chest X-ray.", "text/plain")},
            )

            assert response.status_code == 201
            # Verify the content passed to cosmos_service.create_note
            cosmos_call = mock_cosmos.create_note.call_args
            note_data = cosmos_call[0][1] if len(cosmos_call[0]) > 1 else cosmos_call[1].get("data")
            assert note_data["content"] == "Findings: Normal chest X-ray."
            assert note_data["source_type"] == "upload"

    @pytest.mark.asyncio
    async def test_upload_paste_text_pipeline(self, integration_client):
        """Pasting text content should store in Cosmos and trigger indexing."""
        client, mock_validate = integration_client
        mock_validate.return_value = DOCTOR_A_CLAIMS

        note_doc = {
            "id": "note-new-003",
            "doctor_id": "doctor-001",
            "content": "Normal MRI brain. No acute intracranial abnormality.",
            "source_type": "paste",
            "file_name": None,
            "created_at": datetime.utcnow().isoformat(),
        }

        with (
            patch("app.routers.notes.blob_service") as mock_blob,
            patch("app.routers.notes.cosmos_service") as mock_cosmos,
            patch("app.routers.notes.ai_search_service") as mock_search,
            patch("app.routers.notes.style_extraction_service") as mock_style,
        ):
            mock_cosmos.create_note = AsyncMock(return_value=note_doc)
            mock_search.index_note = AsyncMock()
            mock_style.extract_style = AsyncMock()

            response = await client.post(
                "/api/doctors/doctor-001/notes",
                data={"content": "Normal MRI brain. No acute intracranial abnormality."},
            )

            assert response.status_code == 201
            body = response.json()
            assert body["source_type"] == "paste"

            # Blob upload should NOT have been called for paste
            mock_blob.upload_file.assert_not_called()

            # Cosmos + AI Search + style extraction should all fire
            mock_cosmos.create_note.assert_called_once()
            mock_search.index_note.assert_called_once()
            mock_style.extract_style.assert_called_once_with("doctor-001")


# ===================================================================
# T24 – Full generation pipeline
# ===================================================================
class TestT24GenerationPipeline:
    """Paste dictation → retrieve style → generate → validate grounding → return report."""

    @pytest.mark.asyncio
    async def test_full_generation_pipeline(self, integration_client):
        """Full pipeline: style retrieval → OpenAI generation → grounding → persist."""
        client, mock_validate = integration_client
        mock_validate.return_value = DOCTOR_A_CLAIMS

        report_doc = {
            "id": "report-gen-001",
            "doctor_id": "doctor-001",
            "input_text": SAMPLE_DICTATION,
            "report_type": "CT",
            "body_region": "Abdomen",
            "findings": SAMPLE_GENERATED["findings"],
            "impressions": SAMPLE_GENERATED["impressions"],
            "recommendations": SAMPLE_GENERATED["recommendations"],
            "status": "draft",
            "versions": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.openai_service") as mock_openai,
        ):
            # Style profile exists
            mock_cosmos.get_style_profile = AsyncMock(return_value=SAMPLE_STYLE_A)
            # No few-shot examples
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            # OpenAI returns structured report
            mock_openai.generate_report = AsyncMock(return_value=SAMPLE_GENERATED)
            # Persist report
            mock_cosmos.create_report = AsyncMock(return_value=report_doc)
            # Index for search
            mock_search.index_report = AsyncMock()

            response = await client.post(
                "/api/generate",
                json={
                    "dictated_text": SAMPLE_DICTATION,
                    "doctor_id": "doctor-001",
                    "report_type": "CT",
                    "body_region": "Abdomen",
                },
            )

            assert response.status_code == 200
            body = response.json()

            # Verify structured report sections present
            assert body["findings"]
            assert body["impressions"]
            assert body["recommendations"]

            # Verify grounding validation is included
            assert "grounding" in body
            assert "is_grounded" in body["grounding"]

            # Verify style was retrieved
            mock_cosmos.get_style_profile.assert_called_once_with("doctor-001")

            # Verify OpenAI was called with style instructions
            mock_openai.generate_report.assert_called_once()
            gen_kwargs = mock_openai.generate_report.call_args[1]
            assert gen_kwargs["dictated_text"] == SAMPLE_DICTATION
            # Style instructions should contain doctor's vocabulary
            assert "unremarkable" in gen_kwargs["style_instructions"]

            # Verify report was persisted
            mock_cosmos.create_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_generation_grounding_validates_numbers(self, integration_client):
        """Generated report with values from dictation should be grounded."""
        client, mock_validate = integration_client
        mock_validate.return_value = DOCTOR_A_CLAIMS

        # Generated report uses only values present in the dictation
        grounded_output = {
            "findings": "Liver measures 14.5 cm. 3.2 cm right adrenal mass.",
            "impressions": "Stable 3.2 cm right adrenal mass.",
            "recommendations": "Follow-up recommended.",
        }

        report_doc = {
            "id": "report-gen-002",
            "doctor_id": "doctor-001",
            "input_text": SAMPLE_DICTATION,
            "report_type": "CT",
            "body_region": "Abdomen",
            **grounded_output,
            "status": "draft",
            "versions": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.openai_service") as mock_openai,
        ):
            mock_cosmos.get_style_profile = AsyncMock(return_value=SAMPLE_STYLE_A)
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            mock_openai.generate_report = AsyncMock(return_value=grounded_output)
            mock_cosmos.create_report = AsyncMock(return_value=report_doc)
            mock_search.index_report = AsyncMock()

            response = await client.post(
                "/api/generate",
                json={
                    "dictated_text": SAMPLE_DICTATION,
                    "doctor_id": "doctor-001",
                    "report_type": "CT",
                    "body_region": "Abdomen",
                },
            )

            assert response.status_code == 200
            body = response.json()
            # All values (14.5, 3.2) come from the dictation → grounded
            assert body["grounding"]["is_grounded"] is True

    @pytest.mark.asyncio
    async def test_generation_detects_hallucinated_values(self, integration_client):
        """Generated report with fabricated values should fail grounding."""
        client, mock_validate = integration_client
        mock_validate.return_value = DOCTOR_A_CLAIMS

        # This output includes "7.8 cm" which is NOT in the dictation
        hallucinated_output = {
            "findings": "Liver measures 14.5 cm. A 7.8 cm mass in the left kidney.",
            "impressions": "Large left renal mass.",
            "recommendations": "Recommend urgent biopsy.",
        }

        report_doc = {
            "id": "report-gen-003",
            "doctor_id": "doctor-001",
            "input_text": SAMPLE_DICTATION,
            "report_type": "CT",
            "body_region": "Abdomen",
            **hallucinated_output,
            "status": "draft",
            "versions": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.openai_service") as mock_openai,
        ):
            mock_cosmos.get_style_profile = AsyncMock(return_value=SAMPLE_STYLE_A)
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            mock_openai.generate_report = AsyncMock(return_value=hallucinated_output)
            mock_cosmos.create_report = AsyncMock(return_value=report_doc)
            mock_search.index_report = AsyncMock()

            response = await client.post(
                "/api/generate",
                json={
                    "dictated_text": SAMPLE_DICTATION,
                    "doctor_id": "doctor-001",
                    "report_type": "CT",
                    "body_region": "Abdomen",
                },
            )

            assert response.status_code == 200
            body = response.json()
            # 7.8 is not in the input → grounding should fail
            assert body["grounding"]["is_grounded"] is False
            assert len(body["grounding"]["hallucinated_values"]) > 0


# ===================================================================
# T25 – Auth end-to-end
# ===================================================================
class TestT25AuthEndToEnd:
    """Login → access protected endpoint → logout → verify token revoked."""

    @pytest.mark.asyncio
    async def test_valid_token_accesses_protected_endpoint(self, integration_client):
        """A valid bearer token should allow access to a protected endpoint."""
        client, mock_validate = integration_client
        mock_validate.return_value = DOCTOR_A_CLAIMS

        with patch("app.routers.doctors.cosmos_service") as mock_cosmos:
            mock_cosmos.get_doctor = AsyncMock(return_value={
                "id": "doctor-001",
                "name": "Dr. Jane Smith",
                "specialty": "Radiology",
                "department": "Diagnostic Imaging",
                "created_at": datetime.utcnow().isoformat(),
            })

            response = await client.get("/api/doctors/doctor-001")
            assert response.status_code == 200
            assert response.json()["name"] == "Dr. Jane Smith"

    @pytest.mark.asyncio
    async def test_missing_token_returns_401(self):
        """A request without Authorization header should return 401/403."""
        with (
            patch("app.auth.entra_id.validate_token", new_callable=AsyncMock),
            patch("app.auth.entra_id._get_signing_keys", new_callable=AsyncMock),
            patch("app.auth.dependencies.validate_token", new_callable=AsyncMock),
        ):
            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                # No Authorization header
                response = await ac.get("/api/doctors/doctor-001")
                assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, integration_client):
        """An invalid token that fails validation should return 401."""
        client, mock_validate = integration_client
        mock_validate.side_effect = ValueError("Token validation failed: invalid signature")

        response = await client.get("/api/doctors/doctor-001")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, integration_client):
        """An expired token should return 401."""
        client, mock_validate = integration_client
        mock_validate.side_effect = ValueError("Token validation failed: token expired")

        response = await client.get("/api/doctors/doctor-001")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_revoked_token_returns_401(self, integration_client):
        """After logout (token revocation), subsequent requests should return 401."""
        client, mock_validate = integration_client

        # First request succeeds (valid token)
        mock_validate.return_value = DOCTOR_A_CLAIMS
        with patch("app.routers.doctors.cosmos_service") as mock_cosmos:
            mock_cosmos.get_doctor = AsyncMock(return_value={
                "id": "doctor-001",
                "name": "Dr. Jane Smith",
                "specialty": "Radiology",
                "department": "Diagnostic Imaging",
                "created_at": datetime.utcnow().isoformat(),
            })
            response = await client.get("/api/doctors/doctor-001")
            assert response.status_code == 200

        # Simulate token revocation (logout) — subsequent calls raise ValueError
        mock_validate.side_effect = ValueError("Token revoked")
        mock_validate.return_value = None

        response = await client.get("/api/doctors/doctor-001")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_doctor_cannot_access_other_doctors_endpoint(self, integration_client):
        """A doctor should not be able to access another doctor's profile."""
        client, mock_validate = integration_client
        # Token identifies as doctor-001
        mock_validate.return_value = DOCTOR_A_CLAIMS

        # Try accessing doctor-002's profile
        response = await client.get("/api/doctors/doctor-002")
        assert response.status_code == 403


# ===================================================================
# T26 – Multi-doctor generation
# ===================================================================
class TestT26MultiDoctorGeneration:
    """Two doctors generate reports → each gets their own style applied."""

    @pytest.mark.asyncio
    async def test_doctor_a_gets_own_style(self, integration_client):
        """Doctor A's generation should use Doctor A's style profile."""
        client, mock_validate = integration_client
        mock_validate.return_value = DOCTOR_A_CLAIMS

        report_doc = {
            "id": "report-a-001",
            "doctor_id": "doctor-001",
            "input_text": SAMPLE_DICTATION,
            "report_type": "CT",
            "body_region": "Abdomen",
            **SAMPLE_GENERATED,
            "status": "draft",
            "versions": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.openai_service") as mock_openai,
        ):
            mock_cosmos.get_style_profile = AsyncMock(return_value=SAMPLE_STYLE_A)
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            mock_openai.generate_report = AsyncMock(return_value=SAMPLE_GENERATED)
            mock_cosmos.create_report = AsyncMock(return_value=report_doc)
            mock_search.index_report = AsyncMock()

            response = await client.post(
                "/api/generate",
                json={
                    "dictated_text": SAMPLE_DICTATION,
                    "doctor_id": "doctor-001",
                    "report_type": "CT",
                    "body_region": "Abdomen",
                },
            )

            assert response.status_code == 200

            # Verify Doctor A's style was retrieved
            mock_cosmos.get_style_profile.assert_called_once_with("doctor-001")

            # Verify style instructions contain Doctor A's vocabulary
            gen_kwargs = mock_openai.generate_report.call_args[1]
            assert "unremarkable" in gen_kwargs["style_instructions"]
            assert "within normal limits" in gen_kwargs["style_instructions"]

    @pytest.mark.asyncio
    async def test_doctor_b_gets_own_style(self, integration_client):
        """Doctor B's generation should use Doctor B's style profile."""
        client, mock_validate = integration_client
        mock_validate.return_value = DOCTOR_B_CLAIMS

        generated_b = {
            "findings": "Normal appearance of the liver. No significant change.",
            "impressions": "No acute findings.",
            "recommendations": "Recommend close follow-up.",
        }

        report_doc = {
            "id": "report-b-001",
            "doctor_id": "doctor-002",
            "input_text": SAMPLE_DICTATION,
            "report_type": "CT",
            "body_region": "Abdomen",
            **generated_b,
            "status": "draft",
            "versions": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.openai_service") as mock_openai,
        ):
            mock_cosmos.get_style_profile = AsyncMock(return_value=SAMPLE_STYLE_B)
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            mock_openai.generate_report = AsyncMock(return_value=generated_b)
            mock_cosmos.create_report = AsyncMock(return_value=report_doc)
            mock_search.index_report = AsyncMock()

            response = await client.post(
                "/api/generate",
                json={
                    "dictated_text": SAMPLE_DICTATION,
                    "doctor_id": "doctor-002",
                    "report_type": "CT",
                    "body_region": "Abdomen",
                },
            )

            assert response.status_code == 200

            # Verify Doctor B's style was retrieved (not A's)
            mock_cosmos.get_style_profile.assert_called_once_with("doctor-002")

            # Verify style instructions contain Doctor B's vocabulary
            gen_kwargs = mock_openai.generate_report.call_args[1]
            assert "normal appearance" in gen_kwargs["style_instructions"]
            assert "no significant change" in gen_kwargs["style_instructions"]

    @pytest.mark.asyncio
    async def test_two_doctors_generate_independently(self, integration_client):
        """Two doctors generating reports should each get isolated style profiles."""
        client, mock_validate = integration_client

        # --- Doctor A generates ---
        mock_validate.return_value = DOCTOR_A_CLAIMS

        report_a = {
            "id": "report-a-002",
            "doctor_id": "doctor-001",
            "input_text": SAMPLE_DICTATION,
            **SAMPLE_GENERATED,
            "report_type": "CT",
            "body_region": "Abdomen",
            "status": "draft",
            "versions": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.openai_service") as mock_openai,
        ):
            mock_cosmos.get_style_profile = AsyncMock(return_value=SAMPLE_STYLE_A)
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            mock_openai.generate_report = AsyncMock(return_value=SAMPLE_GENERATED)
            mock_cosmos.create_report = AsyncMock(return_value=report_a)
            mock_search.index_report = AsyncMock()

            resp_a = await client.post(
                "/api/generate",
                json={
                    "dictated_text": SAMPLE_DICTATION,
                    "doctor_id": "doctor-001",
                    "report_type": "CT",
                    "body_region": "Abdomen",
                },
            )

            assert resp_a.status_code == 200
            style_a_instructions = mock_openai.generate_report.call_args[1]["style_instructions"]

        # --- Doctor B generates ---
        mock_validate.return_value = DOCTOR_B_CLAIMS

        generated_b = {
            "findings": "Normal liver. No significant change.",
            "impressions": "No acute findings.",
            "recommendations": "Recommend close follow-up.",
        }
        report_b = {
            "id": "report-b-002",
            "doctor_id": "doctor-002",
            "input_text": SAMPLE_DICTATION,
            **generated_b,
            "report_type": "CT",
            "body_region": "Abdomen",
            "status": "draft",
            "versions": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.openai_service") as mock_openai,
        ):
            mock_cosmos.get_style_profile = AsyncMock(return_value=SAMPLE_STYLE_B)
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            mock_openai.generate_report = AsyncMock(return_value=generated_b)
            mock_cosmos.create_report = AsyncMock(return_value=report_b)
            mock_search.index_report = AsyncMock()

            resp_b = await client.post(
                "/api/generate",
                json={
                    "dictated_text": SAMPLE_DICTATION,
                    "doctor_id": "doctor-002",
                    "report_type": "CT",
                    "body_region": "Abdomen",
                },
            )

            assert resp_b.status_code == 200
            style_b_instructions = mock_openai.generate_report.call_args[1]["style_instructions"]

        # Verify the styles are different between doctors
        assert style_a_instructions != style_b_instructions
        assert "unremarkable" in style_a_instructions
        assert "normal appearance" in style_b_instructions

    @pytest.mark.asyncio
    async def test_doctor_cannot_generate_for_other_doctor(self, integration_client):
        """Doctor A should not be able to generate reports for Doctor B."""
        client, mock_validate = integration_client
        # Token identifies as doctor-001
        mock_validate.return_value = DOCTOR_A_CLAIMS

        response = await client.post(
            "/api/generate",
            json={
                "dictated_text": SAMPLE_DICTATION,
                "doctor_id": "doctor-002",
                "report_type": "CT",
                "body_region": "Abdomen",
            },
        )

        assert response.status_code == 403
