"""Tests for service layer — style extraction, blob storage, generation, OpenAI."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.style_profile import StyleProfile


# ===========================================================================
# StyleExtractionService
# ===========================================================================
class TestStyleExtractionService:
    """Tests for StyleExtractionService."""

    @pytest.mark.asyncio
    async def test_extract_style_no_notes(self):
        """When no notes exist, return an empty style profile."""
        with (
            patch("app.services.style_extraction.cosmos_service") as mock_cosmos,
            patch("app.services.style_extraction.openai_service"),
        ):
            mock_cosmos.list_notes = AsyncMock(return_value=[])
            from app.services.style_extraction import StyleExtractionService

            svc = StyleExtractionService()
            profile = await svc.extract_style("doctor-001")
            assert profile.doctor_id == "doctor-001"
            assert profile.vocabulary_patterns == []

    @pytest.mark.asyncio
    async def test_extract_style_with_notes(self):
        """Notes should be analyzed and a profile created."""
        notes = [
            {"content": "CT abdomen: Liver unremarkable. No acute findings."},
            {"content": "MRI brain: No midline shift. Ventricles normal."},
        ]
        style_data = {
            "vocabulary_patterns": ["unremarkable", "no acute"],
            "abbreviation_map": {"CT": "computed tomography"},
            "sentence_structure": ["short declarative"],
            "section_ordering": ["findings", "impressions"],
            "sample_phrases": ["No acute abnormality."],
        }
        with (
            patch("app.services.style_extraction.cosmos_service") as mock_cosmos,
            patch("app.services.style_extraction.openai_service") as mock_openai,
        ):
            mock_cosmos.list_notes = AsyncMock(return_value=notes)
            mock_cosmos.get_style_profile = AsyncMock(return_value=None)
            mock_cosmos.upsert_style_profile = AsyncMock(side_effect=lambda d: d)
            mock_openai.analyze_style = AsyncMock(return_value=style_data)

            from app.services.style_extraction import StyleExtractionService

            svc = StyleExtractionService()
            profile = await svc.extract_style("doctor-001")
            assert "unremarkable" in profile.vocabulary_patterns
            mock_cosmos.upsert_style_profile.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_style_updates_existing(self):
        """If a profile already exists, it should update with the same id."""
        notes = [{"content": "CT chest: Lungs clear."}]
        existing = {"id": "sp-existing", "doctor_id": "doctor-001"}
        style_data = {
            "vocabulary_patterns": ["clear"],
            "abbreviation_map": {},
            "sentence_structure": [],
            "section_ordering": [],
            "sample_phrases": [],
        }
        with (
            patch("app.services.style_extraction.cosmos_service") as mock_cosmos,
            patch("app.services.style_extraction.openai_service") as mock_openai,
        ):
            mock_cosmos.list_notes = AsyncMock(return_value=notes)
            mock_cosmos.get_style_profile = AsyncMock(return_value=existing)
            mock_cosmos.upsert_style_profile = AsyncMock(side_effect=lambda d: d)
            mock_openai.analyze_style = AsyncMock(return_value=style_data)

            from app.services.style_extraction import StyleExtractionService

            svc = StyleExtractionService()
            profile = await svc.extract_style("doctor-001")
            call_data = mock_cosmos.upsert_style_profile.call_args[0][0]
            assert call_data["id"] == "sp-existing"

    def test_prepare_notes_text(self):
        """Notes should be combined into a single block."""
        from app.services.style_extraction import StyleExtractionService

        svc = StyleExtractionService()
        notes = [
            {"content": "Note one content."},
            {"content": "Note two content."},
            {"content": ""},  # empty note should be skipped
        ]
        text = svc._prepare_notes_text(notes)
        assert "Note one content." in text
        assert "Note two content." in text
        assert "--- Note 1 ---" in text

    def test_build_style_instructions_with_profile(self):
        """Instructions should include vocabulary, abbreviations, etc."""
        from app.services.style_extraction import StyleExtractionService

        svc = StyleExtractionService()
        profile = StyleProfile(
            doctor_id="d-1",
            vocabulary_patterns=["unremarkable", "within normal limits"],
            abbreviation_map={"CT": "computed tomography"},
            sentence_structure=["short declarative"],
            section_ordering=["findings", "impressions"],
            sample_phrases=["No acute abnormality."],
        )
        instructions = svc.build_style_instructions(profile)
        assert "unremarkable" in instructions
        assert "CT = computed tomography" in instructions
        assert "findings → impressions" in instructions
        assert "No acute abnormality." in instructions

    def test_build_style_instructions_empty_profile(self):
        """Empty profile should return default instructions."""
        from app.services.style_extraction import StyleExtractionService

        svc = StyleExtractionService()
        profile = StyleProfile(doctor_id="d-1")
        instructions = svc.build_style_instructions(profile)
        assert "No specific style preferences" in instructions


# ===========================================================================
# BlobStorageService
# ===========================================================================
class TestBlobStorageService:
    """Tests for BlobStorageService."""

    def test_get_blob_path(self):
        """Blob path should include doctor_id prefix."""
        from app.services.blob_storage import BlobStorageService

        svc = BlobStorageService()
        path = svc._get_blob_path("doctor-001", "report.pdf")
        assert path == "doctor-001/report.pdf"

    @pytest.mark.asyncio
    async def test_upload_file(self):
        from app.services.blob_storage import BlobStorageService

        svc = BlobStorageService()
        mock_blob_client = MagicMock()
        mock_blob_client.upload_blob = MagicMock()
        mock_blob_client.url = "https://storage/doctor-001/file.pdf"

        mock_client = MagicMock()
        mock_client.get_blob_client.return_value = mock_blob_client
        svc._client = mock_client

        result = await svc.upload_file("doctor-001", "file.pdf", b"content", "application/pdf")
        assert result["file_name"] == "file.pdf"
        assert result["size"] == 7
        mock_blob_client.upload_blob.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_file_not_initialized(self):
        from app.services.blob_storage import BlobStorageService

        svc = BlobStorageService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.upload_file("d-1", "f.pdf", b"data")

    @pytest.mark.asyncio
    async def test_download_file(self):
        from app.services.blob_storage import BlobStorageService

        svc = BlobStorageService()
        mock_stream = MagicMock()
        mock_stream.readall.return_value = b"file-content"
        mock_blob_client = MagicMock()
        mock_blob_client.download_blob.return_value = mock_stream

        mock_client = MagicMock()
        mock_client.get_blob_client.return_value = mock_blob_client
        svc._client = mock_client

        result = await svc.download_file("doctor-001", "file.pdf")
        assert result == b"file-content"

    @pytest.mark.asyncio
    async def test_download_file_not_initialized(self):
        from app.services.blob_storage import BlobStorageService

        svc = BlobStorageService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.download_file("d-1", "f.pdf")

    @pytest.mark.asyncio
    async def test_delete_file_success(self):
        from app.services.blob_storage import BlobStorageService

        svc = BlobStorageService()
        mock_blob_client = MagicMock()
        mock_blob_client.delete_blob = MagicMock()

        mock_client = MagicMock()
        mock_client.get_blob_client.return_value = mock_blob_client
        svc._client = mock_client

        result = await svc.delete_file("doctor-001", "file.pdf")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self):
        from app.services.blob_storage import BlobStorageService

        svc = BlobStorageService()
        mock_blob_client = MagicMock()
        mock_blob_client.delete_blob.side_effect = Exception("NotFound")

        mock_client = MagicMock()
        mock_client.get_blob_client.return_value = mock_blob_client
        svc._client = mock_client

        result = await svc.delete_file("doctor-001", "nonexistent.pdf")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_file_not_initialized(self):
        from app.services.blob_storage import BlobStorageService

        svc = BlobStorageService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.delete_file("d-1", "f.pdf")

    @pytest.mark.asyncio
    async def test_list_files(self):
        from app.services.blob_storage import BlobStorageService

        svc = BlobStorageService()
        mock_blob = MagicMock()
        mock_blob.name = "doctor-001/report.pdf"
        mock_blob.size = 1024
        mock_blob.last_modified = datetime.utcnow()

        mock_container = MagicMock()
        mock_container.list_blobs.return_value = [mock_blob]

        mock_client = MagicMock()
        mock_client.get_container_client.return_value = mock_container
        svc._client = mock_client

        result = await svc.list_files("doctor-001")
        assert len(result) == 1
        assert result[0]["name"] == "report.pdf"

    @pytest.mark.asyncio
    async def test_list_files_not_initialized(self):
        from app.services.blob_storage import BlobStorageService

        svc = BlobStorageService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.list_files("d-1")


# ===========================================================================
# GenerationService
# ===========================================================================
class TestGenerationService:
    """Tests for the report generation orchestrator."""

    @pytest.mark.asyncio
    async def test_generate_full_pipeline(self):
        """Full generation pipeline with all dependencies mocked."""
        generated = {
            "findings": "Liver is 14.5 cm.",
            "impressions": "No acute findings.",
            "recommendations": "None.",
        }
        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.openai_service") as mock_openai,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.style_extraction_service") as mock_style,
            patch("app.services.generation.monitoring_service"),
        ):
            mock_cosmos.get_doctor = AsyncMock(return_value={"id": "doctor-001"})
            mock_cosmos.get_style_profile = AsyncMock(return_value=None)
            mock_style.extract_style = AsyncMock(
                return_value=StyleProfile(doctor_id="doctor-001")
            )
            mock_style.build_style_instructions.return_value = "Use standard style."
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            mock_openai.generate_report = AsyncMock(return_value=generated)
            mock_cosmos.create_report = AsyncMock(
                return_value={
                    "id": "rpt-001",
                    "doctor_id": "doctor-001",
                    **generated,
                    "status": "draft",
                    "versions": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            mock_search.index_report = AsyncMock()

            from app.services.generation import GenerationService

            svc = GenerationService()
            result = await svc.generate(
                dictated_text="CT abdomen: Liver 14.5 cm.",
                doctor_id="doctor-001",
                report_type="CT",
                body_region="Abdomen",
            )
            assert result["findings"] == "Liver is 14.5 cm."
            assert "grounding_validation" in result
            mock_cosmos.create_report.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_existing_style_profile(self):
        """When a style profile exists, it should be used directly."""
        existing_profile = {
            "doctor_id": "doctor-001",
            "vocabulary_patterns": ["unremarkable"],
            "abbreviation_map": {},
            "sentence_structure": [],
            "section_ordering": ["findings", "impressions"],
            "sample_phrases": [],
            "updated_at": datetime.utcnow().isoformat(),
        }
        generated = {
            "findings": "Normal.",
            "impressions": "None.",
            "recommendations": "None.",
        }
        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.openai_service") as mock_openai,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.style_extraction_service") as mock_style,
            patch("app.services.generation.monitoring_service"),
        ):
            mock_cosmos.get_doctor = AsyncMock(return_value={"id": "doctor-001"})
            mock_cosmos.get_style_profile = AsyncMock(return_value=existing_profile)
            mock_style.build_style_instructions.return_value = "Use unremarkable."
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            mock_openai.generate_report = AsyncMock(return_value=generated)
            mock_cosmos.create_report = AsyncMock(
                return_value={
                    "id": "rpt-002",
                    "doctor_id": "doctor-001",
                    **generated,
                    "status": "draft",
                    "versions": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            mock_search.index_report = AsyncMock()

            from app.services.generation import GenerationService

            svc = GenerationService()
            result = await svc.generate("Normal findings.", "doctor-001")
            # Style extraction should not be called since profile exists
            mock_style.extract_style.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_index_failure_handled(self):
        """Indexing failure should not fail the pipeline."""
        generated = {
            "findings": "Normal.",
            "impressions": "None.",
            "recommendations": "None.",
        }
        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.openai_service") as mock_openai,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.style_extraction_service") as mock_style,
            patch("app.services.generation.monitoring_service"),
        ):
            mock_cosmos.get_doctor = AsyncMock(return_value={"id": "d-1"})
            mock_cosmos.get_style_profile = AsyncMock(return_value=None)
            mock_style.extract_style = AsyncMock(
                return_value=StyleProfile(doctor_id="d-1")
            )
            mock_style.build_style_instructions.return_value = ""
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            mock_openai.generate_report = AsyncMock(return_value=generated)
            mock_cosmos.create_report = AsyncMock(
                return_value={
                    "id": "rpt-003",
                    "doctor_id": "d-1",
                    **generated,
                    "status": "draft",
                    "versions": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            mock_search.index_report = AsyncMock(side_effect=Exception("Search down"))

            from app.services.generation import GenerationService

            svc = GenerationService()
            # Should not raise even though indexing fails
            result = await svc.generate("Findings.", "d-1")
            assert result["id"] == "rpt-003"

    @pytest.mark.asyncio
    async def test_generate_style_extraction_failure(self):
        """Style extraction failure should fall back to empty profile."""
        generated = {
            "findings": "Normal.",
            "impressions": "None.",
            "recommendations": "None.",
        }
        with (
            patch("app.services.generation.cosmos_service") as mock_cosmos,
            patch("app.services.generation.openai_service") as mock_openai,
            patch("app.services.generation.ai_search_service") as mock_search,
            patch("app.services.generation.style_extraction_service") as mock_style,
            patch("app.services.generation.monitoring_service"),
        ):
            mock_cosmos.get_doctor = AsyncMock(return_value={"id": "d-1"})
            mock_cosmos.get_style_profile = AsyncMock(return_value=None)
            mock_style.extract_style = AsyncMock(side_effect=Exception("OpenAI down"))
            mock_style.build_style_instructions.return_value = ""
            mock_search.search_similar_notes = AsyncMock(return_value=[])
            mock_openai.generate_report = AsyncMock(return_value=generated)
            mock_cosmos.create_report = AsyncMock(
                return_value={
                    "id": "rpt-004",
                    "doctor_id": "d-1",
                    **generated,
                    "status": "draft",
                    "versions": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            mock_search.index_report = AsyncMock()

            from app.services.generation import GenerationService

            svc = GenerationService()
            result = await svc.generate("Findings.", "d-1")
            assert result["id"] == "rpt-004"

    def test_build_grounding_rules(self):
        """Grounding rules should include the input text."""
        from app.services.generation import GenerationService

        svc = GenerationService()
        rules = svc._build_grounding_rules("CT abdomen: Liver 14.5 cm.")
        assert "GROUNDING CONSTRAINTS" in rules
        assert "14.5 cm" in rules


# ===========================================================================
# Note model tests
# ===========================================================================
class TestNoteModels:
    """Tests for note Pydantic models."""

    def test_note_create_validation(self):
        from app.models.note import NoteCreate, SourceType

        note = NoteCreate(content="CT findings here")
        assert note.content == "CT findings here"
        assert note.source_type == SourceType.PASTE
        assert note.file_name is None

    def test_note_create_with_file(self):
        from app.models.note import NoteCreate, SourceType

        note = NoteCreate(content="Content", source_type=SourceType.UPLOAD, file_name="report.pdf")
        assert note.source_type == SourceType.UPLOAD
        assert note.file_name == "report.pdf"

    def test_note_create_empty_content_rejected(self):
        from pydantic import ValidationError

        from app.models.note import NoteCreate

        with pytest.raises(ValidationError):
            NoteCreate(content="")

    def test_note_response_model(self):
        from app.models.note import NoteResponse, SourceType

        resp = NoteResponse(
            id="n-1",
            doctor_id="d-1",
            content="CT findings",
            source_type=SourceType.PASTE,
            created_at=datetime.utcnow(),
        )
        assert resp.id == "n-1"
        assert resp.file_name is None

    def test_source_type_enum(self):
        from app.models.note import SourceType

        assert SourceType.UPLOAD.value == "upload"
        assert SourceType.PASTE.value == "paste"


# ===========================================================================
# OpenAIService
# ===========================================================================
class TestOpenAIService:
    """Tests for OpenAIService prompt building."""

    def test_build_system_prompt(self):
        from app.services.openai_service import OpenAIService

        svc = OpenAIService()
        prompt = svc._build_system_prompt("Use short sentences.", "Keep all numbers.")
        assert "Use short sentences." in prompt
        assert "Keep all numbers." in prompt
        assert "JSON" in prompt

    def test_build_few_shot_messages(self):
        from app.services.openai_service import OpenAIService

        svc = OpenAIService()
        examples = [
            {
                "input_text": "CT abdomen findings.",
                "findings": "Liver normal.",
                "impressions": "None.",
                "recommendations": "None.",
            },
        ]
        messages = svc._build_few_shot_messages(examples)
        assert len(messages) == 2  # user + assistant
        assert "CT abdomen findings." in messages[0]["content"]

    def test_build_few_shot_messages_limits_to_three(self):
        from app.services.openai_service import OpenAIService

        svc = OpenAIService()
        examples = [
            {"input_text": f"Note {i}", "findings": "", "impressions": "", "recommendations": ""}
            for i in range(5)
        ]
        messages = svc._build_few_shot_messages(examples)
        assert len(messages) == 6  # 3 examples × 2 messages each

    @pytest.mark.asyncio
    async def test_generate_report_not_initialized(self):
        from app.services.openai_service import OpenAIService

        svc = OpenAIService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.generate_report("text", "style", "rules")

    @pytest.mark.asyncio
    async def test_analyze_style_not_initialized(self):
        from app.services.openai_service import OpenAIService

        svc = OpenAIService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.analyze_style("notes")

    @pytest.mark.asyncio
    async def test_generate_report_success(self):
        from app.services.openai_service import OpenAIService

        svc = OpenAIService()
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = json.dumps({
            "findings": "Normal.",
            "impressions": "None.",
            "recommendations": "None.",
        })
        response = MagicMock()
        response.choices = [choice]
        mock_client.chat.completions.create.return_value = response
        svc._client = mock_client

        result = await svc.generate_report(
            dictated_text="CT abdomen",
            style_instructions="Standard style.",
            grounding_rules="Keep all numbers.",
            report_type="CT",
            body_region="Abdomen",
        )
        assert result["findings"] == "Normal."
        assert result["impressions"] == "None."

    @pytest.mark.asyncio
    async def test_generate_report_empty_response(self):
        from app.services.openai_service import OpenAIService

        svc = OpenAIService()
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = None
        response = MagicMock()
        response.choices = [choice]
        mock_client.chat.completions.create.return_value = response
        svc._client = mock_client

        with pytest.raises(RuntimeError, match="Empty response"):
            await svc.generate_report("text", "style", "rules")

    @pytest.mark.asyncio
    async def test_generate_report_invalid_json(self):
        from app.services.openai_service import OpenAIService

        svc = OpenAIService()
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = "not valid json"
        response = MagicMock()
        response.choices = [choice]
        mock_client.chat.completions.create.return_value = response
        svc._client = mock_client

        with pytest.raises(RuntimeError, match="Invalid JSON"):
            await svc.generate_report("text", "style", "rules")

    @pytest.mark.asyncio
    async def test_analyze_style_success(self):
        from app.services.openai_service import OpenAIService

        svc = OpenAIService()
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = json.dumps({
            "vocabulary_patterns": ["unremarkable"],
            "abbreviation_map": {},
            "sentence_structure": [],
            "section_ordering": [],
            "sample_phrases": [],
        })
        response = MagicMock()
        response.choices = [choice]
        mock_client.chat.completions.create.return_value = response
        svc._client = mock_client

        result = await svc.analyze_style("Some clinical notes.")
        assert "vocabulary_patterns" in result

    @pytest.mark.asyncio
    async def test_analyze_style_empty_response(self):
        from app.services.openai_service import OpenAIService

        svc = OpenAIService()
        mock_client = MagicMock()
        choice = MagicMock()
        choice.message.content = None
        response = MagicMock()
        response.choices = [choice]
        mock_client.chat.completions.create.return_value = response
        svc._client = mock_client

        with pytest.raises(RuntimeError, match="Empty response"):
            await svc.analyze_style("notes")


# ===========================================================================
# AISearchService
# ===========================================================================
class TestAISearchService:
    """Tests for AISearchService."""

    @pytest.mark.asyncio
    async def test_index_note_not_initialized(self):
        from app.services.ai_search import AISearchService

        svc = AISearchService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.index_note({"id": "n-1"})

    @pytest.mark.asyncio
    async def test_index_note_success(self):
        from app.services.ai_search import AISearchService

        svc = AISearchService()
        svc._search_client = MagicMock()
        svc._search_client.upload_documents = MagicMock()
        svc._generate_embedding = MagicMock(return_value=[0.0] * 1536)
        await svc.index_note({"id": "n-1", "content": "CT findings"})
        svc._search_client.upload_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_report(self):
        from app.services.ai_search import AISearchService

        svc = AISearchService()
        svc._search_client = MagicMock()
        svc._search_client.upload_documents = MagicMock()
        svc._generate_embedding = MagicMock(return_value=[0.0] * 1536)
        report = {
            "id": "r-1",
            "doctor_id": "d-1",
            "input_text": "CT",
            "findings": "Normal.",
            "impressions": "None.",
            "recommendations": "None.",
            "report_type": "CT",
            "body_region": "Abdomen",
            "created_at": datetime.utcnow().isoformat(),
        }
        await svc.index_report(report)
        svc._search_client.upload_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_similar_notes(self):
        from app.services.ai_search import AISearchService

        svc = AISearchService()
        svc._search_client = MagicMock()
        svc._search_client.search.return_value = [
            {
                "id": "n-1",
                "content": "CT findings",
                "findings": "",
                "impressions": "",
                "recommendations": "",
                "report_type": "CT",
                "body_region": "Abdomen",
                "@search.score": 0.95,
                "style_rating": 0,
            }
        ]
        svc._generate_embedding = MagicMock(return_value=[0.0] * 1536)
        result = await svc.search_similar_notes(
            doctor_id="d-1",
            query_text="CT abdomen",
            report_type="CT",
            body_region="Abdomen",
        )
        assert len(result) == 1
        assert result[0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_search_not_initialized(self):
        from app.services.ai_search import AISearchService

        svc = AISearchService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.search_similar_notes("d-1", "query")

    @pytest.mark.asyncio
    async def test_delete_document(self):
        from app.services.ai_search import AISearchService

        svc = AISearchService()
        svc._search_client = MagicMock()
        svc._search_client.delete_documents = MagicMock()
        await svc.delete_document("doc-1")
        svc._search_client.delete_documents.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_document_not_initialized(self):
        from app.services.ai_search import AISearchService

        svc = AISearchService()
        with pytest.raises(RuntimeError, match="not initialized"):
            await svc.delete_document("doc-1")
