"""T23 – Integration test: upload → parse → extract style → store pipeline."""

import io
import json
from datetime import datetime

import pytest
from docx import Document as DocxDocument

from app.models.style_profile import StyleProfile
from app.utils.file_parser import extract_text


@pytest.mark.asyncio
async def test_upload_parse_extract_style_store(
    cosmos_client, blob_client, openai_client, sample_doctor, sample_notes
):
    """
    Full pipeline test:
    1. Upload a file to blob storage
    2. Parse the file to extract text
    3. Use OpenAI to extract a writing‑style profile
    4. Store the style profile in Cosmos DB
    """
    db = cosmos_client.get_database_client("impressions_generator")
    doctors = db.get_container_client("doctors")
    notes_container = db.get_container_client("notes")
    styles_container = db.get_container_client("style-profiles")

    # Step 0 – seed doctor
    await doctors.create_item(sample_doctor)

    # Step 1 – simulate file upload (DOCX)
    doc = DocxDocument()
    doc.add_paragraph(
        "CT Abdomen: Liver measures 15.2 cm. Unremarkable. "
        "No acute abnormality. Recommend follow-up in 6 months."
    )
    buf = io.BytesIO()
    doc.save(buf)
    file_bytes = buf.getvalue()

    container_client = blob_client.get_container_client("doctor-notes")
    blob = container_client.get_blob_client("doctor-int-001/note-upload.docx")
    await blob.upload_blob(file_bytes)

    # Step 2 – parse file
    extracted = extract_text("note-upload.docx", file_bytes)
    assert "15.2 cm" in extracted
    assert "Unremarkable" in extracted

    # Store note
    note_doc = {
        "id": "note-upload-001",
        "doctor_id": "doctor-int-001",
        "content": extracted,
        "source_type": "upload",
        "file_name": "note-upload.docx",
        "created_at": datetime.utcnow().isoformat(),
    }
    await notes_container.create_item(note_doc)

    # Also store pasted notes
    for note in sample_notes:
        await notes_container.create_item(note)

    # Step 3 – extract style via OpenAI
    all_notes = notes_container.query_items(
        query="SELECT * FROM c WHERE c.doctor_id = @did",
        parameters=[{"name": "@did", "value": "doctor-int-001"}],
    )
    combined_text = "\n---\n".join(n["content"] for n in all_notes)

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Extract the writing style from these notes."},
            {"role": "user", "content": combined_text},
        ],
    )
    raw_profile = json.loads(response.choices[0].message.content)

    profile = StyleProfile(doctor_id="doctor-int-001", **raw_profile)
    assert len(profile.vocabulary_patterns) > 0

    # Step 4 – store style profile
    profile_doc = {
        "id": "doctor-int-001",
        **profile.model_dump(mode="json"),
    }
    await styles_container.upsert_item(profile_doc)

    # Verify retrieval
    stored = await styles_container.read_item(
        item="doctor-int-001", partition_key="doctor-int-001"
    )
    assert stored["doctor_id"] == "doctor-int-001"
    assert len(stored["vocabulary_patterns"]) > 0


@pytest.mark.asyncio
async def test_upload_multiple_files_builds_richer_profile(
    cosmos_client, blob_client, openai_client, sample_doctor
):
    """Uploading multiple files should produce a style profile."""
    db = cosmos_client.get_database_client("impressions_generator")
    doctors = db.get_container_client("doctors")
    notes_container = db.get_container_client("notes")
    styles_container = db.get_container_client("style-profiles")

    await doctors.create_item(sample_doctor)

    texts = [
        "CT Chest: Lungs clear. No effusion. Heart normal size.",
        "MRI Brain: No acute intracranial process. Ventricles normal.",
        "CT Abdomen: Liver unremarkable. Kidneys within normal limits.",
    ]

    for i, text in enumerate(texts):
        content = text.encode("utf-8")
        await notes_container.create_item({
            "id": f"note-multi-{i}",
            "doctor_id": "doctor-int-001",
            "content": extract_text(f"note{i}.txt", content),
            "source_type": "upload",
            "file_name": f"note{i}.txt",
            "created_at": datetime.utcnow().isoformat(),
        })

    all_notes = notes_container.query_items(query="SELECT * FROM c")
    combined = "\n---\n".join(n["content"] for n in all_notes)

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Extract writing style from these notes."},
            {"role": "user", "content": combined},
        ],
    )
    raw = json.loads(response.choices[0].message.content)
    profile = StyleProfile(doctor_id="doctor-int-001", **raw)

    profile_doc = {"id": "doctor-int-001", **profile.model_dump(mode="json")}
    await styles_container.upsert_item(profile_doc)

    stored = await styles_container.read_item(
        item="doctor-int-001", partition_key="doctor-int-001"
    )
    assert stored["doctor_id"] == "doctor-int-001"
